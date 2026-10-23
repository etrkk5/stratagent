"""Build/verify an unsigned, reproducible developer-preview bundle offline.

Requires the reviewed requirements-build.txt environment and one local runtime
dependency wheel. Never downloads, publishes, signs or changes a workspace.
"""
import argparse
import base64
import csv
from email.parser import BytesParser
import gzip
import hashlib
import io
import json
from importlib import metadata
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from zipfile import BadZipFile, ZipFile

LIMIT = 64 * 1024 * 1024
MAX_FILES = 2000
TOOLS = {"setuptools": "84.1.0", "wheel": "0.48.0", "packaging": "26.3"}
ROOT_FILES = {"pyproject.toml", "requirements-build.txt", "MANIFEST.in", "README.md", "LICENSE",
              "THIRD_PARTY_NOTICES.md", ".gitignore", ".gitattributes"}
ROOT_DIRS = {"src", "tests", "scripts", "docs", "examples", ".github"}


class ReleaseError(Exception):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(value):
    if (not value or len(value) > 500 or any(ord(c) < 32 for c in value)
            or any(c in value for c in "\\:\x7f") or value.startswith("/")
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise ReleaseError("Unsafe archive/source path.")
    devices = {"con", "prn", "aux", "nul", "conin$", "conout$", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
    if any(p.endswith((".", " ")) or p.lower().split(".")[0].rstrip(" ") in devices for p in value.split("/")):
        raise ReleaseError("Nonportable archive/source path.")
    return value


def regular_bytes(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > LIMIT:
        raise ReleaseError("Expected a bounded regular input file.")
    with path.open("rb") as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ReleaseError("Input file exceeds the release limit.")
    return data


def run(arguments, cwd, env=None):
    result = subprocess.run(arguments, cwd=cwd, env=env, capture_output=True, timeout=180)
    if result.returncode:
        raise ReleaseError("Release subprocess failed; inspect the reviewed source/tooling locally.")
    return result.stdout


def source_snapshot(root, allow_dirty):
    if Path(run(["git", "rev-parse", "--show-toplevel"], root).decode().strip()).resolve() != root:
        raise ReleaseError("Source must be the repository root.")
    dirty = bool(run(["git", "status", "--porcelain", "--untracked-files=all"], root))
    if dirty and not allow_dirty:
        raise ReleaseError("Commit/review source changes first; --allow-dirty is developer-only evidence.")
    names = run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], root).decode().split("\0")
    files = {}
    for name in sorted(set(filter(None, names))):
        safe_name(name)
        parts = PurePosixPath(name).parts
        if ((len(parts) == 1 and name not in ROOT_FILES) or (len(parts) > 1 and parts[0] not in ROOT_DIRS)
                or any(p.startswith(".env") or p in (".stratagent", ".venv", "__pycache__") or p.endswith(".egg-info") for p in parts)):
            raise ReleaseError("Unexpected/private source input; review the explicit release source allowlist.")
        current = root
        for part in parts:
            current = current / part
            if current.is_symlink():
                raise ReleaseError("Redirected source inputs are unsupported.")
        files[name] = regular_bytes(current)
    if len(files) > MAX_FILES or sum(map(len, files.values())) > LIMIT:
        raise ReleaseError("Release source budget exceeded.")
    commit = run(["git", "rev-parse", "HEAD"], root).decode().strip()
    epoch = int(run(["git", "show", "-s", "--format=%ct", "HEAD"], root))
    inventory = [{"path": p, "sha256": sha(d), "size": len(d)} for p, d in files.items()]
    return files, {"commit": commit, "dirty": dirty, "sha256": sha(canonical(inventory)), "files": inventory}, epoch


def canonical_sdist(path, epoch):
    """Normalize only generated sdist container metadata; preserve every file byte."""
    files, seen, total = {}, set(), 0
    with tarfile.open(path, "r:gz") as archive:
        for index, member in enumerate(archive):
            if index >= MAX_FILES:
                raise ReleaseError("Source archive member limit exceeded.")
            name = safe_name(member.name.rstrip("/") if member.isdir() else member.name)
            if name.casefold() in seen or not (member.isfile() or member.isdir()):
                raise ReleaseError("Duplicate, redirected or nonregular source archive entry.")
            seen.add(name.casefold())
            if member.isdir():
                continue
            total += member.size
            if member.size < 0 or total > LIMIT:
                raise ReleaseError("Source archive byte limit exceeded.")
            stream = archive.extractfile(member)
            files[name] = stream.read(member.size + 1)
            if len(files[name]) != member.size:
                raise ReleaseError("Truncated source archive.")
    roots = {name.split("/")[0] for name in files}
    if len(roots) != 1 or any("/" not in name for name in files):
        raise ReleaseError("Source archive needs one project root.")
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=epoch) as zipped:
        with tarfile.open(fileobj=zipped, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, data in sorted(files.items()):
                member = tarfile.TarInfo(name)
                member.size, member.mode, member.mtime = len(data), 0o644, epoch
                archive.addfile(member, io.BytesIO(data))
    return output.getvalue(), files


def wheel_info(path):
    """Verify full RECORD coverage before deriving the distribution-level inventory."""
    payload = regular_bytes(path)
    with ZipFile(io.BytesIO(payload)) as archive:
        files, folded, total = {}, set(), 0
        if len(archive.infolist()) > MAX_FILES:
            raise ReleaseError("Wheel member limit exceeded.")
        for item in archive.infolist():
            name = safe_name(item.filename.rstrip("/") if item.is_dir() else item.filename)
            if name.casefold() in folded or stat.S_ISLNK(item.external_attr >> 16):
                raise ReleaseError("Duplicate or symlink wheel entry.")
            folded.add(name.casefold())
            if item.is_dir():
                continue
            total += item.file_size
            if total > LIMIT:
                raise ReleaseError("Wheel expansion limit exceeded.")
            files[name] = archive.read(item)
        records = [p for p in files if p.endswith(".dist-info/RECORD")]
        if len(records) != 1:
            raise ReleaseError("Wheel must contain one RECORD.")
        record = records[0]
        covered = set()
        for row in csv.reader(io.StringIO(files[record].decode())):
            if len(row) != 3 or row[0] in covered or row[0] not in files:
                raise ReleaseError("Invalid wheel RECORD coverage.")
            name, checksum, size = row
            covered.add(name)
            if name == record:
                if checksum or size:
                    raise ReleaseError("RECORD cannot hash itself.")
            elif (checksum != "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(files[name]).digest()).decode().rstrip("=")
                  or size != str(len(files[name]))):
                raise ReleaseError("Wheel RECORD content mismatch.")
        if covered != set(files):
            raise ReleaseError("Wheel RECORD does not cover all files.")
        directory = record.rsplit("/", 1)[0]
        info = BytesParser().parsebytes(files[directory + "/METADATA"])
        name, version = info["Name"], info["Version"]
        if (len(info.get_all("Name", [])) != 1 or len(info.get_all("Version", [])) != 1
                or not name or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name) or not version or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)):
            raise ReleaseError("Unsupported package identity.")
        license_id = info["License-Expression"] or info["License"]
        licenses = [{"path": p, "sha256": sha(data)} for p, data in sorted(files.items())
                    if p.startswith(directory + "/") and ("/licenses/" in p or p.rsplit("/", 1)[-1] == "LICENSE")]
        if license_id != "MIT" or not licenses:
            raise ReleaseError("This release contract requires declared MIT distributions with license evidence.")
        return {"filename": path.name, "name": name, "version": version, "sha256": sha(payload),
                "size": len(payload), "license": license_id, "license_files": licenses,
                "requires_dist": sorted(info.get_all("Requires-Dist", [])),
                "files": [{"path": p, "sha256": sha(d), "size": len(d)} for p, d in sorted(files.items())]}


