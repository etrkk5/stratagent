# StratAgent project architect

## A realistic full-stack service

The fixture at `examples/projects/saas` contains a React/Next.js frontend and FastAPI/PostgreSQL backend dependency manifests. It includes no runnable scripts or credentials. Preview it without initializing anything:

```sh
PYTHONPATH=src python3 -m stratagent plan \
  "React and FastAPI dashboard with PostgreSQL, authentication, privacy and accessibility" \
  --workspace examples/projects/saas --scan-project
```

The planner explains each detected domain using the prompt and recognized dependencies. Design precedes frontend/API/database specialist planning; implementation depends on those contracts. Testing and security review follow the implementation, then the maintainer integrates the results. Each generated role includes acceptance criteria and an evidence handoff. Claude and Antigravity native roles use read-only tools; write-capable work requires separate manual delegation. Codex roles are Agent Skills, not native subagent runtime definitions. Permissions in prose are guidance, not an OS sandbox.

`domain_evidence` distinguishes a user request from an existing dependency. `requirements` identifies authentication, privacy, offline behavior, payments, accessibility and performance signals. `open_questions` makes unresolved data/permission/migration decisions visible. An unfamiliar request leaves domains empty and asks for scope instead of silently inventing an agent project.

## An offline data-review workflow

```sh
PYTHONPATH=src python3 -m stratagent plan \
  "Python CSV veri analizi, KVKK, çevrimdışı çalışma ve performans testleri" \
  --workspace examples/projects/data-review --scan-project
```

The manifest adds pandas/pytest evidence without reading datasets or scripts. A data specialist plans schemas and reproducible fixtures; privacy review and offline criteria enter the test plan. This is heuristic analysis: inflected words, negation and complex intent may be missed or overmatched. The original prompt is retained locally as data for human review. It is not sent to a model.

## Discovery and trust

Skills use existing GitHub catalogs and the Agent Skills format. Source trees and blobs are commit-pinned; complete documentation bundles are conservatively scanned and license checked. Rankings disclose relevance, documentation structure, static policy and popularity components. Popularity is not trust. `recommend` also reports whether the local user has allowed a repository, and only explicitly installed verified resources enter generated role assignments.

MCP discovery uses the official Registry v0.1 API. Server-name search is deliberately bounded to one request, with no automatic retry or pagination. `--query` should be a public technology/service name. The default is one detected domain; neither the raw project request nor dependency file contents are sent. Query relevance is separate from review eligibility.

MCP reviews bind the complete cached Registry response, server name/version, repository, transport and findings to a SHA-256 digest. Registry publication/status comes from the outer Registry metadata, not the publisher's nested `_meta`. Relevance can be recomputed as the project changes without invalidating the underlying review. Unknown/deprecated/deleted status blocks proposals.

MCP metadata is not an executable artifact audit. Static description rules can flag suspicious instructions, but no MCP source code, package tarball, dependency closure, license or tool manifest is downloaded/scanned. npm proposals accept exact package versions and a GitHub source repository, while rejecting runtime overrides, variable arguments and environment. Version pinning does not verify npm artifact hashes. Remote service behavior cannot be pinned by hashing metadata. All findings and these limitations remain visible in the proposal.

## Approval and activation

1. Run `inspect`/`inspect-mcp --content` and read source or metadata and findings.
2. Run `install`, `configure`, or `configure-mcp --option INDEX` with `--content` to inspect generated files. Without `--apply`, previews write nothing.
3. Allow the exact repository for a skill or npm proposal. An allowlist entry does not approve future content.
4. Supply the complete current preview `approval` with `--apply`. It binds the absolute workspace, generator version, source digest and every generated path/hash. Transport selection and platform targets are included.
5. Run `verify`. Identical approved application is a verified no-op; collisions, tampering and changes to installed output fail closed. Ordinary write failures roll back created files.
6. MCP proposals stay under `.stratagent/proposals/mcp/`. They never become `.mcp.json` or `.codex/config.toml` automatically. Review tool capabilities, source/artifact provenance and credentials before manually activating them. A Codex proposal has `enabled = false`. Copying a Claude proposal into an active host configuration can cause connections or execution, especially in noninteractive clients; that is a separate user action.

`configure` recomputes current manifest evidence before calculating approval. Changing a dependency manifest changes the task plan and approval, even when its recognized dependency names stay the same. The manifest stores initial analysis for provenance; `status` and `recommend` reflect current analysis. Project scan warnings are part of the evidence fingerprint. Scans do not follow symlinks or recurse into arbitrary source directories. For directories exceeding the listing budget, inspection is incomplete and disclosed; review the package structure yourself.

## Operations and compatibility

Use `--log-json` for command start/completion/failure events on stderr. Events contain command, elapsed milliseconds and exit code; prompts, credentials, file contents and local paths are excluded. Human-readable failures are JSON error objects. Avoid passing secrets in a prompt: project requests are intentionally saved locally. `.stratagent` and generated proposals may contain untrusted metadata; do not treat Registry descriptions as agent instructions.

The read-only MCP tools share the same services and cannot install, allow, approve or generate active settings. stdio stdout is exclusively JSON-RPC; optional command events use stderr. Network failure does not delete existing reviews; cached inspection/proposals work offline.

Current configuration formats were checked against [OpenAI skill locations](https://learn.chatgpt.com/docs/build-skills), [Codex MCP settings](https://learn.chatgpt.com/docs/extend/mcp), [Claude Code MCP settings](https://code.claude.com/docs/en/mcp) and the [Registry API schema](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/openapi.yaml). JSON/TOML parsing and CLI protocol exchanges are tested; loading into real Claude Code/Codex clients is a separate integration check. No host settings are changed by the test suite.

Version 0.3 adds the [unified decision workflow](decision-workflow.md): your current model/human can supply a grounded structured architectural judgment, while the local fallback remains rule-based. No direct LLM API client, automatic agent execution, native Codex role orchestration, package artifact attestation, automatic upgrades/removal or hostile-local-user protection is implemented. Old workspaces can be inspected, but generator/analysis changes invalidate old approvals. Use a fresh workspace for new generated output rather than manually rewriting the lockfile.
