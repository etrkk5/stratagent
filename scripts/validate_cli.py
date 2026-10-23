"""Portable offline CLI smoke test; no shell syntax or fixed temporary paths."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def validate():
    def cli(root, *arguments, proposal=None):
        result = subprocess.run([sys.executable, "-m", "stratagent", "--workspace", str(root), *arguments],
                                input=json.dumps(proposal) if proposal is not None else None, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError(f"CLI smoke {arguments[0]} failed: {result.stderr[:1000]}")
        return json.loads(result.stdout)

    with tempfile.TemporaryDirectory(prefix="stratagent-cli-") as temporary:
        root = Path(temporary)
        adapters = cli(root / "absent", "platforms")["platforms"]
        if (root / "absent").exists() or len(adapters) != 4 or any(
                adapter["contract_schema_version"] != 1 or adapter["host_runtime_certified"]
                or adapter["scope"] != "inert-file-generation" for adapter in adapters):
            raise RuntimeError("Adapter catalog must be versioned, read-only and explicit about runtime limits.")
        health = cli(root, "doctor")
        capabilities = health["filesystem"]
        if not health["ok"] or health["writes"] or health["network_calls"]:
            raise RuntimeError("Offline health check must succeed without mutation or network access.")
        if not capabilities["local_transactions"]:
            raise RuntimeError("CI filesystem backend does not support transactions.")
        cli(root, "plan", "FastAPI and React dashboard with authentication and privacy", "--scan-project")
        demo = cli(root / "demo", "demo", "--apply")
        verified = cli(root / "demo", "verify")
        if not demo["applied"] or not verified["ok"] or verified["checked"] != 46:
            raise RuntimeError("Installed original demo did not verify 46 outputs.")
        lock = json.loads((root / "demo/.stratagent/lock.json").read_text(encoding="utf-8"))
        for installation in lock["installations"].values():
            selected = installation["adapter_contracts"]
            if selected != [adapter for adapter in adapters if adapter["id"] in installation["platforms"]]:
                raise RuntimeError("Installed provenance must retain the exact selected adapter contracts.")
        health = cli(root / "demo", "doctor", "--check-files")
        if not health["ok"] or not any(check["id"] == "managed-outputs" and check["status"] == "pass" for check in health["checks"]):
            raise RuntimeError("Installed demo health must include successful managed-output verification.")
        project = root / "blueprint"
        project.mkdir()
        prompt = "Small Python API without payments"
        cli(project, "init", prompt, "--platforms", "generic")
        cli(project, "decision-request")
        cli(project, "blueprint", "--content")
        cli(project, "prepare", prompt, "--platforms", "generic", "--offline")
        cli(project, "research-request", prompt)
        started = cli(project, "session-start", prompt, "--platforms", "generic", "--model-turns", "2", "--search-rounds", "1", "--network-requests", "1", "--seconds", "60")
        if started["session"]["state"] != "research-needed":
            raise RuntimeError("Bounded session smoke did not pause for model input.")
        # Original controlled assessment fixture; no host model is launched.
        minimal = root / "keep-existing"
        definition = minimal / ".agents/skills/api-testing/SKILL.md"
        definition.parent.mkdir(parents=True)
        original = b'---\nname: api-testing\ndescription: Python API testing and regression review.\n---\nKeep this user-owned skill.\n'
        definition.write_bytes(original)
        card = cli(minimal, "start", "Build a Python API with tests. No payments.", "--platforms", "codex", "--json")
        details = cli(minimal, "next", "--details", "--json")
        request = details["details"]["model_request"]
        fit = request["fit_request"]
        reference = fit["environment"]["files"][0]["evidence_id"]
        proposal = {"schema_version": 1, "context_digest": fit["context_digest"], "environment_digest": fit["environment_digest"],
                    "outcome": "keep", "reason": "The current host and observed test skill cover this fixture's needs without additional extensions.",
                    "needs": [{"need": "Test the Python API", "quote": "Python API with tests", "status": "existing",
                               "reason": "The existing project-local testing definition is sufficient for this controlled review fixture.",
                               "evidence_refs": ["request", reference], "existing": [reference]}],
                    "alternatives": ["Research another testing resource only if a concrete coverage gap appears."]}
        cli(minimal, "session-submit", card["session_id"], "--request-id", request["request_id"], "--response-stdin",
            proposal={"action": "assess", "assessment": proposal})
        review = cli(minimal, "next", "--json")
        cli(minimal, "session-accept-fit", card["session_id"], "--approve", review["fit_review"]["approval"])
        kept = cli(minimal, "next", "--json")
        status = cli(minimal, "session-status", card["session_id"])
        generated = [p for p in minimal.rglob("*") if p.is_file() and ".stratagent" not in p.relative_to(minimal).parts]
        if (kept["phase"] != "kept" or definition.read_bytes() != original or generated != [definition]
                or status["session"]["usage"] != {"model_turns": 1, "search_rounds": 0, "network_reserved": 0}
                or cli(minimal, "verify")["checked"] != 0):
            raise RuntimeError("No-change assessment must retain the fixture without installing files or performing searches.")
        return {"ok": True, "filesystem": capabilities, "demo_outputs": verified["checked"], "network_calls": 0, "activation": "none",
                "fit": {"outcome": "keep", "synthetic_assessment": True, "model_proposals": 1, "search_rounds": 0,
                        "new_environment_files": 0, "preserved_user_files": 1}}


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
