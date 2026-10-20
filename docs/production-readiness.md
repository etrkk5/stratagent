# StratAgent production-readiness plan

Created October 20, 2026. Status: **in progress; developer preview, not production-ready**. This is an implementation/release-gate document, not a promise that passing unit tests proves safety or broad adoption. The plan and implementation progress are versioned together; publication does not imply completion of the release gates.

## Product contract

A user describes a project. At runtime StratAgent interprets its needs, researches current public sources, compares relevant/popular options, reviews source provenance/security, designs roles and dependencies, previews exact changes, obtains authorization, applies the environment and verifies it. Later requests re-evaluate the existing environment and propose reviewed updates instead of forcing users to start again. Static catalogs, cached rankings and hand-written keyword lists cannot be the primary intelligence layer.

V1 scope is a local CLI plus a narrowly authorized coding-client integration, with host/provider-independent domain logic. It is not a hosted multi-tenant execution service. External text and model output are untrusted data. Popularity is not safety; a policy pass is not a claim of "safest." Source discovery, source review, local installation, credential provision and external process/network activation are separate authorities.

## Implementation sequence and exit gates

| Phase | Required implementation | Exit evidence | Status |
| --- | --- | --- | --- |
| P0: scope and safety contract | Define supported operations, data egress, approval boundaries, threat assumptions and release gates; record existing gaps honestly | This plan, architecture boundaries, explicit unimplemented features and preservation of previous user work | Planned baseline documented |
| P1: runtime research foundation | Provider-independent model research-plan contract, explicit review of public search terms, live per-run evidence cohorts, timestamps/expiry, partial/offline labeling and no stale-cache substitution | Negative tests for stale plans, changed context/query/targets, expired runs, cached-only candidates, unauthorized egress and readonly tools; installed CLI roundtrip | Implemented in 0.3.2; validation recorded separately; broader release gates remain open |
| P2: model-driven orchestration | Existing-host and optional explicitly configured model-provider drivers; bounded plan → search → inspect → compare → refine loop; typed tool results, persisted progress, cancellation/resume and cost/time/network budgets | Real model sessions on diverse projects, unknown/new technology terms, missing-resource questions, quota/outage recovery, no privileged tool authority in model output; API use opt-in with visible cost limits | Not implemented |
| P3: reviewed apply/update lifecycle | Diff against current managed output; stage/review/approve; per-file ownership; conflict refusal; backup/journal/recovery; idempotent updates/removal; structured state migrations; optional separately authorized host activation | Fault injection at every transaction stage, process-kill recovery, concurrent workspace operations, preservation of user files/settings, exact rollback after failed update and stale-approval refusal | New installs exist; updates/recovery/activation pending |
| P4: useful resource assurance | Typed support for real-world Agent Skills metadata and references; read-only code/artifact review without executing it; immutable package integrity when installable; license/permission/tool-manifest review; revocation and vulnerability policy | Adversarial corpus for traversal, archives, injection, secret access, permissive hooks and ambiguous licenses; pinned artifacts; reviewable residual risks; no unsupported source claimed audited | Documentation-only skill/static checks and Registry metadata checks exist; artifact/tool audits pending |
| P5: interoperability and quality | Adapter version/capability contracts, actual Claude Code/Codex/Antigravity sessions, clean machine onboarding, cross-platform installs; human-labeled project/architecture evaluations | At least 30 reviewed EN/TR project cases, no safety/exclusion violation in required cases, recorded false positives and resource gaps, independent pilot reproduction; tested host/version matrix; Windows results or explicit exclusion | One bounded Codex pilot; other runtime/quality gates pending |
| P6: operate and release | Privacy-preserving run diagnostics, health checks, opt-in telemetry, support/incident policy, signed/reproducible distribution evidence, SBOM/dependency review, upgrades/documentation and phased rollout | Green release CI, reviewed security findings closed or explicitly accepted, install/upgrade/uninstall on clean systems, recoverable release rollback, independent user pilots and published limitations | Not implemented |

Phase completion means its exit evidence exists. A file or CLI named after an operation is not completion. Gates P2–P6 cannot be replaced by more mocked tests or stronger README claims. Host support is claimed per capability/version actually exercised; platform independence does not mean universal native runtime compatibility.

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

P1's first local implementation is documented in [runtime-research.md](runtime-research.md), with measured results in [validation.md](validation.md). Next is P2, consuming that contract through an actual model driver and bounded refinement/session loop. P3 is required before advertising continuous environment maintenance. Revenue/adoption/uniqueness are product hypotheses to test with users, not engineering guarantees or reasons to bypass release gates.

## Continuation checkpoint — October 21, 2026

- Resume at P2, not a new static registry or website work. Preserve the StratAgent name and platform/provider-independent core.
- Start with a bounded existing-host model orchestration path over the research contract: propose public queries, pause for egress review, discover/inspect current sources, compare evidence and produce a reviewable architecture. Keep installation approval separate.
- Persist typed progress and sanitized evidence sufficient for cancellation/resume; enforce total model-call, time and network budgets before adding more providers or automatic refinement.
- Add failure-path and integration tests for quota/outage, missing resources, changed context, interrupted sessions and untrusted tool/model output. Do not claim fresh success from partial or cached-only evidence.
- P3 updates/removal/crash recovery, P4 artifact audits and P5 native Claude Code/Antigravity sessions remain outstanding. The bounded Codex pilot and 184-test baseline are evidence, not production certification.
