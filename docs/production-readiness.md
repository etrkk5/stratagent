# StratAgent production-readiness plan

Created October 20, 2026. Status: **in progress; developer preview, not production-ready**. This is an implementation/release-gate document, not a promise that passing unit tests proves safety or broad adoption. The plan and implementation progress are versioned together; publication does not imply completion of the release gates.

## Product contract

A user describes a project. At runtime StratAgent interprets its needs, researches current public sources, compares relevant/popular options, reviews source provenance/security, designs roles and dependencies, previews exact changes, obtains authorization, applies the environment and verifies it. Later requests re-evaluate the existing environment and propose reviewed updates instead of forcing users to start again. Static catalogs, cached rankings and hand-written keyword lists cannot be the primary intelligence layer.

V1 scope is a local CLI plus a narrowly authorized coding-client integration, with host/provider-independent domain logic. It is not a hosted multi-tenant execution service. External text and model output are untrusted data. Popularity is not safety; a policy pass is not a claim of "safest." Source discovery, source review, local installation, credential provision and external process/network activation are separate authorities.

## Current product priority — agent-first experience, October 23, 2026

The user prioritized a compelling, simple product experience before further
announcement/distribution work, selecting natural-language use inside the existing
IDE/coding agent. [The active UX track](agent-first-experience.md) defines the user
journey, engineering acceptance and remaining experiential evidence. Unreleased
0.9.0 adds first-party project skill integration, start/next guidance and useful
review summaries over the existing research/approval/lifecycle engine. A packaged
workflow is not evidence that every agent/user prefers it; native discovery and
real usefulness remain distinct. The published 0.8.0 artifacts are preserved.

The user's subsequent ambition is sustained developer/agent preference and
potential strategic-provider integration. [Product direction](product-direction.md)
records the differentiated-value hypothesis, current gaps and the next product
order: reuse the existing environment, explain recommendation quality, then earn
repeat use through maintenance. These planned increments do not change historical
P1–P5 evidence or turn adoption/acquisition ambitions into achieved outcomes.

## Implementation sequence and exit gates

| Phase | Required implementation | Exit evidence | Status |
| --- | --- | --- | --- |
| P0: scope and safety contract | Define supported operations, data egress, approval boundaries, threat assumptions and release gates; record existing gaps honestly | This plan, architecture boundaries, explicit unimplemented features and preservation of previous user work | Planned baseline documented |
| P1: runtime research foundation | Provider-independent model research-plan contract, explicit review of public search terms, live per-run evidence cohorts, timestamps/expiry, partial/offline labeling and no stale-cache substitution | Negative tests for stale plans, changed context/query/targets, expired runs, cached-only candidates, unauthorized egress and readonly tools; installed CLI roundtrip | Implemented in 0.3.2; validation recorded separately; broader release gates remain open |
| P2: model-driven orchestration | Existing-host plan → search → inspect → compare → refine loop; typed results, questions, persisted progress, cancellation/resume, proposal/time/network limits. Optional direct-provider transport is outside the user-selected current scope | Six real EN/TR cases, directed refinement after controlled quota/outage, question/answer path, real process-death recovery, source/installed tests, no model execution authority; host billing explicitly remains outside the bridge | Existing-host scope implemented and locally validated in 0.4.1; [acceptance record](p2-existing-host-validation.md). Not a production/GA claim |
| P3: reviewed apply/update lifecycle | Diff against current managed output; stage/review/approve; per-file ownership; conflict refusal; backup/journal/recovery; idempotent updates/removal; structured state migrations; optional separately authorized host activation | Fault injection at every transaction stage, process-kill recovery, concurrent workspace operations, preservation of user files/settings, exact rollback after failed update and stale-approval refusal | Reviewed lifecycle implemented in 0.5.0; OS-independent boundary and Windows backend in 0.5.1. [Contract](lifecycle.md), [native OS evidence](validation.md). Optional activation not added; production gates remain open |
| P4: useful resource assurance | Typed support for real-world Agent Skills metadata and references; read-only code/artifact review without executing it; immutable package integrity when installable; license/permission/tool-manifest review; revocation and vulnerability policy | Adversarial corpus for traversal, archives, injection, secret access, permissive hooks and ambiguous licenses; pinned artifacts; reviewable residual risks; no unsupported source claimed audited | 0.7 implements the declared non-executing assurance checkpoint: metadata/references, bounded SRI/archive/code/license/entrypoint audit, tool snapshots, local revocation and fresh root npm OSV policy. Source/installed/adversarial and real-provider evidence are recorded in validation. Unsupported executable/dependency closure remains blocked, not certified; P5/P6 remain necessary |
| P5: interoperability and quality | Versioned adapter contracts, documented host formats/setup and automated interoperability/lifecycle acceptance. Original field scope retained in the acceptance record | Revised acceptance: official-doc review, fix identified format gaps, source/installed regression and CLI checks. Original real multi-host sessions, 30 human reviews and independent installation trials explicitly waived by user; no fabricated passes | Engineering checkpoint complete for the revised scope; [scope decision, contracts and host evidence](interoperability.md), [documented setup](host-setup.md). Claude reserved-name mapping fixed. Runtime certification/usefulness remains unmeasured, not a continuation blocker |
| P6: operate and release | Privacy-preserving run diagnostics, health checks, opt-in telemetry, support/incident policy, signed/reproducible distribution evidence, SBOM/dependency review, upgrades/documentation and phased rollout | Green release CI, reviewed security findings closed or explicitly accepted, install/upgrade/uninstall on clean systems, recoverable release rollback, independent user pilots and published limitations | Implementation checkpoints: offline [diagnostics](diagnostics.md), [repeated source/wheel builds, distribution SBOM, offline package lifecycle and rollback/support procedure](releasing.md). Version 0.8.0 remains a developer preview. Six-job main CI passed for engineering merge `8602a0e`; publication tooling needs fresh exact-commit evidence. External attested promotion, private reporting and read-only declared-pin advisory checks are implemented; actual publication is recorded in its workflow/manifest. PyPI account setup and staffed/broader monitoring remain separate |

