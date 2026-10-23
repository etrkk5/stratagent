"""Portable offline CLI smoke test; no shell syntax or fixed temporary paths."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def validate():
    def cli(root, *arguments):
        result = subprocess.run([sys.executable, "-m", "stratagent", "--workspace", str(root), *arguments], capture_output=True, text=True, timeout=30)
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
        return {"ok": True, "filesystem": capabilities, "demo_outputs": verified["checked"], "network_calls": 0, "activation": "none"}


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
