import base64
import csv
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

spec = importlib.util.spec_from_file_location("stratagent_release_tests", Path(__file__).resolve().parents[1] / "scripts/release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def wheel(path, name="stratagent-cli", version="0.8.0", requires=("PyYAML==6.0.3",), extra=None):
    dist = name.replace("-", "_").lower() + "-" + version + ".dist-info"
    files = {dist + "/METADATA": (f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\nLicense-Expression: MIT\n" +
             "".join("Requires-Dist: " + requirement + "\n" for requirement in requires) + "\n").encode(),
             dist + "/licenses/LICENSE": b"Original license evidence fixture\n", "original/__init__.py": b"# Original fixture\n"}
    if extra:
        files.update(extra)
    record = io.StringIO(newline="")
    writer = csv.writer(record)
    for filename, data in files.items():
        writer.writerow([filename, "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("="), str(len(data))])
    writer.writerow([dist + "/RECORD", "", ""])
    files[dist + "/RECORD"] = record.getvalue().encode()
    with ZipFile(path, "w") as archive:
        for filename, data in files.items():
            archive.writestr(filename, data)
    return path


def archive(path, members, timestamp=1):
    with path.open("wb") as stream, gzip.GzipFile(fileobj=stream, mode="wb", mtime=timestamp) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as bundle:
            for name, data in members:
                member = tarfile.TarInfo(name)
                member.size, member.mtime, member.uid, member.uname = len(data), timestamp, timestamp, "original-test"
                bundle.addfile(member, io.BytesIO(data))
    return path


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def fixture(self):
        app_path = wheel(self.root / "stratagent_cli-0.8.0-py3-none-any.whl")
        dep_path = wheel(self.root / "pyyaml-6.0.3-py3-none-any.whl", "PyYAML", "6.0.3", ())
        source_path = archive(self.root / "stratagent_cli-0.8.0.tar.gz", [("stratagent_cli-0.8.0/README.md", b"Original")])
        app, dep = release.wheel_info(app_path), release.wheel_info(dep_path)
        source = {"dirty": False, "commit": "a" * 40, "sha256": "b" * 64, "files": []}
        artifacts = [{"filename": path.name, "sha256": release.sha(path.read_bytes()), "size": path.stat().st_size} for path in (app_path, dep_path, source_path)]
        report = {"schema_version": 1, "signed": False, "reproducible": True, "toolchain": release.TOOLS,
                  "source": source, "application": app, "dependency": dep, "artifacts": artifacts}
        (self.root / "release.json").write_bytes(release.canonical(report))
        (self.root / "sbom.cdx.json").write_bytes(release.canonical(release.sbom(app, dep, source)))
        self.checksums()
        return report

    def checksums(self):
        (self.root / "SHA256SUMS").write_text("".join(f"{release.sha(p.read_bytes())}  {p.name}\n" for p in sorted(self.root.iterdir()) if p.name != "SHA256SUMS"))

    def test_valid_bundle_has_complete_distribution_inventory_and_no_signature_claim(self):
        self.fixture()
        result = release.verify(self.root)
        self.assertTrue(result["ok"])
        self.assertFalse(result["signed"])
        bom = json.loads((self.root / "sbom.cdx.json").read_bytes())
        self.assertEqual(bom["metadata"]["component"]["purl"], "pkg:pypi/stratagent-cli@0.8.0")
        self.assertEqual(bom["components"][0]["purl"], "pkg:pypi/pyyaml@6.0.3")
        self.assertEqual(bom["components"][0]["licenses"], [{"expression": "MIT"}])

    def test_changed_artifact_fails_checksum(self):
        self.fixture()
        (self.root / "stratagent_cli-0.8.0.tar.gz").write_bytes(b"changed")
        with self.assertRaisesRegex(release.ReleaseError, "checksum"):
            release.verify(self.root)

    def test_extra_or_removed_bundle_files_fail(self):
        self.fixture()
        extra = self.root / "unexpected.txt"
        extra.write_text("Original unexpected fixture")
        with self.assertRaisesRegex(release.ReleaseError, "file set"):
            release.verify(self.root)
        extra.unlink()
        (self.root / "sbom.cdx.json").unlink()
        with self.assertRaisesRegex(release.ReleaseError, "file set"):
            release.verify(self.root)

    def test_rehashed_but_inconsistent_sbom_fails(self):
        self.fixture()
        bom = json.loads((self.root / "sbom.cdx.json").read_bytes())
        bom["components"][0]["version"] = "9.9.9"
        (self.root / "sbom.cdx.json").write_bytes(release.canonical(bom))
        self.checksums()
        with self.assertRaisesRegex(release.ReleaseError, "SBOM"):
            release.verify(self.root)

    def test_artifact_reference_cannot_escape_bundle(self):
        report = self.fixture()
        report["application"]["filename"] = "../outside.whl"
        (self.root / "release.json").write_bytes(release.canonical(report))
        self.checksums()
        with self.assertRaisesRegex(release.ReleaseError, "contract"):
            release.verify(self.root)

    def test_record_hash_and_complete_coverage_are_required(self):
        path = wheel(self.root / "original.whl")
        with ZipFile(path) as original:
            files = {item: original.read(item) for item in original.namelist()}
        for unrecorded in (False, True):
            changed = self.root / f"changed-{unrecorded}.whl"
            with ZipFile(changed, "w") as archive:
                for name, data in files.items():
                    archive.writestr(name, b"Changed fixture" if not unrecorded and name == "original/__init__.py" else data)
                if unrecorded:
                    archive.writestr("unrecorded.txt", b"Original")
            with self.assertRaisesRegex(release.ReleaseError, "RECORD"):
                release.wheel_info(changed)

    def test_runtime_closure_refuses_extra_or_transitive_dependencies(self):
        app = release.wheel_info(wheel(self.root / "app.whl"))
        dep = release.wheel_info(wheel(self.root / "dep.whl", "PyYAML", "6.0.3", ("unknown>=1",)))
        with self.assertRaisesRegex(release.ReleaseError, "closure"):
            release.validate_closure(app, dep)
        dep["requires_dist"] = []
        app["requires_dist"].append("extra==1.0.0")
        with self.assertRaisesRegex(release.ReleaseError, "closure"):
            release.validate_closure(app, dep)

    def test_sdist_reproduction_normalizes_metadata_but_preserves_contents(self):
        first = archive(self.root / "one.tar.gz", [("original/a.py", b"a"), ("original/b.py", b"b")], 1)
        second = archive(self.root / "two.tar.gz", [("original/b.py", b"b"), ("original/a.py", b"a")], 100)
        one, files = release.canonical_sdist(first, 1700000000)
        two, _ = release.canonical_sdist(second, 1700000000)
        self.assertEqual(one, two)
        self.assertEqual(files, {"original/a.py": b"a", "original/b.py": b"b"})

    def test_archive_traversal_duplicates_and_nonportable_paths_are_refused(self):
        for name in ("../outside", "/absolute", "root/../outside", "root/NUL", "root/trailing.", "root/a\\b"):
            with self.subTest(name=name), self.assertRaises(release.ReleaseError):
                release.canonical_sdist(archive(self.root / "bad.tar.gz", [(name, b"original")]), 1700000000)
        with self.assertRaisesRegex(release.ReleaseError, "Duplicate"):
            release.canonical_sdist(archive(self.root / "bad.tar.gz", [("root/A", b"a"), ("root/a", b"b")]), 1700000000)

    def test_dirty_source_and_existing_output_fail_without_overwrites(self):
        with patch.object(release, "run", side_effect=[str(self.root).encode(), b" M README.md"]):
            with self.assertRaisesRegex(release.ReleaseError, "Commit/review"):
                release.source_snapshot(self.root, False)
        output = self.root / "existing"
        output.mkdir()
        (output / "keep").write_bytes(b"User content")
        with self.assertRaisesRegex(release.ReleaseError, "already exists"):
            release.build(self.root, output, self.root)
        self.assertEqual((output / "keep").read_bytes(), b"User content")

    def test_project_and_ci_pin_the_release_toolchain(self):
        import tomllib
        import yaml
        root = Path(__file__).resolve().parents[1]
        config = tomllib.loads((root / "pyproject.toml").read_text())
        lines = [line for line in (root / "requirements-build.txt").read_text().splitlines() if line and not line.startswith("#")]
        requirements = {line.split("==")[0]: line.split("==")[1].split()[0] for line in lines}
        self.assertTrue(all("--hash=sha256:" in line for line in lines))
        self.assertEqual(requirements, release.TOOLS)
        self.assertEqual(config["build-system"]["requires"], ["setuptools==" + requirements["setuptools"]])
        steps = yaml.safe_load((root / ".github/workflows/tests.yml").read_text())["jobs"]["unit"]["steps"]
        commands = [step.get("run", "") for step in steps]
        self.assertTrue(any("scripts/release.py build" in command for command in commands))
        self.assertTrue(any("scripts/release.py verify" in command for command in commands))

    def test_private_inputs_are_refused_inside_otherwise_allowed_source_trees(self):
        with patch.object(release, "run", side_effect=[str(self.root).encode(), b"", b"examples/.env.private\0"]):
            with self.assertRaisesRegex(release.ReleaseError, "private"):
                release.source_snapshot(self.root, False)


if __name__ == "__main__":
    unittest.main()
