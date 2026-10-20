# Runtime research and freshness

Version 0.3.2 implements the P1 foundation in the [production-readiness plan](production-readiness.md). It is not the complete autonomous P2 orchestrator, an update engine or production certification.

## Model-generated search plans

`research-request PROMPT` exports current bounded project evidence and a strict provider-independent schema. It makes no model/network call and need not initialize a workspace. Your existing model/human may propose public technologies outside the built-in vocabulary, such as Qdrant or OpenTelemetry. Each query needs a rationale, a literal request quote and evidence references. These enforce traceability, not semantic correctness or publicness.

The proposal has `schema_version`, `context_digest`, `reason`, `github_queries`, `mcp_queries` and `budgets`. GitHub queries specify `kind` (`skills`, `subagents`, `mcp`) and up to five literal terms. MCP queries specify a public server-name term. Fixed connectors construct outbound requests; no command, arbitrary URL, path, installation approval, credential or permission field is accepted. Budgets cap repositories, definition reviews and per-query MCP results at 20; at most eight GitHub and six MCP queries are allowed. The schema returned at runtime is authoritative.

```sh
mkdir runtime-project
stratagent research-request "Build a small Qdrant retrieval API with privacy." \
  --workspace ./runtime-project --platforms codex
# Have your current model/human return a proposal; save it as runtime-project/research.json.
stratagent research-preview "Build a small Qdrant retrieval API with privacy." \
  --workspace ./runtime-project --platforms codex --research-plan research.json
# Inspect exact outbound terms and budgets. Only then use that preview's search_approval:
stratagent prepare "Build a small Qdrant retrieval API with privacy." \
  --workspace ./runtime-project --platforms codex --research-plan research.json \
  --approve-search SEARCH_APPROVAL_SHA256
```

Search approval binds the workspace, project/target context, complete proposal, outbound text and budgets. It authorizes **research only**, not installation. Missing/stale approval fails before initialization or network calls. The reviewed proposal's budgets control execution; `prepare` budget flags apply to the rule fallback, not an approved model plan. Empty connector query lists cause that connector to be skipped, not substituted with seeds or generic searches. Project-wide offline scope still omits Registry service research. `--offline` cannot be combined with a network research plan.

Query syntax is bounded and credential-like strings are rejected, but short secrets or private names can resemble public words. A human must review egress; automatic validation cannot prove privacy. A malicious model cannot grant its own approval through MCP. `stratagent_research_request` and `stratagent_research_preview` are read-only tools. They do not perform searches, cache evidence or apply output. Passing provider credentials or private project text to a model remains a separate host/user decision.

Without a runtime proposal, `prepare` retains the disclosed public-vocabulary rule fallback. That fallback is not semantic model reasoning and must not be described as the full intended runtime intelligence layer.

## Exact run-scoped evidence

Every `prepare` call creates a new `.stratagent/runs/ID.json`, even for identical input. Runs contain the project digest, mode, start/expiry, partial-result flag, exact source IDs/review digests and research approval reference. The records have a self-consistency digest, not a cryptographic user attestation. Local filesystem/user trust remains an assumption.

Retain the reviewed `research.json` and sanitized preparation report for reconstructing query intent: the run stores its approval reference, not a full copy of the model conversation or proposal. Complete resumable execution/audit journaling belongs to P2/P3, not an implied property of this first record format.

- A live run includes **only** candidates reviewed during that run. Old cache entries remain available for audit/manual use but do not silently enter the new runtime decision or blueprint.
- An explicitly offline run may use cached pinned evidence and labels itself `offline-cache`; it never claims a live refresh.
- Mutable GitHub search, repository and branch metadata is not cached between observations. Immutable Git blobs/trees may be reused without treating a moving branch as immutable.
- Live research errors/incomplete results produce a partial run and block run-scoped application. Inspect and repeat with an attainable research scope; blocked content is never force-enabled. The current policy is intentionally conservative, including source preflight errors.
- Runs expire 15 minutes after research starts. The clock is local UTC epoch seconds. Expired/future/tampered run records, changed project/targets or changed referenced reviews are rejected. This is a bounded freshness policy, not proof that upstream will never change after observation. Revalidation immediately before host activation remains a later release gate.

Use the **same run ID** for model decisions, output review and application:

```sh
stratagent decision-request --run RUN_ID --workspace ./runtime-project
# Optionally save the model/human architecture decision as decision.json in that workspace.
stratagent blueprint --run RUN_ID --decisions decision.json --content --workspace ./runtime-project
# Inspect source contents/findings and resolve repository/scope blockers separately.
stratagent blueprint --run RUN_ID --decisions decision.json --apply \
  --approve INSTALLATION_APPROVAL_SHA256 --workspace ./runtime-project
stratagent verify --workspace ./runtime-project
```

Omit `--decisions` consistently to use the disclosed local rule decision. The blueprint approval binds the run, mode and source cohort through the context and output/provenance hashes. Search approval is not an installation approval. A new run produces a new decision context and cannot reuse the previous decision/hash. Repeating the **same** run and approval is idempotent while the run is valid; approved-output upgrades are still unsupported. Expiry does not delete/revoke previously installed files: `verify` still checks them, and `status` reports that their research context is no longer current.

Low-level `blueprint` without `--run` remains a compatibility/manual cache flow, clearly labeled `unscoped-cache`. It cannot consume a run-scoped approval hash and makes no runtime freshness claim. The new production direction uses run-scoped operations; do not present legacy manual cache operations as live research.

## Verification boundary

Offline tests cover model-planned unknown terms, privacy/authority boundaries, approval scope, stale project plans, expired runs, cached/live separation, partial refresh failure, immutable versus mutable HTTP observations, run-bound decisions, no unapproved connector fallbacks, source drift, status after expiry and installed-file verification. Actual model/provider behavior, full refinement loops, crash-safe updates, artifact audits and additional host runtime sessions are separate production gates. See [validation.md](validation.md) for measured results, not inferred readiness.