Completion against an evidence gate means its evidence exists; a named file/CLI or stronger README claim is not a substitute. An explicit user scope change can waive a gate, but the record must distinguish waiver from a performed/passed test. P5 now uses the documented revised acceptance below. Host runtime certification is claimed only for capabilities/versions actually exercised; documentation-based compatibility remains an explicit assumption.

## Runtime architecture

The intended engine separates `RequirementInterpreter`, `ResearchPlanner`, fixed-host `SourceConnector`s, `EvidenceStore`, `RiskEvaluator`, `WorkspacePlanner`, `TransactionManager` and `HostAdapter`s. These are responsibility boundaries, not a reason to add speculative base classes. Introduce interfaces when more than one real implementation needs them. Keep model transport independent of host rendering and keep executable authority outside model plans.

Each run binds its workspace/project context, selected targets, research plan, budgets, live observations and expiry. Mutable search/default-branch metadata must be re-read for a new run; only immutable blobs/trees may be reused as content cache. A failed refresh must not silently select yesterday's candidates. Partial coverage and deliberately offline, pinned-cache work are distinct modes and must remain visible. Decisions, approval and output provenance must bind the same research run.

Model-proposed public search terms can extend beyond built-in vocabularies, but may accidentally include sensitive data. Preview exact outbound terms and obtain a separate egress approval before executing those queries. Model plans/read-only MCP tools cannot carry search, installation, credential or execution authority. A host that independently grants the same agent unrestricted local shell/file access must enforce its own permission boundary; a plan hash is not cryptographic proof of a human click. Fixed connectors reject arbitrary URLs/commands; network destinations and query budgets are bounded. Quotes/evidence references establish traceability, not semantic truth or automatic proof that terms are public.

## Reliability and security gates

- Explicit state transitions with run IDs and sanitized diagnostics; failures retain partial evidence without claiming a ready environment.
- Request, elapsed-time, result, artifact-size and model-call/cost budgets; bounded retry/backoff honoring provider limits, not quota circumvention. Cancellation/resume must not duplicate destructive actions or charges.
- Exact output/source/target/context approval, drift detection, no implicit overwrite and separately scoped activation/secret handling. Prove ordinary rollback and process interruption recovery; document trusted-local-user/OS assumptions.
- Remote MCP behavior remains mutable after activation. Metadata, source and artifact audits are different assurance levels. Unsupported/audit-incomplete resources cannot be marketed as safe or silently enabled.
- Prompt injection and malicious source descriptions are data, never instructions to the orchestrator. Credential values and private source content must not enter general logs or search queries. Raw model/session logs are not publishable telemetry.
- Never fall back from a failed live provider into a successful-looking fresh result. Show missing evidence, stale state, limited coverage and unsupported formats explicitly.

## Release decision

Maintain a checked release matrix with links to actual test runs, host versions, threat cases, pilot feedback and residual risks. No known critical authority/integrity defect may remain open. The scope/quality evaluation must be reviewed by a human; arbitrary architecture optimality is not mechanically provable. A conservative private pilot precedes public beta; GA is conditional on the declared capability gates, not a date.

P1's first local implementation is documented in [runtime-research.md](runtime-research.md), with measured results in [validation.md](validation.md). P2 consumes that contract through an actual model driver and bounded refinement/session loop; its first progress is recorded below. P3 is required before advertising continuous environment maintenance. Revenue/adoption/uniqueness are product hypotheses to test with users, not engineering guarantees or reasons to bypass release gates.

## Current checkpoint — preview publication and community launch, October 23, 2026

