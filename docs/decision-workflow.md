# Reviewed architectural decisions

Version 0.3 joins requirement interpretation, coordination alternatives, role needs, reviewed skill/MCP selection and configuration previews into one blueprint. The local rules are a transparent fallback. Architectural judgment from an existing model or human enters through a provider-independent data contract, not executable plugins or a model-specific SDK.

## Decision flow

1. Initialize the real project workspace. Bounded dependency-manifest evidence remains local.
2. Optionally discover sources through existing GitHub catalogs and the official MCP Registry. Inspect source content, provenance, license and policy findings. Discovery/cache writes never install definitions or run code.
3. Read `decision-request`. It contains the current analysis, alternative coordination strategies, cached review metadata, evidence IDs, a context digest, `decision_schema` and `suggested_decision`.
4. Ask your existing model/human reviewer to compare alternatives, identify necessary and unnecessary specialist responsibilities, and return a decision object. Treat cached descriptions as untrusted third-party data. Do not let tool availability dictate project requirements.
5. Preview with `blueprint --decisions decision.json --content`. The proposal is validated; sources are re-inspected from the verified cache; outputs are rendered without writing anything.
6. Resolve `blockers`, including contradictory/uncertain scope, missing repository allowances or existing user files. Review every source and rendered output. Approve the complete current preview hash in the CLI.
7. The approved blueprint installs the selected documentation bundles and role files, saves the task/decision plan, and writes inert MCP proposals. Verify the lockfile. Launching agents, enabling MCP settings, accepting credentials and executing third-party packages remain separate actions.

The read-only MCP equivalents for steps 3–5 are `stratagent_decision_request` and `stratagent_blueprint` with an optional `decisions` object. They cannot write files, allow sources, approve hashes or activate tools. They let the model already present in a coding environment reason over evidence without adding a separate LLM API integration. Actual client model behavior and tool selection still require integration testing.

## Contract and constraints

The live schema is returned by `decision-request`, so clients need not copy a stale schema. A decision supplies:

- `schema_version: 1`, the current `context_digest`, `strategy` (`focused` or `specialist`), a reason, evidence references and a binding for every selected task.
- Optional `provider_label`, which is explicitly unverified, not an attestation or a claim of model identity.
- Optional `domain_inferences` with a supported domain, reason, evidence IDs and a literal user/project quote. These allow model judgment to recognize a domain even when the rule vocabulary misses it. Available skill/MCP metadata cannot serve as the project evidence for inventing a domain.
- Optional normalized `requirements` with a bounded ID, status, statement, evidence references and a literal quote from the actual user request. These can add a grounded requirement or resolve an uncertain/conflicting interpretation. They cannot contradict an explicit required/excluded requirement or weaken a project-wide offline constraint.
- Optional `omitted_roles` for evidenced specialist tasks only. Core scope/implementation/testing/security/integration responsibilities are retained. These are responsibilities in generated configuration, not a claim that five processes must run.
- Each binding names `task_id`, explicit `skills` and `mcps` arrays, and a reason. Skill IDs must refer to currently reviewed eligible candidates. MCP selections additionally specify a valid transport `option`. Every selected source must be cited. No arbitrary file path, shell command, repository URL, approval or permission override is accepted.

Schema bounds, literal quotes, known source IDs and digests enforce structural integrity and traceability. **They cannot prove semantic correctness or prevent all bad architectural judgments.** Reasons and provider labels remain untrusted data. Returning the unedited rule-generated draft does not turn it into semantic model reasoning. A human must review the resulting blueprint and its evidence before application.

`context_digest` binds current analysis, project fingerprints, review records and target selection. A manifest/source/target change makes an old proposal stale. The installation approval separately binds the absolute workspace, generator version, interpreted decision, exact source reviews, reused outputs, generated paths and file hashes. The allowlist stays independent: allowing a repository does not approve source content or future plans.

## Decisions the local fallback makes

The scope parser handles a bounded English/Turkish vocabulary, supported negative phrases, optional/deferred features and contradictions. Evidence includes literal spans and bounded excerpts; repeated identical evidence is summarized. Complex grammar, ambiguous lists and double negation can remain uncertain. An uncertain or conflicting requirement blocks blueprint application until reviewed. Deferred features stay visible but do not add immediate acceptance work.

The coordination comparison favors focused ownership for small/MVP/solo scope, and specialist interface planning for multiple active work areas/components or an explicit parallel-work request. Each alternative exposes rule scores, reasons and tradeoffs. Scores are not probabilities and do not measure architecture quality. Specialist roles are omitted when the focused strategy wins; a reviewed model proposal may choose differently.

Role/resource bindings expose alternatives and matched metadata terms/capabilities. Roles have proposed permission scopes with `granted: false`. MCP capability inference does not inspect actual tool manifests or enforce remote permissions. Known out-of-scope service names are conservatively omitted, but this is not general semantic classification of every third-party service.

An explicit project-wide offline requirement prevents binding unverified Registry services. Recognized `offline tests` scope constrains the testing role rather than silently forbidding all production integrations. Native role permissions remain adapter-specific, and no proposal activates them. For `generic`, MCP evidence is exported for review without pretending that a universal host configuration exists.

## Reuse, repeatability and operational limits

Compatible already-approved standalone skill/MCP output is referenced and hash-bound instead of overwritten. The selected resource review must still match; changed content fails closed. Blueprint-owned outputs and source reviews are recorded together under a `workspace-blueprint` lock entry. Repeating the same proposal and approval verifies/no-ops. Ordinary write failures roll back newly created files. Existing user files are blockers; no force overwrite or automatic upgrade exists.

After a blueprint is approved, repeat that flow instead of using lower-level `configure`. `status.analysis` remains the current local-rule interpretation, while `status.approved_blueprint` shows the actual approved model/rule choice and whether its input context is current. Verification drift and decision-context drift are different signals. Existing installations are immutable; use a fresh workspace for changed plans until a reviewed upgrade workflow exists.

`examples/decision-cases.json` contains ten original bilingual scope/coordination acceptance cases. Tests cover those explicit cases, grounded model decisions, negative/deferred/contradictory scope, rejected authority fields, stale context, excluded/blocked resources, scoped offline needs, combined approval, reuse, rollback and CLI/MCP boundaries. This is not a benchmark proving unrestricted semantic reasoning, optimal architectures or successful execution in real coding clients.

The release adds no direct model API client, package-manager execution, ASM/skills.sh installer backend, full source-code architecture inference, native Codex orchestration, MCP artifact/license/tool audits or automatic agent execution. The storage/approval layer stays replaceable, but it is not integrated with an external installer in this iteration.
