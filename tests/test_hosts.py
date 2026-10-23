import json
import os
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
from types import MappingProxyType
import unittest
from unittest.mock import patch

from stratagent.adapters import render_bundle, render_tasks
from stratagent.common import StratagentError, canonical
from stratagent.demo import sample_snapshot
from stratagent.hosts import ADAPTERS, HostAdapter, catalog, contracts, platforms
from stratagent.planner import analyze
from stratagent.registry import assess_server, render_server
from stratagent.security import assess, metadata, unpack
from stratagent.service import LOCK, MANIFEST, Stratagent
from test_stratagent import replace_file


class HostContractTests(unittest.TestCase):
    def test_catalog_distinguishes_native_roles_portable_skills_and_mcp(self):
        entries = {entry["id"]: entry for entry in catalog()["platforms"]}
        self.assertEqual(set(entries), {"claude", "codex", "antigravity", "generic"})
        self.assertEqual(entries["codex"]["role_format"], "portable-skill")
        self.assertEqual(entries["antigravity"]["role_format"], "native-agent")
        self.assertFalse(entries["generic"]["mcp_proposals"])
        self.assertTrue(all(not entry["automatic_execution"] for entry in entries.values()))

    def test_new_trusted_adapter_renders_skills_roles_and_mcp_without_core_changes(self):
        def proposal(name, selected):
            return "example.json", canonical({"name": name, "transport": selected, "activation": "manual-only"})

        adapter = HostAdapter("example", ".example/skills", ".example/agents", "tools: [inspect]\n", proposal)
        snapshot = sample_snapshot()
        review = assess(snapshot)
        server = assess_server({"server": {"name": "io.github.example/tools", "version": "1.0.0", "description": "Original test metadata",
                                           "remotes": [{"type": "streamable-http", "url": "https://mcp.example.com/mcp"}]},
                                "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active"}}})
        with patch("stratagent.hosts.ADAPTERS", MappingProxyType({**ADAPTERS, "example": adapter})):
            self.assertIn(".example/skills/python-review/SKILL.md", render_bundle(review, unpack(snapshot), ["example"]))
            roles = render_tasks({"analysis": analyze("Python API")}, ["example"])
            self.assertIn(".example/agents/sa-architect.md", roles)
            self.assertIn(b"tools: [inspect]", roles[".example/agents/sa-architect.md"])
            self.assertTrue(any(path.endswith("/example.json") for path in render_server(server, 0, ["example"])))

    def test_conflicting_adapter_output_is_refused_instead_of_overwritten(self):
        adapters = {"first": HostAdapter("first", ".shared/skills", ".shared/agents", "tools: [inspect]\n"),
                    "second": HostAdapter("second", ".shared/skills", ".shared/agents", "tools: [different]\n")}
        with patch("stratagent.hosts.ADAPTERS", MappingProxyType(adapters)):
            with self.assertRaisesRegex(StratagentError, "conflicting content"):
                render_tasks({"analysis": analyze("Python API")}, ["first", "second"])

    def test_invalid_or_unknown_targets_fail_explicitly(self):
        for targets in (None, [], [None], [["codex"]], ["unknown-editor"], "codex"):
            with self.subTest(targets=targets), self.assertRaisesRegex(StratagentError, "Platforms"):
                platforms(targets)


class VersionedHostContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.service = Stratagent(self.root)
        self.service.init("Small Python API without payments", ["codex"], scan_project=False)

    def changed_adapter(self, target="codex", **changes):
        return patch("stratagent.hosts.ADAPTERS", MappingProxyType({
            **ADAPTERS, target: replace(ADAPTERS[target], **changes)}))

    def test_contracts_distinguish_export_behavior_from_runtime_certification(self):
        entries = {item["id"]: item for item in contracts(list(ADAPTERS))}
        for item in entries.values():
            self.assertEqual(item["contract_schema_version"], 1)
            self.assertEqual(item["adapter_version"], ADAPTERS[item["id"]].contract_version)
            self.assertEqual(item["scope"], "inert-file-generation")
            self.assertFalse(item["host_runtime_certified"])
            self.assertFalse(item["native_multi_agent_orchestration"])
            self.assertEqual(len(item["role_header_sha256"]), 64)
        self.assertEqual(entries["generic"]["mcp_activation"], "unsupported")
        self.assertEqual(entries["codex"]["mcp_activation"], "manual-only")
        self.assertEqual(contracts(["codex", "claude", "codex"]), [entries["claude"], entries["codex"]])

    def test_invalid_contract_version_fails_before_output_writes(self):
        for version in (None, True, 1, "1", "1.0", "01.0.0", "1.0.0\n", "1.0.0;run"):
            with self.subTest(version=version), self.changed_adapter(contract_version=version):
                with self.assertRaisesRegex(StratagentError, "major.minor.patch"):
                    self.service.configure()
        self.assertFalse((self.root / ".agents").exists())

    def test_version_change_invalidates_approval_even_when_output_bytes_match(self):
        before = self.service.configure()
        with self.changed_adapter(contract_version="1.1.0"):
            after = self.service.configure()
            self.assertEqual(before["outputs"], after["outputs"])
            self.assertNotEqual(before["approval"], after["approval"])
            with self.assertRaisesRegex(StratagentError, "Approval digest"):
                self.service.configure(before["approval"], True)
        self.assertFalse((self.root / ".agents").exists())

    def test_staged_apply_rechecks_selected_contract(self):
        stage = self.service.stage("configure")
        with self.changed_adapter(contract_version="2.0.0"):
            with self.assertRaisesRegex(StratagentError, "stale"):
                self.service.apply_stage(stage["stage_id"], stage["plan"]["approval"])
        self.assertFalse((self.root / ".agents").exists())

    def test_unselected_adapter_does_not_invalidate_approval(self):
        before = self.service.configure()
        with self.changed_adapter("claude", contract_version="2.0.0"):
            self.assertEqual(before["approval"], self.service.configure()["approval"])
            self.service.configure(before["approval"], True)
        recorded = self.service.lock()["installations"]["task-configuration"]["adapter_contracts"]
        self.assertEqual(recorded, contracts(["codex"]))
        self.assertTrue(self.service.verify()["ok"])

    def test_installed_noop_cannot_reuse_an_old_contract_approval(self):
        before = self.service.configure()
        self.service.configure(before["approval"], True)
        self.assertTrue(self.service.configure(before["approval"], True)["already_installed"])
        with self.changed_adapter(contract_version="1.0.1"):
            with self.assertRaisesRegex(StratagentError, "Approval digest"):
                self.service.configure(before["approval"], True)
            current = self.service.configure()
            self.service.configure(current["approval"], True)
            recorded = self.service.lock()["installations"]["task-configuration"]["adapter_contracts"]
            self.assertEqual(recorded[0]["adapter_version"], "1.0.1")
            self.assertTrue(self.service.configure(current["approval"], True)["already_installed"])

    def test_role_header_change_is_visible_in_contract_and_approval(self):
        before = contracts(["claude"])
        with self.changed_adapter("claude", agent_header="permissionMode: plan\n"):
            after = contracts(["claude"])
        self.assertNotEqual(before[0]["role_header_sha256"], after[0]["role_header_sha256"])

    def test_legacy_lock_can_verify_and_remove_without_silent_contract_migration(self):
        plan = self.service.configure()
        self.service.configure(plan["approval"], True)
        lock = self.service.lock()
        del lock["installations"]["task-configuration"]["adapter_contracts"]
        self.service.ws.write(LOCK, lock)
        original = self.service.ws.path(LOCK).read_bytes()
        self.assertTrue(self.service.verify()["ok"])
        self.service.status()
        self.assertEqual(original, self.service.ws.path(LOCK).read_bytes())
        removal = self.service.remove("task-configuration")
        self.service.remove("task-configuration", removal["approval"], True)
        self.assertEqual(self.service.lock()["installations"], {})
        self.assertTrue(self.service.verify()["ok"])


