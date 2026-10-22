import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import stratagent
from stratagent.common import StratagentError, canonical, identity
from stratagent.demo import sample_snapshot
from stratagent.lifecycle import JOURNAL, MAX_BYTES, Transactions, encoded, validate_lock
from stratagent.mcp import Server
from stratagent.service import LOCK, MANIFEST, POLICY, Stratagent
from test_architect import FakeRegistry
from test_runtime_research import PROMPT, model_plan
from test_stratagent import FakeGitHub
from process_support import wait_ready

LARGE = "Build a React frontend, Python API and PostgreSQL database with privacy and testing. No payments."
SMALL = "Small Python API with privacy and testing. No payments or frontend."


class LifecycleCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.service = Stratagent(self.root)
        self.service.init(LARGE, ["generic"])

    def install(self):
        stage = self.service.stage("blueprint")
        self.service.apply_stage(stage["stage_id"], stage["plan"]["approval"])
        return stage

    def revise(self):
        plan = self.service.revise(SMALL)
        self.service.revise(SMALL, approval=plan["approval"], apply=True)

    def managed(self):
        return {output["path"]: (self.service.ws.path(output["path"]).read_bytes(), self.service.ws.fs.mode(self.service.ws.path(output["path"]).stat()))
                for installation in self.service.lock()["installations"].values() for output in installation["outputs"]}

    def apply(self, stage):
        return self.service.apply_stage(stage["stage_id"], stage["plan"]["approval"])


