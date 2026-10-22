# Artifact, tool and revocation assurance

Version 0.7.0 adds operator-only, **non-executing** assurance. It does not enable npm installation, run lifecycle hooks, extract archives onto disk, start a server or trust a tool's claimed permissions. Model/host/OS-independent planning and the existing review/approval boundary remain unchanged. P5/P6 and broad executable interoperability are not completed by this feature.

## Exact-package review

```sh
stratagent inspect-mcp MCP_ID --workspace ./project
stratagent audit-package MCP_ID --option 0 --workspace ./project
# Review public package/version, fixed endpoints, budgets and the network-only hash.
stratagent audit-package MCP_ID --option 0 --approve-network EXACT_HASH --workspace ./project
stratagent inspect-mcp MCP_ID --workspace ./project
```

The default is a no-write/no-network preview. Approval binds the workspace, exact cached Registry review/option, public npm identifier/version, repository, current local policy and outbound purpose. It permits three fixed-host requests within a 90-second total budget: exact-version npm metadata, its canonical npm tarball, and a root-package OSV query. Requests use verified TLS without redirects or inherited GitHub credentials; each request has at most 20 seconds. Arbitrary source URLs and noncanonical tarball endpoints are refused. No project prompt, source, environment or credential is sent.

The npm metadata name/version and GitHub repository must match the selected Registry option. The archive's `package.json` identity must match too. A single canonical SHA-512 SRI value is mandatory and checked **before decompression**. This proves correspondence to the observed registry digest, not publisher signature, build provenance, correspondence to a Git commit or future immutable registry behavior. The private cache binds exact bytes, registry metadata, source review and advisory observation into a content-addressed record. Later previews re-inspect that record and include its manifest reference in lifecycle approval; an audit change invalidates previously staged installation proposals.

Limits: 4 MiB compressed, 16 MiB decompressed tar, 200 members, 256 KiB per regular file, 8 MiB total file payload. The archive is read in memory; no member is extracted to the filesystem. Traversal, absolute/drive/nonportable names, case/component collisions, file/directory collisions, links, devices, privileged modes, sparse/PAX extensions and non-padding trailing content fail closed. Unsupported formats/oversized files are not claimed audited.

Reports retain per-file hashes/sizes/modes, declared bin entrypoints, license evidence, lifecycle script names, declared dependencies and static code capability/risk findings. Python syntax is parsed, not evaluated; other code receives disclosed lexical checks. Group/world-writable files, lifecycle install hooks, implicit native builds, unknown/binary content, missing/unsafe entrypoints, ambiguous licenses and known dangerous instructions block the static policy. Conservative complete license-body matching still applies. Executable modes are visible but never granted execution. Static scanning is not malware detection proof or a sandbox.

Dependency ranges, optional/peer/bundled dependencies are **not resolved or silently trusted**: unverified dependency closure blocks the package. There is no new package resolver or registry. Standard [npm package declarations](https://docs.npmjs.com/cli/v11/configuring-npm/package-json/) are inspected as data, without invoking npm. Unsupported executable installation remains deliberately unavailable; `execution_eligible` is always false, even for an original no-dependency fixture that passes static checks.

Even after inspection, an inert `npx` proposal does not force the host to execute the audited tarball: manual activation can fetch different registry bytes or dependencies. The cached SRI review is not an installation lock or execution authorization. Do not activate it as if those unsupported guarantees existed.

## Advisory freshness and failure

The [OSV query API](https://google.github.io/osv.dev/post-v1-query/) receives only the exact public root npm package/version. A successful bounded response records active advisory IDs and a 24-hour expiry. Empty results mean only no IDs returned for that exact root query, not safety or transitive coverage. Known advisories, deprecated npm versions, expired evidence, partial/error responses and unavailable providers block recorded assurance. Runtime PyYAML dependency monitoring/SBOM remains a separate P6 obligation.

A refresh persists `pending` **before** IO, replacing any previously usable assurance reference. Ordinary failure records `failed`; process interruption may leave `pending`. Neither state silently falls back to an older successful audit. An explicit new preview/approval/refresh is required to recover. Source/policy changes during IO and concurrent publication refuse the result. Metadata/code/advisory evidence is cached privately, never installed. Each index is bounded to 100 entries; there is no automatic cache eviction or policy reinstatement.

## MCP tools/list review

```sh
# Capture this separately with the server owner's/host's consent; StratAgent does not start/contact it.
stratagent audit-tools MCP_ID --file reviewed-tools.json --workspace ./project
stratagent inspect-mcp MCP_ID --workspace ./project
```

The input is a bounded local JSON tools/list result, either its `tools` object or a JSON-RPC envelope. At most 100 unique bounded tool names are accepted; input schemas must be object-shaped, known annotations boolean, and pagination complete. External schema references and known injection/credential payloads block the report. This is a constrained structural/description review, not a complete JSON Schema validator, implementation audit, authenticated server snapshot or behavior attestation. [MCP's tool specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) treats annotations as untrusted too.

Operator association with an MCP ID is recorded, **not independently attested**. Descriptions and schemas remain untrusted; every tool's `permissions_granted` is empty. Evidence binds the exact Registry review and expires after 24 hours; that observation age does not prove remote tool behavior stayed unchanged. New server metadata requires new tool evidence. Private captures can contain sensitive data: restrict the workspace and never publish `.stratagent` or raw capture files. CLI event logs omit contents and operator reasons.

## Local revocation and installed impact

```sh
stratagent revoke repo:owner/repository --reason "Security hold pending review" --workspace ./project
stratagent revoke npm:@scope/package@1.2.3 --reason "Advisory review" --workspace ./project
stratagent revoke artifact:SHA256 --reason "Artifact incident" --workspace ./project
stratagent security-status --workspace ./project
stratagent verify --workspace ./project
```

Other exact subjects are `review:SHA256` and `mcp:SERVER_NAME@SERVER_VERSION`. Policy is local to this workspace: up to 500 subject/reason records, no wildcard grants or global signed revocation feed. Repeated identical revocation is idempotent; changed reasons/duplicates/malformed state fail closed. `allow` cannot undo a revocation. There is no automatic reinstatement or model-facing revocation/policy-write tool.

Current inspection, recommendation, blueprint selection, staging and apply reject revoked resources or blocked recorded assurance. Policy changes invalidate old approvals. `status` marks cached revoked skills ineligible. `security-status` reports **installed** source impact separately from file integrity: an intact revoked installation can have `verify.ok: true` and `security.ok: false`. Uninstalled blocked candidates do not make installed-impact status fail. Review findings, remove dependent managed configuration first when required, then explicitly remove the affected installation. Nothing is automatically deleted; separately copied/activated host configuration must be disabled manually by its operator. Existing default MCP remains 13 read-only tools and no audit/revoke/approval authority.

## Checkpoint and limits

The [validation record](validation.md) distinguishes original adversarial/CLI fixtures, fresh npm provider observations and unavailable GitHub compatibility evidence. The requested artifact/tool inspection and local revocation/advisory mechanisms are implemented for this declared non-executing scope. Broad executable dependency closure/installation, sidecar/binary skill support, signed provenance, independent review and P5/P6 release evidence remain unsupported/open. Do not call the whole application production-ready or silently advance past these gates.
