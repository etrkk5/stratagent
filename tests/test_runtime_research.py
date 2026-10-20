import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from stratagent.common import StratagentError
from stratagent.demo import sample_snapshot
from stratagent.github import GitHub
from stratagent.mcp import RPCError, Server
from stratagent.service import Stratagent
from test_architect import FakeRegistry
from test_stratagent import FakeGitHub, file_state

PROMPT = "Build a small Qdrant retrieval API with privacy."


def model_plan(service, github=True, mcp=True, prompt=PROMPT, targets=None):
    request = service.research_request(prompt, targets)
    grounding = {"reason": "Retrieval needs a project-specific public tool search.", "quote": "Qdrant retrieval API", "evidence_refs": ["request"]}
    return {"schema_version": 1, "context_digest": request["context"]["context_digest"], "reason": "Research the actual requested retrieval technology rather than fixed Python catalogs.",
            "github_queries": [{"kind": "skills", "terms": ["Qdrant", "skill"], **grounding}] if github else [],
            "mcp_queries": [{"term": "qdrant", **grounding}] if mcp else [],
            "budgets": {"repositories": 2, "definitions": 2, "mcp_results": 2}}


class RuntimeResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.github, self.registry = FakeGitHub(), FakeRegistry()
        self.service = Stratagent(self.root, github=self.github, registry=self.registry)

    def plan(self, github=True, mcp=True):
        return model_plan(self.service, github, mcp, targets=["generic"])

    def execute(self, plan):
        preview = self.service.preview_research(plan, PROMPT, ["generic"])
        return self.service.prepare(PROMPT, ["generic"], research_plan=plan, approve_search=preview["search_approval"])

    def test_unknown_public_technology_is_valid_and_preview_has_no_side_effects(self):
        before = file_state(self.root)
        plan = self.plan()
        preview = self.service.preview_research(plan, PROMPT, ["generic"])
        self.assertIn('"Qdrant" "skill"', preview["github_queries"][0]["query"])
        self.assertFalse(preview["network_executed"])
        self.assertEqual(file_state(self.root), before)
        self.assertFalse(self.github.calls)
        self.assertFalse(self.registry.calls)

    def test_missing_or_wrong_search_approval_cannot_initialize_or_use_network(self):
        plan = self.plan()
        for approval in (None, "yes", "0" * 64):
            with self.subTest(approval=approval), self.assertRaisesRegex(StratagentError, "search approval"):
                self.service.prepare(PROMPT, ["generic"], research_plan=plan, approve_search=approval)
            self.assertFalse((self.root / ".stratagent").exists())
        self.assertFalse(self.github.calls)
        self.assertFalse(self.registry.calls)

    def test_approval_binds_workspace_queries_budgets_targets_and_context(self):
        plan = self.plan()
        original = self.service.preview_research(plan, PROMPT, ["generic"])["search_approval"]
        for change in ("query", "budget", "reason"):
            changed = copy.deepcopy(plan)
            if change == "query":
                changed["github_queries"][0]["terms"] = ["OpenTelemetry", "skill"]
            elif change == "budget":
                changed["budgets"]["repositories"] = 3
            else:
                changed["reason"] = "A separately reviewed search rationale."
            self.assertNotEqual(original, self.service.preview_research(changed, PROMPT, ["generic"])["search_approval"])
        with tempfile.TemporaryDirectory() as other:
            self.assertNotEqual(original, Stratagent(other).preview_research(plan, PROMPT, ["generic"])["search_approval"])
        with self.assertRaisesRegex(StratagentError, "stale"):
            self.service.preview_research(plan, PROMPT, ["codex"])

    def test_changed_project_manifest_invalidates_research_plan(self):
        plan = self.plan()
        (self.root / "requirements.txt").write_text("fastapi\n")
        with self.assertRaisesRegex(StratagentError, "stale"):
            self.service.preview_research(plan, PROMPT, ["generic"])

    def test_research_schema_rejects_authority_fields_credentials_and_unsupported_queries(self):
        original = self.plan()
        proposals = [{**original, "command": "execute"}, {**original, "approve": True}]
        for term in ("https://evil.example", "user:private", "token\nvalue", "ghp_" + "A" * 32):
            changed = copy.deepcopy(original)
            changed["github_queries"][0]["terms"] = [term]
            proposals.append(changed)
        changed = copy.deepcopy(original)
        changed["github_queries"][0]["quote"] = "Fabricated project text"
        proposals.append(changed)
        changed = copy.deepcopy(original)
        changed["github_queries"].append(copy.deepcopy(changed["github_queries"][0]))
        proposals.append(changed)
        changed = copy.deepcopy(original)
        changed["budgets"]["repositories"] = True
        proposals.append(changed)
        for proposal in proposals:
            with self.subTest(proposal=proposal), self.assertRaises(StratagentError):
                self.service.preview_research(proposal, PROMPT, ["generic"])

    def test_approved_plan_drives_connectors_and_does_not_add_seed_repositories(self):
        result = self.execute(self.plan())
        searches = [params for endpoint, params in self.github.calls if endpoint.startswith("/search/")]
        self.assertEqual(len(searches), 1)
        self.assertIn("Qdrant", searches[0]["q"])
        self.assertEqual(len(result["github_discovery"]["inspected_repositories"]), 1)
        self.assertEqual(result["github_discovery"]["research"]["query_origin"], "reviewed-runtime-plan")
        self.assertEqual([query for query, _ in self.registry.calls], ["qdrant"])
        self.assertEqual(result["github_discovery"]["coverage"]["repository_limit"], 2)
        self.assertFalse(self.service.policy()["allow_repositories"])
        self.assertFalse(self.service.lock()["installations"])

    def test_mcp_only_and_github_only_plans_do_not_make_unapproved_fallback_calls(self):
        for github, mcp in ((True, False), (False, True)):
            with self.subTest(github=github), tempfile.TemporaryDirectory() as root:
                client, registry = FakeGitHub(), FakeRegistry()
                service = Stratagent(root, github=client, registry=registry)
                plan = model_plan(service, github, mcp, targets=["generic"])
                approval = service.preview_research(plan, PROMPT, ["generic"])["search_approval"]
                service.prepare(PROMPT, ["generic"], research_plan=plan, approve_search=approval)
                self.assertEqual(bool(client.calls), github)
                self.assertEqual(bool(registry.calls), mcp)

    def test_offline_plan_and_orphan_approval_are_rejected_before_initialization(self):
        for settings in ({"research_plan": self.plan(), "offline": True}, {"approve_search": "0" * 64}):
            with self.assertRaises(StratagentError):
                self.service.prepare(PROMPT, ["generic"], **settings)
            self.assertFalse((self.root / ".stratagent").exists())

    def test_new_live_run_does_not_mix_previous_cached_candidates(self):
        self.service.init(PROMPT, ["generic"])
        old = self.service.import_snapshot(sample_snapshot())
        self.github.snap["repo"] = "original/current-run"
        result = self.execute(self.plan(mcp=False))
        self.assertIn(old["id"], self.service.manifest()["candidates"])
        self.assertNotIn(old["id"], {item["id"] for item in result["decision_request"]["context"]["skills"]})
        self.assertNotIn(old["id"], {item["id"] for item in result["research_run"]["skills"]})

    def test_failed_live_refresh_never_falls_back_to_cached_success(self):
        self.service.init(PROMPT, ["generic"])
        self.service.import_snapshot(sample_snapshot())
        with patch.object(self.github, "research", side_effect=StratagentError("Provider unavailable")):
            result = self.execute(self.plan(mcp=False))
        self.assertEqual(result["research_run"]["mode"], "live")
        self.assertTrue(result["research_run"]["partial"])
        self.assertFalse(result["decision_request"]["context"]["skills"])
        self.assertTrue(any(item["rule"] == "incomplete-runtime-research" for item in result["blueprint"]["blockers"]))
        with self.assertRaisesRegex(StratagentError, "blockers"):
            self.service.blueprint(approval=result["blueprint"]["approval"], apply=True, run_id=result["research_run"]["id"])

    def test_offline_run_labels_cached_evidence_without_claiming_freshness(self):
        self.service.init(PROMPT, ["generic"])
        old = self.service.import_snapshot(sample_snapshot())
        with patch.object(self.github, "get", side_effect=AssertionError("No network")):
            result = self.service.prepare(PROMPT, offline=True)
        self.assertEqual(result["research_run"]["mode"], "offline-cache")
        self.assertFalse(result["blueprint"]["source"]["blueprint"]["freshness"]["live_run"])
        self.assertIn(old["id"], {item["id"] for item in result["decision_request"]["context"]["skills"]})

    def test_new_registry_run_excludes_previous_cached_mcp_records(self):
        self.service.init(PROMPT, ["generic"])
        old = self.service.discover_mcp("original")["candidates"][0]
        self.registry.records[0]["server"]["name"] = "io.github.example/current-qdrant"
        result = self.execute(self.plan(github=False))
        self.assertIn(old["id"], self.service.manifest()["mcp_candidates"])
        self.assertNotIn(old["id"], {item["id"] for item in result["decision_request"]["context"]["mcps"]})
        self.assertNotIn(old["id"], {item["id"] for item in result["research_run"]["mcps"]})

    def test_run_identity_binds_decisions_and_installation_approval(self):
        first = self.execute(self.plan(mcp=False))
        second = self.execute(self.plan(mcp=False))
        self.assertNotEqual(first["research_run"]["id"], second["research_run"]["id"])
        with self.assertRaisesRegex(StratagentError, "stale"):
            self.service.blueprint(first["decision_request"]["suggested_decision"], run_id=second["research_run"]["id"])
        self.service.allow(self.github.snap["repo"])
        with self.assertRaisesRegex(StratagentError, "Approval digest"):
            self.service.blueprint(approval=first["blueprint"]["approval"], apply=True)

    def test_expired_run_cannot_preview_or_apply_but_installed_outputs_still_verify(self):
        result = self.service.prepare(PROMPT, ["generic"], offline=True)
        run = result["research_run"]
        self.service.blueprint(approval=result["blueprint"]["approval"], apply=True, run_id=run["id"])
        self.assertTrue(self.service.status()["approved_blueprint"]["context_current"])
        with patch("stratagent.sessions.time.time", return_value=run["expires_at"]):
            for apply in (False, True):
                with self.assertRaisesRegex(StratagentError, "expired"):
                    self.service.blueprint(approval=result["blueprint"]["approval"], apply=apply, run_id=run["id"])
            status = self.service.status()
            self.assertFalse(status["approved_blueprint"]["context_current"])
            self.assertIn("expired", status["approved_blueprint"]["context_error"])
            self.assertTrue(self.service.verify()["ok"])

    def test_research_run_context_source_tampering_and_unknown_ids_fail_closed(self):
        result = self.execute(self.plan(mcp=False))
        run_id = result["research_run"]["id"]
        for value in ("../escape", "0" * 32, None, True):
            if value is None:
                continue
            with self.subTest(value=value), self.assertRaises(StratagentError):
                self.service.blueprint(run_id=value)
        path = f".stratagent/runs/{run_id}.json"
        record = self.service.ws.read(path)
        self.service.ws.write(path, {**record, "partial": 1})
        with self.assertRaises(StratagentError):
            self.service.blueprint(run_id=run_id)
        self.service.ws.write(path, record)
        (self.root / "requirements.txt").write_text("pandas\n")
        with self.assertRaisesRegex(StratagentError, "changed since research"):
            self.service.blueprint(run_id=run_id)

    def test_source_refresh_invalidates_old_run_reference(self):
        result = self.execute(self.plan(mcp=False))
        changed = copy.deepcopy(self.github.snap)
        changed["commit"] = "e" * 40
        self.service.import_snapshot(changed)
        with self.assertRaisesRegex(StratagentError, "source changed"):
            self.service.blueprint(run_id=result["research_run"]["id"])

    def test_research_mcp_tools_are_readonly_and_cannot_grant_egress(self):
        self.service.init(PROMPT, ["generic"])
        server = Server(self.root)
        before = file_state(self.root)
        request = server.call_tool("stratagent_research_request", {})
        self.assertFalse(request["isError"])
        preview = server.call_tool("stratagent_research_preview", {"plan": self.plan()})
        self.assertFalse(preview["isError"])
        self.assertEqual(file_state(self.root), before)
        with self.assertRaises(RPCError):
            server.call_tool("stratagent_research_preview", {"plan": self.plan(), "approve_search": "yes"})

    def test_research_search_approval_never_authorizes_installation(self):
        plan = self.plan(mcp=False)
        approval = self.service.preview_research(plan, PROMPT, ["generic"])["search_approval"]
        result = self.execute(plan)
        self.service.allow(self.github.snap["repo"])
        with self.assertRaisesRegex(StratagentError, "Approval digest"):
            self.service.blueprint(approval=approval, apply=True, run_id=result["research_run"]["id"])


