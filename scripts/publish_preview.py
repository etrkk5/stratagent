"""Prepare/verify release assets from six successful, exact-commit CI bundles.

Local consistency checks only; the release workflow separately signs and verifies
GitHub provenance before publishing. No network, subprocesses or publishing here.
"""
import argparse
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import tomllib
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from release import ReleaseError, canonical, regular_bytes, safe_name, sha, verify

REPOSITORY = "etrkk5/stratagent"
MATRIX = tuple((os, python) for os in ("ubuntu-latest", "macos-latest", "windows-latest") for python in ("3.11", "3.14"))
BUNDLES = tuple(f"stratagent-preview-{os}-py{python}" for os, python in MATRIX)
JOBS = {f"unit ({os}, {python})" for os, python in MATRIX}


def identity(tag, commit):
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ReleaseError("Expected a vMAJOR.MINOR.PATCH tag and an exact Git commit.")
    return tag[1:]


def check_ci(run, jobs, commit):
    if (run.get("status") != "completed" or run.get("conclusion") != "success"
            or run.get("head_sha") != commit or run.get("head_branch") != "main"
            or run.get("event") != "push" or run.get("path") != ".github/workflows/tests.yml"
            or run.get("repository", {}).get("full_name") != REPOSITORY
            or type(run.get("id")) is not int or run["id"] <= 0):
        raise ReleaseError("Release requires a successful exact-commit main push from tests.yml.")
    records = jobs.get("jobs", [])
    if (jobs.get("total_count") != 6 or len(records) != 6 or {j.get("name") for j in records} != JOBS
            or any(j.get("status") != "completed" or j.get("conclusion") != "success" or j.get("head_sha") != commit for j in records)):
        raise ReleaseError("All six native jobs must pass at the same source commit.")


def write_new(output, payloads):
    if output.exists() or output.is_symlink():
        raise ReleaseError("Output exists; choose a new directory. Nothing is overwritten.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stratagent-promotion-", dir=output.parent) as temporary:
        stage = Path(temporary) / "assets"
        stage.mkdir()
        for name, data in payloads.items():
            (stage / name).write_bytes(data)
        if output.exists() or output.is_symlink():
            raise ReleaseError("Output appeared; refusing replacement.")
        stage.rename(output)


def prepare(source, downloads, output, run, jobs, tag, commit):
    version = identity(tag, commit)
    check_ci(run, jobs, commit)
    if tomllib.loads(regular_bytes(source / "pyproject.toml").decode())["project"]["version"] != version:
        raise ReleaseError("Tag does not match the reviewed package version.")
    if {p.name for p in downloads.iterdir()} != set(BUNDLES):
        raise ReleaseError("Exactly six named native bundles are required.")
    payloads, canonical_bundle = {}, None
    for name in BUNDLES:
        bundle = downloads / name
        if bundle.is_symlink() or not bundle.is_dir():
            raise ReleaseError("Bundle must be a real directory.")
        result = verify(bundle)
        receipt = json.loads(regular_bytes(bundle / "release.json"))
        if (result["version"] != version or result["source_dirty"] or receipt["source"]["commit"] != commit
                or receipt["source"]["sha256"] != sha(canonical(receipt["source"]["files"]))):
            raise ReleaseError("Bundle source/version does not match the passed main commit.")
        epoch = receipt["source_date_epoch"]
        if type(epoch) is not int or not 315532800 <= epoch <= 4102444800:
            raise ReleaseError("Invalid archive timestamp.")
        archive_name = f"stratagent-{version}-{name.removeprefix('stratagent-preview-')}.zip"
        stream = io.BytesIO()
        with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(bundle.iterdir()):
                info = ZipInfo(safe_name(path.name), time.gmtime(epoch)[:6])
                info.create_system, info.external_attr, info.compress_type = 3, 0o100644 << 16, ZIP_DEFLATED
                archive.writestr(info, regular_bytes(path))
        payloads[archive_name] = stream.getvalue()
        if name == BUNDLES[0]:
            canonical_bundle = archive_name
            distribution_names = [receipt["application"]["filename"]] + [a["filename"] for a in receipt["artifacts"] if a["filename"].endswith(".tar.gz")]
            if len(distribution_names) != 2:
                raise ReleaseError("Expected one wheel and one source archive.")
            for filename in distribution_names:
                payloads[filename] = regular_bytes(bundle / filename)
    manifest = {"schema_version": 1, "tag": tag, "version": version, "source_commit": commit,
                "ci_run_id": run["id"], "ci_url": f"https://github.com/{REPOSITORY}/actions/runs/{run['id']}",
                "canonical_bundle": canonical_bundle,
                "scope": "Developer preview; each native ZIP retains its own SBOM, dependency wheel and unsigned local receipt. External GitHub provenance is verified separately.",
                "assets": [{"filename": name, "sha256": sha(data), "size": len(data)} for name, data in sorted(payloads.items())]}
    payloads["RELEASE-MANIFEST.json"] = canonical(manifest)
    payloads["SHA256SUMS"] = "".join(f"{sha(data)}  {name}\n" for name, data in sorted(payloads.items())).encode()
    write_new(output, payloads)
    verify_assets(output, tag, commit)
    return manifest


