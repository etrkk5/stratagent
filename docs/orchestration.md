# Existing-host orchestration (0.4)

StratAgent now has a **cooperative existing-host model driver**: a durable, bounded plan → approved live research → compare → optionally refine → blueprint workflow. Claude Code, Codex, Antigravity or another MCP-capable host can provide the model; the core does not launch a particular host, import a model SDK or require another API key. Native host/version interoperability still needs individual testing. The user selected existing-host operation for P2; optional direct-provider APIs are outside this iteration. P2 evidence does not complete the production-readiness plan.

The host model actually proposes the queries and architecture. StratAgent validates its structured output and drives the state transitions. The model cannot authorize its own searches through this bridge. An operator must run each approved search round and return the host to the next request. This is deliberately not a headless, unattended model-provider loop or automatic installation.

## Start and attach your host

Use an existing disposable project directory. `session-start` initializes StratAgent state when necessary, but never overwrites an existing request or changes its selected targets. Neither startup nor model proposals make network calls.

```sh
stratagent session-start "Build a Qdrant retrieval API with privacy. No payments." \
  --workspace ./my-agent --platforms generic \
  --model-turns 6 --search-rounds 2 --network-requests 160 --seconds 900
```

Copy `session.id`. Run this local stdio server through your host's MCP configuration using an absolute Python/CLI path:

```sh
stratagent serve --workspace ./my-agent --orchestration SESSION_ID
```

This explicit mode exposes **only two tools**:

- `stratagent_session_request`: read the next request, query review or blueprint.
- `stratagent_session_submit`: validate/save a bounded model proposal to this one session. Its annotation is **not read-only**. It cannot search, approve, allow repositories, install, activate, resume/cancel, address another session or choose output paths.

The normal `stratagent serve` remains the existing 13-tool read-only surface. Its discovery tools are not exposed in scoped mode, preventing bypass of session query review through another tool on this server. Host-side tools, unrestricted shell access and other MCP servers are outside this boundary; the host must configure its own permissions. Session digests detect drift under the trusted-local-user assumption, not malicious edits by the OS account.

## Model → review → research → model

Ask your host to read `stratagent_session_request`, reason from the actual project and submit this envelope using the returned `model_request.request_id`:

```json
{"request_id": "EXACT_CURRENT_REQUEST_ID", "response": {"action": "research", "plan": {}}}
```

`plan` must be the complete `research_schema` proposal included in the request; `{}` is only a placeholder here. Public technology names need not be in a bundled vocabulary. Every query must quote/cite actual request evidence. Unsupported authority fields, arbitrary URLs and credential-like terms are rejected. Schema/quote validation does not prove that terms are public or semantically correct.

The CLI equivalent reads a workspace-relative response file whose entire contents are `{"action":"research","plan":...}`:

```sh
stratagent session-submit SESSION_ID --workspace ./my-agent \
  --request-id EXACT_CURRENT_REQUEST_ID --response research-response.json
stratagent session-request SESSION_ID --workspace ./my-agent
```

At `awaiting-search-approval`, inspect **every** `search_review.search_preview` query, destination, source/result budget and `reserved_connector_calls`. Then explicitly authorize the current session review, not the underlying `research-preview` hash:

```sh
stratagent session-search SESSION_ID --workspace ./my-agent \
  --approve-search EXACT_SEARCH_REVIEW_APPROVAL
```

That approval binds the workspace, project, targets, exact proposal, budgets, session ID and revision. It is research-only. The round runs the existing fixed-host GitHub/official Registry connectors; no registry, executable installer or trust endorsement is invented. A repeated approval does not replay the network action. Partial results stay partial and never borrow older cached sources.

Return the host to `stratagent_session_request`. At `comparison-needed` it receives the exact fresh cohort, observed coverage/partial status and the architectural decision schema. It must compare alternatives and explain missing/ineligible resources. Submit either:

- `{"action":"decide","decision":...}` to save a grounded architecture and reach `review-required`.
- `{"action":"refine","plan":...}` to propose another bounded search. This pauses for a **new** egress approval; the next cohort replaces, rather than merges, the previous round's source selection. Earlier round summaries remain in history, not a trusted evergreen catalog.
- `{"action":"clarify","questions":["..."]}` to pause for 1–3 missing project/resource questions. This is also allowed before the first search. It does not invent unspecified facts or authorize any action.

