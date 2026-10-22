# P2 existing-host acceptance record

Recorded October 22, 2026, on macOS/Python 3.14.3 with the developing 0.4.1 worktree and Codex CLI 0.163.0-alpha.10.2. **P2's existing-host scope is implemented and locally validated; the overall product remains a developer preview.** The user explicitly selected using the existing LLM session first, not an additional direct-provider API. No API SDK/key requirement, hidden provider call or claim of an upstream billing cap is added. That optional extension is outside this scope, not represented as implemented.

## Declared acceptance scope

- The model proposes project-specific public queries and grounded architecture through a host/provider-neutral contract; no product resource catalog supplies its decisions.
- Every source-query plan, including a refinement, pauses for a separate exact operator review. Model proposal tools cannot grant search/installation/credential/execution authority.
- Current evidence, partial failures and unsupported/irrelevant resources remain visible. A proposal can reach review while application remains blocked; no ready-environment claim follows.
- The model can ask missing project/resource questions; only the operator changes planning input, with old context/approvals invalidated and no budget reset.
- Progress is durable; request identities, budgets, cancellation and explicit no-replay resume are enforced. Actual process-death tests cover the supported local POSIX planning scope.
- Source/installed-package tests, console/stdio boundaries and opt-in real-model procedures are reproducible. Cross-host native runtime and broad architecture-quality/user acceptance remain P5, not inferred from an MCP adapter contract.

## Six real project cases

The [opt-in helper](../scripts/validate_existing_host.py) contains original public test ideas, not a registry. Three EN and three TR cases were evaluated with actual existing model sessions. Each final case reached `review-required` with **zero installations, repository trust grants, server activations or third-party code execution**. The table records observations at proposal time, not evergreen resource availability or an approval reusable after evidence expiry.

| Original case | Real model path | Latest observed source cohort | Result at review |
| --- | --- | --- | --- |
| EN: Qdrant retrieval API/privacy/synthetic tests/no payments | Research → approved live sources → compare | 2 repository inspections, 0 definitions, 2 MCP metadata records; 9 connector calls; complete bounded run | Focused architecture, seven local outputs; ineligible MCPs not selected; no claim of complete dependency setup |
| TR: DuckDB CSV quality/offline tests/no UI or payments | Research → separately approved controlled 429/outage → model refinement → new approval → live sources → compare | First: 2 controlled failing calls, partial. Latest: 1 repository inspection, 0 definitions/MCPs, 9 calls, GitHub review errors | Focused architecture; current partial run blocks application; failed first cohort not substituted as fresh evidence |
| EN: Playwright browser/accessibility/privacy/no payments | Research → approved live sources → compare | 2 repository inspections, 0 definitions/MCPs, 9 calls, Registry errors | Focused architecture, explicit payment exclusion; partial research blocks application |
| TR: Rust/NATS JetStream/OpenTelemetry/failure tests/no payments | Research → approved live sources → compare | 1 repository inspection, 0 definitions/MCPs, 6 calls, Registry errors | Focused ownership retains independent failure/security review; partial research blocks application |
| EN: SvelteKit/PostgreSQL staff/auth/privacy/no payments | Research → approved live sources → compare | 2 repository inspections, 2 definition reviews, 0 MCPs, 13 calls, Registry errors | Specialist frontend/API/database ownership; malformed definition rejected, eligible but unrelated fleet-coordination skill not selected; partial research blocks application |
| TR: underspecified support assistant → public Markdown FAQ/Python/container/read-only/no personal data or payments | Model questions → operator's complete revised request → fresh model research → new approval → live sources → compare | 0 repository inspections/definitions, 2 MCP metadata records, 3 calls; complete bounded run | Focused architecture; eligible but irrelevant publishing MCP and ineligible conversion MCP not selected; independent testing/privacy review retained |

These final paths involved **14 real model sessions**, each exiting 0. Their logs contain **29 scoped MCP calls** and no other host tool actions. The helper verifies the request/submit allowlist rather than assuming its prompt was followed. Required research/refinement/clarification branches were explicitly directed by the evaluation procedure; this validates transport/state/approval behavior and observed reasoning, **not autonomous action-selection quality**. The comparison proposals used actual observed candidates and explained scope, exclusions and resource gaps. Resource eligibility and popularity were not treated as safety or usefulness guarantees. One observed GitHub query reported 2,393 matches but returned only the approved top ten; only two repositories were inspected. Counts of all matches, returned metadata, inspected repositories and reviewed definitions are not interchangeable or evidence of exhaustive GitHub coverage.

Queries were reviewed by the implementing assistant/operator against the original public fixtures before exact session approval. This is not evidence that an end user clicked a UI approval. The 429/connection outage in the DuckDB first round was deliberately injected into the real connector path; it was **not an actual provider incident**. Other recorded source errors were real connector observations. No retry bypassed a quota or proceeded without a new query approval. Raw client/model logs and cached test workspaces remain temporary local artifacts, not Git contents or telemetry.

## Failures found and retested

Earlier attempts are not counted as final passes. They exposed real defects:

- `Testler çevrimdışı çalışmalı` was misclassified as project-wide offline rather than test-only. Offline classification now examines each occurrence's span and recognizes before/after test wording without weakening a separately stated project-wide constraint.
- `Do not add payment functionality` and `ödeme entegrasyonu içermeyecek` were incorrectly classified as required payments. Explicit EN/TR exclusions now remain excluded, with regression tests; affected cases were restarted with fresh contexts and approvals.
- Generic model rejection text obscured the cause of a scope conflict; one earlier support-assistant comparison timed out after repeated rejected attempts. The host now receives the actionable domain/schema reason, including the conflicting requirement ID/status. Raw rejected text is not saved in event history. The final repeated support-assistant case completed the full question/answer/research/comparison path, with its final model step taking approximately 34 seconds.
- A directory-only mutex could remain after a killed planning process. Local POSIX mutation now uses a persistent kernel-held advisory lock; forced termination releases it without deleting/guessing stale owner directories. Unknown legacy directory markers remain refused. Concurrent mixed-version writers and Windows forced-process recovery are not claimed supported.

No old approval or stale source cohort was reused to conceal a failed attempt. The tests also verify bounded source diagnostics without upstream response bodies, no model authority fields, clarification refusal for installed environments, ordinary answer-write failure recovery, independent file preservation and unchanged proposal/source budget accounting.

## Remaining boundaries and handoff

The offline suite passes **221 tests** from source and an independently installed 0.4.1 wheel; three tests actually terminate child processes during a held planning mutex, a source wait, and the two-write answer checkpoint. This is not installation/update power-loss recovery. CI is configured for Ubuntu/Python 3.11 and 3.14 and macOS/Python 3.14. These are prepublication local results; published commit-specific CI is tracked in [GitHub Actions](https://github.com/etrkk5/stratagent/actions/workflows/tests.yml). Default MCP remains read-only; scoped proposal mode exposes only its two declared tools.

The next phase is **P3 reviewed environment lifecycle**, not more silent scope expansion of P2. It still needs managed ownership/diffs, staging, backups/journals, approved updates/removal, installation crash recovery and state migration. P4 artifact/source assurance, native Claude Code/Antigravity runtime checks, P5's broader reviewed evaluation set and P6 release/operational evidence remain open. Completing this bounded existing-host P2 scope is not GA readiness, proof of optimal architecture, or a promise of revenue/adoption.