The publication workflow promotes only six successful exact-commit main CI bundles without rebuilding, attests each public asset, verifies workflow/ref/commit identity, creates a draft and rechecks uploaded bytes before publishing a pre-release. [Publishing](publishing.md) records consumer verification, recovery and optional account-owner PyPI setup. Private reporting is enabled and verified; support forms and read-only scheduled direct-pin advisory checks are configured. [Announcement drafts](community-launch.md) and a measured offline demo replace the obsolete 0.2 positioning. Actual workflow outcomes, not the presence of these files, establish publication. The original P5 waivers remain unchanged.

## Earlier checkpoint — 0.8.0 reproducible preview distribution, October 23, 2026

The user authorized completing the distribution/SBOM/release checks and branch CI. The release helper builds two independent normalized source archives and their wheels in fresh directories, refuses mismatches/dirty source/existing output by default, verifies complete wheel RECORDs and generates hash-bound distribution/license inventories plus CycloneDX 1.6. Build tooling is pinned by version and universal-wheel hashes. Offline developer acceptance covers clean install, real 0.7.0 → 0.8.0 package upgrade, workspace preservation and package uninstall. [Release/rollback/support procedure](releasing.md) records exact commands and boundaries; [validation](validation.md) separates measured local results from actual branch CI. The package is a developer preview, unsigned and unpublished to PyPI; no human/native-host evidence or signing identity is invented.

## Earlier checkpoint — P6 offline health diagnostics, October 23, 2026

The user authorized preserving P5 in a local commit and continuing with installation health. P5 was saved as `63f3794` on the existing branch. `doctor` now runs without the YAML-dependent application imports and diagnoses pinned dependency availability, package/code version mismatch, filesystem/adapter declarations, incomplete state, metadata schemas and recovery needs. `--check-files` opts into bounded output verification. Reports omit private paths/content and raw exceptions; no network, process launch, mutation, automatic repair or telemetry occurs. [Diagnostic usage and limits](diagnostics.md) and measured [validation](validation.md) record the scope. P6 remains in progress; this is not a release/production claim and does not waive remaining distribution, support or incident-response work.

## Earlier checkpoint — P5 revised documentation-based acceptance, October 23, 2026

After the initial audit, the user explicitly waived real Claude Code/Antigravity sessions, the 30 human evaluations and independent installation trials, asking to proceed from official documentation and assumptions. These are recorded as **waived, not performed or passed**. P5 engineering is complete for the revised scope: versioned contracts, official host-format review, the Claude reserved skill-name fix, documented scoped bridge setup and source/installed/CLI regression evidence. The [acceptance record](interoperability.md) and [setup guide](host-setup.md) identify actual references and limits. No host certification or human evaluation results are invented; P6 is the next phase and is still unimplemented. The scope decision does not weaken source policy, per-action approvals or transaction recovery.

## Earlier checkpoint — initial P5 adapter contracts, October 23, 2026

The [continuation audit](continuation-2026-10-23.md) recovered the actual P1–P5 sequence from GitHub after this Mac's checkout was found 14 commits behind. The final P4 and README commits were already published on main. P5 begins with versioned, explicit inert-renderer contracts in the adapter catalog, exact approval payloads and lock provenance. Selected contract changes invalidate staged/direct approvals and cannot reuse the identical-installation shortcut; historical locks remain readable/removable without silent migration. [Interoperability](interoperability.md) separates these contracts and actual Codex configuration parsing from native runtime certification. No new human-reviewed corpus, independent pilot or Claude Code/Antigravity session exists; P5 is not complete. Measured local source/installed results are recorded in [validation](validation.md). P6 remains unimplemented.

## Earlier checkpoint — P4 artifact/tool and security policy, October 22, 2026

Version 0.7.0 implements the requested remaining artifact/tool inspection and local revocation/advisory mechanisms for the declared strictly non-executing checkpoint. [Artifact assurance](artifact-assurance.md) defines exact network approval, pinned bytes, archive/code/license/permission boundaries, root-only advisory TTL/failure policy, untrusted tool snapshots and installed impact. No package manager, lifecycle hook or third-party server is run; incomplete dependency closure blocks artifacts. Local source/installed tests and actual provider evidence are recorded in [validation](validation.md). An anonymous GitHub rate limit was reported honestly, then two additional MIT text skills were verified through the existing authenticated GitHub session. Two real npm archives were SRI-verified and rejected for explicit dependency/license limitations. This completes the bounded audit/policy implementation, not universal skill/package compatibility or production certification. P5/P6 remain unstarted; today stops after the authorized reviewed main publication, without automatic follow-up or package release.

## Earlier checkpoint — P4 source metadata/references, October 22, 2026

