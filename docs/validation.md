# Validation

## Version 0.3.0 reviewed architectural decisions — October 19, 2026

This iteration joins project scope, coordination tradeoffs, roles, reviewed skill/MCP bindings, proposed permissions and exact configuration output in one `blueprint`. `decision-request` exports a strict, provider-independent contract so an existing model or human can supply judgment without a new model API dependency. The local fallback remains explicitly rule-based. Verification was completed on `feat/project-aware-architect` before committing/pushing; publication history is recorded in Git. The README and package description also make the platform/model-agnostic boundary explicit without promising universal native runtime compatibility.

### Automated and packaged verification

- **132 tests pass** both from source and using the independently installed 0.3.0 wheel from outside the repository. The 24 additional tests include ten original bilingual acceptance cases, negative/deferred/contradictory scope, bounded repeated evidence, focused/specialist alternatives, grounded domain/requirement proposals, omitted specialists, mandatory review responsibilities, stale context, unknown/blocked sources, scoped offline needs, rejected authority fields, approval invalidation, combined installation, reuse, rollback, existing-file preservation and CLI/MCP boundaries.
- The dependency-free runtime wheel was built, installed with `--no-index --no-deps` into the separate verification environment, and installed into the project virtual environment. Bytecode compilation and `git diff --check` pass.
- An assistant-authored structured decision was exercised through the installed CLI on an original-only temporary example: a small internal Python order viewer with staff screens, seven-day retention, excluded payments and offline tests. The reviewed proposal inferred the screen/UI domain, added a literal-quote retention requirement, chose focused ownership and bound original review documents. Preview did not change files; explicit repository allowance and exact approval applied **39 outputs** across Claude, Codex, Antigravity and generic targets; repeat application was a verified no-op. `status` reported the approved external-structured proposal and current context. This was not an actual host/model integration session or a benchmark of general reasoning quality.
- The installed original-only offline demo still verifies **46 outputs**. No real third-party skill, server package or agent was executed.
- An installed CLI stdio subprocess exercised initialize, tools/list, decision context, the assistant-authored blueprint proposal and an invalid mutation argument: **five JSON-RPC replies, 11 read-only tools**, successful context/proposal roundtrip, rejected `apply` argument and unchanged workspace files. Two structured lifecycle events stayed on stderr. This validates the wire boundary, not native client startup or model tool selection.
- CI now includes portable decision-request/blueprint CLI smoke steps in addition to the full test suite and original demo. GitHub Actions has **not** been triggered for the local branch. Current local execution is macOS/Python 3.14.3; the updated cross-platform matrix remains pending.

### Remaining boundaries

Literal quotes, strict source IDs and digests validate traceability, not semantic truth or optimal architecture. Returning an unchanged generated draft does not demonstrate model reasoning. Native Claude Code/Codex/Antigravity loading, real client/model decision behavior, model-quality evaluation and remote MCP artifact/tool/license audits remain unverified. The previous official Registry endpoint timeout remains unresolved; fixture-based integration coverage is not evidence of a successful live Registry response. MCP configurations remain inert and require separate manual activation.

No direct LLM API client, ASM/skills.sh installation backend, automatic agent execution or installed-output upgrade workflow was added. Existing lower-level installations may be reused when their reviewed bytes match; changed approved plans require a fresh workspace. Version 0.3 requires new previews/approvals. See [decision workflow](decision-workflow.md) for the exact contract and limits. Earlier sections below describe historical iteration results, not additional current-release claims.

## Version 0.2.2 platform-independent core — October 19, 2026

This preceding iteration isolates host-specific paths, native role metadata and MCP serialization in the trusted `HostAdapter` catalog (`hosts.py`). Shared reasoning/security/discovery/approval services consume that contract. `stratagent platforms` lists capabilities without requiring an initialized or existing workspace; `generic` remains the portable export target. Default host selection is UI configuration, not an input to project reasoning.

- **108 tests pass** from source and from the independently installed 0.2.2 wheel in the separate verification environment. The eight new tests cover identical analysis across targets, a new original example adapter without core changes, adapter output conflicts, explicit capability reporting, invalid targets, selected-host resource references, portable installation/configuration and workspace-free CLI capability listing.
- Before refactoring, 20 output groups were captured for each existing host's skill, subagent, task-role and HTTP/stdio proposal rendering. After refactoring, all 20 groups are **byte-identical**. No host format was changed in this iteration. Existing client-loading limitations remain applicable.
- Shared paths deduplicate identical bytes and reject conflicting bytes. Resource assignments no longer recognize vendor-specific directories in the service; they use selected adapter ownership. Unknown hosts fail explicitly instead of claiming universal native compatibility.
- Compilation and `git diff --check` pass. The project virtual environment is updated to 0.2.2. Core plan assumptions and generator version changed, so fresh approval hashes are required even though host-rendered instruction/configuration files retain their previous format.
- This is a trusted code extension contract, not an automatic external plugin loader. Host permission models remain separate. Generic exports portable skills/roles and project/task data; it does not invent a universal host MCP configuration or promise native execution in every editor.