The bridge cannot attest that a human or particular model generated a proposal, nor prove architecture optimality. Returning the suggested local draft unchanged is not evidence of model reasoning. Required-resource gaps and partial coverage must not be described as a ready environment.

## Answer missing project information

At `clarification-needed`, the operator supplies a **complete revised project request**, incorporating the answers rather than just an ambiguous yes/no:

```sh
stratagent session-answer SESSION_ID \
  "Build a Python support assistant over public Markdown FAQs. Use synthetic test data. No customer-record writes and no payments. Privacy review is required." \
  --workspace ./my-agent
```

Only this local CLI action changes planning scope. No MCP tool can answer the questions or edit the user request. This is supported **before installation only**: any existing installation causes refusal without changing its files or request. The revised prompt becomes exact user evidence; previous research/decision approvals become stale. Limits and expiry are not reset; the model must propose a fresh plan and obtain new egress approval. Older round summaries are labeled against their project digest and cannot enter the new source cohort. `session-resume` cannot silently skip a pending question.

The metadata change has an `answer-pending` checkpoint containing old/new prompt and context digests. If interrupted between the manifest and session writes, repeat `session-answer` with the **identical** revised prompt. A different answer, changed project files, expired session or concurrent modification is refused. This recovers a planning-input change, not an installed environment update or a substitute for P3 transactions. Validated prompt/answer text is local workspace state; inspect it before publishing.

## Review and apply separately

```sh
stratagent blueprint --session SESSION_ID --workspace ./my-agent --content
# Review source findings, exact outputs and blockers. Allow a repository only if independently justified.
stratagent blueprint --session SESSION_ID --workspace ./my-agent \
  --apply --approve EXACT_BLUEPRINT_APPROVAL
stratagent verify --workspace ./my-agent
```

`--session` supplies the saved decision and exact research run; it cannot be combined with `--run` or `--decisions`. The usual source policy, per-repository allowance, hash approval, collision refusal and verification still apply. Neither `session-submit` nor `session-search` installs anything. `environment_applied_by_session:false` describes this separation, not the absence of independently installed files. Canceling a session stops its orchestration; it does not revoke separate CLI authority, remove installed files or erase an independently approved blueprint.

## Bounded progress and interruption

- Session defaults: six submitted proposal attempts, two search rounds, 160 connector calls and 900 seconds **including human review pauses**. Bounds are 2–16 attempts, 1–3 rounds, 1–300 calls and 30–3600 seconds. The 15-minute research evidence TTL is independently enforced even in a longer session.
- Before network access, each round **durably reserves a share of the remaining connector calls**, capped at 80: `min(80, ceil(remaining_calls / remaining_rounds))`. For example, 160 calls/two rounds reserves 80 then 80; 20 calls/two rounds reserves 10 then 10. Reservations are never refunded, even after failure, cancellation or process death. Cached immutable GitHub reads count conservatively too. Inspect the exact allocation before approval; a new session is required when budgets are exhausted.
- GitHub and Registry share that bound. Remaining lifetime clamps socket timeouts; cancellation/context/deadline checks run before connector calls and transport opens, and after research. In-flight socket reads may finish or time out before cancellation is observed. This is not a hard real-time process-kill guarantee.
- Accepted/rejected structured attempts consume proposal turns; stale request replays do not. Exact accepted response retries are effect-idempotent. Validation failures return their actionable domain/schema reason without saving raw rejection text in event history. The bridge does **not** call/bill the model, control the host's internal retries or enforce an upstream currency/token cap. The user explicitly selected existing-host P2 operation; optional direct-provider transport/accounting is a separate future extension, not a hidden credential requirement.
- Session files at `.stratagent/orchestrations/ID.json` use bounded schemas, atomic replacements, the workspace write lock and revision compare-and-swap. Event history stores only timestamps, state and fixed event codes, not rejected response text or raw model logs. Validated plans/decisions are stored locally for review and may contain sensitive request quotes; do not publish the workspace state without inspection.
- Round observations retain bounded connector-generated diagnostics (stage, sanitized message and source/query reference) so quota, format and connectivity errors are actionable. The built-in clients discard upstream response bodies and credential values before producing these messages. Diagnostics are untrusted review data, not model instructions or execution authority; they are local state, not telemetry.

```sh
stratagent session-status SESSION_ID --workspace ./my-agent
stratagent session-cancel SESSION_ID --workspace ./my-agent
stratagent session-resume SESSION_ID --workspace ./my-agent
```

