# StratAgent

[![Tests](https://github.com/etrkk5/stratagent/actions/workflows/tests.yml/badge.svg)](https://github.com/etrkk5/stratagent/actions/workflows/tests.yml)

**A platform-agnostic, project-aware architect for agent workspaces.**

Describe what you are building, not which tools to install. StratAgent combines natural-language requirements with bounded local project evidence, compares focused and specialist architectures, maps roles to reviewed skills and MCP server proposals, and generates a workspace plan you can inspect before applying.

```text
Project requirements → Architecture & roles → Skill/MCP selection → Reviewed workspace configuration
```

Use the same decision and approval workflow with Claude Code, Codex, Antigravity, or a portable export. Your project drives the plan; your coding environment determines how it is rendered.

StratAgent treats reusable agent instructions as software dependencies: **pin the source, inspect the content, approve the exact plan, and record what was installed.**

The CLI combines evidence-based planning, transparent candidate ranking, commit-pinned skill snapshots, repository allowlists, content-bound approval and a provenance lockfile. MCP server metadata is reviewed separately: approved proposals stay inert until you manually activate them. A read-only MCP interface exposes analysis, discovery and inspection while keeping approval authority in the local CLI.

Python 3.11+, with pinned PyYAML for bounded safe metadata parsing. No LLM API key or Git CLI required. Local filesystem backends cover macOS/Linux and Windows; their durability and permission capabilities differ. See [OS portability and actual validation](docs/os-portability.md), not a blanket production-readiness claim.

## Platform- and model-agnostic by design

- **OS-independent lifecycle:** planning and transactions share one filesystem capability boundary. POSIX and Windows use native kernel locks and same-filesystem replacements; `stratagent doctor` reports real permission/durability differences without modifying the project. Network filesystems and physical power loss are not certified.
- **Platform-agnostic core:** requirements, task dependencies, acceptance criteria, discovery ranking and approval policy do not depend on a particular coding environment. Trusted, pure adapters translate the plan into host paths, constrained role metadata and inert MCP proposals.
- **Model/provider-agnostic decisions:** use your existing model or human judgment through a strict JSON contract, the default read-only MCP interface or an explicitly selected proposal-only orchestration session. StratAgent adds no model SDK dependency or provider credential requirement. Without an external proposal, it uses its disclosed local rules.
- **Standards over a private ecosystem:** reuse Agent Skills definitions, GitHub sources and the official MCP Registry rather than requiring a new StratAgent registry.

Platform-agnostic does **not** mean every host has identical capabilities or that every model has been integration-tested. `stratagent platforms` lists the capabilities of each built-in adapter without reading or initializing a workspace:

| Target | Skills | Roles | Host MCP proposal |
| --- | --- | --- | --- |
| `generic` | Portable Agent Skills | Portable role skills and task plan | Review metadata only |
| `claude` | Host skill directory | Native read-only role definitions | JSON |
| `codex` | Shared Agent Skills directory | Portable role skills | Disabled TOML |
| `antigravity` | Shared Agent Skills directory | Native read-only role definitions | Disabled JSON |

Choose `--platforms generic` for portable exports or combine explicit targets. The three-host CLI default is an onboarding convenience, not a planner dependency. Permissions and native orchestration differ between hosts; portable instructions do not create a universal runtime permission model. An unsupported host needs an adapter and interoperability testing before native support is claimed.

The adapter contract is in `src/stratagent/hosts.py`. Adding a reviewed built-in adapter defines its skill/role layout, constrained role metadata and optional pure MCP renderer; the planner, source scanner, discovery service and approval writer need no host-specific branches. Identical shared outputs are deduplicated; conflicting content for the same path fails closed. External adapters/plugins are not automatically imported or executed. See [architecture.md](docs/architecture.md) for the boundary and extension procedure.

## Why StratAgent

Start with project decisions, not a shopping list of tools. The blueprint explains which responsibilities to retain or omit, which reviewed resources serve them, and which permissions remain ungranted. Discovery and installation support that architecture rather than defining it.

A reusable skill can carry instructions, references, scripts, permissions and license obligations. Installing it is a dependency decision. StratAgent makes that decision inspectable:

| Question | Evidence StratAgent provides |
| --- | --- |
| What does this project need? | Prompt matches, recognized dependency evidence, requirement criteria and open questions |
| Why this architecture? | Focused/specialist tradeoffs, retained/omitted roles and evidence-linked model/human decisions when supplied |
| What is this resource relevant to? | Matched terms, ranking components, role recommendations and explicit repository permission |
| Where did it come from? | Repository, immutable commit, entry path and verified Git blob identities |
| What will be installed? | Exact output paths, file sizes and SHA-256 hashes in a deterministic dry-run |
| What did I approve? | A full plan digest bound to source content, destination and generated outputs |
| Has anything changed? | A provenance lockfile and verification of every installed output |

This is an early, working release. The local fallback uses explicit rules; a provider-independent decision contract lets your current model or a human supply architectural judgment. Static checks and model proposals still require human review, and agent processes are not launched automatically.

**Release status: developer preview.** A [live Codex pilot](docs/pilot-validation.md) exercised model decisions through the read-only MCP server, reviewed local approval and subsequent use of a generated portable role on a working [offline CSV example](examples/projects/inventory-review). That is a bounded integration result, not a claim of production readiness or verified runtime support across every target.

## Quick start

Clone the repository and install locally:

```sh
git clone https://github.com/etrkk5/stratagent.git
cd stratagent
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/stratagent --help
.venv/bin/stratagent demo --workspace ./demo-workspace --apply
.venv/bin/stratagent verify --workspace ./demo-workspace
```

The offline demo uses original examples included in this project. Omit `--apply` to prepare review evidence and dry-run plans without activating platform files. Use a new directory for each demo. Its synthetic commits are explicitly labeled `demo-offline` in provenance.

After installing dependencies, run the checkout's source directly:

```sh
PYTHONPATH=src .venv/bin/python -m stratagent plan "Build a Python API agent for data analysis"
PYTHONPATH=src .venv/bin/python -m stratagent demo --workspace ./another-demo --apply
```

## Start from one project idea

StratAgent's goal is **idea → researched dependencies → architecture → reviewed environment**, not a fixed list of packages or two preferred repositories. Start in an existing, disposable project directory:

```sh
mkdir my-agent
.venv/bin/stratagent prepare "React frontend and Python API with PostgreSQL and privacy" \
  --workspace ./my-agent --platforms claude,codex,antigravity \
  --repo-limit 12 --limit 6 --mcp-limit 3
```

`prepare` initializes project state, runs broad GitHub discovery, searches up to three relevant MCP Registry terms, caches source reviews and returns a complete blueprint preview plus `decision_request` for your current model/human. It does **not** install, allow repositories, enable servers or launch agents. Its status is `review-required`, not "environment ready." Review `errors`, source findings, `unassisted_roles`, alternative decisions and exact outputs; then use the existing blueprint approval flow. Required resources may be absent or blocked, and a simple project may need no external resource at all. The first preview uses disclosed local rules unless you subsequently supply a reviewed model/human decision.

Each preparation now creates an exact `research_run.id`. Use `decision-request --run ID` and `blueprint --run ID` for subsequent review/application; run-scoped approvals cannot be reused without that run. Live runs never silently include previous cached candidates, partial live research blocks application, and research expires after 15 minutes. Offline/manual cache flows are explicitly labeled, not advertised as current live discovery.

For genuinely model-planned runtime queries, use `research-request` → `research-preview` → `prepare --research-plan FILE --approve-search HASH`. Your existing model can propose new public technology names outside the fallback vocabulary; the human reviews exact outbound terms/budgets before network access. Search approval never authorizes installation. See [runtime-research.md](docs/runtime-research.md).

**Version 0.4 adds cooperative existing-host orchestration:** `session-start` creates durable progress; `serve --orchestration ID` exposes only model request/proposal tools for that one session. The model proposes a plan, `session-search` requires separate exact query approval, and the model compares current evidence or proposes a separately reviewed refinement. `blueprint --session ID --content` previews its final architecture; installation remains an independent approval. Proposal turns, search rounds, shared connector calls and session lifetime are bounded; cancel/resume never silently replays a search or resets budgets. No model SDK, provider credential or particular host is required. This is an operator-mediated runtime loop, **not** an unattended provider driver, upstream billing cap or environment-upgrade engine. Follow the [orchestration walkthrough](docs/orchestration.md) and [production-readiness gates](docs/production-readiness.md).

In **0.4.1**, the model can pause for missing project/resource details using `clarify`. Only the operator's `session-answer` can revise the planning request before installation; previous decisions/query approvals then become stale without resetting budgets. POSIX mutation locks release on process death. **0.5 adds reviewed environment transactions:** stage an exact diff, approve it separately, update/remove only owned files, and recover an interrupted operation from a durable backup journal. See the [lifecycle walkthrough](docs/lifecycle.md); host activation remains manual and separately authorized.

The [existing-host P2 acceptance record](docs/p2-existing-host-validation.md) covers six real EN/TR cases, a separately approved model refinement after controlled source failure and the clarification/answer flow. Unsupported or irrelevant sources were not selected; partial research remained blocked. This is a bounded planning/orchestration result, not proof that all project dependencies can already be installed or that the product is production-ready.

GitHub discovery surveys up to **eight star-sorted queries and 80 result slots**, deduplicates public repositories and preserves coverage across skills, agent/subagent definitions and MCP-related repositories. It inspects up to **12 repositories by default, configurable to 20**. Each selected source is pinned before supported definition content is reviewed. The report distinguishes metadata found, repositories inspected, definitions discovered and candidates actually reviewed; these are not interchangeable counts. Popularity helps discover alternatives, **never proves safety or overrides policy**. The default fallback sends only allowlisted public vocabulary; model-proposed terms require separate exact egress review. Source connectors receive approved query terms, not the raw project request. See [discovery.md](docs/discovery.md) for limits and assurance levels.

`prepare --offline` uses only local/cached evidence and makes no discovery network requests. An offline *project* requirement instead skips Registry service discovery but still permits reviewing GitHub documents during preparation. Existing workspaces retain their request and targets; use a separately reviewed `revise` operation to change them before fresh research. Revision changes planning context, not installed files. Preparation writes only local state/cache, not active environment files. Sources are still untrusted, Registry metadata is not a package audit, and native host capabilities remain adapter-specific.

The lower-level examples below are alternative entry points; do not initialize an already prepared workspace again.

## One reviewed workspace blueprint

```sh
mkdir my-agent
.venv/bin/stratagent init "Small Python API. Payments are not required. Privacy required." \
  --workspace ./my-agent --platforms generic

# Optional: discover/cache skills and MCP metadata before requesting a decision.
.venv/bin/stratagent discover --workspace ./my-agent --repo openai/skills --limit 3
.venv/bin/stratagent discover-mcp --workspace ./my-agent --query documentation --limit 3
.venv/bin/stratagent blueprint --workspace ./my-agent --content
```

The blueprint compares focused versus specialist coordination, explains retained/omitted roles, binds reviewed skills and MCP proposals to tasks, and lists permission needs with `granted: false`. Small/MVP scope favors fewer handoffs; multiple evidenced work areas can justify specialist planning. Scores are inspectable rules, not confidence probabilities. Requirements distinguish `required`, `excluded`, `deferred`, `uncertain` and `conflicting` scope. Unresolved conflicts/uncertainty block application. Supported negative phrases such as “ödeme istemiyorum” and “payments are not required” exclude payment scope; complex language remains a review obligation.

For model/human judgment, `decision-request` returns current evidence, immutable source review IDs, alternative strategies, a strict JSON schema and a draft decision:

```sh
.venv/bin/stratagent decision-request --workspace ./my-agent
# Ask your current model to review this context and return the decision object.
# Save that object as ./my-agent/decision.json, then inspect every source/output:
.venv/bin/stratagent blueprint --decisions decision.json --content --workspace ./my-agent

# Allow each exact skill/npm repository reported by the preview after review.
.venv/bin/stratagent allow owner/repo --workspace ./my-agent
.venv/bin/stratagent blueprint --decisions decision.json --content --workspace ./my-agent
.venv/bin/stratagent blueprint --decisions decision.json --apply \
  --approve BLUEPRINT_APPROVAL_SHA256 --workspace ./my-agent
.venv/bin/stratagent verify --workspace ./my-agent
```

Use actual repository names and the current preview's complete approval. An empty discovery result is a gap, not permission to invent a resource. Without `--decisions`, the same blueprint workflow uses the disclosed local rules. An imported proposal must match the current context digest, cite known evidence and bind every selected task, including explicit empty resource arrays. New requirement/domain interpretations need literal user/project evidence quotes. Quotes and IDs provide traceability, not proof that an interpretation is correct. Provider labels are unverified claims. Explicit scope exclusions, required review responsibilities and source policy cannot be bypassed by a model proposal.

One approval writes the selected skill files, generated role definitions, inert MCP proposals, `.stratagent/task-plan.json` and `.stratagent/blueprint.json`, with reviewed-source provenance and hashes under one lock entry. Existing compatible standalone installations are reused without overwriting them. The allowlist remains a separate gate; there is no automatic MCP activation or agent launch. Repeating the same approved effect verifies/no-ops. Files, policy, inputs, sources, installed state or decisions changing invalidates approvals for new mutations. Version 0.5 supports explicit reviewed updates/removal and a version 1 → 2 lock migration, not unattended upgrades.

## Review, update and recover

```sh
# After source review and exact repository allowances:
.venv/bin/stratagent stage blueprint --decisions decision.json --workspace ./my-agent
# Inspect the returned plan, diff, blockers and approval before applying:
.venv/bin/stratagent apply STAGE_ID --approve EXACT_PLAN_SHA256 --workspace ./my-agent
.venv/bin/stratagent verify --workspace ./my-agent

# For changed requirements/targets, separately stage a complete revised request:
.venv/bin/stratagent stage revise --prompt "Small Python API. Privacy required. No payments." \
  --platforms generic --workspace ./my-agent
# Approve/apply that revision, then start fresh runtime research and stage its blueprint.

# Review interrupted work before issuing another write:
.venv/bin/stratagent recover --workspace ./my-agent
.venv/bin/stratagent recover --apply --approve EXACT_RECOVERY_SHA256 --workspace ./my-agent
```

Staging does not install. Apply recomputes the selected plan, rechecks source reviews and research freshness, and rejects stale approvals. Updates replace/delete only files owned by that installation; unowned files, user edits, permission drift and cross-installation dependencies block the change. `stage remove --key KEY` uses exact installation keys from `status`; it never deletes the project or global settings. Backups include private prompt/instruction text: keep `.stratagent` out of version control and use a restricted user-owned directory (Windows inherits its ACLs). Recovery restores the pretransaction files/lock before the commit point, or finalizes a fully committed operation; it refuses conflicting external edits. See [lifecycle.md](docs/lifecycle.md) for limits and examples.

`status` distinguishes the approved decision from current rule analysis and reports whether its input context is still current. `configure` is a lower-level alternative for separate setup, not an additional step after an approved blueprint.

The read-only MCP pair `stratagent_decision_request` → `stratagent_blueprint` lets the model in an existing coding environment reason and preview directly, without a vendor SDK or extra API key. StratAgent does not make an LLM API call; sending context to another service is a separate user/host action. A draft returned unchanged is still rule-generated, not evidence of model reasoning. See [decision-workflow.md](docs/decision-workflow.md) for the contract, acceptance cases and limits.

## Separate discovery and installation commands

```sh
mkdir my-agent
.venv/bin/stratagent init "Build a Python API agent with data analysis, tests and security review" \
  --workspace ./my-agent --platforms claude,codex,antigravity,generic

.venv/bin/stratagent discover --workspace ./my-agent \
  --repo openai/skills \
  --repo VoltAgent/awesome-claude-code-subagents --limit 4

.venv/bin/stratagent recommend --workspace ./my-agent
```

Without `--repo`, discovery uses the multi-query GitHub survey described above. The seed catalogs `openai/skills`, `anthropics/skills` and `VoltAgent/awesome-claude-code-subagents` only fill unused repository slots; they are not the discovery universe or trusted repositories. `--repo-limit 1..20` controls deep inspection, while `--limit 1..20` controls the total definition reviews. Explicit `--repo` entries skip search and must fit the repository budget. Search uses repository search followed by pinned Git tree/blob API calls; authenticated code search is not required. Results are bounded, not exhaustive.

Review a candidate using its `id` from the JSON output:

```sh
# Replace CANDIDATE_ID and APPROVAL_SHA256 with values from the output.
.venv/bin/stratagent inspect CANDIDATE_ID --content --workspace ./my-agent
.venv/bin/stratagent install CANDIDATE_ID --dry-run --workspace ./my-agent

# After reviewing all source files, licenses, findings and output paths:
.venv/bin/stratagent allow owner/repo --workspace ./my-agent
.venv/bin/stratagent install CANDIDATE_ID --content --workspace ./my-agent
.venv/bin/stratagent install CANDIDATE_ID --apply \
  --approve APPROVAL_SHA256 --workspace ./my-agent
```

Use the candidate's actual repository name for `allow`. Installation requires the full `approval` SHA-256 from its dry-run, not the separate `review_digest`. Approval binds the absolute destination, source commit, source hashes, license, scanner version and generated file hashes. Changes invalidate the approval. Blocked candidates have no force-install option.

Generate task configurations after installing the resources you selected:

```sh
.venv/bin/stratagent configure --dry-run --workspace ./my-agent
# Use this configuration preview's own approval value:
.venv/bin/stratagent configure --apply --approve APPROVAL_SHA256 --workspace ./my-agent
.venv/bin/stratagent verify --workspace ./my-agent
.venv/bin/stratagent status --workspace ./my-agent
```

Configuration produces a task graph covering architecture, implementation, testing, security review and integration, adding frontend, API, data and database planning roles when evidence supports them. Specialist planning runs after design; testing and implementation security review run after build. Only explicitly installed resources that pass verification are associated with tasks. No coding-agent process is launched.

## Project-aware planning

```sh
# Reads selected dependency manifests, without initializing or writing anything:
.venv/bin/stratagent plan "FastAPI and React dashboard with login, privacy and accessibility" \
  --workspace ./existing-project --scan-project

# init includes this bounded scan by default; --no-scan-project opts out.
.venv/bin/stratagent init "Python data review with offline operation and performance tests" \
  --workspace ./existing-project
```

The analysis reports `domain_evidence`, `requirements`, `open_questions`, specialist tasks and `architecture.parallel_waves`. Inspection reads only root manifests and manifests inside up to eight immediate packages in each of `apps/` and `packages/`. It recognizes `package.json`, `pyproject.toml`, `requirements.txt`, `Cargo.toml` and `go.mod`, with a 256 KiB file limit. Only known dependency names, evidence paths and content hashes enter the plan. Scripts, source files, `.env`, private dependency names and credentials are not included. Symlinks, malformed manifests and truncation produce explicit warnings.

Local analysis uses bounded English/Turkish scope rules and dependency evidence. It recognizes supported exclusions/deferrals and compares coordination alternatives, but does not claim unrestricted language understanding or full source-code architecture analysis. `decision-request` and `blueprint --decisions` accept grounded judgments from your current model or a human. Review evidence and open questions. Project changes invalidate old decision contexts and configuration approvals. Installed output changes require a new reviewed lifecycle plan; discovery never automatically upgrades it.

## Discover and review MCP servers

```sh
.venv/bin/stratagent discover-mcp --query playwright --limit 4 --workspace ./my-agent
.venv/bin/stratagent inspect-mcp MCP_ID --content --workspace ./my-agent
.venv/bin/stratagent configure-mcp MCP_ID --option 0 --content --workspace ./my-agent

# For npm proposals, also review and allow the exact source repository:
.venv/bin/stratagent allow owner/repo --workspace ./my-agent
.venv/bin/stratagent configure-mcp MCP_ID --option 0 --content --workspace ./my-agent
.venv/bin/stratagent configure-mcp MCP_ID --option 0 --apply \
  --approve MCP_PROPOSAL_APPROVAL_SHA256 --workspace ./my-agent
.venv/bin/stratagent verify --workspace ./my-agent
```

Replace `MCP_ID`, repository and approval with inspected values. Discovery uses the [official MCP Registry API](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/openapi.yaml), not a private registry. Its `search` parameter matches server names; use a specific public term. Only that query is sent, not the project prompt, local manifests or GitHub credentials. Discovery makes one bounded HTTPS request with a timeout and refuses redirects. Partial invalid records are reported in `errors` without discarding valid reviews.

Approval creates files under `.stratagent/proposals/mcp/ID/OPTION/`: `claude.mcp.json`, disabled `codex.config.toml`, disabled `antigravity.mcp_config.json` and `review.json`, according to selected targets. These files are not host settings and do not start a process or connection. Manually review and merge an approved Claude entry into `.mcp.json`, a Codex entry into `.codex/config.toml`, or an Antigravity entry into `.agents/mcp_config.json`, enabling only when ready. Activation may download/execute npm packages or contact a remote service; it is a separate user action.

Supported proposal transports are public HTTPS Streamable HTTP without embedded credentials/headers/variables/query, and exact-version npm stdio packages with an identified GitHub repository and no custom runtime, arguments or environment. Other transports remain inspectable but are not rendered. Inactive entries and suspicious descriptions are blocked. Registry identity and metadata hashes **do not establish executable safety, license compatibility or tool permissions**. npm versions are pinned but package artifact integrity is not verified; remote service behavior remains mutable. Skill source scanning and MCP metadata scanning are different assurance levels.

See [the architect guide](docs/project-architect.md) for realistic examples, approval boundaries and remaining limitations.

## Antigravity support

`init` defaults to `claude,codex,antigravity`. For an Antigravity-only project:

```sh
.venv/bin/stratagent init "Python API with testing and security review" \
  --workspace ./my-agent --platforms antigravity
.venv/bin/stratagent configure --content --workspace ./my-agent
# Review the exact outputs, then use this preview's approval digest:
.venv/bin/stratagent configure --apply --approve APPROVAL_SHA256 --workspace ./my-agent
```

Skills use `.agents/skills/<name>/SKILL.md`, shared with Codex. Selecting both targets emits each shared skill file once. Reviewed sub-agent definitions and generated roles use `.agents/agents/sa-*.md`, with `view_file`/`grep_search` tools, `mainAgent: false` and `commandExecutionPolicy: "off"`. Provider-specific upstream tools, hooks and permissions are not copied. No agent is launched by StratAgent. This targets the current Antigravity app/CLI custom-agent format; IDE skills are supported, while native role loading depends on the host surface/version.

Antigravity MCP proposals use `mcpServers`, `serverUrl` for remote connections, or pinned `command`/`args` for stdio, with `disabled: true`. Active workspace/global configuration is never modified. Existing settings and files retain the same overwrite refusal, source review, approval, lockfile and drift protections. Platform targets themselves are approval-bound, even when shared skill output bytes are identical. Generator version changes require fresh previews/approvals; installed outputs are not automatically upgraded.

Formats checked against official [skills](https://www.antigravity.google/docs/skills), [custom subagents](https://www.antigravity.google/docs/subagents/) and [MCP](https://www.antigravity.google/docs/mcp) documentation. File generation and approval behavior are tested; actual Antigravity runtime loading remains unverified.

## CLI reference

All results are JSON. `--workspace` and `--log-json` work before or after the subcommand. Optional structured command events go to stderr and contain no prompt, file contents, paths or credentials. `--content` on install/configuration previews shows the exact generated files without writing them.

| Command | Behavior |
| --- | --- |
| `plan PROMPT` | Analyze requirements and tasks without writing files |
| `platforms` | List built-in adapter capabilities without reading a workspace |
| `decision-request` | Export project/resource evidence, decision schema and a reviewable draft; no model API call |
| `blueprint --content` | Preview one architecture/resource/environment plan; `--decisions FILE` accepts a workspace-relative model/human proposal |
| `blueprint --apply --approve HASH` | Apply the exact reviewed blueprint after resolving scope/allowlist/collision blockers |
| `init PROMPT` | Create a manifest, empty lockfile and empty repository allowlist |
| `prepare PROMPT` | Initialize/reuse a matching workspace, research broad GitHub/MCP sources and return a reviewed-environment preview; `--offline` skips network; never applies |
| `research-request PROMPT` | Export current project evidence and a strict model-neutral runtime query-plan schema; no model/network call |
| `research-preview PROMPT --research-plan FILE` | Preview exact outbound query text/budgets and research-only approval; no writes or network |
| `discover` | Survey popular project-relevant repositories, pin supported definitions and rank reviewed candidates; report coverage; `--repo-limit` bounds inspection |
| `discover-mcp --query TERM` | Search the official MCP Registry and cache metadata reviews |
| `inspect-mcp ID --content` | Read metadata, provenance, policy findings and transport option indexes |
| `configure-mcp ID --option 0` | Preview inert host proposals; `--apply --approve HASH` writes only proposals |
| `inspect ID --content` | Read findings and all cached, untrusted source text |
| `recommend` | Suggest eligible candidates for each task |
| `allow owner/repo` | Explicitly allow one exact repository locally |
| `doctor` | Read-only local filesystem capabilities, permission/durability caveats and release status |
| `stage KIND` | Persist a blueprint/configuration/resource/removal/request revision plan and exact diff |
| `apply ID --approve HASH` | Revalidate and transactionally apply one staged plan; never activate |
| `revise PROMPT` | Preview a new planning request/targets; `--apply --approve HASH` is separate |
| `remove KEY` | Preview/remove one owned installation; dependency/drift conflicts fail closed |
| `recover` | Preview interrupted work; `--apply --approve HASH` explicitly authorizes recovery |
| `transactions` | List local transaction IDs/states without private backup contents |
| `install ID` | Preview by default; write only with `--apply --approve HASH` |
| `configure` | Preview or approve generated task configurations |
| `verify` | Check SHA-256 hashes of every locked output |
| `status` | Show the plan, candidates, policy and verification result |
| `demo` | Run an offline demo with original fixtures |
| `serve` | Default read-only stdio MCP, or explicitly scoped proposal-only session tools |
| `session-start`, `session-request`, `session-submit` | Durable existing-host model planning and bounded proposal validation |
| `session-search` | One separately approved live research round; never install/activate |
| `session-answer` | Operator's revised planning request before installation; stale prior approvals |
| `session-status`, `session-cancel`, `session-resume` | Inspect progress, stop and explicitly resume without replay/reset |

Exit codes: `0` success, `2` input/policy/access error, `3` verification drift, `4` discovery returned no candidates, `130` user interruption. Partial failures appear in `errors`; global rate/budget limits stop further requests and set `stopped_early`.

## Workspace layout and portability

```text
my-agent/
├── .stratagent/
│   ├── manifest.json          # Request, tasks, candidates, findings and scores
│   ├── policy.json            # Explicit local repository allowlist
│   ├── cache/<digest>.json    # Inert source text stored as JSON/base64
│   ├── mcp-cache/<hash>.json  # Untrusted official Registry response metadata
│   ├── proposals/mcp/        # Approved inert host proposals; no automatic activation
│   ├── lock.json              # Sources, hashes, licenses and approval records
│   ├── task-plan.json         # Task graph and approved resource assignments
│   ├── blueprint.json         # Approved decisions, roles, bindings, permission needs and evidence
│   ├── portable/skills/       # Generic Agent Skills output
│   └── notices/               # Notices for adapted definitions
├── .agents/
│   ├── skills/               # Shared Codex/Antigravity skills and text references
│   └── agents/               # Read-only Antigravity custom sub-agent definitions
└── .claude/
    ├── skills/               # Claude Code skills and text references
    └── agents/               # Read-only Claude Code sub-agent definitions
```

Skill adapters emit `name`, `description` and optional passive `compatibility` metadata and preserve relative text references and license/notice files. Typed source metadata and pinned local reference checks are bound into the review; tool grants, unsupported metadata and missing/unsafe references block installation. See [resource assurance](docs/resource-assurance.md) for supported syntax, scanner refresh and remaining P4 gates. Original source content remains in the evidence cache. Claude sub-agents use `Read, Grep, Glob` and `permissionMode: plan`; Antigravity agents use a constrained read-only tool list and shell execution policy `off`. The parent environment's permission settings also apply. Codex roles are represented as portable skills, not native multi-agent runtime configuration.

StratAgent does not change user-authored `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.mcp.json`, `.codex/config.toml`, `.agents/mcp_config.json`, global host settings or hooks. Unowned file conflicts stop installation, even for identical bytes. Reviewed updates/removal affect only recorded managed outputs and refuse drift.

## Security boundaries

- **Read-only network access.** Fixed-host HTTPS GET requests to GitHub and the official MCP Registry, no redirects, bounded responses and sanitized errors. GitHub tokens are sent only to GitHub in the API authorization header, never to the Registry or local state. TLS verification cannot be disabled; configure a trusted `SSL_CERT_FILE` if needed. MCP proposal endpoints are never contacted by StratAgent.
- **No external execution.** No Git clone, archive extraction, dependency installation, shell commands or plugin hooks run during discovery/installation/proposal generation. Installing StratAgent itself through `pip` is a separate package installation step.
- **Content integrity.** Sources are pinned to immutable commits. Git blob identities and file SHA-256 hashes are verified. Installation uses the reviewed snapshot, not a fresh download from a moving branch.
- **Separate approval gates.** The repository allowlist starts empty. Skills and npm proposals require repository permission and exact plan-hash approval. Remote proposals require exact approval and remain inert. The read-only MCP interface cannot grant either permission or activate a proposal.
- **Bounded inspection.** GitHub limits are 256 KiB per file, 2 MiB/80 files per bundle, 8 MiB per response, 100 requests and 20 results per discovery. Truncated repository trees are refused. Registry discovery uses one request, a 2 MiB response limit and at most 20 results; an individual metadata record is limited to 256 KiB.
- **Conservative file policy.** Symlinks, executables, submodules, traversal, absolute paths, control characters, non-portable paths and oversized/non-text content are refused. Installable bundles contain only `.md`, `.txt`, `.rst` and license/notice text. YAML, JSON, scripts and binaries block a bundle, including otherwise valid skills containing `agents/openai.yaml`.
- **Static risk signals.** Rules flag instruction overrides, remote shell execution, destructive commands, credential access and active permission/hook configuration. Security documentation can trigger false positives. These checks are not proof of safety; review every file before approval.
- **Conservative license matching.** Full supported license bodies are compared with pinned reference texts. Missing, unknown, customized or conflicting licenses are blocked. Supported texts are MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause and ISC. A match does not establish legal compatibility; review the actual notices and obligations.
- **Controlled local writes.** Persistent native kernel locks serialize POSIX/Windows mutations. Reviewed transactions back up bytes/mode semantics, journal before output changes, migrate ownership under exact approval and restore precommit failures. A lockfile replacement is the commit point. Interrupted writes block further mutation until explicitly reviewed recovery; identical repeated effects no-op. User edits/read-only files are never force-overwritten. Windows inherits directory ACLs rather than emulating private POSIX permissions. Multi-file visibility is not atomic for concurrent readers; physical power-loss/network-filesystem behavior is not certified. Quiesce hosts during updates and run `verify` afterwards.

The local user and operating system are trusted. There is no signature/attestation protection against an attacker who can rewrite the manifest, cache and lockfile together, or OS sandbox protection against hostile concurrent replacement of parent directories. Activated skills remain subject to the coding environment's own security boundaries.

For GitHub rate limits, narrow discovery with `--repo`/`--limit` or set `GITHUB_TOKEN` with only the necessary read permissions. StratAgent does not read `.env` files.

## Read-only MCP server

```sh
.venv/bin/stratagent serve --workspace /absolute/path/to/my-agent
```

The server uses newline-delimited JSON-RPC over stdio with MCP protocol version `2025-03-26`. stdout contains protocol messages only. Tools are `stratagent_analyze`, `stratagent_project`, `stratagent_recommend`, `stratagent_status`, `stratagent_inspect`, `stratagent_preview`, `stratagent_discover`, `stratagent_discover_mcp`, `stratagent_inspect_mcp`, `stratagent_research_request`, `stratagent_research_preview`, `stratagent_decision_request` and `stratagent_blueprint`. MCP discovery reads from the network without saving files. Research previews do not execute outbound queries. Decision/blueprint tools accept an optional exact `run_id`. Project/decision analysis reads bounded manifests and cached evidence; tool arguments cannot redirect it elsewhere. Model proposals cannot carry search approval, installation or permission authority. No mutating tool is exposed.

Adapt this example to your MCP client, replacing both paths:

```json
{
  "mcpServers": {
    "stratagent": {
      "command": "/absolute/path/to/stratagent/.venv/bin/stratagent",
      "args": ["serve", "--workspace", "/absolute/path/to/my-agent"]
    }
  }
}
```

This is a generic example; StratAgent does not modify user settings. Automated subprocess tests verify stdio behavior, and an [actual Codex CLI model pilot](docs/pilot-validation.md) exercised decision/preview/status tools and a generated portable role. MCP Inspector and actual Claude Code/Antigravity client sessions remain untested.

## Development and verification

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip wheel . --no-deps --wheel-dir /tmp/stratagent-wheels
```

The offline test suite covers project evidence/privacy and bounds, specialist task graphs, Registry transport and metadata validation, approval scope, inert proposal generation, rollback and drift, pinned GitHub fixtures, malicious paths, licenses, source scanning, the CLI and read-only MCP messages. Current and historical validation evidence is in [validation.md](docs/validation.md).

See [architecture.md](docs/architecture.md) for implementation boundaries and [community-launch.md](docs/community-launch.md) for a concise project description and launch copy.

## Ecosystem references

Primary sources checked on October 18–19, 2026:

- [Agent Skills specification](https://agentskills.io/specification)
- [OpenAI local skill locations](https://learn.chatgpt.com/docs/build-skills)
- [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp) and [Claude Code MCP configuration](https://code.claude.com/docs/en/mcp)
- [Official MCP Registry API](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/openapi.yaml)
- [Claude Code sub-agents](https://code.claude.com/docs/en/sub-agents)
- [GitHub tree API](https://docs.github.com/en/rest/git/trees) and [blob API](https://docs.github.com/en/rest/git/blobs)
- [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
- [OpenAI skills](https://github.com/openai/skills), [Anthropic skills](https://github.com/anthropics/skills) and [VoltAgent sub-agents](https://github.com/VoltAgent/awesome-claude-code-subagents)
- [SPDX license texts](https://github.com/spdx/license-list-data); pinned reference commits/hashes are in `src/stratagent/data/license_sources.json`.

StratAgent source code is MIT-licensed. Discovered resources retain their own licenses. Version 0.6 requires source review refresh and fresh previews/approvals; the reviewed lock migration contract remains in force. Do not edit approval-bound state by hand. This remains a developer preview, not a production/GA claim.
