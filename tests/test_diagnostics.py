import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from stratagent.cli import main
from stratagent.common import StratagentError, identity
from stratagent.diagnostics import MAX_STATE_BYTES, diagnose
from stratagent.filesystem import LocalFilesystem
from stratagent.lifecycle import JOURNAL
from stratagent.service import LOCK, MANIFEST, POLICY, Stratagent
from test_stratagent import file_state

PRIVATE = "DIAGNOSTIC_PRIVATE_SENTINEL"


def checks(report):
    return {item["id"]: item for item in report["checks"]}


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / PRIVATE
        self.root.mkdir()
        self.service = Stratagent(self.root)

    def init(self):
        self.service.init("Small Python API " + PRIVATE, ["generic"], scan_project=False)

    def install(self):
        self.init()
        plan = self.service.configure()
        self.service.configure(plan["approval"], True)
        return self.service.ws.path(next(iter(self.service.lock()["owners"])))

    def test_fresh_workspace_does_not_write_or_claim_resource_host_checks(self):
        (self.root / ".env").write_text(PRIVATE)
        original = file_state(self.root)
        with contextlib.ExitStack() as stack:
            for target in ("socket.create_connection", "urllib.request.OpenerDirector.open", "subprocess.Popen",
                           "stratagent.workspace.Workspace.write", "stratagent.workspace.Workspace.mutation"):
                stack.enter_context(patch(target, side_effect=AssertionError("No network, process or write")))
            report = diagnose(self.root, True)
        self.assertTrue(report["ok"])
        self.assertEqual(checks(report)["workspace-initialization"]["status"], "skip")
        self.assertEqual(report["coverage"]["host_runtime"], "not-checked")
        self.assertFalse(report["production_ready"])
        self.assertEqual(report["network_calls"], 0)
        self.assertFalse(report["writes"])
        self.assertEqual(original, file_state(self.root))
        self.assertNotIn(PRIVATE, json.dumps(report))

    def test_missing_workspace_is_structured_and_not_created(self):
        root = self.root / "absent"
        report = diagnose(root)
        self.assertFalse(report["ok"])
        self.assertEqual(checks(report)["workspace-directory"]["status"], "fail")
        self.assertFalse(root.exists())

    def test_incomplete_initialization_is_not_reinitialized(self):
        state = self.root / ".stratagent"
        state.mkdir()
        (state / "policy.json").write_text('{"private":"' + PRIVATE + '"}')
        before = file_state(self.root)
        report = diagnose(self.root)
        self.assertEqual(checks(report)["workspace-initialization"]["status"], "fail")
        self.assertFalse(report["ok"])
        self.assertEqual(before, file_state(self.root))
        self.assertNotIn(PRIVATE, json.dumps(report))

    def test_valid_initialized_state_skips_content_hashes_by_default(self):
        self.init()
        before = file_state(self.root)
        with patch.object(Stratagent, "verify", side_effect=AssertionError("Must be opt-in")):
            report = diagnose(self.root)
        self.assertTrue(report["ok"])
        self.assertEqual(checks(report)["managed-outputs"]["status"], "skip")
        self.assertEqual(before, file_state(self.root))

    def test_opt_in_verification_detects_drift_without_disclosing_path_or_contents(self):
        output = self.install()
        self.assertEqual(checks(diagnose(self.root, True))["managed-outputs"]["status"], "pass")
        output.write_bytes(PRIVATE.encode())
        before = file_state(self.root)
        report = diagnose(self.root, True)
        self.assertEqual(checks(report)["managed-outputs"]["status"], "fail")
        self.assertFalse(report["ok"])
        self.assertNotIn(output.relative_to(self.service.ws.root).as_posix(), json.dumps(report))
        self.assertNotIn(PRIVATE, json.dumps(report))
        self.assertEqual(before, file_state(self.root))

    def test_missing_managed_output_is_not_recreated(self):
        output = self.install()
        output.unlink()
        report = diagnose(self.root, True)
        self.assertFalse(report["ok"])
        self.assertFalse(output.exists())

    def test_pending_transaction_retains_journal_and_defers_hash_scan(self):
        self.install()
        journal = self.service.ws.read(JOURNAL)
        journal["state"] = "writing"
        journal["digest"] = identity({key: value for key, value in journal.items() if key != "digest"})
        self.service.ws.write(JOURNAL, journal)
        before = file_state(self.root)
        with patch.object(Stratagent, "verify", side_effect=AssertionError("Recovery must come first")):
            report = diagnose(self.root, True)
        self.assertEqual(checks(report)["transaction-recovery"]["status"], "fail")
        self.assertEqual(checks(report)["managed-outputs"]["status"], "skip")
        self.assertFalse(report["ok"])
        self.assertEqual(before, file_state(self.root))

    def test_legacy_lock_marker_is_retained(self):
        self.init()
        marker = self.service.ws.path(".stratagent/.write-lock")
        marker.mkdir()
        report = diagnose(self.root)
        self.assertFalse(report["ok"])
        self.assertEqual(checks(report)["legacy-write-lock"]["status"], "fail")
        self.assertTrue(marker.is_dir())

    def test_invalid_json_and_nested_metadata_fail_without_raw_errors(self):
        self.init()
        for content in (PRIVATE, '{"schema_version":1,"installations":[' + json.dumps(PRIVATE) + ']}'):
            with self.subTest(content=content):
                self.service.ws.path(LOCK).write_text(content)
                report = diagnose(self.root, True)
                self.assertFalse(report["ok"])
                self.assertNotIn(PRIVATE, json.dumps(report))

    def test_private_exception_is_not_copied_into_report_or_logs(self):
        self.init()
        with patch.object(Stratagent, "manifest", side_effect=OSError(PRIVATE)):
            with patch("sys.stdout", new_callable=io.StringIO) as out, patch("sys.stderr", new_callable=io.StringIO) as err:
                code = main(["doctor", "--workspace", str(self.root), "--log-json"])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(out.getvalue())["ok"])
        self.assertNotIn(PRIVATE, out.getvalue() + err.getvalue())
        events = [json.loads(line) for line in err.getvalue().splitlines()]
        self.assertEqual(events[-1]["exit_code"], 2)

    def test_oversized_metadata_is_refused_before_read(self):
        self.init()
        with self.service.ws.path(LOCK).open("wb") as handle:
            handle.truncate(MAX_STATE_BYTES + 1)
        with patch("pathlib.Path.open", side_effect=AssertionError("Oversized file must not be read")):
            # The bounded snapshot reads the small preceding metadata first.
            from stratagent.diagnostics import _state_snapshot
            with patch("stratagent.diagnostics.STATE_FILES", (LOCK,)):
                with self.assertRaisesRegex(StratagentError, "bounded regular"):
                    _state_snapshot(self.service.ws)
        self.assertFalse(diagnose(self.root)["ok"])

    def test_redirected_metadata_is_not_followed(self):
        self.init()
        outside = self.root / "private-file"
        outside.write_text(PRIVATE)
        lock = self.service.ws.path(LOCK)
        lock.unlink()
        lock.symlink_to(outside)
        report = diagnose(self.root)
        self.assertFalse(report["ok"])
        self.assertEqual(outside.read_text(), PRIVATE)
        self.assertNotIn(PRIVATE, json.dumps(report))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX-only FIFO metadata regression")
    def test_fifo_metadata_is_refused_before_open(self):
        self.init()
        lock = self.service.ws.path(LOCK)
        lock.unlink()
        os.mkfifo(lock)
        report = diagnose(self.root)
        self.assertFalse(report["ok"])
        self.assertEqual(checks(report)["workspace-metadata"]["status"], "fail")

    def test_hash_budget_is_explicit_and_does_not_report_successful_verification(self):
        self.init()
        outputs = [{"path": f".stratagent/portable/skills/large-{i}/SKILL.md", "size": 4 * 1024 * 1024, "sha256": "a" * 64} for i in range(5)]
        self.service.ws.write(LOCK, {"schema_version": 1, "installations": {"original-fixture": {"source": {}, "outputs": outputs}}})
        with patch.object(Stratagent, "verify", side_effect=AssertionError("Must honor hash budget")):
            report = diagnose(self.root, True)
        self.assertEqual(checks(report)["managed-outputs"]["status"], "warn")
        self.assertEqual(report["status"], "attention")

    def test_concurrent_metadata_change_invalidates_snapshot(self):
        self.init()
        verify = Stratagent.verify

        def change_during_scan(service):
            result = verify(service)
            policy = service.policy()
            policy["operator_note"] = PRIVATE
            service.ws.write(POLICY, policy)
            return result

        with patch.object(Stratagent, "verify", change_during_scan):
            report = diagnose(self.root, True)
        self.assertEqual(checks(report)["workspace-snapshot"]["status"], "fail")
        self.assertFalse(report["ok"])
        self.assertNotIn(PRIVATE, json.dumps(report))

    def test_dependency_and_package_mismatch_are_actionable_without_raw_versions(self):
        with patch("stratagent.diagnostics.metadata.version", return_value=PRIVATE):
            report = diagnose(self.root)
        self.assertEqual(checks(report)["pyyaml-runtime"]["status"], "fail")
        self.assertEqual(checks(report)["package-metadata"]["status"], "warn")
        self.assertNotIn(PRIVATE, json.dumps(report))

    def test_unsupported_runtime_and_backend_are_failures(self):
        with patch("stratagent.diagnostics.sys.version_info", (3, 10)), patch(
                "stratagent.diagnostics.LocalFilesystem", return_value=LocalFilesystem("unsupported")):
            report = diagnose(self.root)
        self.assertEqual(checks(report)["python-runtime"]["status"], "fail")
        self.assertEqual(checks(report)["filesystem-backend"]["status"], "fail")

    def test_missing_dependency_can_be_diagnosed_before_importing_application(self):
        environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
        process = subprocess.run([sys.executable, "-S", "-m", "stratagent", "doctor", "--workspace", str(self.root), "--log-json"],
                                 capture_output=True, text=True, env=environment, timeout=20)
        self.assertEqual(process.returncode, 2)
        report = json.loads(process.stdout)
        self.assertEqual(checks(report)["pyyaml-runtime"]["status"], "fail")
        self.assertNotIn("Traceback", process.stderr)
        self.assertNotIn(PRIVATE, process.stdout + process.stderr)

    def test_other_commands_with_missing_dependency_get_safe_recovery_guidance(self):
        environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
        process = subprocess.run([sys.executable, "-S", "-m", "stratagent", "plan", PRIVATE],
                                 capture_output=True, text=True, env=environment, timeout=20)
        self.assertEqual(process.returncode, 2)
        self.assertIn("doctor", json.loads(process.stderr)["error"])
        self.assertNotIn("Traceback", process.stderr)
        self.assertNotIn(PRIVATE, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
