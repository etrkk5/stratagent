"""Developer acceptance: offline package install/optional upgrade/uninstall.

Only an already reviewed local release bundle is installed in a disposable venv.
No user environment, host settings or production project is reused.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import venv

from release import ReleaseError, verify, wheel_info


def validate(bundle, previous=None):
    bundle = bundle.resolve()
    evidence = verify(bundle)
    report = json.loads((bundle / "release.json").read_bytes())
    application = bundle / report["application"]["filename"]
    if previous:
        previous = previous.resolve()
        old = wheel_info(previous)
        if old["name"].lower().replace("_", "-") != "stratagent-cli" or old["version"] == report["application"]["version"]:
            raise ReleaseError("Previous artifact must be a reviewed, different StratAgent version.")
    with tempfile.TemporaryDirectory(prefix="stratagent-distribution-") as temporary:
        temporary = Path(temporary)
        environment = {key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "PYTHONHOME")}
        venv.EnvBuilder(with_pip=True).create(temporary / "venv")
        scripts = temporary / "venv" / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        console = scripts / ("stratagent.exe" if os.name == "nt" else "stratagent")

        def run(arguments):
            result = subprocess.run([str(arg) for arg in arguments], cwd=temporary, env=environment, capture_output=True, timeout=90)
            if result.returncode:
                raise ReleaseError("Disposable distribution acceptance failed; no user project was modified.")
            return result.stdout

        def pip(*arguments):
            return run([python, "-m", "pip", "--isolated", "--disable-pip-version-check", *arguments])

        def snapshot(root):
            return {p.relative_to(root).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(), stat.S_IMODE(p.stat().st_mode))
                    for p in root.rglob("*") if p.is_file()}

        pip("install", "--no-index", "--find-links", bundle, previous or application)
        run([python, "-m", "pip", "check"])
        project = temporary / "project"
        project.mkdir()
        (project / "user-notes.md").write_text("Original user project notes.\n")
        (project / ".env").write_text("ORIGINAL_SYNTHETIC_FIXTURE=preserve\n")
        run([console, "demo", "--workspace", project, "--apply"])
        before = snapshot(project)
        if previous:
            pip("install", "--no-index", "--find-links", bundle, "--upgrade", application)
        if run([console, "--version"]).decode().strip() != report["application"]["version"]:
            raise ReleaseError("Installed console version differs from the release bundle.")
        verification = json.loads(run([console, "verify", "--workspace", project]))
        health = json.loads(run([console, "doctor", "--workspace", project, "--check-files"]))
        if not verification["ok"] or not health["ok"] or before != snapshot(project):
            raise ReleaseError("Package install/upgrade changed the project or failed verification.")
        run([python, "-m", "pip", "check"])
        pip("uninstall", "--yes", "stratagent-cli")
        run([python, "-c", "import importlib.util; assert importlib.util.find_spec('stratagent') is None"])
        if console.exists() or before != snapshot(project):
            raise ReleaseError("Uninstall did not remove the package or changed project files.")
        return {"ok": True, "case": "disposable-offline-distribution", "version": report["application"]["version"],
                "upgrade_from": old["version"] if previous else None, "managed_outputs": verification["checked"],
                "project_files_preserved": len(before), "package_uninstalled": True,
                "network_calls": 0, "host_activation": "none", "source_dirty": evidence["source_dirty"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--previous-wheel", type=Path, help="Optional separately reviewed older wheel; never downloaded")
    arguments = parser.parse_args()
    try:
        print(json.dumps(validate(arguments.bundle, arguments.previous_wheel), indent=2, sort_keys=True))
        return 0
    except (ReleaseError, OSError, ValueError, KeyError, subprocess.SubprocessError):
        print(json.dumps({"ok": False, "error": "Local distribution acceptance failed; user environments were not reused."}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
