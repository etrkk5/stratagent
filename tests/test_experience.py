import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from stratagent.cli import main
from stratagent.common import StratagentError, identity
from stratagent.diagnostics import diagnose
from stratagent.experience import begin, connect, guide, render
from stratagent.mcp import RPCError, Server
from stratagent.lifecycle import Transactions
from stratagent.orchestration import Orchestrator
from stratagent.service import Stratagent
from test_architect import FakeRegistry
from test_runtime_research import PROMPT, model_plan
from test_stratagent import FakeGitHub, file_state


class ExperienceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.github, self.registry = FakeGitHub(), FakeRegistry()
        self.service = Stratagent(self.root, github=self.github, registry=self.registry)
        self.driver = Orchestrator(self.service)

    def start(self):
        return begin(self.service, PROMPT, ["generic"])

    def proposed(self):
        card = self.start()
        request = guide(self.service, details=True)["details"]["model_request"]
        return self.driver.submit(card["session_id"], request["request_id"], {"action": "research", "plan": model_plan(self.service, github=False)})

    def final(self):
        proposed = self.proposed()
        comparison = self.driver.search(proposed["session"]["id"], proposed["search_review"]["approval"])
        decision = copy.deepcopy(comparison["model_request"]["decision_request"]["suggested_decision"])
        decision["reason"] = "Keep focused ownership and show missing external resources honestly."
        for binding in decision["bindings"]:
            binding["skills"], binding["mcps"] = [], []
        return self.driver.submit(comparison["session"]["id"], comparison["model_request"]["request_id"], {"action": "decide", "decision": decision})

    def test_fresh_guidance_and_default_mcp_are_readonly_without_creating_state(self):
        before = file_state(self.root)
        card = guide(self.service)
        self.assertEqual(card["phase"], "welcome")
        server = Server(self.root)
        result = json.loads(server.call_tool("stratagent_next", {})["content"][0]["text"])
        self.assertEqual(result, card)
        self.assertEqual(before, file_state(self.root))
        self.assertFalse(self.github.calls or self.registry.calls)
        for invalid in ({"apply": True}, {"details": 1}, {"details": "yes"}, {"approve_search": "yes"}):
            with self.assertRaises(RPCError):
                server.call_tool("stratagent_next", invalid)

    def test_begin_reuses_progress_and_never_resets_budgets_or_changed_scope(self):
        first = self.start()
        self.proposed()
        before = file_state(self.root)
        second = self.start()
        self.assertEqual(second["session_id"], first["session_id"])
        self.assertEqual(second["phase"], "search-review")
        self.assertEqual(before, file_state(self.root))
        for prompt, targets in (("A different project", ["generic"]), (PROMPT, ["claude"])):
            with self.assertRaises(StratagentError):
                begin(self.service, prompt, targets)
        self.assertEqual(before, file_state(self.root))

    def test_next_progressively_exposes_live_schemas_without_consuming_turns(self):
        self.start()
        before = file_state(self.root)
        compact, full = guide(self.service), guide(self.service, details=True)
        self.assertNotIn("details", compact)
        self.assertIn("response_schemas", full["details"]["model_request"])
        self.assertEqual(full["next_action"]["kind"], "model-proposal")
        self.assertIn("--response-stdin", full["next_action"]["submit_argv"])
        self.assertEqual(before, file_state(self.root))
        self.assertFalse(self.github.calls or self.registry.calls)

    def test_search_card_shows_exact_egress_and_does_not_authorize_it(self):
        proposed = self.proposed()
        before = file_state(self.root)
        card = guide(self.service)
        text = render(card)
        self.assertEqual(card["phase"], "search-review")
        self.assertIn("qdrant", text)
        self.assertIn("https://registry.modelcontextprotocol.io", text)
        self.assertIn("Reserved connector calls", text)
        self.assertNotIn(proposed["search_review"]["approval"], text)
        self.assertEqual(before, file_state(self.root))
        self.assertFalse(self.github.calls or self.registry.calls)
        with self.assertRaises(StratagentError):
            self.driver.search(card["session_id"], "yes")

    def test_full_review_to_existing_stage_apply_verify_preserves_user_files(self):
        (self.root / "user-notes.md").write_text("Preserve original user notes.\n")
        reviewed = self.final()
        before = file_state(self.root)
        card = guide(self.service, details=True)
        self.assertEqual(card["phase"], "review")
        self.assertTrue(card["review"]["roles"])
        self.assertEqual(card["review"]["decision_engine"], "external-structured-proposal")
        self.assertEqual(card["review"]["resource_counts"], {"skills": 0, "mcp_proposals": 0})
        self.assertTrue(card["details"]["file_contents"])
        self.assertTrue(card["details"]["diff"])
        self.assertEqual(before, file_state(self.root))
        self.assertFalse(self.service.lock()["installations"])
        selection = self.driver.review(reviewed["session"]["id"])
        stage = self.service.stage("blueprint", **selection)
        with self.assertRaises(StratagentError):
            self.service.apply_stage(stage["stage_id"], "yes")
        self.service.apply_stage(stage["stage_id"], stage["plan"]["approval"])
        ready = guide(self.service)
        self.assertEqual(ready["phase"], "ready")
        self.assertTrue(ready["verification"]["ok"])
        self.assertFalse(ready["research_revalidated"])
        self.assertEqual((self.root / "user-notes.md").read_text(), "Preserve original user notes.\n")

    def test_different_model_decision_at_same_context_is_not_reported_installed(self):
        reviewed = self.final()
        stage = self.service.stage("blueprint", **self.driver.review(reviewed["session"]["id"]))
        self.service.apply_stage(stage["stage_id"], stage["plan"]["approval"])
        self.assertEqual(guide(self.service)["phase"], "ready")
        value = self.driver.status(reviewed["session"]["id"])["session"]
        value["decisions"][0]["reason"] = "A different reviewed choice with the same project evidence."
        self.driver._save(value)
        self.assertNotEqual(guide(self.service)["phase"], "ready")

    def test_user_drift_and_new_project_evidence_are_never_reported_ready(self):
        reviewed = self.final()
        stage = self.service.stage("blueprint", **self.driver.review(reviewed["session"]["id"]))
        self.service.apply_stage(stage["stage_id"], stage["plan"]["approval"])
        output = self.service.ws.path(stage["plan"]["outputs"][0]["path"])
        output.write_bytes(output.read_bytes() + b"User edit\n")
        before = file_state(self.root)
        self.assertEqual(guide(self.service)["phase"], "drift")
        self.assertEqual(before, file_state(self.root))
        (self.root / "requirements.txt").write_text("qdrant-client\n")
        self.assertEqual(guide(self.service)["phase"], "context-changed")

    def test_existing_conflict_blocks_review_and_has_no_stage_suggestion(self):
        self.final()
        card = guide(self.service, details=True)
        output = next(path for path in card["details"]["file_contents"] if path.endswith("SKILL.md"))
        self.service.ws.path(output).parent.mkdir(parents=True, exist_ok=True)
        self.service.ws.path(output).write_text("Original user-owned instructions.\n")
        before = file_state(self.root)
        blocked = guide(self.service)
        self.assertEqual(blocked["phase"], "blocked")
        self.assertNotIn("after_review_argv", blocked["next_action"])
        self.assertEqual(before, file_state(self.root))

    def test_expiry_cancel_and_multiple_sessions_need_deliberate_selection(self):
        card = self.start()
        self.driver.cancel(card["session_id"])
        before = file_state(self.root)
        self.assertEqual(self.start()["phase"], "paused")
        self.assertEqual(before, file_state(self.root))
        with patch("stratagent.orchestration.time.time", return_value=self.driver.status(card["session_id"])["session"]["deadline_at"]):
            self.assertTrue(guide(self.service)["expired"])
        added = begin(self.service, PROMPT, ["generic"], new_session=True)
        choices = guide(self.service)
        self.assertEqual(choices["phase"], "choose-session")
        self.assertEqual(len(choices["sessions"]), 2)
        self.assertEqual(guide(self.service, added["session_id"])["phase"], "research")

    def test_clarification_is_a_user_decision_not_an_automatic_scope_change(self):
        started = self.start()
        request = guide(self.service, details=True)["details"]["model_request"]
        self.driver.submit(started["session_id"], request["request_id"], {"action": "clarify", "questions": ["Should this project use a database?"]})
        before = file_state(self.root)
        card = guide(self.service)
        self.assertEqual(card["phase"], "question")
        self.assertTrue(card["next_action"]["requires_user"])
        self.assertEqual(before, file_state(self.root))

    def test_partial_and_nonregular_metadata_fail_without_starting_over(self):
        state = self.root / ".stratagent"
        state.mkdir()
        (state / "policy.json").write_text('{"schema_version":1}')
        before = file_state(self.root)
        self.assertEqual(guide(self.service)["phase"], "state-attention")
        with self.assertRaises(StratagentError):
            self.start()
        self.assertEqual(before, file_state(self.root))

    def test_real_post_commit_interruption_requires_recovery_before_ready(self):
        reviewed = self.final()
        stage = self.service.stage("blueprint", **self.driver.review(reviewed["session"]["id"]))

        def interrupt(event):
            if event == "lock-committed":
                raise KeyboardInterrupt

        with patch.object(Transactions, "checkpoint", side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
            self.service.apply_stage(stage["stage_id"], stage["plan"]["approval"])
        before = file_state(self.root)
        card = guide(self.service)
        self.assertEqual(card["phase"], "recovery")
        self.assertTrue(card["next_action"]["requires_user"])
        self.assertEqual(before, file_state(self.root))

    def test_session_count_budget_fails_before_another_record_is_written(self):
        self.start()
        before = file_state(self.root)
        with patch("stratagent.experience.MAX_SESSIONS", 1), self.assertRaises(StratagentError):
            begin(self.service, PROMPT, ["generic"], new_session=True)
        self.assertEqual(before, file_state(self.root))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO")
    def test_fifo_session_is_refused_before_read_and_never_blocks(self):
        self.start()
        fifo = self.service.ws.path(".stratagent/orchestrations/" + "a" * 32 + ".json")
        os.mkfifo(fifo)
        with self.assertRaisesRegex(StratagentError, "regular"):
            guide(self.service)


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.service = Stratagent(self.root)

    def test_preview_deduplicates_shared_host_path_and_never_changes_settings(self):
        (self.root / ".mcp.json").write_text('{"original":true}\n')
        before = file_state(self.root)
        card = connect(self.service)
        self.assertEqual(card["phase"], "connect-review")
        self.assertEqual(len(card["connection"]["files"]), 2)
        self.assertEqual(before, file_state(self.root))
        self.assertFalse((self.root / ".stratagent").exists())
        result = connect(self.service, approval=card["connection"]["approval"], apply=True)
        self.assertTrue(result["connection"]["applied"])
        self.assertEqual((self.root / ".mcp.json").read_text(), '{"original":true}\n')
        self.assertTrue(diagnose(self.root)["ok"])
        self.assertEqual(guide(self.service)["phase"], "welcome")

    def test_connection_is_idempotent_and_cannot_reuse_approval_in_another_root(self):
        card = connect(self.service, ["codex"])
        approval = card["connection"]["approval"]
        with tempfile.TemporaryDirectory() as other, self.assertRaises(StratagentError):
            connect(Stratagent(other), ["codex"], approval, True)
        connect(self.service, ["codex"], approval, True)
        before = file_state(self.root)
        fresh = connect(self.service, ["codex"])
        self.assertTrue(fresh["connection"]["already_connected"])
        repeated = connect(self.service, ["codex"], fresh["connection"]["approval"], True)
        self.assertFalse(repeated["connection"]["applied"])
        self.assertEqual(before, file_state(self.root))

    def test_user_skill_conflict_and_stale_approval_preserve_all_files(self):
        card = connect(self.service)
        name = card["connection"]["files"][0]["path"]
        path = self.service.ws.path(name)
        path.parent.mkdir(parents=True)
        path.write_text("User instructions must survive.\n")
        before = file_state(self.root)
        self.assertEqual(connect(self.service)["phase"], "blocked")
        with self.assertRaises(StratagentError):
            connect(self.service, approval=card["connection"]["approval"], apply=True)
        self.assertEqual(before, file_state(self.root))

    @unittest.skipIf(os.name == "nt", "POSIX umask semantics")
    def test_restrictive_user_umask_keeps_connection_idempotent_without_permission_changes(self):
        card = connect(self.service, ["codex"])
        previous = os.umask(0o077)
        try:
            connect(self.service, ["codex"], card["connection"]["approval"], True)
        finally:
            os.umask(previous)
        path = self.service.ws.path(card["connection"]["files"][0]["path"])
        mode = path.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)
        repeated = connect(self.service, ["codex"])
        self.assertTrue(repeated["connection"]["already_connected"])
        connect(self.service, ["codex"], repeated["connection"]["approval"], True)
        self.assertEqual(path.stat().st_mode & 0o777, mode)

    def test_multi_file_connection_rolls_back_new_files_if_second_create_fails(self):
        card = connect(self.service)
        original = os.open

        def fail_second(path, *args, **kwargs):
            if str(path).replace("\\", "/").endswith(".claude/skills/stratagent/SKILL.md"):
                raise OSError("Injected create failure")
            return original(path, *args, **kwargs)

        with patch("stratagent.workspace.os.open", side_effect=fail_second), self.assertRaises(OSError):
            connect(self.service, approval=card["connection"]["approval"], apply=True)
        for record in card["connection"]["files"]:
            self.assertFalse(self.service.ws.path(record["path"]).exists())

    def test_cli_welcome_human_view_and_bounded_stdin_proposal(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main([]), 0)
        self.assertIn("connect", stdout.getvalue())
        self.assertFalse(stderr.getvalue())
        started = begin(self.service, PROMPT, ["generic"])
        request = guide(self.service, details=True)["details"]["model_request"]
        response = {"action": "research", "plan": model_plan(self.service, github=False)}
        arguments = ["session-submit", started["session_id"], "--request-id", request["request_id"], "--response-stdin", "--workspace", str(self.root)]
        with patch("sys.stdin", io.StringIO(json.dumps(response))), redirect_stdout(io.StringIO()):
            self.assertEqual(main(arguments), 0)
        self.assertEqual(guide(self.service)["phase"], "search-review")
        before = file_state(self.root)
        with patch("sys.stdin", io.StringIO("x" * (128 * 1024 + 1))), redirect_stderr(io.StringIO()):
            self.assertEqual(main(arguments), 2)
        self.assertEqual(before, file_state(self.root))

    def test_returned_proposal_command_runs_in_the_same_environment_without_temp_files(self):
        begin(self.service, PROMPT, ["generic"])
        card = guide(self.service, details=True)
        response = {"action": "research", "plan": model_plan(self.service, github=False)}
        result = subprocess.run(card["next_action"]["submit_argv"], input=json.dumps(response), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["session"]["state"], "awaiting-search-approval")
        self.assertEqual(guide(self.service)["phase"], "search-review")
        self.assertEqual({p.name for p in self.root.iterdir()}, {".stratagent"})

    def test_human_render_does_not_emit_control_sequences_or_digest_wall(self):
        card = guide(self.service)
        card["headline"] = "Unsafe\x1b[31m terminal\u202e control"
        text = render(card)
        self.assertNotIn("\x1b", text)
        self.assertNotIn("\u202e", text)
        self.assertNotIn("session_id", text)
