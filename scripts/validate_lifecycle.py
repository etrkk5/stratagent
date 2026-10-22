"""Offline installed-CLI acceptance using only original generated instructions."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def validate(root):
    root.mkdir()
    settings = {".mcp.json": b'{"user_setting":true}\n', ".codex/config.toml": b'model = "user-managed"\n',
                ".agents/mcp_config.json": b'{"user_setting":true}\n', "project-notes.md": b"Keep this user file.\n"}
    for relative, data in settings.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    commands = 0

    def cli(*arguments):
        nonlocal commands
        commands += 1
        result = subprocess.run([sys.executable, "-m", "stratagent", "--workspace", str(root), *arguments], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError(f"Lifecycle acceptance command {arguments[0]} failed: {result.stderr[:1000]}")
        return json.loads(result.stdout)

    def apply(stage):
        return cli("apply", stage["stage_id"], "--approve", stage["plan"]["approval"])

    cli("init", "React frontend, Python API and PostgreSQL database with privacy and testing. No payments.", "--platforms", "claude,codex,antigravity,generic")
    initial = cli("stage", "blueprint")
    first = apply(initial)
    if not apply(initial).get("already_installed"):
        raise RuntimeError("Repeated approved stage was not idempotent.")
    revision = cli("stage", "revise", "--prompt", "Small Python API with privacy and testing. No frontend or payments.", "--platforms", "generic")
    apply(revision)
    update = cli("stage", "blueprint")
    if not any(entry["action"] == "delete" for entry in update["plan"]["lifecycle"]["changes"]):
        raise RuntimeError("Retarget/update did not propose obsolete managed-file removal.")
    updated = apply(update)
    verification = cli("verify")
    if not verification["ok"]:
        raise RuntimeError("Updated managed environment did not verify.")
    removal = cli("stage", "remove", "--key", "workspace-blueprint")
    removed = apply(removal)
    if not apply(removal).get("already_installed"):
        raise RuntimeError("Repeated removal stage was not effect-idempotent.")
    status = cli("status")
    if status["installations"] or not cli("verify")["ok"]:
        raise RuntimeError("Removal did not leave an empty verified managed environment.")
    if any((root / relative).read_bytes() != data for relative, data in settings.items()):
        raise RuntimeError("User-owned files/settings changed.")
    history = cli("transactions")
    return {"schema_version": 1, "case": "original-offline-cli-lifecycle", "workspace": str(root), "commands": commands,
            "initial_outputs": len(first["written"]), "updated_outputs": len(updated["written"]), "obsolete_outputs_removed": len(updated["removed"]),
            "final_outputs_removed": len(removed["removed"]), "preserved_user_files": len(settings), "transactions": len(history["transactions"]),
            "network_calls": 0, "third_party_executions": 0, "activation": "none", "ok": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, help="New, nonexistent disposable directory; never reuses an existing project")
    arguments = parser.parse_args()
    if arguments.workspace:
        result = validate(arguments.workspace.absolute())
    else:
        with tempfile.TemporaryDirectory(prefix="stratagent-lifecycle-") as temporary:
            result = validate(Path(temporary) / "workspace")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
