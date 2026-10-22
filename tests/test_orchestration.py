import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from stratagent.cli import main
from stratagent.common import StratagentError, identity
from stratagent.mcp import RPCError, Server, serve
from stratagent.orchestration import NetworkBudget, Orchestrator, TimedOpener
from stratagent.service import Stratagent
from test_architect import FakeRegistry
from test_runtime_research import PROMPT, model_plan
from test_stratagent import FakeGitHub, file_state


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.github, self.registry = FakeGitHub(), FakeRegistry()
        self.service = Stratagent(self.root, github=self.github, registry=self.registry)
        self.driver = Orchestrator(self.service)

    def start(self, **limits):
        return self.driver.start(PROMPT, ["generic"], **limits)

    def propose(self, started=None, github=True, mcp=True):
        started = started or self.start()
        plan = model_plan(self.service, github, mcp)
        return self.driver.submit(started["session"]["id"], started["model_request"]["request_id"], {"action": "research", "plan": plan})

    def search(self, proposed=None):
        proposed = proposed or self.propose()
        return self.driver.search(proposed["session"]["id"], proposed["search_review"]["approval"])

    def test_start_is_local_bounded_and_resumes_with_another_driver_instance(self):
        result = self.start()
        self.assertEqual(result["session"]["state"], "research-needed")
        self.assertEqual(result["model_request"]["allowed_actions"], ["research", "clarify"])
        self.assertFalse(self.github.calls or self.registry.calls)
        restored = Orchestrator(Stratagent(self.root)).request(result["session"]["id"])
        self.assertEqual(result, restored)
        self.assertFalse(self.service.lock()["installations"])

    def test_invalid_limits_fail_before_initialization(self):
        for limits in ({"model_turns": True}, {"search_rounds": 4}, {"network_requests": 0}, {"seconds": 3601}):
            with self.subTest(limits=limits), self.assertRaises(StratagentError):
                self.start(**limits)
            self.assertFalse((self.root / ".stratagent").exists())

    def test_proposal_needs_separate_session_bound_search_approval(self):
        result = self.propose()
        before = file_state(self.root)
        for approval in (None, "yes", result["search_review"]["search_preview"]["search_approval"]):
            with self.subTest(approval=approval), self.assertRaisesRegex(StratagentError, "approval"):
                self.driver.search(result["session"]["id"], approval)
        self.assertEqual(before, file_state(self.root))
        self.assertFalse(self.github.calls or self.registry.calls)

    def test_model_replay_is_idempotent_and_changed_response_is_rejected(self):
        started = self.start()
        session_id, request_id = started["session"]["id"], started["model_request"]["request_id"]
        response = {"action": "research", "plan": model_plan(self.service)}
        self.driver.submit(session_id, request_id, response)
        before = file_state(self.root)
        replay = self.driver.submit(session_id, request_id, response)
        self.assertEqual(replay["session"]["usage"]["model_turns"], 1)
        self.assertEqual(before, file_state(self.root))
        response["plan"]["reason"] = "A changed proposal is not the original replay."
        with self.assertRaisesRegex(StratagentError, "Stale"):
            self.driver.submit(session_id, request_id, response)

    def test_rejected_model_authority_consumes_a_turn_without_persisting_its_text(self):
        started = self.start()
        response = {"action": "research", "plan": model_plan(self.service), "execute": "SECRET-DO-NOT-STORE"}
        with self.assertRaisesRegex(StratagentError, "proposal rejected"):
            self.driver.submit(started["session"]["id"], started["model_request"]["request_id"], response)
        current = self.driver.request(started["session"]["id"])
        self.assertEqual(current["session"]["usage"]["model_turns"], 1)
        self.assertNotEqual(current["model_request"]["request_id"], started["model_request"]["request_id"])
        self.assertEqual(current["session"]["events"][-1]["code"], "proposal-rejected")
        self.assertNotIn("SECRET-DO-NOT-STORE", json.dumps(current["session"]))
        self.assertFalse(self.github.calls or self.registry.calls)

    def test_rejected_attempts_cannot_reset_model_turn_budget(self):
        result = self.start(model_turns=2)
        session_id = result["session"]["id"]
        for unused in range(2):
            with self.assertRaises(StratagentError):
                self.driver.submit(session_id, result["model_request"]["request_id"], {"action": "install"})
            if unused == 0:
                result = self.driver.request(session_id)
        with self.assertRaisesRegex(StratagentError, "model-turn budget"):
            self.driver.request(session_id)
        self.assertFalse(self.github.calls or self.registry.calls)

    def test_search_persists_exact_fresh_cohort_without_granting_permissions(self):
        result = self.search()
        session = result["session"]
        self.assertEqual(session["state"], "comparison-needed")
        self.assertEqual(session["usage"]["network_reserved"], 80)
        self.assertEqual(session["runs"][0]["connector_calls"], len(self.github.calls) + len(self.registry.calls))
        self.assertEqual(result["model_request"]["decision_request"]["context"]["research_session"]["id"], session["runs"][0]["id"])
        self.assertFalse(self.service.policy()["allow_repositories"])
        self.assertFalse(self.service.lock()["installations"])

    def test_one_shared_budget_caps_github_and_registry_and_partial_is_visible(self):
        result = self.search(self.propose(self.start(network_requests=1)))
        self.assertEqual(len(self.github.calls), 1)
        self.assertFalse(self.registry.calls)
        self.assertEqual(result["session"]["runs"][0]["connector_calls"], 1)
        self.assertTrue(result["session"]["runs"][0]["partial"])
        self.assertIn("github-discovery-errors", result["session"]["runs"][0]["issues"])
        decision = result["model_request"]["decision_request"]["suggested_decision"]
        reviewed = self.driver.submit(result["session"]["id"], result["model_request"]["request_id"], {"action": "decide", "decision": decision})
        self.assertIn("incomplete-runtime-research", [item["rule"] for item in reviewed["blueprint"]["blockers"]])

    def test_complete_model_exchange_previews_but_requires_independent_install_approval(self):
        result = self.search()
        session_id = result["session"]["id"]
        decision = copy.deepcopy(result["model_request"]["decision_request"]["suggested_decision"])
        decision["reason"] = "Keep focused ownership; reviewed resources do not justify an external dependency for this small API."
        for binding in decision["bindings"]:
            binding["skills"], binding["mcps"] = [], []
        reviewed = self.driver.submit(session_id, result["model_request"]["request_id"], {"action": "decide", "decision": decision})
        self.assertEqual(reviewed["session"]["state"], "review-required")
        self.assertFalse(self.service.lock()["installations"])
        self.assertFalse(reviewed["environment_applied_by_session"])
        run_id = reviewed["session"]["runs"][-1]["id"]
        self.service.blueprint(decision, reviewed["blueprint"]["approval"], True, run_id)
        self.assertTrue(self.service.verify()["ok"])

    def test_refinement_requires_new_approval_and_never_blends_rounds(self):
        result = self.search()
        session_id = result["session"]["id"]
        plan = model_plan(self.service, github=False)
        plan["mcp_queries"][0]["term"] = "Qdrant retrieval"
        refined = self.driver.submit(session_id, result["model_request"]["request_id"], {"action": "refine", "plan": plan})
        before = len(self.github.calls) + len(self.registry.calls)
        self.assertEqual(refined["session"]["state"], "awaiting-search-approval")
        self.assertEqual(len(self.github.calls) + len(self.registry.calls), before)
        self.registry.records[0]["server"]["name"] = "io.github.example/refined"
        second = self.search(refined)
        cohort = second["model_request"]["decision_request"]["context"]
        self.assertEqual(len(second["session"]["runs"]), 2)
        self.assertEqual(second["session"]["usage"]["network_reserved"], 160)
        self.assertFalse(cohort["skills"])
        self.assertTrue(all(item["name"].endswith("refined") for item in cohort["mcps"]))
        with self.assertRaisesRegex(StratagentError, "proposal rejected"):
            self.driver.submit(session_id, second["model_request"]["request_id"], {"action": "refine", "plan": plan})

    def test_search_is_not_replayed_by_duplicate_approval(self):
        proposed = self.propose()
        self.search(proposed)
        before = len(self.github.calls) + len(self.registry.calls)
        with self.assertRaisesRegex(StratagentError, "not awaiting"):
            self.search(proposed)
        self.assertEqual(len(self.github.calls) + len(self.registry.calls), before)

    def test_interrupt_reserves_budget_and_resume_demands_new_plan_and_approval(self):
        proposed = self.propose(github=False)
        session_id = proposed["session"]["id"]
        with patch.object(self.registry, "search", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.search(proposed)
        interrupted = self.driver.status(session_id)
        self.assertEqual(interrupted["session"]["state"], "interrupted")
        self.assertEqual(interrupted["session"]["usage"]["network_reserved"], 80)
        resumed = self.driver.resume(session_id)
        self.assertEqual(resumed["session"]["usage"], interrupted["session"]["usage"])
        self.assertEqual(resumed["model_request"]["allowed_actions"], ["research", "clarify"])
        replacement = self.propose(resumed, github=False)
        with self.assertRaisesRegex(StratagentError, "approval"):
            self.driver.search(session_id, proposed["search_review"]["approval"])
        self.assertNotEqual(replacement["search_review"]["approval"], proposed["search_review"]["approval"])

    def test_cancellation_during_search_stops_next_call_and_cannot_be_overwritten(self):
        proposed = self.propose()
        session_id = proposed["session"]["id"]
        original = self.github.get

        def cancel_after_first(endpoint, params=None):
            self.driver.cancel(session_id)
            return original(endpoint, params)

        with patch.object(self.github, "get", side_effect=cancel_after_first), self.assertRaises(StratagentError):
            self.search(proposed)
        state = self.driver.status(session_id)["session"]
        self.assertEqual(state["state"], "cancelled")
        self.assertEqual(len(self.github.calls), 1)
        self.assertFalse(self.registry.calls)
        self.assertFalse(state["runs"])

    def test_crashed_search_checkpoint_resumes_without_replay(self):
        proposed = self.propose()
        state = proposed["session"]
        self.driver._transition(state, "searching", "search-started", usage={**state["usage"], "search_rounds": 1, "network_reserved": 80})
        result = self.driver.resume(state["id"])
        self.assertEqual(result["session"]["state"], "research-needed")
        self.assertEqual(result["session"]["usage"]["network_reserved"], 80)
        self.assertFalse(self.github.calls or self.registry.calls)

    def test_cancel_is_idempotent_and_cannot_reset_exhausted_budgets(self):
        result = self.search(self.propose(self.start(search_rounds=1)))
        session_id = result["session"]["id"]
        self.driver.cancel(session_id)
        before = file_state(self.root)
        self.driver.cancel(session_id)
        self.assertEqual(before, file_state(self.root))
        with self.assertRaisesRegex(StratagentError, "budget exhausted"):
            self.driver.resume(session_id)

    def test_expiration_and_changed_context_fail_closed_but_status_is_readable(self):
        result = self.start()
        session_id = result["session"]["id"]
        with patch("stratagent.orchestration.time.time", return_value=result["session"]["deadline_at"]):
            self.assertTrue(self.driver.status(session_id)["expired"])
            with self.assertRaisesRegex(StratagentError, "expired"):
                self.driver.request(session_id)
            with self.assertRaisesRegex(StratagentError, "expired"):
                self.driver.resume(session_id)
        (self.root / "requirements.txt").write_text("qdrant-client\n")
        with self.assertRaisesRegex(StratagentError, "context changed"):
            self.driver.request(session_id)

    def test_tampered_state_and_unsafe_session_paths_are_rejected(self):
        result = self.start()
        session_id = result["session"]["id"]
        path = self.driver._path(session_id)
        value = self.service.ws.read(path)
        value["usage"]["model_turns"] = 0
        value["limits"]["model_turns"] = 16
        self.service.ws.write(path, value)
        with self.assertRaisesRegex(StratagentError, "state changed"):
            self.driver.status(session_id)
        for unsafe in ("../manifest", "a" * 33, None):
            with self.subTest(unsafe=unsafe), self.assertRaises(StratagentError):
                self.driver.status(unsafe)

    def test_default_mcp_remains_readonly_and_scoped_mode_has_no_network_or_authority_tools(self):
        started = self.start()
        regular = Server(self.root)
        with self.assertRaises(RPCError):
            regular.call_tool("stratagent_session_submit", {})
        scoped = Server(self.root, started["session"]["id"])
        self.assertEqual({item["name"] for item in scoped.tools}, {"stratagent_session_request", "stratagent_session_submit"})
        self.assertFalse(scoped.tools[1]["annotations"]["readOnlyHint"])
        for forbidden in ("stratagent_discover", "stratagent_discover_mcp", "session-search", "allow", "blueprint"):
            with self.subTest(forbidden=forbidden), self.assertRaises(RPCError):
                scoped.call_tool(forbidden, {})
        result = scoped.call_tool("stratagent_session_submit", {"request_id": started["model_request"]["request_id"],
                                 "response": {"action": "research", "plan": model_plan(self.service)}})
        self.assertFalse(result["isError"])
        self.assertFalse(self.github.calls or self.registry.calls)
        with self.assertRaises(RPCError):
            scoped.call_tool("stratagent_session_request", {"session_id": "b" * 32})

    def test_scoped_stdio_roundtrip_saves_only_validated_proposal(self):
        started = self.start()
        messages = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "stratagent_session_submit", "arguments": {
                        "request_id": started["model_request"]["request_id"], "response": {"action": "research", "plan": model_plan(self.service)}}}}]
        output = io.StringIO()
        serve(self.root, io.StringIO("\n".join(json.dumps(message) for message in messages)), output, started["session"]["id"])
        replies = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(replies), 3)
        self.assertEqual(len(replies[1]["result"]["tools"]), 2)
        self.assertFalse(replies[2]["result"]["isError"])
        self.assertFalse(self.service.lock()["installations"])

    def test_network_timeout_clamps_remaining_lifetime_and_rejects_further_calls(self):
        with patch("stratagent.orchestration.time.monotonic", return_value=100):
            budget = NetworkBudget(1, 2, lambda: None)
        opener = unittest.mock.Mock()
        guarded = TimedOpener(opener, budget)
        with patch("stratagent.orchestration.time.monotonic", return_value=101):
            budget.take()
            guarded.open("fixed-request", timeout=20)
            opener.open.assert_called_once_with("fixed-request", timeout=1)
            with self.assertRaisesRegex(StratagentError, "network budget"):
                budget.take()
        with patch("stratagent.orchestration.time.monotonic", return_value=102):
            with self.assertRaisesRegex(StratagentError, "time budget"):
                guarded.open("fixed-request")

    def test_cli_start_submit_review_and_logging_boundaries(self):
        def command(arguments):
            output, errors = io.StringIO(), io.StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                code = main(["--workspace", str(self.root), "--log-json", *arguments])
            return code, output.getvalue(), errors.getvalue()

        code, output, errors = command(["session-start", PROMPT, "--platforms", "generic"])
        self.assertEqual(code, 0)
        started = json.loads(output)
        session_id = started["session"]["id"]
        self.assertNotIn("Qdrant", errors)
        response = {"action": "research", "plan": model_plan(self.service)}
        self.service.ws.write("response.json", response)
        code, output, errors = command(["session-submit", session_id, "--request-id", started["model_request"]["request_id"], "--response", "response.json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["session"]["state"], "awaiting-search-approval")
        self.assertEqual(command(["session-search", session_id, "--approve-search", "wrong"])[0], 2)
        self.assertEqual(command(["blueprint", "--session", session_id])[0], 2)
        self.assertFalse(self.github.calls or self.registry.calls)
        compared = self.driver.search(session_id, json.loads(output)["search_review"]["approval"])
        decision = compared["model_request"]["decision_request"]["suggested_decision"]
        self.driver.submit(session_id, compared["model_request"]["request_id"], {"action": "decide", "decision": decision})
        code, output, errors = command(["blueprint", "--session", session_id, "--content"])
        self.assertEqual(code, 0)
        self.assertIn("file_contents", json.loads(output))
        self.assertEqual(command(["blueprint", "--session", session_id, "--run", compared["session"]["runs"][-1]["id"]])[0], 2)

    def test_session_symlink_and_concurrent_transition_are_refused(self):
        started = self.start()
        state = started["session"]
        self.driver.cancel(state["id"])
        with self.assertRaisesRegex(StratagentError, "concurrently"):
            self.driver._transition(state, "research-needed", "resumed")
        path = self.service.ws.path(self.driver._path(state["id"]))
        saved = path.with_suffix(".saved")
        path.rename(saved)
        path.symlink_to(saved)
        with self.assertRaisesRegex(StratagentError, "Symlinks"):
            self.driver.status(state["id"])

    def test_inconsistent_checkpoint_is_actionable_even_with_a_matching_digest(self):
        result = self.start()
        session_id = result["session"]["id"]
        path = self.driver._path(session_id)
        value = self.service.ws.read(path)
        value["state"] = "review-required"
        value["events"][-1]["state"] = "review-required"
        value["digest"] = identity({key: item for key, item in value.items() if key != "digest"})
        self.service.ws.write(path, value)
        with self.assertRaisesRegex(StratagentError, "checkpoint"):
            self.driver.request(session_id)

    def test_host_targets_are_context_not_driver_branches_and_cross_session_approval_fails(self):
        for targets in (["generic"], ["claude"], ["codex"], ["antigravity"], ["claude", "codex", "antigravity"]):
            with self.subTest(targets=targets), tempfile.TemporaryDirectory() as directory:
                service = Stratagent(directory, github=FakeGitHub(), registry=FakeRegistry())
                driver = Orchestrator(service)
                started = driver.start(PROMPT, targets)
                self.assertEqual(set(started["model_request"]["research_request"]["context"]["targets"]), set(targets))
                response = {"action": "research", "plan": model_plan(service)}
                first = driver.submit(started["session"]["id"], started["model_request"]["request_id"], response)
                second = driver.start(PROMPT, targets)
                second = driver.submit(second["session"]["id"], second["model_request"]["request_id"], response)
                with self.assertRaisesRegex(StratagentError, "approval"):
                    driver.search(second["session"]["id"], first["search_review"]["approval"])
                self.assertFalse(service.github.calls or service.registry.calls)
