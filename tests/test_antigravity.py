import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from stratagent.adapters import platforms, render_bundle, render_tasks
from stratagent.common import StratagentError
from stratagent.demo import demo, sample_snapshot
from stratagent.planner import analyze
from stratagent.registry import assess_server, render_server
from stratagent.security import assess, metadata, unpack
from stratagent.service import MANIFEST, Stratagent


def server_review(remote=False):
    server = {"name": "io.github.example/test-server", "version": "1.0.0", "description": "Test tools for Python.",
              "repository": {"url": "https://github.com/example/test-server"}}
    if remote:
        server["remotes"] = [{"type": "streamable-http", "url": "https://mcp.example.com/mcp"}]
    else:
        server["packages"] = [{"registryType": "npm", "identifier": "@example/test-server", "version": "1.2.3", "transport": {"type": "stdio"}}]
    return assess_server({"server": server, "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active"}}})


class AntigravityAdaptersTests(unittest.TestCase):
    def test_target_is_valid_and_unknown_names_remain_errors(self):
        self.assertEqual(platforms(["antigravity", "codex", "antigravity"]), ["antigravity", "codex"])
        with self.assertRaises(StratagentError):
            platforms(["antgravity"])

    def test_skills_share_codex_paths_and_identical_content(self):
        snapshot = sample_snapshot()
        review = assess(snapshot)
        antigravity = render_bundle(review, unpack(snapshot), ["antigravity"])
        codex = render_bundle(review, unpack(snapshot), ["codex"])
        combined = render_bundle(review, unpack(snapshot), ["antigravity", "codex"])
        self.assertEqual(antigravity, codex)
        self.assertEqual(combined, codex)
        self.assertIn(".agents/skills/python-review/references/checklist.md", combined)
        metadata(combined[".agents/skills/python-review/SKILL.md"].decode())
        self.assertTrue(any("stratagent-notices" in path for path in combined))

    def test_native_agents_limit_tools_and_strip_upstream_provider_metadata(self):
        snapshot = sample_snapshot("subagent")
        review = assess(snapshot)
        files = render_bundle(review, unpack(snapshot), ["antigravity"])
        definition = files[f".agents/agents/sa-{review['id']}.md"].decode()
        header = definition.split("---", 2)[1]
        self.assertIn("tools: [view_file, grep_search]", header)
        self.assertIn('commandExecutionPolicy: "off"', header)
        self.assertIn("mainAgent: false", header)
        self.assertIn("subagent: true", header)
        for forbidden in ("run_command", "replace_file_content", "permissionMode", "Read, Grep", "mcpServers", "hooks"):
            self.assertNotIn(forbidden, header)
        self.assertTrue(any(path.startswith(".stratagent/notices/antigravity/") for path in files))
        self.assertFalse(any(path.endswith("SKILL.md") for path in files))

    def test_native_task_roles_preserve_dependencies_and_handoffs(self):
        analysis = analyze("Python API with privacy")
        files = render_tasks({"analysis": analysis, "assignments": []}, ["antigravity"])
        self.assertEqual(len(files), len(analysis["tasks"]))
        self.assertTrue(all(path.startswith(".agents/agents/") for path in files))
        security = files[".agents/agents/sa-security-reviewer.md"].decode()
        self.assertIn("Dependencies: build", security)
        self.assertIn("Handoff:", security)
        self.assertIn("Write policy:", security)

    def test_mcp_http_proposal_uses_server_url_and_is_disabled(self):
        files = render_server(server_review(True), 0, ["antigravity"])
        path = next(path for path in files if path.endswith("antigravity.mcp_config.json"))
        entry = next(iter(json.loads(files[path])["mcpServers"].values()))
        self.assertEqual(entry, {"serverUrl": "https://mcp.example.com/mcp", "disabled": True})
        self.assertTrue(all(path.startswith(".stratagent/proposals/") for path in files))

    def test_mcp_stdio_proposal_pins_version_and_is_disabled(self):
        files = render_server(server_review(), 0, ["antigravity"])
        entry = next(iter(json.loads(next(data for path, data in files.items() if path.endswith("antigravity.mcp_config.json")))["mcpServers"].values()))
        self.assertEqual(entry, {"command": "npx", "args": ["--yes", "@example/test-server@1.2.3"], "disabled": True})


class AntigravityWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.forge = Stratagent(self.root)
        self.forge.init("Python API testing", ["antigravity"])

    def install_original(self, kind):
        candidate = self.forge.import_snapshot(sample_snapshot(kind))
        self.forge.allow(candidate["repo"])
        plan = self.forge.install(candidate["id"])
        self.forge.install(candidate["id"], plan["approval"], True)
        return candidate

    def test_install_configure_and_repeat_preserve_existing_host_settings(self):
        self.install_original("skill")
        candidate = self.install_original("subagent")
        settings = self.root / ".agents/mcp_config.json"
        settings.write_text('{"mcpServers":{"user-server":{"disabled":true}}}')
        original = settings.read_bytes()
        preview = self.forge.configure()
        test_assignment = next(assignment for assignment in preview["source"]["task_plan"]["assignments"] if assignment["task_id"] == "test")
        self.assertTrue(any(f".agents/agents/sa-{candidate['id']}.md" in resource["paths"] for resource in test_assignment["resources"]))
        self.forge.configure(preview["approval"], True)
        self.assertTrue(self.forge.configure(preview["approval"], True)["already_installed"])
        self.assertTrue(self.forge.verify()["ok"])
        self.assertEqual(settings.read_bytes(), original)
        self.assertFalse((self.root / ".claude").exists())

    def test_shared_skill_paths_still_bind_distinct_platform_targets_to_approval(self):
        candidate = self.forge.import_snapshot(sample_snapshot())
        before = self.forge.install(candidate["id"])
        manifest = self.forge.manifest()
        manifest["platforms"] = ["antigravity", "codex"]
        self.forge.ws.write(MANIFEST, manifest)
        after = self.forge.install(candidate["id"])
        self.assertEqual(before["outputs"], after["outputs"])
        self.assertNotEqual(before["approval"], after["approval"])
        self.forge.allow(candidate["repo"])
        with self.assertRaisesRegex(StratagentError, "Approval digest"):
            self.forge.install(candidate["id"], before["approval"], True)

    def test_antigravity_symlink_parent_is_refused(self):
        candidate = self.forge.import_snapshot(sample_snapshot("subagent"))
        self.forge.allow(candidate["repo"])
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / ".agents").mkdir()
        (self.root / ".agents/agents").symlink_to(outside, target_is_directory=True)
        plan = self.forge.install(candidate["id"])
        with self.assertRaisesRegex(StratagentError, "Symlinks"):
            self.forge.install(candidate["id"], plan["approval"], True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_approved_mcp_proposal_never_writes_active_settings(self):
        class OriginalRegistry:
            def search(self, query, limit=6):
                return [{"server": {"name": "io.github.example/remote", "version": "1.0.0", "description": "Original test metadata",
                                     "remotes": [{"type": "streamable-http", "url": "https://mcp.example.com/mcp"}]},
                         "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active"}}}]
        self.forge.registry = OriginalRegistry()
        candidate = self.forge.discover_mcp("remote")["candidates"][0]
        preview = self.forge.configure_mcp(candidate["id"])
        self.assertFalse((self.root / ".agents/mcp_config.json").exists())
        self.forge.configure_mcp(candidate["id"], approval=preview["approval"], apply=True)
        self.assertTrue(self.forge.configure_mcp(candidate["id"], approval=preview["approval"], apply=True)["already_installed"])
        self.assertTrue(self.forge.verify()["ok"])
        self.assertFalse((self.root / ".agents/mcp_config.json").exists())

    def test_offline_demo_includes_all_three_hosts(self):
        with tempfile.TemporaryDirectory() as root:
            result = demo(root, apply=True)
            self.assertTrue(result["verification"]["ok"])
            self.assertTrue((Path(root) / ".agents/agents/sa-architect.md").exists())
            self.assertTrue((Path(root) / ".agents/skills/sa-architect/SKILL.md").exists())
            self.assertTrue((Path(root) / ".claude/agents/sa-architect.md").exists())

    def test_cli_defaults_and_explicit_antigravity_target(self):
        environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
        for targets in ([], ["--platforms", "antigravity"]):
            with tempfile.TemporaryDirectory() as root:
                result = subprocess.run([sys.executable, "-m", "stratagent", "init", "Python API", "--workspace", root, *targets],
                                        env=environment, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = json.loads(result.stdout)["platforms"]
                self.assertEqual(actual, ["antigravity"] if targets else ["antigravity", "claude", "codex"])


if __name__ == "__main__":
    unittest.main()
