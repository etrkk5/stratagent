import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_release import wheel, archive

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
with patch.object(sys, "path", [str(SCRIPTS), *sys.path]):
    spec = importlib.util.spec_from_file_location("stratagent_promotion_tests", SCRIPTS / "publish_preview.py")
    promotion = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(promotion)
    spec = importlib.util.spec_from_file_location("stratagent_dependency_audit_tests", SCRIPTS / "audit_dependencies.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)

release = sys.modules["release"]
COMMIT = "a" * 40


class PromotionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "pyproject.toml").write_text('[project]\nversion = "0.8.0"\n')
        self.downloads = self.root / "downloaded"
        self.downloads.mkdir()
        self.output = self.root / "output"
        self.run = {"id": 42, "status": "completed", "conclusion": "success", "head_sha": COMMIT,
                    "head_branch": "main", "event": "push", "path": ".github/workflows/tests.yml",
                    "repository": {"full_name": promotion.REPOSITORY}}
        self.jobs = {"total_count": 6, "jobs": [{"name": name, "status": "completed", "conclusion": "success", "head_sha": COMMIT} for name in promotion.JOBS]}
        for name in promotion.BUNDLES:
            directory = self.downloads / name
            directory.mkdir()
            app = wheel(directory / "stratagent_cli-0.8.0-py3-none-any.whl")
            dep = wheel(directory / "pyyaml-6.0.3-py3-none-any.whl", "PyYAML", "6.0.3", ())
            source = archive(directory / "stratagent_cli-0.8.0.tar.gz", [("stratagent_cli-0.8.0/README.md", b"Original")])
            application, dependency = release.wheel_info(app), release.wheel_info(dep)
            evidence = {"dirty": False, "commit": COMMIT, "sha256": release.sha(release.canonical([])), "files": []}
            report = {"schema_version": 1, "signed": False, "reproducible": True, "toolchain": release.TOOLS,
                      "source": evidence, "source_date_epoch": 315532800,
                      "application": application, "dependency": dependency,
                      "artifacts": [{"filename": p.name, "sha256": release.sha(p.read_bytes()), "size": p.stat().st_size} for p in (app, dep, source)]}
            (directory / "release.json").write_bytes(release.canonical(report))
            (directory / "sbom.cdx.json").write_bytes(release.canonical(release.sbom(application, dependency, evidence)))
            self.checksums(directory)

    def checksums(self, directory):
        (directory / "SHA256SUMS").write_text("".join(f"{release.sha(p.read_bytes())}  {p.name}\n" for p in sorted(directory.iterdir()) if p.name != "SHA256SUMS"))

    def prepare(self, output=None):
        return promotion.prepare(self.root, self.downloads, output or self.output, self.run, self.jobs, "v0.8.0", COMMIT)

    def test_successful_exact_commit_promotion_retains_all_native_bundles_and_pypi_bytes(self):
        self.prepare()
        manifest = promotion.verify_assets(self.output, "v0.8.0", COMMIT)
        self.assertEqual(10, len(list(self.output.iterdir())))
        self.assertEqual(8, len(manifest["assets"]))
        result = promotion.pypi_inputs(self.output, self.root / "pypi", "v0.8.0", COMMIT)
        self.assertEqual(2, len(result["distributions"]))
        for path in (self.root / "pypi").iterdir():
            self.assertEqual(path.read_bytes(), (self.downloads / promotion.BUNDLES[0] / path.name).read_bytes())

    def test_wrong_branch_workflow_commit_provider_or_incomplete_run_fails(self):
        for key, value in (("head_branch", "feature"), ("path", ".github/workflows/other.yml"), ("head_sha", "b" * 40),
                           ("event", "pull_request"), ("conclusion", "failure"), ("status", "in_progress"), ("repository", {"full_name": "other/repo"})):
            with self.subTest(key=key):
                run = dict(self.run, **{key: value})
                with self.assertRaises(release.ReleaseError):
                    promotion.check_ci(run, self.jobs, COMMIT)

    def test_all_six_unique_jobs_must_pass_at_same_commit(self):
        for mutate in (lambda j: j["jobs"].pop(), lambda j: j["jobs"][0].update(conclusion="skipped"),
                       lambda j: j["jobs"][0].update(head_sha="b" * 40),
                       lambda j: j["jobs"][0].update(name=j["jobs"][1]["name"])):
            jobs = copy.deepcopy(self.jobs)
            mutate(jobs)
            with self.assertRaises(release.ReleaseError):
                promotion.check_ci(self.run, jobs, COMMIT)

    def test_missing_extra_or_dirty_bundle_fails_before_output(self):
        directory = self.downloads / promotion.BUNDLES[0]
        report = json.loads((directory / "release.json").read_bytes())
        report["source"]["dirty"] = True
        (directory / "release.json").write_bytes(release.canonical(report))
        self.checksums(directory)
        with self.assertRaises(release.ReleaseError):
            self.prepare()
        self.assertFalse(self.output.exists())
        (self.downloads / "unexpected").mkdir()
        with self.assertRaises(release.ReleaseError):
            self.prepare()

    def test_tag_and_source_inventory_must_match(self):
        with self.assertRaises(release.ReleaseError):
            promotion.identity("v0.8.0;command", COMMIT)
        (self.root / "pyproject.toml").write_text('[project]\nversion = "0.9.0"\n')
        with self.assertRaises(release.ReleaseError):
            self.prepare()
        (self.root / "pyproject.toml").write_text('[project]\nversion = "0.8.0"\n')
        directory = self.downloads / promotion.BUNDLES[0]
        report = json.loads((directory / "release.json").read_bytes())
        report["source"]["sha256"] = "b" * 64
        (directory / "release.json").write_bytes(release.canonical(report))
        self.checksums(directory)
        with self.assertRaises(release.ReleaseError):
            self.prepare()

    def test_changed_added_and_missing_release_assets_fail(self):
        self.prepare()
        path = self.output / "stratagent_cli-0.8.0-py3-none-any.whl"
        original = path.read_bytes()
        path.write_bytes(b"changed")
        with self.assertRaises(release.ReleaseError):
            promotion.verify_assets(self.output, "v0.8.0", COMMIT)
        path.write_bytes(original)
        extra = self.output / "extra.txt"
        extra.write_text("unexpected")
        with self.assertRaises(release.ReleaseError):
            promotion.verify_assets(self.output, "v0.8.0", COMMIT)
        extra.unlink()
        path.unlink()
        with self.assertRaises(release.ReleaseError):
            promotion.verify_assets(self.output, "v0.8.0", COMMIT)

    def test_manifest_path_escape_and_wrong_release_identity_are_refused(self):
        self.prepare()
        with self.assertRaises(release.ReleaseError):
            promotion.verify_assets(self.output, "v0.8.0", "b" * 40)
        path = self.output / "RELEASE-MANIFEST.json"
        manifest = json.loads(path.read_bytes())
        manifest["assets"][0]["filename"] = "../outside"
        path.write_bytes(release.canonical(manifest))
        with self.assertRaises(release.ReleaseError):
            promotion.verify_assets(self.output, "v0.8.0", COMMIT)

    def test_existing_output_is_preserved_and_repeated_archives_match(self):
        self.prepare()
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        with self.assertRaises(release.ReleaseError):
            self.prepare()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir()})
        second = self.root / "second"
        self.prepare(second)
        self.assertEqual(before, {p.name: p.read_bytes() for p in second.iterdir()})


