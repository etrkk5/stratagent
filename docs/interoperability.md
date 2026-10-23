# P5 adapter contracts and native-host evidence

P5's engineering checkpoint is **complete for the revised documentation-based scope**. Versioned renderer contracts, official-documentation review, the reserved Claude skill-name fix and automated source/installed acceptance support this checkpoint. Native runtime certification and human usefulness were not established. The original [production plan](production-readiness.md) required additional field evidence; the user's explicit scope change below removes those items as blockers to continuation.

## Scope decision — October 23, 2026

The user explicitly chose to skip real Claude Code/Antigravity sessions, the 30 human evaluations and independent installation trials, and proceed using the hosts' documentation and disclosed assumptions. These three checks are **waived by user decision, not performed or passed**. They no longer block P5 engineering completion or P6 work. No synthetic reviewer identities, native-session results or independent-pilot records are added. `host_runtime_certified` remains false.

The replacement acceptance is official-documentation review of supported skill/role/MCP formats, correction of identified renderer gaps, automated approval/collision/provenance/lifecycle tests and reproducible setup instructions. [Host setup](host-setup.md) links each host's actual official pages and provides scoped local-bridge configurations. This scope decision does not alter source, egress, exact-install approval or inactive-server boundaries, and does not establish production readiness.

## Renderer contract

Run `stratagent platforms` without an initialized workspace. Each target now reports its `contract_schema_version`, `adapter_version`, skill/role roots and format, MCP proposal support, a digest of the generated role header and explicit execution/permission boundaries. The command reads no workspace, starts no host and makes no network calls.

Contract schema 1 describes **inert file generation**. Adapter versions use `major.minor.patch`; they are StratAgent renderer versions, not host versions or supported host-version ranges. A major change breaks the declared output contract; minor changes add behavior; patches correct behavior within that contract. Maintainers must revise an adapter's version when changing rendering semantics, paths, supported formats or permission headers. Output hashes independently bind the actual bytes; the header digest also exposes header changes directly. These declarations are maintained in trusted source, not downloaded plugin metadata.

Claude adapter **1.1.0** adds the documented reserved-name mapping. Other built-in adapters remain 1.0.0. The `reserved_skill_names` and `reserved_name_prefix` policy is part of the contract and therefore exact approval. Skill paths and generated names agree; relative references/notices and original reviewed source are preserved. Existing reserved-name installations are not silently renamed: review a lifecycle update/removal, with ordinary ownership/drift/conflict checks.

Every new installation/update/removal/revision preview includes the selected `adapter_contracts` in its approval payload. Staging/apply reconstructs the contracts; a changed selected adapter invalidates an unapplied stage even when output bytes match. Installed provenance retains the approved contracts. Changing an unselected adapter does not invalidate an otherwise identical plan. The identical-installation shortcut also compares contracts before accepting an older approval.

Earlier lock records without contracts remain readable, verifiable and removable with a fresh removal approval. Reading them does not migrate or certify them. Reapplying with current contracts requires a fresh review/approval; it does not reuse historical approval authority. A completed stage may still return a verified no-op for that already committed transaction; that does not authorize new writes. Recovery continues to use the recorded transaction bytes rather than rendering a new environment.

All targets report `host_runtime_certified: false` and `native_multi_agent_orchestration: false`. Permission headers are requests interpreted by the host, not an OS sandbox or proof of enforcement. MCP output remains a separate, inactive proposal requiring manual activation; generic output has no host MCP renderer.

## Observed host matrix

| Host | Exact observed version | Evidence | Still missing |
| --- | --- | --- | --- |
| Codex CLI | `0.163.0-alpha.10.2` | Historical [October 20 pilot](pilot-validation.md) and [October 22 existing-host acceptance](p2-existing-host-validation.md). October 23: actual CLI reads both generated disabled HTTP and pinned npm stdio proposals with `mcp get --json`, exit 0, `enabled: false` | Fresh full P5 native-session matrix, clean-machine onboarding and independent reproduction; parsing alone does not test model/tool invocation or permission enforcement |
| Claude Code | Not observed on this Mac; executable absent from PATH | Offline renderer tests only | Installed/versioned native session, skill/role loading, scoped MCP invocation, permission behavior and onboarding |
| Antigravity | Not observed on this Mac; executable absent from PATH | Offline renderer tests only | Same native evidence; do not infer runtime support from exported agent headers |
| Generic | No universal native host version | Portable-output and approval/lifecycle tests | A specific consumer must supply its own version and actual loading evidence |

The October 23 Codex parser check uses command-line overrides for one uniquely named disabled proposal. It does not edit persistent host settings, invoke a model, contact either example endpoint or run `npx`. The first invocation rejected a top-level `--ignore-user-config` flag; the successful checks omitted that unsupported flag and read only the explicitly named entry. Codex also emitted a PATH-alias permission warning; the two configuration reads themselves succeeded. This is configuration parsing evidence, not a passed native-session gate.

## Original field procedure — now optional under the waiver

Use a fresh disposable copy of an original public fixture for each tested host/version. Record the OS, Python, StratAgent base commit/diff and exact host version before connecting the local scoped MCP bridge. Follow [orchestration.md](orchestration.md) and the [pilot procedure](pilot-validation.md), keeping source search, installation and activation authority separate.

Record actual tool calls, validated proposals, generated files read by the host, refusal/failure observations, final hash verification and preservation of original user files/settings. State which permissions were actually exercised. Do not turn fixture parsing or the presence of a disabled setting into a permission-enforcement pass. Retain sanitized evidence, not credentials or raw private model logs.

The original quality gate called for at least 30 **human-reviewed** EN/TR project cases covering scope, exclusions, role allocation, alternatives, unnecessary resources, false positives and missing resources. That gate is now waived for continuation. If collected later, record the reviewer, actual proposal/run identity, observations and disposition. The ten existing deterministic fixtures and six historical P2 cases are not relabeled as 30 completed human reviews. No new human reviews or independent pilots were performed.

Cross-platform package/lifecycle CI remains separate from native host compatibility. New local changes cannot inherit a previous commit's CI result. P6 operational/distribution work is next and remains outstanding; the three waived P5 field checks are not prerequisites for starting it.