def validate_closure(application, dependency):
    normalized = lambda s: re.sub(r"[-_.]+", "-", s).lower()
    if (normalized(application["name"]) != "stratagent-cli" or normalized(dependency["name"]) != "pyyaml"
            or dependency["version"] != "6.0.3" or dependency["requires_dist"]
            or [re.sub(r"\s+", "", r).lower() for r in application["requires_dist"]] != ["pyyaml==6.0.3"]):
        raise ReleaseError("Unsupported or incomplete Python distribution dependency closure.")


def sbom(application, dependency, source):
    def component(info, kind):
        name = re.sub(r"[-_.]+", "-", info["name"]).lower()
        ref = f"pkg:pypi/{name}@{info['version']}"
        return {"type": kind, "bom-ref": ref, "name": info["name"], "version": info["version"], "purl": ref,
                "hashes": [{"alg": "SHA-256", "content": info["sha256"]}], "licenses": [{"expression": info["license"]}]}
    root, dep = component(application, "application"), component(dependency, "library")
    return {"$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json", "bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
            "metadata": {"component": root, "properties": [
                {"name": "stratagent:source-sha256", "value": source["sha256"]},
                {"name": "stratagent:inventory-scope", "value": "Selected Python distribution wheels only; not native-library, OS, vulnerability or build-tool closure."}]},
            "components": [dep], "dependencies": [{"ref": root["bom-ref"], "dependsOn": [dep["bom-ref"]]}, {"ref": dep["bom-ref"], "dependsOn": []}]}