class DependencyAuditTests(unittest.TestCase):
    def setUp(self):
        self.source = Path(__file__).resolve().parents[1]

    def response(self, payload):
        from unittest.mock import MagicMock
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = payload
        return opener

    def test_queries_only_reviewed_public_pins_and_does_not_update(self):
        opener = self.response(b'{"results":[{},{},{},{}]}')
        with patch.object(audit, "build_opener", return_value=opener):
            result = audit.audit(self.source)
        self.assertTrue(result["ok"])
        self.assertFalse(result["automatic_changes"])
        request = opener.open.call_args.args[0]
        self.assertEqual("https://api.osv.dev/v1/querybatch", request.full_url)
        payload = json.loads(request.data)
        self.assertEqual(audit.ALLOWED, {q["package"]["name"] for q in payload["queries"]})
        self.assertTrue(all(set(q) == {"package", "version"} for q in payload["queries"]))

    def test_findings_fail_and_missing_malformed_oversized_responses_never_pass(self):
        with patch.object(audit, "build_opener", return_value=self.response(b'{"results":[{"vulns":[{"id":"GHSA-example-1234"}]},{},{},{}]}')):
            self.assertFalse(audit.audit(self.source)["ok"])
        for data in (b'{"results":[]}', b'{"results":[null,{},{},{}]}', b'{"results":[{"vulns":[{"id":"private\\nvalue"}]},{},{},{}]}', b"x" * (audit.LIMIT + 1)):
            with self.subTest(size=len(data)), patch.object(audit, "build_opener", return_value=self.response(data)):
                with self.assertRaises((audit.AuditError, ValueError)):
                    audit.audit(self.source)

    def test_unreviewed_dependency_names_fail_before_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            (source / "pyproject.toml").write_text('[project]\ndependencies=["private-project-name==1.0.0"]\n')
            (source / "requirements-build.txt").write_bytes((self.source / "requirements-build.txt").read_bytes())
            with patch.object(audit, "build_opener") as network:
                with self.assertRaises(audit.AuditError):
                    audit.audit(source)
                network.assert_not_called()