class RuntimeBoundaryTests(unittest.TestCase):
    def test_mutable_github_metadata_is_not_cached_between_observations(self):
        client = GitHub(token="")
        with patch.object(client.opener, "open", side_effect=lambda *args, **kwargs: io.BytesIO(b'{"items": []}')) as network:
            client.get("/search/repositories", {"q": "Qdrant"})
            client.get("/search/repositories", {"q": "Qdrant"})
            client.get("/repos/original/repo")
            client.get("/repos/original/repo")
            client.get("/repos/original/repo/commits/main")
            client.get("/repos/original/repo/commits/main")
        self.assertEqual(network.call_count, 6)

    def test_immutable_git_content_can_be_reused(self):
        client = GitHub(token="")
        with patch.object(client.opener, "open", side_effect=lambda *args, **kwargs: io.BytesIO(b'{"content": "original"}')) as network:
            endpoint = "/repos/original/repo/git/blobs/" + "a" * 40
            client.get(endpoint)
            client.get(endpoint)
        self.assertEqual(network.call_count, 1)

    def test_cli_runtime_run_preview_approval_and_verify(self):
        with tempfile.TemporaryDirectory() as root:
            environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
            def command(*arguments):
                return subprocess.run([sys.executable, "-m", "stratagent", *arguments, "--workspace", root], env=environment, text=True, capture_output=True, timeout=15)
            prepared = command("prepare", PROMPT, "--platforms", "generic", "--offline")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            result = json.loads(prepared.stdout)
            run_id = result["research_run"]["id"]
            preview = command("blueprint", "--run", run_id, "--content")
            self.assertEqual(json.loads(preview.stdout)["approval"], result["blueprint"]["approval"])
            applied = command("blueprint", "--run", run_id, "--apply", "--approve", result["blueprint"]["approval"])
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertTrue(json.loads(command("verify").stdout)["ok"])
