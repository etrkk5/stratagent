# Idea-to-environment discovery

The product goal is for a user to describe a project, then review an environment assembled from the resources it actually needs: architecture, roles/subagents, skills and MCP proposals. Discovery is not limited to a short built-in catalog. It must also avoid confusing popularity, source integrity and safety.

Version 0.3.2 adds [model-generated runtime research plans and exact fresh-run source cohorts](runtime-research.md). The fixed public-vocabulary survey below remains a disclosed fallback, not the primary intended intelligence layer. Use the returned research run ID for subsequent decisions and application. Runtime model orchestration/refinement and continuous updates remain open production gates.

## One-prompt preparation

`stratagent prepare PROMPT --workspace PATH` initializes or reuses a matching workspace, performs bounded research, caches reviewed evidence and returns `blueprint`, `decision_request`, `available_resources`, `unassisted_roles`, `errors` and explicit discovery skips. It preserves an existing workspace's targets when `--platforms` is omitted. Changed requests or targets never silently reset state. Invalid budgets fail before initialization.

GitHub definition review defaults to six candidates across up to 12 repository inspections; both budgets can increase to 20 with `--limit` and `--repo-limit`. Registry discovery uses at most three fixed public name queries derived from active domains, prioritizing database, web and API boundaries, with `--mcp-limit` results per query. These are bounded heuristics, not semantic search of every tool on the internet. `--offline` skips all network discovery; project-wide offline scope skips Registry service discovery while allowing source documents to be reviewed during provisioning.

Preparation's status is always `review-required`, and `environment_applied` is false. It may return partial results when a provider is unavailable, making stage errors and missing matches visible. Empty bindings are not invented dependencies, and unassisted roles do not necessarily require an external resource. A model/human can then judge the returned evidence through the existing provider-independent contract. Resolve scope and repository blockers, inspect the exact blueprint and approve locally before environment files are written. MCP activation and agent execution remain separate actions. No new model API client or mutating MCP tool is added.

## Broad GitHub survey

The survey uses the official [repository search API](https://docs.github.com/en/rest/search/search#search-repositories), with `sort=stars`, `order=desc`, public vocabulary and archived/fork exclusions. It runs three resource-family queries plus up to five queries derived from two recognized public project terms. Unknown or private project terms are omitted; the full user request is not sent.

- At most eight queries and ten result slots per query, first page only: at most 80 slots before deduplication. This is not exhaustive indexing or authenticated code search.
- Private, archived, disabled and forked results are skipped. Invalid records are reported without discarding valid records. Duplicate repositories retain query/category provenance and observed stars.
- Selection takes a round-robin across star-sorted query results. This retains popular options in each family instead of letting a single large catalog fill every slot. It is not a promise that the globally highest-starred repository is the best choice.
- By default, 12 repositories receive immutable commit/tree inspection; the explicit maximum is 20. Seeds only fill unused slots and never confer trust. Counts distinguish metadata results from actual source inspection and definition review.
- Only supported `SKILL.md` and agent/subagent Markdown definitions become skill/role candidates. Repositories without these definitions remain visible in coverage; StratAgent does not guess how to install arbitrary applications.

MCP-related GitHub repositories are research evidence, not executable server configurations. The separate official Registry path still provides reviewed transport/version metadata. Publication there is not an endorsement. Joining arbitrary GitHub code to an installation command, auditing package artifacts/licenses/tool manifests and automatically activating MCP servers are not implemented. That limitation must stay visible when describing a "ready environment."

## Selection and approval

Popularity has a bounded relevance-ranking component, separate from static policy eligibility. A high-starred source that fails content, license or integrity checks is not selectable. Eligible means "passes current conservative filters and remains subject to human review," not "proven safest." The selected resource's provenance, pinned content and generated output enter approval; stars cannot grant repository permission or approval.

Supported sources are fetched using verified Git tree/blob identities, never cloned or executed. The existing documentation-only file policy still blocks scripts, executables, unsupported metadata and suspicious content. Broader search does not weaken those controls. Automatic discovery can therefore find many popular repositories but few installable resources; the report must make that gap explicit rather than claim successful setup.

## Budgets, partial results and reproducibility

The GitHub client keeps its 100-request budget and checks a 120-second deadline before network requests; each socket timeout is at most 20 seconds and no longer than the remaining deadline. This is not an OS-level hard wall-clock guarantee. The definition snapshot attempt cap is 40, enforced inside repository rounds. A global rate/request/time limit stops further calls without retries. Previously observed search metadata or successfully reviewed candidates remain available as partial results.

`research.queries` records actual query/sort/page settings, reported totals, incompleteness and query errors. `research.repositories` records deduplicated popularity and search-family evidence. `inspected_repositories` records actual commit identities, star observations, definition counts and search/seed/explicit origin. `coverage` records limits, actual inspection counts, remaining request budget and candidate/attempt caps. None of these metadata fields bypasses source review or approval.

Offline tests cover multi-query diversity, up to 80 metadata slots, more than eight repository inspections, invalid/private/archived/forked records, duplicate results, partial rate limits, expired deadlines, exact attempt caps, read-only MCP behavior, one-prompt preparation, cache-only mode, unchanged workspace targets, partial provider failure and rejection of a highly popular malicious candidate. Live results and current test counts are recorded separately in [validation.md](validation.md); test fixtures are not live-catalog evidence.