def verify_assets(directory, tag, commit):
    version = identity(tag, commit)
    manifest = json.loads(regular_bytes(directory / "RELEASE-MANIFEST.json"))
    if (manifest.get("schema_version") != 1 or manifest.get("tag") != tag or manifest.get("version") != version
            or manifest.get("source_commit") != commit or type(manifest.get("ci_run_id")) is not int
            or manifest["ci_run_id"] <= 0 or manifest.get("ci_url") != f"https://github.com/{REPOSITORY}/actions/runs/{manifest['ci_run_id']}"):
        raise ReleaseError("Release manifest identity differs from the selected tag/commit.")
    names = {f"stratagent-{version}-{n.removeprefix('stratagent-preview-')}.zip" for n in BUNDLES}
    names |= {f"stratagent_cli-{version}-py3-none-any.whl", f"stratagent_cli-{version}.tar.gz"}
    inventory = manifest["assets"]
    if (len(inventory) != len(names) or {a["filename"] for a in inventory} != names
            or manifest.get("canonical_bundle") != f"stratagent-{version}-ubuntu-latest-py3.11.zip"
            or {p.name for p in directory.iterdir()} != names | {"SHA256SUMS", "RELEASE-MANIFEST.json"}):
        raise ReleaseError("Release asset set changed.")
    payloads = {}
    for name in sorted(names | {"RELEASE-MANIFEST.json"}):
        safe_name(name)
        payloads[name] = regular_bytes(directory / name)
    for item in inventory:
        data = payloads[item["filename"]]
        if item["size"] != len(data) or item["sha256"] != sha(data):
            raise ReleaseError("Release asset inventory mismatch.")
    if regular_bytes(directory / "SHA256SUMS") != "".join(f"{sha(data)}  {name}\n" for name, data in sorted(payloads.items())).encode():
        raise ReleaseError("Release checksum manifest changed.")
    return manifest


def pypi_inputs(directory, output, tag, commit):
    manifest = verify_assets(directory, tag, commit)
    version = manifest["version"]
    names = (f"stratagent_cli-{version}-py3-none-any.whl", f"stratagent_cli-{version}.tar.gz")
    write_new(output, {name: regular_bytes(directory / name) for name in names})
    return {"version": version, "distributions": list(names), "source_commit": commit}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify", "pypi-inputs"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ci-report", type=Path)
    parser.add_argument("--ci-jobs", type=Path)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.source, args.input, args.output, json.loads(regular_bytes(args.ci_report)), json.loads(regular_bytes(args.ci_jobs)), args.tag, args.source_sha)
        elif args.command == "pypi-inputs":
            result = pypi_inputs(args.input, args.output, args.tag, args.source_sha)
        else:
            result = verify_assets(args.input, args.tag, args.source_sha)
        print(json.dumps({"ok": True, "version": result["version"], "source_commit": result["source_commit"]}, sort_keys=True))
        return 0
    except (ReleaseError, OSError, ValueError, KeyError, TypeError, AttributeError):
        print(json.dumps({"ok": False, "error": "Release promotion inputs failed validation; nothing was published."}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
