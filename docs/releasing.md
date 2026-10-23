# Build and operate a reviewed developer-preview release

Version 0.8.0 adds an offline release bundle with repeat-build evidence, a CycloneDX 1.6 Python-distribution SBOM, file/license inventories and package lifecycle acceptance. It remains a developer preview. The local release helper only builds/verifies; the separate [publication workflow](publishing.md) promotes exact-commit main CI outputs, verifies external GitHub provenance and publishes a GitHub pre-release. It never activates a host or alters a user workspace. PyPI is separately configured and manually dispatched.

## Build a candidate

Use a clean, reviewed Git checkout and Python 3.11+. Activate a dedicated build environment, then install the exact toolchain. `requirements-build.txt` pins setuptools, wheel and packaging by version **and universal-wheel SHA-256**. It is development tooling, not a runtime dependency list.

```sh
python3 -m venv .build-venv
.build-venv/bin/python -m pip install --require-hashes -r requirements-build.txt
.build-venv/bin/python -m pip download --only-binary=:all: --no-deps PyYAML==6.0.3 --dest dist
.build-venv/bin/python scripts/release.py build --source . --output dist/release-0.8.0 --wheelhouse dist
.build-venv/bin/python scripts/release.py verify --output dist/release-0.8.0
```

On Windows use `python` and `.build-venv\Scripts\python.exe`. The helper itself uses argument arrays and portable filesystem APIs. A local wheelhouse can replace the first two network preparation steps: pass `--no-index --find-links PATH` when installing tooling. The build/verify phase performs no downloads. Keep one platform-appropriate PyYAML 6.0.3 wheel in the selected wheelhouse; ambiguous or incompatible wheels fail.

The backend is pinned in `pyproject.toml`. The helper makes two fresh source directories, builds a source archive in each, normalizes source-archive timestamps/ownership/modes/order, then builds each wheel **from its source archive**. It compares both wheel bytes and canonical source-archive bytes before creating the output. `SOURCE_DATE_EPOCH` defaults to the source commit timestamp; an explicit value must be an integer between 1980 and 2100. Original file bytes are preserved. Versions, Python/platform, epoch, source commit, source file digest and artifact hashes are recorded.

The default refuses dirty/untracked source and existing output directories. It never stashes, resets, deletes old bundles or overwrites them. `--allow-dirty` is only a development aid: the receipt explicitly labels it dirty and does not identify it as a clean published commit. Unexpected source inputs, `.env*`, workspace state, redirects and oversized data are refused. Local build environments/output belong in ignored paths; `.build-venv/`, `.venv/` and `dist/` are ignored.

## Inspect the bundle

| File | Purpose |
| --- | --- |
| `stratagent_cli-0.8.0-py3-none-any.whl` | Installable application wheel |
| `stratagent_cli-0.8.0.tar.gz` | Canonical source archive with build inputs/docs/tests |
| One `pyyaml-6.0.3-…whl` | Exact selected platform/Python runtime dependency |
| `SHA256SUMS` | Hashes of all other bundle files |
| `release.json` | Source/artifact evidence, toolchain and all wheel-member/license-file hashes |
| `sbom.cdx.json` | CycloneDX 1.6 declared Python-distribution dependency graph, package URLs, hashes and licenses |

Verification requires the exact file set, checksum agreement, complete wheel `RECORD` coverage, wheel content hashes/sizes, supported dependency closure and an SBOM matching those actual wheels. Missing/changed/additional files, unsupported requirements and inventory inconsistencies fail. The current closure is StratAgent → PyYAML 6.0.3, with no declared Python dependencies below PyYAML. The declared MIT license and actual notice/license file hashes are recorded; this is not a legal-compatibility verdict. Bundled SPDX license-reference data retains the notices in `THIRD_PARTY_NOTICES.md`.

The SBOM is explicitly **distribution-level**. It does not claim a complete inventory of native libraries embedded in PyYAML's extension, the OS, build-tool vendoring or runtime-downloaded resources. A file inventory includes binary bytes but is not native dependency analysis. No current vulnerability-free or safe-code assertion follows from hashes, registry names or an empty advisory query.

Repeatability is established for the recorded Python/platform/toolchain and source snapshot. It is not a cross-platform byte-equality or hermetic/signed-build claim. Checksums plus receipts prove local consistency, not publisher identity: all bundles currently state `signed: false`. The separate [publisher](publishing.md) adds and verifies external GitHub OIDC/Sigstore provenance over the public release assets; inner receipts remain unsigned local consistency records. [Private security intake](../SECURITY.md) is configured on GitHub. No personal signing identity or credential is fabricated.