Version 0.6.0 begins P4 with a bounded standard YAML parser, typed Agent Skills metadata, raw/decoded injection scanning, pinned local-document reference evidence, fail-closed source permissions/unsupported fields and explicit non-audited assurance levels. Scanner 1 reviews require rediscovery; no installed file or prior authority is silently migrated. [Resource assurance](resource-assurance.md) records exact supported syntax/limits, dependency review, realistic source gaps and remaining artifact/tool/revocation work. P4 remains in progress; do not advance to P5 or call this production-ready.

## Earlier checkpoint — P3 reviewed lifecycle, October 22, 2026

P3 implements CLI-only stage/review/exact approval, current-state/source revalidation, per-file ownership, explicit request/target revisions, reviewed blueprint updates/removal and v1 → v2 lock migration. A backup journal precedes output changes; lockfile replacement commits the transaction. Precommit failures restore original bytes/modes/lock, process interruption requires reviewed rollback/finalization, and pending recovery blocks unrelated writes. User files/settings, drift and resource dependencies fail closed. The [lifecycle contract](lifecycle.md) records authority boundaries and reproducible acceptance; [validation.md](validation.md) records measured results.

The declared implementation scope is **inert managed files on local filesystems**. Version 0.5.1 centralizes POSIX/Windows locks, replacement, mode observation and redirect rejection behind [filesystem capabilities](os-portability.md). The [accepted native Ubuntu/macOS/Windows × Python 3.11/3.14 matrix](https://github.com/etrkk5/stratagent/actions/runs/39838604544) passes all six jobs, including source/installed suites and original CLI acceptance; [validation](validation.md) records all 275 tests, expected POSIX skip and earlier failures/cancelled run. Windows inherits ACLs and does not claim POSIX directory fsync. Arbitrary dependency execution/activation, physical power-loss certification and network filesystems are not claimed. Optional activation remains manual until P4/P5 assurance gates. P4 has not started. The [release checklist](release-readiness.md) names the still-blocking artifact, human/host evaluation and operational release evidence; OS CI cannot replace them.

## Earlier checkpoint — P2 existing-host scope, October 22, 2026

The user chose to complete P2 using the existing LLM session first. The optional direct-provider API/true upstream billing-accounting path is therefore **not required for this scoped checkpoint and is not claimed implemented**. The host retains model transport/account billing; StratAgent bounds submitted proposals, source calls and session lifetime. Core host/provider independence is preserved.

The [acceptance record](p2-existing-host-validation.md) documents six final real EN/TR cases, model refinement after controlled source failure, missing-information questions and operator answers, preserved exclusions, current-cohort selection, actual POSIX process termination/recovery, 221 source/installed tests and known limits. Earlier defective attempts were fixed and retested with fresh contexts/approvals, not counted as passes. P3 lifecycle work has not begun; it is the next phase after review of this P2 checkpoint. This checkpoint records prepublication local validation; publication history and commit-specific CI results are available in Git and [GitHub Actions](https://github.com/etrkk5/stratagent/actions/workflows/tests.yml).

## Earlier P2 progress — October 22, 2026

The first [cooperative existing-host driver](orchestration.md) now persists typed model requests, validated research/decision proposals, exact run cohorts, budgets and sanitized event history. Scoped MCP exposes only one session's request/submit tools; separately approved CLI research drives the comparison/refinement loop. Revision checks, durable reservations, explicit cancellation and no-replay resume address bounded orchestration interruption, not installation/update recovery. This is not an unattended provider driver: the operator returns the host to each request and separately approves each query plan. Submitted-proposal limits cannot be claimed as upstream model billing/call limits. Direct opt-in provider transport/cost control, diverse real model evaluations and the remaining P2 exit evidence are still required. Local validation is recorded in [validation.md](validation.md); no release/CI claim follows merely from creating these files.

That earlier checkpoint required diverse EN/TR cases and refinement/quota/interruption evidence beyond the single-query pilot. Those existing-host checks are recorded above; optional direct-provider work was explicitly deferred by the user's scope choice. P3 remains necessary before continuous environment maintenance is advertised.

## Continuation checkpoint — October 21, 2026

- Resume at P2, not a new static registry or website work. Preserve the StratAgent name and platform/provider-independent core.
- Start with a bounded existing-host model orchestration path over the research contract: propose public queries, pause for egress review, discover/inspect current sources, compare evidence and produce a reviewable architecture. Keep installation approval separate.
- Persist typed progress and sanitized evidence sufficient for cancellation/resume; enforce total model-call, time and network budgets before adding more providers or automatic refinement.
- Add failure-path and integration tests for quota/outage, missing resources, changed context, interrupted sessions and untrusted tool/model output. Do not claim fresh success from partial or cached-only evidence.
- P3 updates/removal/crash recovery, P4 artifact audits and P5 native Claude Code/Antigravity sessions remain outstanding. The bounded Codex pilot and 184-test baseline are evidence, not production certification.
