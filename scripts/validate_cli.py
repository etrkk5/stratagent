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
        capabilities = cli(root, "doctor")["filesystem"]
        if not capabilities["local_transactions"]:
            raise RuntimeError("CI filesystem backend does not support transactions.")
        cli(root, "plan", "FastAPI and React dashboard with authentication and privacy", "--scan-project")
        demo = cli(root / "demo", "demo", "--apply")
        verified = cli(root / "demo", "verify")
        if not demo["applied"] or not verified["ok"] or verified["checked"] != 46:
            raise RuntimeError("Installed original demo did not verify 46 outputs.")
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
