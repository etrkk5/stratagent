import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import io

import stratagent
from stratagent.common import StratagentError
from stratagent.orchestration import Orchestrator
from stratagent.github import GitHub
from stratagent.registry import Registry
from stratagent.service import Stratagent
from stratagent.planner import analyze
from test_runtime_research import PROMPT, model_plan


class PlanningRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = Stratagent(self.root)
        self.driver = Orchestrator(self.service)

    def clarify(self):
        result = self.driver.start(PROMPT, ["generic"])
        return self.driver.submit(result["session"]["id"], result["model_request"]["request_id"],
                                  {"action": "clarify", "questions": ["Which data may be sent to Qdrant, and what must stay local?"]})

    def worker(self, code, *arguments):
        environment = {**os.environ, "PYTHONPATH": str(Path(stratagent.__file__).resolve().parent.parent)}
        process = subprocess.Popen([sys.executable, "-c", code, str(self.root), *arguments], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        def cleanup():
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
            process.stdout.close()
            process.stderr.close()

        self.addCleanup(cleanup)
        ready, _, _ = select.select([process.stdout], [], [], 10)
        self.assertTrue(ready, "Worker did not reach its durable checkpoint.")
        line = process.stdout.readline().strip()
        self.assertEqual(line, "ready", process.stderr.read() if process.poll() is not None else "Worker checkpoint was not reached.")
        return process

    def test_clarification_pauses_without_search_and_only_operator_changes_scope(self):
        result = self.clarify()
        session_id = result["session"]["id"]
        self.assertEqual(result["session"]["state"], "clarification-needed")
        with self.assertRaisesRegex(StratagentError, "Answer the model"):
            self.driver.resume(session_id)
        revised = PROMPT + " Use only synthetic data; exclude personal data and payments."
        answered = self.driver.answer(session_id, revised)
        self.assertEqual(answered["session"]["state"], "research-needed")
        self.assertEqual(answered["session"]["usage"], result["session"]["usage"])
        self.assertNotEqual(answered["session"]["project_digest"], result["session"]["project_digest"])
        self.assertEqual(self.service.manifest()["analysis"]["prompt"], revised)
        self.assertTrue(answered["session"]["answer_checkpoint"]["completed"])
        self.assertFalse(self.service.lock()["installations"])

    def test_clarification_checkpoint_recovers_identical_answer_after_write_failure(self):
        result = self.clarify()
        session_id = result["session"]["id"]
        revised = PROMPT + " Synthetic data only."
        original = self.service.ws.write

        def fail_completion(path, value):
            if "/orchestrations/" in path and value.get("state") == "research-needed":
                raise OSError("simulated interrupted metadata write")
            return original(path, value)

        with patch.object(self.service.ws, "write", side_effect=fail_completion), self.assertRaises(OSError):
            self.driver.answer(session_id, revised)
        self.assertEqual(self.driver.status(session_id)["session"]["state"], "answer-pending")
        with self.assertRaisesRegex(StratagentError, "session-answer"):
            self.driver.request(session_id)
        with self.assertRaisesRegex(StratagentError, "exact revised prompt"):
            self.driver.answer(session_id, revised + " A different answer.")
        recovered = self.driver.answer(session_id, revised)
        self.assertEqual(recovered["session"]["state"], "research-needed")
        self.assertEqual(recovered["session"]["usage"]["model_turns"], 1)

    def test_clarification_never_mutates_an_installed_environment(self):
        initial = self.driver.start(PROMPT, ["generic"])
        prepared = self.service.prepare(PROMPT, offline=True)
        self.service.blueprint(approval=prepared["blueprint"]["approval"], apply=True, run_id=prepared["research_run"]["id"])
        clarified = self.driver.submit(initial["session"]["id"], initial["model_request"]["request_id"],
                                       {"action": "clarify", "questions": ["Should the project scope change?"]})
        manifest = self.service.manifest()
        with self.assertRaisesRegex(StratagentError, "installed outputs"):
            self.driver.answer(clarified["session"]["id"], PROMPT + " No payments.")
        self.assertEqual(self.service.manifest(), manifest)
        self.assertEqual(self.driver.status(initial["session"]["id"])["session"]["state"], "clarification-needed")
        self.assertTrue(self.service.verify()["ok"])

    def test_small_total_budget_leaves_a_separately_approved_refinement_share(self):
        result = self.driver.start(PROMPT, ["generic"], network_requests=20, search_rounds=2)
        proposed = self.driver.submit(result["session"]["id"], result["model_request"]["request_id"], {"action": "research", "plan": model_plan(self.service, github=False)})
        self.assertEqual(proposed["search_review"]["reserved_connector_calls"], 10)

    def test_real_connector_quota_and_outage_exceptions_remain_partial_and_sanitized(self):
        github, registry = GitHub(token=""), Registry()
        service = Stratagent(self.root, github=github, registry=registry)
        driver = Orchestrator(service)
        result = driver.start(PROMPT, ["generic"])
        plan = model_plan(service)
        proposed = driver.submit(result["session"]["id"], result["model_request"]["request_id"], {"action": "research", "plan": plan})
        error = HTTPError("https://api.github.com", 429, "private upstream text", {}, io.BytesIO(b"secret-provider-body"))
        with patch.object(github.opener, "open", side_effect=error) as github_open, patch.object(registry.opener, "open", side_effect=URLError("secret-provider-body")) as registry_open:
            compared = driver.search(result["session"]["id"], proposed["search_review"]["approval"])
        self.assertEqual(github_open.call_count, 1)
        self.assertEqual(registry_open.call_count, 1)
        self.assertTrue(compared["session"]["runs"][-1]["partial"])
        self.assertIn("github-discovery-errors", compared["session"]["runs"][-1]["issues"])
        self.assertIn("registry-discovery-errors", compared["session"]["runs"][-1]["issues"])
        diagnostics = compared["session"]["runs"][-1]["diagnostics"]
        self.assertEqual({item["stage"] for item in diagnostics}, {"github", "mcp-registry"})
        self.assertTrue(any("rate limit" in item["message"] for item in diagnostics))
        self.assertNotIn("secret-provider-body", json.dumps(compared))
        decision = compared["model_request"]["decision_request"]["suggested_decision"]
        reviewed = driver.submit(result["session"]["id"], compared["model_request"]["request_id"], {"action": "decide", "decision": decision})
        self.assertIn("incomplete-runtime-research", [item["rule"] for item in reviewed["blueprint"]["blockers"]])

    def test_clarification_preserves_multiline_human_request_and_stales_old_approvals(self):
        result = self.driver.start(PROMPT, ["generic"])
        plan = model_plan(self.service)
        old_search = self.service.preview_research(plan)["search_approval"]
        clarification = self.driver.submit(result["session"]["id"], result["model_request"]["request_id"], {"action": "clarify", "questions": ["Which deployment is required?"]})
        revised = PROMPT + "\nDeployment is a private development container."
        answered = self.driver.answer(clarification["session"]["id"], revised)
        self.assertIn("\n", self.service.manifest()["analysis"]["prompt"])
        self.assertNotEqual(answered["model_request"]["request_id"], result["model_request"]["request_id"])
        with self.assertRaisesRegex(StratagentError, "stale"):
            self.service.prepare(revised, research_plan=plan, approve_search=old_search)
        self.assertFalse(self.service.lock()["installations"])

    def test_legacy_directory_lock_is_never_guessed_to_be_stale(self):
        self.service.init(PROMPT, ["generic"])
        legacy = self.root / ".stratagent/.write-lock"
        legacy.mkdir()
        with self.assertRaisesRegex(StratagentError, "Another write"):
            with self.service.ws.mutation():
                pass
        self.assertTrue(legacy.is_dir())

    def test_bilingual_testing_scope_tracks_each_offline_occurrence_not_whole_quote(self):
        examples = {"Testler çevrimdışı çalışmalı.": "testing", "Tests must run offline.": "testing",
                    "Offline tests are required.": "testing", "Çevrimdışı testler gerekli.": "testing",
                    "The whole project must run offline with offline tests.": "project",
                    "Testler gerekli. Uygulama çevrimdışı çalışmalı.": "project"}
        for prompt, expected in examples.items():
            with self.subTest(prompt=prompt):
                requirement = next(item for item in analyze(prompt)["requirements"] if item["id"] == "offline")
                self.assertEqual(requirement["scope"], expected)

    def test_explicit_payment_exclusions_survive_english_and_turkish_variants(self):
        for prompt in ("Do not add payment functionality.", "Don't implement payments.", "Ödeme entegrasyonu içermeyecek."):
            with self.subTest(prompt=prompt):
                requirement = next(item for item in analyze(prompt)["requirements"] if item["id"] == "payments")
                self.assertEqual(requirement["status"], "excluded")

    def test_rejected_proposal_returns_actionable_validation_reason_without_saving_it(self):
        started = self.driver.start(PROMPT, ["generic"])
        with self.assertRaisesRegex(StratagentError, "Unsupported model action"):
            self.driver.submit(started["session"]["id"], started["model_request"]["request_id"], {"action": "execute"})
        self.assertNotIn("Unsupported model action", json.dumps(self.driver.status(started["session"]["id"])))

    @unittest.skipUnless(os.name == "posix", "POSIX process-death lock recovery; Windows remains outside the validated scope")
    def test_sigkill_releases_workspace_mutex_without_manual_lock_deletion(self):
        self.service.init(PROMPT, ["generic"])
        process = self.worker("import sys,time\nfrom stratagent.workspace import Workspace\nwith Workspace(sys.argv[1]).mutation():\n print('ready',flush=True)\n time.sleep(120)\n")
        with self.assertRaisesRegex(StratagentError, "Another write"):
            with self.service.ws.mutation():
                pass
        process.kill()
        process.wait(timeout=10)
        with self.service.ws.mutation():
            self.service.ws.write(".stratagent/recovered.json", {"recovered": True})
        self.assertTrue(self.service.ws.read(".stratagent/recovered.json")["recovered"])

    @unittest.skipUnless(os.name == "posix", "POSIX forced-process termination")
    def test_sigkill_during_network_wait_retains_reservation_and_never_replays(self):
        started = self.driver.start(PROMPT, ["generic"])
        proposed = self.driver.submit(started["session"]["id"], started["model_request"]["request_id"], {"action": "research", "plan": model_plan(self.service, github=False)})
        session_id = started["session"]["id"]
        code = "import sys,time\nfrom stratagent.service import Stratagent\nfrom stratagent.orchestration import Orchestrator\nclass Paused:\n def search(self,*args):\n  print('ready',flush=True)\n  time.sleep(120)\nOrchestrator(Stratagent(sys.argv[1],registry=Paused())).search(sys.argv[2],sys.argv[3])\n"
        process = self.worker(code, session_id, proposed["search_review"]["approval"])
        process.kill()
        process.wait(timeout=10)
        state = self.driver.status(session_id)["session"]
        self.assertEqual(state["state"], "searching")
        self.assertEqual(state["usage"]["network_reserved"], 80)
        resumed = self.driver.resume(session_id)
        self.assertEqual(resumed["session"]["usage"], state["usage"])
        self.assertEqual(resumed["session"]["state"], "research-needed")
        self.assertFalse(resumed["session"]["runs"])
        with self.assertRaisesRegex(StratagentError, "not awaiting"):
            self.driver.search(session_id, proposed["search_review"]["approval"])

    @unittest.skipUnless(os.name == "posix", "POSIX forced-process termination")
    def test_sigkill_between_answer_metadata_writes_recovers_exact_intent(self):
        clarified = self.clarify()
        session_id = clarified["session"]["id"]
        revised = PROMPT + " Synthetic data only."
        code = "import sys,time\nfrom stratagent.service import Stratagent\nfrom stratagent.orchestration import Orchestrator\nservice=Stratagent(sys.argv[1])\noriginal=service.ws.write\ndef paused(path,value):\n if '/orchestrations/' in path and value.get('state')=='research-needed':\n  print('ready',flush=True)\n  time.sleep(120)\n return original(path,value)\nservice.ws.write=paused\nOrchestrator(service).answer(sys.argv[2],sys.argv[3])\n"
        process = self.worker(code, session_id, revised)
        process.kill()
        process.wait(timeout=10)
        self.assertEqual(self.driver.status(session_id)["session"]["state"], "answer-pending")
        recovered = self.driver.answer(session_id, revised)
        self.assertEqual(recovered["session"]["state"], "research-needed")
        self.assertEqual(recovered["session"]["usage"], clarified["session"]["usage"])


if __name__ == "__main__":
    unittest.main()
