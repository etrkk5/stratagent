# Publish and verify a preview

## Maintainer release sequence

1. Merge reviewed changes and wait for all six jobs in the **main push** run of
   `tests.yml`. The earlier engineering merge `8602a0e` has
   [six passing jobs](https://github.com/etrkk5/stratagent/actions/runs/39953444968);
   new publication tooling needs its own exact-commit CI result.
2. Run `preview-release` (`release.yml`) on main with that successful run ID and
   `v0.8.0`. It rejects other branches/events/workflows/commits, incomplete jobs,
   dirty bundles, changed bytes and an existing release.
3. Six native bundles are verified without rebuilding and packed into deterministic
   ZIPs. The canonical Ubuntu/Python 3.11 wheel/source archive are exposed separately.
4. GitHub OIDC/Sigstore provenance covers all assets, including manifest/checksums.
   Before upload, verification requires this repository, `release.yml`, main,
   the exact source digest and a GitHub-hosted runner. The workflow creates a
   draft, downloads it, checks exact bytes/files again, then publishes a **pre-release**.
5. Verify a downloaded public asset, check support/private reporting, then use the
   [announcement drafts](community-launch.md). PyPI is a separate operation.

The workflow only runs from main, with non-cancelling release concurrency. No
personal token/signing key is stored here. Existing releases/assets/tags are never
overwritten, deleted or moved by the workflow.

If a run fails after creating a draft, retain its tag, logs and files. Do not use
`--clobber`, delete assets, move tags or bypass verification. Download the draft,
compare the manifest and attestations, and review recovery separately. Changed
published bytes require a new version; rollback preserves the original release.

## Verify and install

Download from https://github.com/etrkk5/stratagent/releases/tag/v0.8.0.
The application wheel is universal; PyYAML still needs a compatible wheel.
For every asset you will use, verify signed provenance (network and an
authenticated GitHub CLI may be needed):

```sh
gh attestation verify stratagent_cli-0.8.0-py3-none-any.whl --repo etrkk5/stratagent --signer-workflow etrkk5/stratagent/.github/workflows/release.yml --source-ref refs/heads/main --deny-self-hosted-runners
```

Compare the source commit against the release manifest/tag; add `--source-digest
EXACT_SOURCE_COMMIT` to enforce it. Verify `RELEASE-MANIFEST.json` and `SHA256SUMS`
the same way before trusting them. With all assets downloaded, use
`sha256sum -c SHA256SUMS`; PowerShell users can compare `Get-FileHash -Algorithm
SHA256` results. Hashes alone do not authenticate a publisher.

In an activated Python 3.11+ virtual environment, install the downloaded wheel:

```sh
python -m pip install ./stratagent_cli-0.8.0-py3-none-any.whl
stratagent --version
stratagent doctor
```

For offline installation, select the ZIP matching your OS/architecture **and**
Python minor version. Initial CI targets Ubuntu x86-64, Windows x86-64 and the
recorded macOS runner architecture. Inspect its receipt/wheel tags; other machines
need an independently obtained compatible PyYAML wheel. Verify the ZIP before
extracting it into a new directory, then run there in a virtual environment:

```sh
python -m pip install --no-index --find-links . stratagent-cli==0.8.0
stratagent --version
stratagent doctor
```

No host is activated. Follow [host setup](host-setup.md) and separate approvals.
[Rollback](releasing.md#roll-back-without-losing-project-state) preserves project state.

## Optional PyPI setup

The public `stratagent-cli` JSON endpoint returned HTTP 404 on October 23, 2026.
This does not reserve its name or establish ownership. GitHub login does not
sign in to PyPI. The account owner must sign in, complete required account
authentication and configure this pending Trusted Publisher:

| Field | Value |
| --- | --- |
| Project | `stratagent-cli` |
| Repository owner | `etrkk5` |
| Repository | `stratagent` |
| Workflow filename | `pypi.yml` |
| Environment | `pypi` |

Configure the intended main-branch/reviewer policy on the GitHub `pypi` environment.
Then manually run `pypi.yml` on main with the existing preview tag. It verifies
release/workflow/source attestations, selects the exact released wheel/source
without rebuilding, and hands only those two files to a separate least-privilege
OIDC publishing job. The pinned PyPA action produces PyPI attestations. No persistent
PyPI API token is needed. Installing this workflow alone does not publish anything;
account/publisher association is required. `0.8.0` has no PEP 440 prerelease suffix,
so pip/PyPI treats it as a normal version even though the product label remains
developer preview. Review this distinction before PyPI publication.

Sources: [GitHub attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations),
[private reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately),
[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/).
