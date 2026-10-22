# Resource assurance — P4 first checkpoint

Version 0.6.0 started P4's metadata/reference checkpoint. Version 0.7.0 adds [non-executing artifact/tool inspection and local revocation/advisory policy](artifact-assurance.md). Neither authorizes executable resources or completes broad production interoperability. Runtime discovery remains live GitHub/official MCP Registry research, not a bundled catalog. Popularity still contributes only to discovery/relevance, never safety.

## Supported review contract

Agent Skills frontmatter follows the [published specification](https://agentskills.io/specification): required `name`/`description`, optional `license`, `compatibility`, string-to-string `metadata` and experimental `allowed-tools`. Names must match the directory, be ASCII lowercase slugs without doubled hyphens and fit 64 characters. Description/compatibility limits are 1024/500 characters; environment requirements remain unverified, not automatically installed.

StratAgent uses pinned **PyYAML 6.0.3**, not a homegrown YAML scalar parser or the demonstration-only skills-ref runtime. A restricted `SafeLoader` rejects duplicate/non-string mapping keys, merges, aliases, anchors, explicit tags, non-finite numbers, unsupported scalar types and invalid/control-character text. Limits: 16 KiB frontmatter, 512 parser events, six collection levels, 64 keys per mapping; standard `metadata` has at most 32 string values of at most 1024 characters. YAML errors never echo source fragments. Both raw files and decoded metadata strings are scanned, so YAML escapes cannot hide a known instruction/credential rule. [PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation) describes the safe-loader boundary; these additional restrictions are StratAgent policy, not universal YAML compatibility.

Unknown top-level metadata blocks installation rather than disappearing from its safety review. Experimental `allowed-tools` is typed but **not authorized**: its presence blocks installation. A subagent's exact `Read`, `Grep`, `Glob` hints are recorded and stripped; other source tool grants block. Trusted adapters remain the only source of emitted host permissions. Passive compatibility text is preserved for skill exports; arbitrary extra metadata, hooks and tool declarations are never copied into generated frontmatter. Original metadata stays in the hashed review/cache for inspection.

## Reference evidence, not silent fetching

The bounded reference reviewer recognizes explicit inline/defined Markdown links, full/collapsed reference labels, quoted HTML `href`/`src`, and literal `scripts/`, `references/`, `assets/` paths. Every text supporting document is checked, not just SKILL.md. Local links resolve relative to the containing document inside the pinned skill directory; verified targets record their path and SHA-256. Missing targets/labels, conflicting definitions, traversal (including encoded/double-encoded traversal), absolute/drive paths, embedded credentials, unsafe schemes and query-bearing local references block installation. An optional leading `./` and file fragments are supported.

HTTPS links are **not fetched**, and do not prove external content or license integrity. Anchors are explicitly unverified. More than 256 distinct file/target pairs or 512 parser observations (including overlapping detections) blocks the bundle. Recognized inline-link starts with unsupported/malformed destinations block rather than silently disappear. This is not a full CommonMark/HTML/RST parser: shortcut labels, complex/escaped syntax, dynamic code references and semantic completeness are not certified. Conservative checks also examine examples/code fences and can flag illustrative paths; inspect the finding rather than bypassing it.

Every skill review now includes `metadata`, `reference_review`, `assurance`, and `scanner_version: 2`, all bound into `review_digest`. Rank changes still do not change source approval. `assurance` explicitly says static text only, never executed, vulnerability status not checked, tool behavior not audited and malware safety not proven. `eligible` means this restricted import policy permits human review, not that a resource is safe.

## Existing workspaces and approval

Source reviews from scanner 1 fail closed with an instruction to rediscover/review; `status` marks their scanner non-current and eligibility false. There is no silent review/approval migration. Rediscover the exact source repositories before using cached candidates; use a fresh, separately approved research run for current decisions. Historical candidates that are no longer discoverable are not usable through the unscoped recommendation path; a new workspace/current scoped run is preferable to editing private approval-bound state. Installed files are not changed by this check, and hash verification/removal remain available. Stages and approvals issued before the new scanner/generator/metadata must not be reused. Changing only publisher metadata also invalidates a staged installation.

```sh
stratagent discover --repo owner/repository --workspace ./project
stratagent inspect CANDIDATE_ID --content --workspace ./project
# Read every file, typed metadata, references, license and residual risks first.
stratagent allow owner/repository --workspace ./project
stratagent stage install --candidate-id CANDIDATE_ID --workspace ./project
stratagent apply STAGE_ID --approve EXACT_NEW_HASH --workspace ./project
```

`inspect --content` can show blocked UTF-8 code as untrusted text; it never imports/runs that code. The existing 80-file/2-MiB bundle, per-file 256-KiB, immutable commit/blob, safe path, regular-file and conservative complete-license-body requirements remain in force. Code, archives, binary assets, executable bits, symlinks and host-specific sidecar YAML/JSON still cannot install. A server's Registry metadata review is not a package, tool-manifest, vulnerability or remote-behavior audit. Host activation remains separate/manual.

## Dependency and validation boundary

PyYAML is the first third-party runtime dependency. Standard pip installation resolves the pinned version. CI downloads only its published wheel, then installs the project and dependency using `--no-index` from the local wheel directory; no dependency source build is requested. The application uses the pure-Python safe loader, not optional C-loader behavior. Wheel signing/reproducibility, full dependency SBOM and a maintained advisory/revocation policy remain P6/P4 gates respectively.

The point-in-time OSV query for PyPI/PyYAML 6.0.3 returned no advisory IDs on October 22, 2026. That is only an observed response, **not** ongoing monitoring, a comprehensive audit or a vulnerability-free guarantee. No private project text was sent. [Validation](validation.md) records original adversarial/integration tests, separately installed acceptance, live-source rejection gaps and commit-specific CI evidence.

## P4 continuation — declared scope and remaining gates

- Implemented in 0.7.0: bounded npm artifact integrity/archive/code/license/permission review, operator-supplied MCP tools/list review, exact local revocations, root-package OSV freshness/outage handling and installed-source impact reporting. See the contract and validation, not a claim of behavioral safety.
- Unverified transitive/optional/peer/bundled dependency closure blocks artifacts. Executable installation, lifecycle hooks and activation remain unavailable; no unsupported artifact is claimed audited or installable to improve coverage.
- Broad universal skill compatibility is not claimed. Additional GitHub samples first hit the anonymous rate limit, then two MIT text skills passed inspection using the existing authenticated session. Two fresh npm provider samples verify SRI and expose actual unsupported license/dependency gaps. The validation record retains failures and limitations rather than pretending every popular source is installable.

P5 native host sessions/human evaluations and P6 release operations remain blocked independently. This checkpoint does not publish a package, merge main, start an MCP server or delegate an agent.