Changes remain local and uncommitted on `feat/project-aware-architect`; no push or third-party agent execution was performed. Previous version results below are stage-specific records.

## Version 0.2.1 Antigravity support — October 19, 2026

The current local branch also supports `antigravity` as a platform target. `init` now defaults to `claude,codex,antigravity`; explicit targets remain supported. No commit or push was made.

- Current official [skills](https://www.antigravity.google/docs/skills), [custom agent](https://www.antigravity.google/docs/subagents/) and [MCP](https://www.antigravity.google/docs/mcp) documentation was checked. Skills share `.agents/skills` with Codex; native custom agents use `.agents/agents`. Skills in the shared directory may be discovered by either host in the same workspace; target selection does not provide host isolation.
- Generated/imported Antigravity agents use `view_file` and `grep_search`, are subagent-only, and have a quoted string shell policy `commandExecutionPolicy: "off"`. Upstream provider tools, hooks and permissions are stripped. License/notice evidence is retained. Runtime enforcement remains the host's responsibility.
- MCP proposal JSON uses `serverUrl` for HTTP or version-pinned stdio `command`/`args`, with `disabled: true`. Proposals stay outside active host settings. No workspace/global MCP settings are changed and no third-party process is launched.
- Codex/Antigravity shared skill output is deduplicated. Explicit normalized platform targets now enter the approval payload, so adding a host invalidates an old approval even if paths/content are identical. Fresh 0.2.1 approvals are required; automatic installed-output upgrades remain unsupported.
- **100 tests pass** from source and from an independently installed 0.2.1 wheel in a clean environment. The 12 added tests cover native roles, shared paths, disabled HTTP/stdio proposals, approval scope, installed-resource assignments, idempotence, symlink refusal, existing settings preservation, CLI target selection and the offline demo.
- The installed three-host/generic offline demo verifies **46 outputs**. An Antigravity-only installed-CLI configure/apply/verify flow verifies **7 outputs**, repeats as a no-op, and writes no active MCP configuration. Compilation and `git diff --check` pass.
- The local project virtual environment is updated to 0.2.1. Neither `agy` nor `antigravity` was found on PATH; real Antigravity app/CLI startup, role loading and permission behavior were not exercised. Use a disposable Antigravity project for that final host check.

## Version 0.2 local development — October 19, 2026

Work is on `feat/project-aware-architect`, based on main commit `7bf6375fbefb080397bcfbc1eea05b44c2bc67ee`. Changes are local and uncommitted; nothing was pushed. This section records the preceding 0.2.0 result; later iteration results are above. The 0.1 report below is historical evidence, not CI for this branch.

Environment: macOS, Python 3.14.3. There are no third-party runtime dependencies. Build isolation downloads setuptools from PyPI; no discovered skill or MCP package is executed.

### Changes verified

- Evidence-based English/Turkish requirement planning, bounded dependency manifest inspection, privacy-preserving summaries and explicit warnings.
- Frontend/API/data/database specialist planning, acceptance criteria, dependency graph validation, parallel waves and explicit handoffs. Security review waits for implementation.
- Official MCP Registry v0.1 discovery, metadata/status/transport policy, exact metadata provenance and cached offline inspection. Unsupported transports and metadata limitations remain visible.
- Exact approval for inert Claude/Codex proposals, repository permission for npm proposals, disabled Codex configuration, output verification, collision refusal, rollback and identical-repeat no-op.
- Current project evidence invalidates stale configuration approval. Editable saved tasks cannot inject arbitrary output paths/roles.
- CLI exact-content previews, safe JSON errors, structured stderr events and nine read-only MCP tools. Malformed candidate/policy/lock records fail with actionable errors.
- Version 0.2 metadata, new examples, documentation and an additional CI example command. GitHub Actions was not triggered for these local changes.

### Automated and installed-package results

- The source suite passes **88 tests** (52 baseline tests plus 36 additional tests), offline.
- A `stratagent_cli-0.2.0-py3-none-any.whl` was built and installed with `--no-index --no-deps` into a separate clean virtual environment. The installed-package suite passes the same **88 tests**.
- The installed console entry point runs the original offline demo and `verify` checks **37 generated outputs** successfully.
- The full-stack example reads two manifests, detects project domains and plans **nine roles** across five dependency waves.
- An installed-CLI stdio subprocess exchanges initialize, notification, tools/list, project analysis and recommendation messages: four JSON-RPC replies and **nine read-only tools**, with structured events confined to stderr.
- JSON/TOML proposal files parse in unit tests. The local **Codex CLI 0.163.0-alpha.10.2** accepts both disabled Streamable HTTP and pinned npm stdio settings using temporary command-line overrides and `mcp get --json`. This validates configuration parsing only: no server is started and no persistent client configuration is changed. The CLI reported a sandbox warning about inability to create PATH aliases, but both reads returned success.
- Bytecode compilation and `git diff --check` pass. No additional formatter/linter was introduced.

### Live network results

The current service successfully inspected the real GitHub API for `voltagent/awesome-claude-code-subagents`, resolved commit `408d3c9eee2d0c75c12a3abb5de29e53c2ca6b9e`, verified the blobs for `categories/01-core-development/api-designer.md`, and returned one eligible candidate with no errors. `save=False` was used; the candidate was not installed or executed. Review digest: `35b76189637ec89e59ab7a3de1eb83eddab06a0f580a4666756d941fd067a724`.

The new Registry client was exercised against `https://registry.modelcontextprotocol.io/v0.1/servers?search=playwright&version=latest&limit=3`. Read access outside the sandbox still timed out after the configured 20-second socket timeout; a diagnostic request confirmed `TimeoutError` while reading the response. TLS verification was not disabled and no alternate untrusted registry was substituted. **Live Registry response compatibility remains unverified**. Fixture tests validate the official API envelope and cover malformed responses, timeouts, credential isolation and metadata policy. Cached review and proposal generation pass offline tests.

### Remaining checks and next actions

1. Retry `discover-mcp --query playwright --limit 3` from an initialized workspace when the official endpoint is reachable; inspect live metadata and dry-run a proposal. Do not infer package safety from registry publication.
2. Install/use the generated skill and role layouts in disposable Claude Code/Codex projects, and exercise the read-only server through MCP Inspector or actual clients. Claude Code is not installed on this machine. Client startup, tool invocation, permission behavior and third-party server execution were not tested.
3. Review the local diff before committing or publishing. Updated CI configuration is present but has not run for this branch. Current local verification covers Python 3.14.3/macOS; Python 3.11/Linux/Windows checks for 0.2 remain pending.

Semantic LLM interpretation, native Codex subagent orchestration, MCP artifact/source/license audits, automatic agent execution, upgrades/removal and protection against a hostile local user are not implemented. Generated MCP settings remain inert and require manual activation. Existing 0.1 approval hashes must not be reused for 0.2 output.

---

## Historical 0.1 validation — October 18–19, 2026

Executed locally on macOS with Python 3.14.7. [GitHub Actions passed](https://github.com/etrkk5/stratagent/actions/workflows/tests.yml) on Ubuntu with Python 3.11 and 3.14, and macOS with Python 3.14. Each job installed the package, passed all 52 tests, ran the offline demo and verified its generated files.

Validation covers the `stratagent-cli` package, the `stratagent` command, `.stratagent/` workspace state and `stratagent_*` MCP tools.

## Automated checks

- 52 standard-library `unittest` tests pass without network access.
- Editable package installation succeeded in a new virtual environment.
- A standard wheel was built and installed with `--no-index` into another clean environment. The installed console entry point ran the offline demo and verified 31 generated files.
- CLI subprocess tests cover demo, planning, clean error output and a nonzero exit when file hashes drift.
- MCP tests exchange newline-delimited initialize, notification, tools/list and tools/call messages. Invalid JSON, invalid arguments, unknown/mutating tools and initialization ordering are checked.
- Safety tests cover Git blob/hash mismatch, mutable refs, traversal, control characters, duplicate paths, executable/symlink/submodule modes, binary/oversized files, unknown/conflicting/customized licenses, injection signals, exact approval scope, allowlist, no overwrites, rollback, concurrency locking, cache drift and role-resource binding.

## Live, read-only GitHub validation

Repository search was exercised through the actual GitHub API. For the broad `python agent skills` query, results included `langgenius/dify` and `shubhamsaboo/awesome-llm-apps`; this demonstrates the API path and also the limitations of repository-level search. Explicit repositories give more focused discovery.

Discovery inspected immutable commits:

| Repository | Commit | Result |
| --- | --- | --- |
| `openai/skills` | `49f948faa9258a0c61caceaf225e179651397431` | 44 definition paths enumerated; sampled security skills assessed |
| `VoltAgent/awesome-claude-code-subagents` | `408d3c9eee2d0c75c12a3abb5de29e53c2ca6b9e` | API designer and FastAPI developer definitions assessed |

The first live discovery returned four assessed candidates with no errors. MIT-licensed API designer/FastAPI sub-agents were eligible for human review. Security skill bundles with YAML metadata/scripts were blocked by the documentation-only policy. A security reference also triggered the conservative credential rule; this is not a claim that the upstream project is malicious.

After strengthening full license-body comparison, a second live run again recognized the Apache-2.0 skill and MIT sub-agent licenses, and produced an install dry-run for the API designer. The remaining requests encountered GitHub's unauthenticated rate limit. This exposed repeated requests after a global limit; the client now opens a circuit and discovery returns partial evidence after the first limit error. Regression tests confirm this behavior without making further network requests.

No real third-party candidate was installed, executed or launched. The tested install/lockfile/adapter flow uses only original bundled examples. The built-in live review/dry-run remained outside the source tree in a temporary workspace.

## Remaining verification limits

- Actual Claude Code/Codex runtime loading and a real MCP client/Inspector session were not executed.
- Python 3.11 and 3.14 were exercised in CI; intermediate Python versions and Windows were not tested.
- Static checks and license text matching are conservative filters, not a proof of safety, correctness or legal compatibility.
- Existing installation upgrades/removal, semantic LLM planning and launching coding-agent processes are outside this MVP.