class LifecycleTests(LifecycleCase):
    def test_stage_is_inert_and_default_mcp_has_no_lifecycle_authority(self):
        (self.root / ".mcp.json").write_text('{"user":true}\n')
        before = self.service.ws.path(LOCK).read_bytes()
        stage = self.service.stage("blueprint")
        self.assertEqual(self.service.ws.path(LOCK).read_bytes(), before)
        self.assertFalse(self.service.ws.path(".stratagent/blueprint.json").exists())
        self.assertTrue(stage["diff"])
        self.assertEqual(len(Server(self.root).tools), 13)
        self.assertFalse(any(tool["name"] in ("stratagent_apply", "stratagent_recover", "stratagent_revise") for tool in Server(self.root).tools))
        with self.assertRaisesRegex(StratagentError, "Approval"):
            self.service.apply_stage(stage["stage_id"], "yes")
        self.apply(stage)
        self.assertEqual((self.root / ".mcp.json").read_text(), '{"user":true}\n')

    def test_legacy_migration_is_reviewed_and_reads_do_not_write(self):
        self.assertEqual(self.service.lock()["schema_version"], 1)
        before = self.service.ws.path(LOCK).read_bytes()
        stage = self.service.stage("blueprint")
        self.assertEqual(stage["plan"]["lifecycle"]["lock_migration"], {"from": 1, "to": 2})
        self.assertEqual(before, self.service.ws.path(LOCK).read_bytes())
        self.apply(stage)
        lock = self.service.lock()
        self.assertEqual(lock["schema_version"], 2)
        self.assertEqual(lock["revision"], 1)
        self.assertEqual(set(lock["owners"].values()), {"workspace-blueprint"})
        self.assertTrue(self.service.verify()["ok"])

    def test_revision_keeps_installed_files_until_reviewed_blueprint_update(self):
        self.install()
        before = self.managed()
        self.revise()
        self.assertEqual(before, self.managed())
        self.assertEqual(self.service.manifest()["analysis"]["prompt"], SMALL)
        self.assertFalse(self.service.status()["approved_blueprint"]["context_current"])
        stage = self.service.stage("blueprint")
        changes = stage["plan"]["lifecycle"]["changes"]
        self.assertTrue(any(entry["action"] == "delete" for entry in changes))
        self.assertTrue(any(entry["action"] == "replace" for entry in changes))
        self.apply(stage)
        self.assertTrue(self.service.verify()["ok"])
        self.assertTrue(self.service.status()["approved_blueprint"]["context_current"])
        for entry in changes:
            if entry["action"] == "delete":
                self.assertFalse(self.service.ws.path(entry["path"]).exists())

    def test_retarget_removes_only_owned_outputs(self):
        self.install()
        user = self.root / ".agents/skills/user-owned/SKILL.md"
        user.parent.mkdir(parents=True)
        user.write_text("user-authored\n")
        plan = self.service.revise(LARGE, ["claude", "codex", "antigravity"])
        self.service.revise(LARGE, ["claude", "codex", "antigravity"], plan["approval"], True)
        self.apply(self.service.stage("blueprint"))
        self.assertEqual(user.read_text(), "user-authored\n")
        self.assertFalse(any(path.startswith(".stratagent/portable/") for path in self.service.lock()["owners"]))
        self.assertTrue(any(path.startswith(".claude/agents/") for path in self.service.lock()["owners"]))
        self.assertTrue(any(path.startswith(".agents/agents/") for path in self.service.lock()["owners"]))

    def test_repeated_stage_and_direct_apply_are_noops(self):
        stage = self.install()
        before = self.service.ws.path(LOCK).read_bytes()
        self.assertTrue(self.apply(stage)["already_installed"])
        self.assertTrue(self.service.blueprint(approval=stage["plan"]["approval"], apply=True)["already_installed"])
        fresh = self.service.blueprint()
        self.assertTrue(self.service.blueprint(approval=fresh["approval"], apply=True)["already_installed"])
        self.assertEqual(before, self.service.ws.path(LOCK).read_bytes())

    def test_removal_is_reviewed_idempotent_and_preserves_user_files(self):
        self.install()
        user = self.root / ".stratagent/portable/skills/user-owned/SKILL.md"
        user.parent.mkdir()
        user.write_text("keep")
        stage = self.service.stage("remove", key="workspace-blueprint")
        self.assertTrue(all(entry["action"] == "delete" for entry in stage["plan"]["lifecycle"]["changes"]))
        self.apply(stage)
        self.assertFalse(self.service.lock()["installations"])
        self.assertTrue(self.apply(stage)["already_installed"])
        self.assertEqual(user.read_text(), "keep")
        preview = self.service.remove("workspace-blueprint")
        self.assertTrue(self.service.remove("workspace-blueprint", preview["approval"], True)["already_removed"])

    def test_direct_removal_and_revision_receipts_are_idempotent(self):
        self.install()
        revision = self.service.revise(SMALL)
        self.service.revise(SMALL, approval=revision["approval"], apply=True)
        self.assertTrue(self.service.revise(SMALL, approval=revision["approval"], apply=True)["already_applied"])
        plan = self.service.remove("workspace-blueprint")
        self.service.remove("workspace-blueprint", plan["approval"], True)
        self.assertTrue(self.service.remove("workspace-blueprint", plan["approval"], True)["already_applied"])

    def test_stages_are_bound_to_policy_context_lock_and_generator(self):
        for mutation in ("policy", "manifest", "lock", "project", "generator"):
            with self.subTest(mutation=mutation):
                stage = self.service.stage("blueprint")
                if mutation == "policy":
                    self.service.allow("example/reviewed")
                elif mutation == "manifest":
                    value = self.service.manifest()
                    value["platforms"] = ["claude"]
                    self.service.ws.write(MANIFEST, value)
                elif mutation == "lock":
                    value = self.service.lock()
                    value["generator_version"] = "previous"
                    self.service.ws.write(LOCK, value)
                elif mutation == "project":
                    (self.root / "requirements.txt").write_text("fastapi\n")
                else:
                    with patch("stratagent.service.__version__", "next"):
                        with self.assertRaisesRegex(StratagentError, "stale"):
                            self.apply(stage)
                    continue
                with self.assertRaisesRegex(StratagentError, "stale"):
                    self.apply(stage)
                self.assertFalse(self.service.lock()["installations"])

    def test_unrelated_operation_invalidates_other_stages(self):
        first = self.service.stage("blueprint")
        second = self.service.stage("revise", prompt=SMALL)
        self.apply(second)
        with self.assertRaisesRegex(StratagentError, "stale"):
            self.apply(first)

    def test_existing_identical_user_file_is_not_adopted(self):
        plan, files = self.service.preview_blueprint()
        relative, data = next(iter(files.items()))
        target = self.service.ws.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        with self.assertRaisesRegex(StratagentError, "blockers"):
            self.service.stage("blueprint")
        self.assertEqual(target.read_bytes(), data)

    def test_user_drift_and_permissions_refuse_updates_and_removal(self):
        self.install()
        relative = next(iter(self.managed()))
        target = self.service.ws.path(relative)
        original = target.read_bytes()
        target.write_bytes(b"user edits")
        for kind in ("blueprint", "remove"):
            with self.assertRaises(StratagentError):
                self.service.stage(kind, **({"key": "workspace-blueprint"} if kind == "remove" else {}))
        self.assertEqual(target.read_bytes(), b"user edits")
        target.write_bytes(original)
        target.chmod(0o444 if os.name == "nt" else 0o600)
        self.assertFalse(self.service.verify()["ok"])
        with self.assertRaises(StratagentError):
            self.service.stage("remove", key="workspace-blueprint")
        target.chmod(0o644)

    def test_separately_installed_resource_in_use_cannot_be_removed(self):
        candidate = self.service.import_snapshot(sample_snapshot())
        self.service.allow(candidate["repo"])
        self.apply(self.service.stage("install", candidate_id=candidate["id"]))
        self.apply(self.service.stage("configure"))
        plan = self.service.remove("candidate:" + candidate["id"])
        self.assertTrue(any(entry["rule"] == "resource-in-use" for entry in plan["lifecycle"]["blockers"]))
        with self.assertRaises(StratagentError):
            self.service.stage("remove", key="candidate:" + candidate["id"])
        self.apply(self.service.stage("remove", key="task-configuration"))
        self.apply(self.service.stage("remove", key="candidate:" + candidate["id"]))

    def test_standalone_and_blueprint_ownership_cannot_silently_overlap(self):
        self.install()
        with self.assertRaises(StratagentError):
            self.service.stage("configure")
        lock = self.service.lock()
        lock["installations"]["copy"] = copy.deepcopy(lock["installations"]["workspace-blueprint"])
        with self.assertRaisesRegex(StratagentError, "ownership"):
            validate_lock(lock)

    def test_lock_schema_migration_rejects_unsafe_versions_and_paths(self):
        for value in ({"schema_version": True, "installations": {}}, {"schema_version": 2, "installations": {}},
                      {"schema_version": 3, "installations": {}},
                      {"schema_version": 1, "installations": {"bad": {"outputs": [{"path": ".codex/config.toml", "size": 0, "sha256": "f" * 64}]}}}):
            with self.subTest(value=value), self.assertRaises(StratagentError):
                validate_lock(value)

    def test_transaction_bounds_are_checked_before_journaling(self):
        with self.assertRaisesRegex(StratagentError, "4 MiB"):
            encoded(b"x" * (MAX_BYTES + 1), 0o600)
        legacy = {"schema_version": 1, "installations": {"workspace-blueprint": {"outputs": [
            {"path": f".stratagent/portable/skills/role-{index}/SKILL.md", "size": 0, "sha256": "f" * 64} for index in range(600)]}}}
        self.service.ws.write(LOCK, legacy)
        with self.assertRaisesRegex(StratagentError, "limit"):
            Transactions(self.service.ws).preview("workspace-blueprint", {".stratagent/blueprint.json": b"{}"}, {})
        self.assertFalse(self.service.ws.path(JOURNAL).exists())

    def test_initialization_never_overwrites_partial_existing_ownership_or_policy(self):
        self.install()
        lock, policy, before = self.service.ws.path(LOCK).read_bytes(), self.service.ws.path(POLICY).read_bytes(), self.managed()
        self.service.ws.path(MANIFEST).unlink()
        with self.assertRaisesRegex(StratagentError, "partial state"):
            self.service.init(SMALL, ["generic"])
        self.assertEqual(lock, self.service.ws.path(LOCK).read_bytes())
        self.assertEqual(policy, self.service.ws.path(POLICY).read_bytes())
        for relative, (data, mode) in before.items():
            self.assertEqual(self.service.ws.path(relative).read_bytes(), data)

    def test_journal_and_archive_failures_leave_managed_state_untouched(self):
        self.install()
        self.revise()
        before, lock = self.managed(), self.service.ws.path(LOCK).read_bytes()
        for location in ("journal", "archive"):
            with self.subTest(location=location):
                stage = self.service.stage("blueprint")
                original = self.service.ws.write
                def fail(relative, value):
                    if (location == "journal" and relative == JOURNAL) or (location == "archive" and relative.startswith(".stratagent/transactions/")):
                        raise OSError("injected metadata failure")
                    return original(relative, value)
                with patch.object(self.service.ws, "write", side_effect=fail):
                    with self.assertRaises(OSError):
                        self.apply(stage)
                self.assertEqual(before, self.managed())
                self.assertEqual(lock, self.service.ws.path(LOCK).read_bytes())
                self.assertFalse(self.service.recover()["pending"])

    def test_changed_stage_or_foreign_workspace_refuses(self):
        stage = self.service.stage("blueprint")
        relative = f".stratagent/stages/{stage['stage_id']}.json"
        record = self.service.ws.read(relative)
        record["workspace"] = "/different"
        record["digest"] = identity({key: value for key, value in record.items() if key != "digest"})
        self.service.ws.write(relative, record)
        with self.assertRaisesRegex(StratagentError, "foreign"):
            self.apply(stage)
        with self.assertRaises(StratagentError):
            self.service.apply_stage("../escape", "yes")

    def test_staged_cache_is_reinspected_not_blindly_replayed(self):
        candidate = self.service.import_snapshot(sample_snapshot())
        self.service.allow(candidate["repo"])
        stage = self.service.stage("install", candidate_id=candidate["id"])
        relative = f".stratagent/cache/{candidate['review_digest']}.json"
        snapshot = self.service.ws.read(relative)
        snapshot["commit"] = "e" * 40
        self.service.ws.write(relative, snapshot)
        with self.assertRaisesRegex(StratagentError, "changed"):
            self.apply(stage)

    def test_staged_runtime_research_is_rechecked_for_expiry(self):
        other = self.root / "live-workspace"
        other.mkdir()
        client = FakeGitHub()
        service = Stratagent(other, github=client, registry=FakeRegistry())
        proposal = model_plan(service, mcp=False, targets=["generic"])
        review = service.preview_research(proposal, PROMPT, ["generic"])
        prepared = service.prepare(PROMPT, ["generic"], research_plan=proposal, approve_search=review["search_approval"])
        service.allow(client.snap["repo"])
        stage = service.stage("blueprint", run_id=prepared["research_run"]["id"])
        with patch("stratagent.sessions.time.time", return_value=prepared["research_run"]["expires_at"] + 1):
            with self.assertRaisesRegex(StratagentError, "expired"):
                service.apply_stage(stage["stage_id"], stage["plan"]["approval"])
        self.assertFalse(service.lock()["installations"])

    def test_existing_v1_installation_migrates_without_adopting_unowned_files(self):
        self.install()
        legacy = self.service.lock()
        legacy["schema_version"] = 1
        legacy.pop("owners")
        legacy.pop("revision")
        for installation in legacy["installations"].values():
            for output in installation["outputs"]:
                output.pop("mode")
        self.service.ws.write(LOCK, legacy)
        before = self.managed()
        self.revise()
        self.assertEqual(before, self.managed())
        self.assertEqual(self.service.lock()["schema_version"], 2)
        self.assertTrue(all("mode" in output for installation in self.service.lock()["installations"].values() for output in installation["outputs"]))

    def test_faults_before_commit_restore_exact_outputs_lock_and_modes(self):
        self.install()
        self.revise()
        before, lock = self.managed(), self.service.ws.path(LOCK).read_bytes()
        stage = self.service.stage("blueprint")
        events = ["prepared", "writing"] + [f"output:{index}" for index in range(sum(entry["action"] != "unchanged" for entry in stage["plan"]["lifecycle"]["changes"]))]
        for event in events:
            with self.subTest(event=event):
                current = self.service.stage("blueprint")
                def fail(checkpoint):
                    if checkpoint == event:
                        raise OSError("injected transaction fault")
                with patch.object(Transactions, "checkpoint", side_effect=fail):
                    with self.assertRaises(OSError):
                        self.apply(current)
                self.assertEqual(self.managed(), before)
                self.assertEqual(self.service.ws.path(LOCK).read_bytes(), lock)
                self.assertFalse(self.service.recover()["pending"])
                self.assertTrue(self.service.verify()["ok"])

    def test_lock_replace_failure_rolls_back_an_update(self):
        self.install()
        self.revise()
        before, lock = self.managed(), self.service.ws.path(LOCK).read_bytes()
        stage = self.service.stage("blueprint")
        replace = os.replace
        def fail_once(source, destination):
            if Path(destination).as_posix().endswith(LOCK):
                raise OSError("lock replace failure")
            return replace(source, destination)
        with patch("stratagent.workspace.os.replace", side_effect=fail_once):
            with self.assertRaises(OSError):
                self.apply(stage)
        self.assertEqual(self.managed(), before)
        self.assertEqual(self.service.ws.path(LOCK).read_bytes(), lock)

    def test_exception_after_commit_requires_finalize_not_rollback(self):
        stage = self.service.stage("blueprint")
        def fail(checkpoint):
            if checkpoint == "lock-committed":
                raise OSError("receipt write failure")
        with patch.object(Transactions, "checkpoint", side_effect=fail):
            with self.assertRaises(OSError):
                self.apply(stage)
        recovery = self.service.recover()
        self.assertEqual(recovery["action"], "finalize")
        self.service.recover(recovery["approval"], True)
        self.assertTrue(self.service.verify()["ok"])
        self.assertTrue(self.apply(stage)["already_installed"])

    def test_history_is_content_free_and_contains_terminal_backups(self):
        self.install()
        self.revise()
        history = Transactions(self.service.ws).history()
        self.assertEqual(len(history["transactions"]), 2)
        self.assertNotIn(LARGE, json.dumps(history))
        self.assertNotIn("entries", json.dumps(history))

    def test_concurrent_mutation_refuses_staging_and_apply(self):
        stage = self.service.stage("blueprint")
        with self.service.ws.mutation():
            with self.assertRaisesRegex(StratagentError, "Another write"):
                self.apply(stage)
            with self.assertRaisesRegex(StratagentError, "Another write"):
                self.service.stage("blueprint")

    def test_failed_rollback_retains_journal_and_blocks_other_writes(self):
        self.install()
        self.revise()
        before, lock = self.managed(), self.service.ws.path(LOCK).read_bytes()
        stage = self.service.stage("blueprint")
        def fail(checkpoint):
            if checkpoint in ("output:1", "rollback:0"):
                raise OSError("injected rollback fault")
        with patch.object(Transactions, "checkpoint", side_effect=fail):
            with self.assertRaisesRegex(StratagentError, "rollback could not finish"):
                self.apply(stage)
        self.assertFalse(self.service.verify()["ok"])
        with self.assertRaisesRegex(StratagentError, "recovery"):
            self.service.allow("example/blocked")
        recovery = self.service.recover()
        self.service.recover(recovery["approval"], True)
        self.assertEqual(before, self.managed())
        self.assertEqual(lock, self.service.ws.path(LOCK).read_bytes())

    def test_cli_lifecycle_and_structured_events(self):
        script = Path(__file__).resolve().parents[1] / "scripts/validate_lifecycle.py"
        environment = {**os.environ, "PYTHONPATH": str(Path(stratagent.__file__).resolve().parent.parent)}
        process = subprocess.run([sys.executable, str(script)], env=environment, capture_output=True, text=True, timeout=60)
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["preserved_user_files"], 4)
        self.assertEqual(result["transactions"], 4)
        self.assertGreater(result["obsolete_outputs_removed"], 0)
        process = subprocess.run([sys.executable, "-m", "stratagent", "stage", "revise", "--workspace", str(self.root), "--prompt", SMALL, "--log-json"],
                                 env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertNotIn(SMALL, process.stderr)
        self.assertEqual([json.loads(line)["event"] for line in process.stderr.splitlines()], ["command.started", "command.completed"])

    def test_cli_rejects_mismatched_stage_options(self):
        from stratagent.cli import main
        import io
        with patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(main(["stage", "configure", "--workspace", str(self.root), "--prompt", SMALL]), 2)
            self.assertEqual(main(["stage", "install", "--workspace", str(self.root)]), 2)
            self.assertEqual(main(["recover", "--workspace", str(self.root), "--approve", "yes"]), 2)

    def test_unknown_filesystem_backend_is_explicitly_unsupported(self):
        stage = self.service.stage("blueprint")
        lock = self.service.lock()
        with patch.object(self.service.ws.fs, "platform", "unsupported"):
            with self.assertRaisesRegex(StratagentError, "Unsupported filesystem"):
                Transactions(self.service.ws).execute(stage["plan"], {}, "workspace-blueprint", lock)


class ProcessRecoveryTests(LifecycleCase):
    def worker(self, stage, event, recover=False, kill=True):
        environment = {**os.environ, "PYTHONPATH": str(Path(stratagent.__file__).resolve().parent.parent)}
        code = '''
import sys, time
from stratagent.lifecycle import Transactions
from stratagent.service import Stratagent
from stratagent.workspace import Workspace
service = Stratagent(sys.argv[1])
def pause(self, event):
    if event == sys.argv[4]:
        print("ready", flush=True)
        time.sleep(60)
Transactions.checkpoint = pause
def io_pause(self, relative, event):
    if relative == sys.argv[6] and event == sys.argv[4]:
        print("ready", flush=True)
        time.sleep(60)
Workspace.checkpoint = io_pause
if sys.argv[5] == "recover":
    review = service.recover()
    service.recover(review["approval"], True)
else:
    service.apply_stage(sys.argv[2], sys.argv[3])
'''
        first_path = next(entry["path"] for entry in stage["plan"]["lifecycle"]["changes"] if entry["action"] != "unchanged")
        process = subprocess.Popen([sys.executable, "-c", code, str(self.root), stage["stage_id"], stage["plan"]["approval"], event, "recover" if recover else "apply", first_path],
                                   env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
            process.stdout.close()
            process.stderr.close()
        self.addCleanup(cleanup)
        wait_ready(self, process)
        if kill:
            process.kill()
            process.wait(timeout=10)
        return process

    def test_sigkill_at_every_update_boundary_recovers_exact_original_or_commits(self):
        self.install()
        self.revise()
        before, lock = self.managed(), self.service.ws.path(LOCK).read_bytes()
        stage = self.service.stage("blueprint")
        count = sum(entry["action"] != "unchanged" for entry in stage["plan"]["lifecycle"]["changes"])
        events = ["prepared", "writing", *(f"output:{index}" for index in range(count)), "lock-committed", "committed"]
        for event in events:
            with self.subTest(event=event):
                stage = self.service.stage("blueprint")
                self.worker(stage, event)
                recovery = self.service.recover()
                if event == "committed":
                    self.assertFalse(recovery["pending"])
                else:
                    self.assertTrue(recovery["pending"])
                    with self.assertRaisesRegex(StratagentError, "recovery"):
                        self.service.allow("example/blocked")
                    self.service.recover(recovery["approval"], True)
                self.assertTrue(self.service.verify()["ok"])
                self.assertFalse(list(self.root.rglob(".stratagent-*.tmp")))
                if event not in ("lock-committed", "committed"):
                    self.assertEqual(before, self.managed())
                    self.assertEqual(lock, self.service.ws.path(LOCK).read_bytes())
                else:
                    self.assertTrue(self.apply(stage)["already_installed"])
                    if event == "lock-committed":
                        self.service.remove("workspace-blueprint", self.service.remove("workspace-blueprint")["approval"], True)
                        self.service.revise(LARGE, approval=self.service.revise(LARGE)["approval"], apply=True)
                        self.install()
                        self.revise()
                        before, lock = self.managed(), self.service.ws.path(LOCK).read_bytes()

    def test_killed_initial_install_restores_legacy_lock_and_removes_created_directories(self):
        lock = self.service.ws.path(LOCK).read_bytes()
        stage = self.service.stage("blueprint")
        self.worker(stage, "output:0")
        review = self.service.recover()
        self.assertEqual(review["action"], "rollback")
        self.service.recover(review["approval"], True)
        self.assertEqual(lock, self.service.ws.path(LOCK).read_bytes())
        self.assertFalse(self.service.ws.path(".stratagent/portable").exists())

    def test_recovery_preserves_external_edits_and_stale_approval_refuses(self):
        stage = self.service.stage("blueprint")
        self.worker(stage, "output:0")
        review = self.service.recover()
        journal = self.service.ws.read(JOURNAL)
        changed = journal["entries"][0]["path"]
        self.service.ws.path(changed).write_text("user changed after interruption")
        conflict = self.service.recover()
        self.assertIn(changed, conflict["conflicts"])
        with self.assertRaisesRegex(StratagentError, "stale"):
            self.service.recover(review["approval"], True)
        self.assertEqual(self.service.ws.path(changed).read_text(), "user changed after interruption")

    def test_sigkill_during_rollback_can_be_recovered_again(self):
        self.install()
        self.revise()
        before, lock = self.managed(), self.service.ws.path(LOCK).read_bytes()
        stage = self.service.stage("blueprint")
        self.worker(stage, "output:2")
        self.worker(stage, "rollback:0", recover=True)
        review = self.service.recover()
        self.assertEqual(review["action"], "rollback")
        self.service.recover(review["approval"], True)
        self.assertEqual(before, self.managed())
        self.assertEqual(lock, self.service.ws.path(LOCK).read_bytes())

    def test_sigkill_revision_recovers_original_manifest_and_lock(self):
        self.install()
        manifest = self.service.ws.path(MANIFEST).read_bytes()
        lock = self.service.ws.path(LOCK).read_bytes()
        stage = self.service.stage("revise", prompt=SMALL)
        self.worker(stage, "output:0")
        review = self.service.recover()
        self.service.recover(review["approval"], True)
        self.assertEqual(manifest, self.service.ws.path(MANIFEST).read_bytes())
        self.assertEqual(lock, self.service.ws.path(LOCK).read_bytes())

    def test_sigkill_inside_atomic_write_cleans_known_temporary_files(self):
        for event in ("temporary-written", "temporary-synced", "replaced"):
            with self.subTest(event=event):
                lock = self.service.ws.path(LOCK).read_bytes()
                stage = self.service.stage("blueprint")
                self.worker(stage, event)
                review = self.service.recover()
                self.service.recover(review["approval"], True)
                self.assertEqual(lock, self.service.ws.path(LOCK).read_bytes())
                self.assertFalse(list(self.root.rglob(".stratagent-*.tmp")))
                self.assertFalse(self.service.ws.path(".stratagent/portable").exists())

    def test_user_modified_transaction_temporary_is_preserved(self):
        stage = self.service.stage("blueprint")
        self.worker(stage, "temporary-written")
        journal = self.service.ws.read(JOURNAL)
        relative = journal["entries"][0]["temporary"]
        self.service.ws.path(relative).write_text("user modified temporary")
        review = self.service.recover()
        self.assertIn(relative, review["conflicts"])
        with self.assertRaises(StratagentError):
            self.service.recover(review["approval"], True)
        self.assertEqual(self.service.ws.path(relative).read_text(), "user modified temporary")

    def test_live_process_blocks_other_workspace_writers(self):
        stage = self.service.stage("blueprint")
        process = self.worker(stage, "prepared", kill=False)
        with self.assertRaisesRegex(StratagentError, "Another write"):
            self.service.stage("blueprint")
        with self.assertRaisesRegex(StratagentError, "Another write"):
            self.service.recover("0" * 64, True)
        process.kill()
        process.wait(timeout=10)
        review = self.service.recover()
        self.service.recover(review["approval"], True)

    def test_killed_removal_recovers_deleted_managed_files(self):
        self.install()
        before, lock = self.managed(), self.service.ws.path(LOCK).read_bytes()
        stage = self.service.stage("remove", key="workspace-blueprint")
        self.worker(stage, "output:0")
        review = self.service.recover()
        self.service.recover(review["approval"], True)
        self.assertEqual(before, self.managed())
        self.assertEqual(lock, self.service.ws.path(LOCK).read_bytes())

    def test_committed_lock_with_external_output_edit_cannot_finalize(self):
        stage = self.service.stage("blueprint")
        self.worker(stage, "lock-committed")
        relative = self.service.ws.read(JOURNAL)["entries"][0]["path"]
        self.service.ws.path(relative).write_text("user edited after commit")
        review = self.service.recover()
        self.assertIn(LOCK, review["conflicts"])
        with self.assertRaises(StratagentError):
            self.service.recover(review["approval"], True)
        self.assertEqual(self.service.ws.path(relative).read_text(), "user edited after commit")