## Test installation and optional upgrade

```sh
python scripts/validate_distribution.py --bundle dist/release-0.8.0
python scripts/validate_distribution.py --bundle dist/release-0.8.0 --previous-wheel /path/to/reviewed-older-wheel.whl
```

The script verifies the bundle, creates a disposable virtual environment, installs offline, exercises the original demo, checks the console version, dependency consistency, `verify` and `doctor --check-files`, then uninstalls the package. Original notes, a synthetic `.env` and all generated workspace state/files must remain byte/mode-identical through package upgrade/uninstall. The optional older artifact is local and explicitly supplied; no older package is fetched or impersonated. This is developer acceptance, not an independent user pilot. CI runs clean install/uninstall; version-to-version upgrade evidence is recorded separately when a real older wheel is available.

Application package upgrades do not silently migrate or approve workspace changes. Inspect a changed environment's staged lifecycle plan separately. File hash verification, local `security-status` and research freshness answer different questions.

## Roll back without losing project state

1. Stop the connected local StratAgent bridge and quiesce writers. If an environment transaction is pending, retain backups and review `recover` before further environment changes.
2. Preserve a private copy of project files and `.stratagent/` state; do not publish that backup. Retain both the current and known-good reviewed bundles/checksums.
3. For a **package-only rollback**, create a separate virtual environment and install the known-good wheel/dependencies offline. Repoint the local bridge only after reviewing that interpreter path. Test `doctor`/`verify` against a disposable copy first; an older version may refuse newer schemas.
4. If the older version cannot read the current state, return to the newer environment. Do not delete metadata, rewrite schemas by hand or reuse an old approval to force compatibility. An approved workspace change uses the separate [lifecycle recovery/update](lifecycle.md) contract; a package downgrade is not a workspace rollback.
5. Uninstalling StratAgent removes its environment's package/entry point, not user project files. Delete a disposable virtual environment only after confirming it is no longer referenced by a host.

## CI and publication

The six Ubuntu/macOS/Windows × Python 3.11/3.14 jobs now install hash-pinned tooling, retain source/installed tests and original CLI/lifecycle checks, reproduce both distributions, verify the SBOM/RECORD/checksum contract and run disposable install/uninstall acceptance. Checkout, Python setup and artifact-upload actions are pinned to exact upstream commits. Each job uploads its own platform/Python preview bundle for 14 days. A previous commit's green matrix is not evidence for a new artifact. Compare the source commit in its receipt with the workflow's exact commit.

Branch CI artifacts are review candidates. Package publication, a GitHub Release, signing and merging main are separate deliberate actions. Do not silently promote a dirty/local build, ignore a failed platform job or publish a package simply because its version is 0.8.0. Keep the developer-preview label and the [P5 field waivers](interoperability.md) visible.

## Support and incident handling

Use [doctor](diagnostics.md) for a minimal local report. For a non-sensitive bug, record the application/Python version, exact commit/artifact hash, affected command, fixed diagnostic check IDs and a minimal synthetic reproduction. Never attach private workspaces, raw prompts/model logs, tokens or transaction backups to public issues.

For a suspected compromised resource, stop host activation/bridge use, preserve private evidence and inspect the exact source/installed impact using `security-status`. Use explicit local revocation where appropriate; do not claim revocation removes already-read instructions or undoes external effects. For a distribution incident, retain its hashes, pause further promotion and use the reviewed package rollback path above. Credential exposure must be handled through the credential issuer's actual revocation process.

Use the verified [GitHub private reporting channel](../SECURITY.md#report-privately) for sensitive reports. No email address or response SLA is invented. A scheduled read-only OSV audit checks four declared runtime/build pins and fails on findings/outage; maintainers must monitor and triage workflow notifications. It does not cover vendored/native/transitive closure, change dependencies or provide staffed incident response.

References checked October 23, 2026: [PyPA build strategy/reproducibility](https://build.pypa.io/en/latest/explanation/how-it-works.html), [SOURCE_DATE_EPOCH](https://reproducible-builds.org/specs/source-date-epoch/), [setuptools project/license configuration](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html), [CycloneDX 1.6 schema](https://cyclonedx.org/schema/bom-1.6.schema.json).
