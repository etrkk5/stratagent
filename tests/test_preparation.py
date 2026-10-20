import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from stratagent.common import StratagentError
from stratagent.service import Stratagent
from test_architect import FakeRegistry, file_state
from test_discovery import BroadGitHub


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.github, self.registry = BroadGitHub(), FakeRegistry()
        self.service = Stratagent(self.root, github=self.github, registry=self.registry)

    def test_one_idea_researches_sources_and_previews_an_environment_without_installing(self):
        result = self.service.prepare("React frontend and FastAPI API with PostgreSQL and privacy", ["codex"])
        self.assertEqual(result["status"], "review-required")
        self.assertFalse(result["environment_applied"])
        self.assertEqual(len(result["github_discovery"]["inspected_repositories"]), 12)
        self.assertTrue(result["available_resources"]["eligible_skills_or_roles"])
        self.assertEqual([query for query, _ in self.registry.calls], ["postgres", "playwright", "openapi"])
        self.assertEqual(result["decision_request"]["context"]["context_digest"], result["blueprint"]["source"]["blueprint"]["context_digest"])
        self.assertFalse((self.root / ".agents").exists())
        self.assertFalse((self.root / ".stratagent/blueprint.json").exists())
        self.assertFalse(self.service.lock()["installations"])
        self.assertEqual(self.service.policy()["allow_repositories"], [])
        self.assertTrue(result["blueprint"]["missing_repository_allowances"])

    def test_offline_mode_never_calls_network_and_keeps_existing_targets(self):
        self.service.init("Small Python API", ["generic"])
        with patch.object(self.github, "get", side_effect=AssertionError("No network")), patch.object(self.registry, "search", side_effect=AssertionError("No network")):
            result = self.service.prepare("Small Python API", offline=True)
        self.assertIsNone(result["github_discovery"])
        self.assertFalse(result["mcp_discovery"])
        self.assertEqual(result["decision_request"]["context"]["targets"], ["generic"])
        self.assertTrue(result["unassisted_roles"])
        self.assertTrue(result["discovery_skips"])

    def test_project_offline_scope_skips_registry_but_can_review_github_documents(self):
        result = self.service.prepare("Small Python API with offline operation", ["generic"])
        self.assertTrue(result["github_discovery"]["candidates"])
        self.assertFalse(self.registry.calls)
        self.assertTrue(result["discovery_skips"])
        self.assertTrue(all(not role["binding"]["mcps"] for role in result["blueprint"]["source"]["blueprint"]["roles"]))

    def test_network_failures_return_visible_partial_results_not_a_ready_claim(self):
        with patch.object(self.github, "research", side_effect=StratagentError("GitHub unreachable")), patch.object(self.registry, "search", side_effect=StratagentError("Registry unavailable")):
            result = self.service.prepare("Small Python API", ["generic"])
        self.assertEqual({item["stage"] for item in result["errors"]}, {"github", "mcp-registry"})
        self.assertEqual(result["status"], "review-required")
        self.assertEqual(result["available_resources"]["skills_or_roles"], 0)
        self.assertFalse(result["environment_applied"])

    def test_existing_request_or_target_changes_never_reset_workspace(self):
        self.service.init("Small Python API", ["generic"])
        before = file_state(self.root)
        for prompt, targets in (("Different request", None), ("Small Python API", ["codex"])):
            with self.subTest(prompt=prompt), self.assertRaisesRegex(StratagentError, "never resets"):
                self.service.prepare(prompt, targets, offline=True)
            self.assertEqual(file_state(self.root), before)

    def test_invalid_inputs_do_not_initialize_or_contact_sources(self):
        for settings in ({"limit": 0}, {"repo_limit": 21}, {"mcp_limit": True}, {"offline": "yes"}, {"targets": ["unsupported"]}):
            with self.subTest(settings=settings), self.assertRaises(StratagentError):
                self.service.prepare("Small Python API", **settings)
            self.assertFalse((self.root / ".stratagent").exists())
        self.assertEqual(self.github.search_count, 0)
        self.assertFalse(self.registry.calls)

    def test_repeat_preparation_adds_a_run_but_repeats_the_same_run_without_output_changes(self):
        result = self.service.prepare("Small Python API without payments", ["generic"], offline=True)
        before = file_state(self.root)
        repeated = self.service.prepare("Small Python API without payments", offline=True)
        self.assertEqual({path: data for path, data in file_state(self.root).items() if "/runs/" not in path}, {path: data for path, data in before.items() if "/runs/" not in path})
        self.assertNotEqual(result["research_run"]["id"], repeated["research_run"]["id"])
        self.assertNotEqual(result["blueprint"]["approval"], repeated["blueprint"]["approval"])
        run_id = result["research_run"]["id"]
        self.service.blueprint(approval=result["blueprint"]["approval"], apply=True, run_id=run_id)
        self.assertTrue(self.service.blueprint(approval=result["blueprint"]["approval"], apply=True, run_id=run_id)["already_installed"])
        self.assertTrue(self.service.verify()["ok"])

    def test_uncertain_scope_is_not_hidden_by_preparation(self):
        result = self.service.prepare("Python API with optional payments", ["generic"], offline=True)
        self.assertTrue(any(item["rule"] == "unresolved-scope" for item in result["blueprint"]["blockers"]))

    def test_cli_prepare_is_one_prompt_and_does_not_expose_apply_authority(self):
        environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
        command = [sys.executable, "-m", "stratagent", "prepare", "Small Python API without payments", "--workspace", str(self.root), "--platforms", "generic", "--offline"]
        result = subprocess.run(command, env=environment, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "review-required")
        denied = subprocess.run(command + ["--apply"], env=environment, text=True, capture_output=True, timeout=15)
        self.assertNotEqual(denied.returncode, 0)
        self.assertFalse((self.root / ".stratagent/blueprint.json").exists())
