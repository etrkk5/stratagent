import json
import os
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
from stratagent.hosts import ADAPTERS, HostAdapter, catalog, platforms
from stratagent.planner import analyze
from stratagent.registry import assess_server, render_server
from stratagent.security import assess, unpack
from stratagent.service import MANIFEST, Stratagent


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