class ReservedSkillNameTests(unittest.TestCase):
    def snapshot(self, name):
        snapshot = sample_snapshot()
        source = unpack(snapshot)[snapshot["entry"]].replace(b"name: python-review", ("name: " + name).encode())
        snapshot = replace_file(snapshot, snapshot["entry"], source)
        for item in snapshot["files"]:
            item["path"] = item["path"].replace("skills/python-review/", "skills/" + name + "/")
        snapshot["entry"] = "skills/" + name + "/SKILL.md"
        return snapshot

    def test_documented_reserved_names_are_remapped_only_in_claude_exports(self):
        for name in ("synced", "anthropic-skills"):
            with self.subTest(name=name):
                snapshot = self.snapshot(name)
                review = assess(snapshot)
                self.assertTrue(review["eligible"])
                source = unpack(snapshot)
                files = render_bundle(review, source, list(ADAPTERS))
                for root, output_name in ((".claude/skills", "sa-" + name), (".agents/skills", name),
                                          (".stratagent/portable/skills", name)):
                    path = f"{root}/{output_name}"
                    header, _ = metadata(files[path + "/SKILL.md"].decode())
                    self.assertEqual(header["name"], output_name)
                    self.assertIn(path + "/references/checklist.md", files)
                    self.assertTrue(any(p.startswith(path + "/stratagent-notices/") for p in files))
                self.assertNotIn(f".claude/skills/{name}/SKILL.md", files)
                self.assertEqual(metadata(source[snapshot["entry"]].decode())[0]["name"], name)

    def test_remapped_destination_keeps_collision_refusal(self):
        with tempfile.TemporaryDirectory() as root:
            service = Stratagent(root)
            service.init("Small Python API testing", ["claude"], scan_project=False)
            candidate = service.import_snapshot(self.snapshot("synced"))
            service.allow(candidate["repo"])
            path = Path(root) / ".claude/skills/sa-synced/SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"Original user instructions\n")
            preview = service.install(candidate["id"])
            with self.assertRaisesRegex(StratagentError, "refusing to overwrite"):
                service.install(candidate["id"], preview["approval"], True)
            self.assertEqual(path.read_bytes(), b"Original user instructions\n")
            self.assertEqual(service.lock()["installations"], {})

    def test_installed_assignments_use_actual_remapped_paths_and_verify(self):
        with tempfile.TemporaryDirectory() as root:
            service = Stratagent(root)
            service.init("Small Python API testing", ["claude", "codex"], scan_project=False)
            candidate = service.import_snapshot(self.snapshot("synced"))
            service.allow(candidate["repo"])
            plan = service.install(candidate["id"])
            service.install(candidate["id"], plan["approval"], True)
            task_plan = service.configure()
            paths = {p for item in task_plan["source"]["task_plan"]["assignments"]
                     for resource in item["resources"] for p in resource["paths"]}
            self.assertIn(".claude/skills/sa-synced/SKILL.md", paths)
            self.assertIn(".agents/skills/synced/SKILL.md", paths)
            service.configure(task_plan["approval"], True)
            self.assertTrue(service.verify()["ok"])

    def test_reserved_name_policy_is_approval_bound_even_for_ordinary_names(self):
        with tempfile.TemporaryDirectory() as root:
            service = Stratagent(root)
            service.init("Small Python API", ["claude"], scan_project=False)
            candidate = service.import_snapshot(sample_snapshot())
            before = service.install(candidate["id"])
            adapter = replace(ADAPTERS["claude"], reserved_skill_names=())
            with patch("stratagent.hosts.ADAPTERS", MappingProxyType({**ADAPTERS, "claude": adapter})):
                after = service.install(candidate["id"])
            self.assertEqual(before["outputs"], after["outputs"])
            self.assertNotEqual(before["approval"], after["approval"])


class NeutralCoreTests(unittest.TestCase):
    def test_analysis_is_identical_for_every_target(self):
        analyses = []
        for target in ADAPTERS:
            with tempfile.TemporaryDirectory() as root:
                service = Stratagent(root)
                service.init("Python API with privacy and offline tests", [target], scan_project=False)
                analyses.append(service.analysis())
        self.assertTrue(all(analysis == analyses[0] for analysis in analyses))

    def test_portable_export_has_no_native_host_files_and_verifies(self):
        with tempfile.TemporaryDirectory() as root:
            service = Stratagent(root)
            service.init("Python API", ["generic"])
            candidate = service.import_snapshot(sample_snapshot())
            service.allow(candidate["repo"])
            install = service.install(candidate["id"])
            service.install(candidate["id"], install["approval"], True)
            plan = service.configure()
            service.configure(plan["approval"], True)
            self.assertTrue(service.verify()["ok"])
            self.assertTrue(all(output["path"].startswith(".stratagent/") for output in plan["outputs"]))
            self.assertFalse((Path(root) / ".agents").exists())
            self.assertFalse((Path(root) / ".claude").exists())

    def test_role_assignments_use_only_selected_adapter_resources(self):
        with tempfile.TemporaryDirectory() as root:
            service = Stratagent(root)
            service.init("Python API testing", ["claude", "codex"])
            candidate = service.import_snapshot(sample_snapshot("subagent"))
            service.allow(candidate["repo"])
            install = service.install(candidate["id"])
            service.install(candidate["id"], install["approval"], True)
            manifest = service.manifest()
            manifest["platforms"] = ["codex"]
            service.ws.write(MANIFEST, manifest)
            assignments = service.configure()["source"]["task_plan"]["assignments"]
            references = [path for assignment in assignments for resource in assignment["resources"] for path in resource["paths"]]
            self.assertTrue(references)
            self.assertTrue(all(path.startswith(".agents/skills/") for path in references))

    def test_cli_catalog_needs_no_existing_workspace(self):
        environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
        with tempfile.TemporaryDirectory() as root:
            result = subprocess.run([sys.executable, "-m", "stratagent", "platforms", "--workspace", str(Path(root) / "absent")],
                                    env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), catalog())
            self.assertEqual(list(Path(root).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