Status remains readable after cancellation/expiry. A failed/interrupted round retains its checkpoint and reservation. `session-resume` never replays it: it requests a new model plan and a new query approval without resetting any budget or extending expiry. It may supersede an orphaned `searching` checkpoint; an old live worker is then refused at its next boundary. Changed projects, expired sessions or exhausted budgets require a new session. Ordinary interrupted-state tests are not proof of all P3 installation/update crash-recovery gates.

On local POSIX filesystems, `Workspace.mutation` uses a kernel-held advisory lock at `.stratagent/.mutation-lock`; process death releases it automatically. **Do not delete/replace that persistent file**, and do not run pre-0.4.1 and 0.4.1 writers concurrently on one workspace. Unknown legacy `.write-lock` directories are refused, not guessed stale or deleted. Windows retains the previous directory lock and has no verified forced-process recovery guarantee; Windows support is not claimed by these P2 results. Installation/update crash consistency remains P3 work even though the planning mutex now survives process death.

## Reproduce opt-in real model checks

`scripts/validate_existing_host.py` contains six original public EN/TR test requests, not a product resource catalog. It is an optional Codex CLI test adapter; the product driver has no Codex dependency. Run it from the repository with source import enabled and an existing authenticated test host:

```sh
PYTHONPATH=src python3 scripts/validate_existing_host.py \
  --workspace /tmp/stratagent-host-check --case en-retrieval --phase research
```

Read the exact plan through `session-request`, independently review/approve queries using `session-search`, then run the helper with `--phase compare`. `--phase refine` exercises a test-directed refinement proposal after observations; it never approves or runs the changed queries. `--case tr-questions --phase clarify` exercises questions; answer through the CLI, then run `--phase research`. Existing phase/context mismatch fails before any model call. No test helper grants trust or installs/activates sources. Host calls consume that host's normal usage; the helper's subprocess timeout is not a currency cap. Raw logs are written only in the explicitly selected disposable workspace and must not be published unchecked. The regular offline test suite never launches a model or contacts external services.

## Observed existing-host test — October 22, 2026

Two actual Codex CLI 0.163.0-alpha.10.2 sessions used existing ChatGPT authentication, temporary command-line MCP configuration, `--ignore-user-config`, `--ephemeral`, a read-only shell sandbox and only the two scoped StratAgent tools. No persistent host settings were edited. The temporary MCP setup follows the official [MCP configuration](https://learn.chatgpt.com/docs/extend/mcp) documentation; host [sandbox/approval policy](https://learn.chatgpt.com/docs/agent-approvals-security) remains separate from StratAgent's narrow tool authority.

1. An original public request described a small Qdrant retrieval API, privacy and excluded payments. The first real model called request → submit, generated a literal-evidence-grounded one-query Registry plan and reached `awaiting-search-approval` in approximately **14.0 seconds**, exit 0. No source query ran in that model session.
2. The implementing assistant inspected the exact public `Qdrant` term and separately supplied the CLI session approval. This was an assistant/operator-reviewed test, **not evidence that an end user clicked an approval button**. One live official Registry connector call completed in approximately **7.0 seconds**, producing one reviewed metadata record (`de.fidonis/qdrant-mcp-rbac`), no inspected GitHub repositories or skills, and `partial:false` for this deliberately bounded scope. The candidate was ineligible because its package/transport was unsupported. Nothing contacted the candidate's endpoint or executed its package.
3. The second real model called request → submit, compared focused/specialist ownership, preserved independent testing/privacy review, excluded payments and explicitly rejected the ineligible MCP rather than inventing a usable dependency. It reached `review-required` in approximately **43.4 seconds**, exit 0. Its proposal disclosed the single-query coverage and unresolved artifact/license/data-flow questions. The blueprint preview had **seven outputs and no policy blockers**, because it selected only local generated roles and zero external resources. This does not mean the Qdrant project environment is fully prepared or all required dependencies were discovered.

The durable session recorded two proposal turns, one search round and 20 reserved connector calls (one used). There were **zero installations, repository trust grants, server activations or third-party code executions**. Raw model/session logs remain in a temporary local test workspace, not Git. This verifies a real cooperative model → approval boundary → live research → model comparison flow, not broad GitHub coverage, automatic refinement quality, native Claude Code/Antigravity interoperability, unattended orchestration or production readiness. Offline fixtures separately cover refinement, failure, cancellation and no-replay resume; broader real sessions remain a release gate.