def verify(directory):
    sums = regular_bytes(directory / "SHA256SUMS").decode().splitlines()
    expected = {}
    for line in sums:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match[2] in expected or match[2] == "SHA256SUMS":
            raise ReleaseError("Invalid checksum manifest.")
        expected[match[2]] = match[1]
    if set(expected) != {p.name for p in directory.iterdir()} - {"SHA256SUMS"}:
        raise ReleaseError("Release bundle file set changed.")
    for name, checksum in expected.items():
        if sha(regular_bytes(directory / name)) != checksum:
            raise ReleaseError("Release bundle checksum mismatch.")
    report = json.loads(regular_bytes(directory / "release.json"))
    if report.get("schema_version") != 1 or report.get("signed") is not False or report.get("reproducible") is not True:
        raise ReleaseError("Invalid release evidence contract.")
    artifacts = report["artifacts"]
    if any(safe_name(item["filename"]) != Path(item["filename"]).name for item in artifacts):
        raise ReleaseError("Artifact path must be a filename.")
    names = {item["filename"] for item in artifacts}
    if (len(artifacts) != 3 or len(names) != 3 or set(expected) != names | {"release.json", "sbom.cdx.json"}
            or report["application"]["filename"] not in names or report["dependency"]["filename"] not in names
            or report["application"]["filename"] == report["dependency"]["filename"]
            or type(report["source"]["dirty"]) is not bool or report.get("toolchain") != TOOLS):
        raise ReleaseError("Release artifact/source/toolchain contract changed.")
    for item in artifacts:
        actual = regular_bytes(directory / item["filename"])
        if item["sha256"] != sha(actual) or item["size"] != len(actual):
            raise ReleaseError("Artifact inventory mismatch.")
    application = wheel_info(directory / report["application"]["filename"])
    dependency = wheel_info(directory / report["dependency"]["filename"])
    validate_closure(application, dependency)
    if application != report["application"] or dependency != report["dependency"]:
        raise ReleaseError("Wheel inventory changed.")
    if json.loads(regular_bytes(directory / "sbom.cdx.json")) != sbom(application, dependency, report["source"]):
        raise ReleaseError("SBOM does not match the inspected wheels/source.")
    return {"ok": True, "version": application["version"], "artifacts": len(artifacts), "signed": False,
            "source_dirty": report["source"]["dirty"], "scope": "Local byte consistency; checksums are not publisher authentication."}


def build(root, output, wheelhouse, allow_dirty=False):
    root, output = root.resolve(), output.absolute()
    if output.exists() or output.is_symlink():
        raise ReleaseError("Output already exists; choose a new directory. Nothing is overwritten.")
    for name, version in TOOLS.items():
        if metadata.version(name) != version:
            raise ReleaseError("Install the exact requirements-build.txt toolchain first.")
    if tomllib.loads((root / "pyproject.toml").read_text())["build-system"]["requires"] != ["setuptools==84.1.0"]:
        raise ReleaseError("Build backend pin changed; review the release toolchain contract.")
    files, source, default_epoch = source_snapshot(root, allow_dirty)
    value = os.environ.get("SOURCE_DATE_EPOCH", str(default_epoch))
    if not re.fullmatch(r"[0-9]{1,10}", value) or not 315532800 <= int(value) <= 4102444800:
        raise ReleaseError("SOURCE_DATE_EPOCH must be an integer between 1980 and 2100.")
    epoch = int(value)
    dependencies = sorted(wheelhouse.glob("pyyaml-6.0.3-*.whl"))
    if len(dependencies) != 1:
        raise ReleaseError("Provide exactly one platform-appropriate PyYAML 6.0.3 wheel in the local wheelhouse.")
    dependency = wheel_info(dependencies[0])
    from packaging.tags import sys_tags
    from packaging.utils import parse_wheel_filename
    if not parse_wheel_filename(dependencies[0].name)[3].intersection(sys_tags()):
        raise ReleaseError("Dependency wheel does not match this Python/platform.")
    environment = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch), PYTHONHASHSEED="0", PIP_NO_INDEX="1")
    with tempfile.TemporaryDirectory(prefix="stratagent-release-") as temporary:
        temporary = Path(temporary)
        builds = []
        for index in range(2):
            snapshot = temporary / f"source-{index}"
            snapshot.mkdir()
            for name, data in files.items():
                path = snapshot / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                path.chmod(0o644)
                os.utime(path, (epoch, epoch))
            out = temporary / f"build-{index}"
            out.mkdir()
            run([sys.executable, "-c", "from setuptools.build_meta import build_sdist; build_sdist(" + repr(str(out)) + ")"], snapshot, environment)
            archives = list(out.glob("*.tar.gz"))
            if len(archives) != 1:
                raise ReleaseError("Expected one source distribution.")
            data, members = canonical_sdist(archives[0], epoch)
            archives[0].write_bytes(data)
            unpacked = temporary / f"unpacked-{index}"
            unpacked.mkdir()
            for name, content in members.items():
                path = unpacked / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                path.chmod(0o644)
                os.utime(path, (epoch, epoch))
            project = unpacked / next(iter(members)).split("/")[0]
            run([sys.executable, "-c", "from setuptools.build_meta import build_wheel; build_wheel(" + repr(str(out)) + ")"], project, environment)
            wheels = list(out.glob("*.whl"))
            if len(wheels) != 1:
                raise ReleaseError("Expected one application wheel.")
            builds.append({p.name: regular_bytes(p) for p in (archives[0], wheels[0])})
        if builds[0] != builds[1]:
            raise ReleaseError("Independent builds differ; no release bundle was created.")
        wheel_name = next(name for name in builds[0] if name.endswith(".whl"))
        application = wheel_info(temporary / "build-0" / wheel_name)
        validate_closure(application, dependency)
        project_version = tomllib.loads(files["pyproject.toml"].decode())["project"]["version"]
        if application["version"] != project_version:
            raise ReleaseError("Built application version differs from the reviewed project metadata.")
        payloads = {**builds[0], dependency["filename"]: regular_bytes(dependencies[0])}
        report = {"schema_version": 1, "signed": False, "reproducible": True, "source": source,
                  "source_date_epoch": epoch, "python": sys.version.split()[0], "platform": sys.platform,
                  "toolchain": TOOLS, "reproducibility_scope": "Two isolated source directories in this recorded toolchain/Python/platform; not a cross-platform or hermetic-build claim.",
                  "application": application, "dependency": dependency,
                  "artifacts": [{"filename": name, "sha256": sha(data), "size": len(data)} for name, data in sorted(payloads.items())]}
        payloads["release.json"] = canonical(report)
        payloads["sbom.cdx.json"] = canonical(sbom(application, dependency, source))
        payloads["SHA256SUMS"] = "".join(f"{sha(data)}  {name}\n" for name, data in sorted(payloads.items())).encode()
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".stratagent-release-", dir=output.parent) as staging:
            staging = Path(staging)
            bundle = staging / "bundle"
            bundle.mkdir()
            for name, data in payloads.items():
                (bundle / name).write_bytes(data)
            result = verify(bundle)
            if output.exists() or output.is_symlink():
                raise ReleaseError("Output appeared during build; refusing replacement.")
            bundle.rename(output)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, default=Path("dist"))
    parser.add_argument("--allow-dirty", action="store_true", help="Developer-only snapshot; recorded as dirty, never publication evidence")
    args = parser.parse_args()
    try:
        result = build(args.source, args.output, args.wheelhouse, args.allow_dirty) if args.command == "build" else verify(args.output)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ReleaseError, OSError, ValueError, KeyError, TypeError, BadZipFile, csv.Error, metadata.PackageNotFoundError, subprocess.SubprocessError, tarfile.TarError) as error:
        print(json.dumps({"ok": False, "error": str(error) if isinstance(error, ReleaseError) else "Invalid or inaccessible local release inputs."}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
