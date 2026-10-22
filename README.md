# StratAgent

[![Tests](https://github.com/etrkk5/stratagent/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/etrkk5/stratagent/actions/workflows/tests.yml)

**Describe your project. Design its agent workspace. Approve what gets installed.**

StratAgent is a **platform-agnostic AI agent workspace architect**. It turns your project idea and local dependency evidence into an architecture, agent/subagent responsibilities, reviewed Agent Skills and MCP server proposals—not just a list of packages.

Use the model and coding environment you already have: **Claude Code, Codex, Antigravity, or a generic export**. No additional LLM API key required.

> “Build a React dashboard with a Python API and PostgreSQL. Include testing and privacy review. No payments.”

```text
Your idea → Architecture & roles → Live resource discovery → Source review
         → Your approval → Workspace files → Verify / update / remove
```

**Developer preview · Python 3.11+ · macOS, Linux & Windows · MIT**

## Why use StratAgent?

- **Start with the project, not the catalog.** Compare focused vs. specialist ownership, task dependencies and acceptance criteria before choosing tools.
- **Discover at runtime.** Search GitHub across skill, agent/subagent and MCP-related repositories, including star-sorted results; use the official MCP Registry for server metadata. Research is bounded, not an exhaustive crawl or a frozen built-in catalog.
- **Understand each choice.** Inspect relevance, alternatives, source commits, license/static findings and coverage gaps. Popularity helps discovery; it never proves safety.
- **Keep the workspace portable.** One reviewed blueprint, host-specific outputs, a provenance lockfile and repeatable setup. Update or remove only managed files, with drift checks and recovery.

StratAgent prepares the environment; your coding host builds the application. It does not autonomously launch agents or install and run arbitrary GitHub code.

## Put it to work

| Your project idea | What to review in its workspace plan | Example |
| --- | --- | --- |
| React/Next.js frontend + FastAPI/PostgreSQL API | Frontend/API ownership, interface coordination, testing and relevant skill/MCP candidates | [SaaS manifest fixtures](examples/projects/saas) |
| A pandas data-review pipeline | Data-quality, testing and privacy responsibilities; offline constraints and resource gaps | [Data project fixture](examples/projects/data-review) |
| A small offline CSV inventory checker, without a web UI | Focused ownership and test review, without unnecessary web/payment tooling | [Runnable project + walkthrough](examples/projects/inventory-review/README.md) |

The first two examples are dependency fixtures, not finished applications. The CSV example includes working code and a [recorded Codex pilot](docs/pilot-validation.md).

## Try it locally

Install from this repository in a virtual environment:

```sh
git clone https://github.com/etrkk5/stratagent.git
cd stratagent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
stratagent --help
```

On Windows, use `python` instead of `python3` and activate with `.venv\Scripts\Activate.ps1` in PowerShell. See [OS support and limitations](docs/os-portability.md).

**Explore without network access or a model:**

```sh
stratagent plan "Build a Python data-review API. Include testing and privacy. No payments."
stratagent demo --workspace ./demo-workspace/preview
stratagent demo --workspace ./demo-workspace/applied --apply
stratagent verify --workspace ./demo-workspace/applied
```

`plan` is a read-only, disclosed rule-based preview. The offline demo uses original synthetic fixtures: inspect its preview, then explicitly apply generated skill/role files and inert MCP proposals in a separate directory. Use fresh demo directories on repeat runs. It does not download third-party content or execute agents.

## From your idea to a reviewed environment

Start a model-assisted session in an existing project directory; use a disposable copy first:

```sh
stratagent session-start "Build a React dashboard and Python API with PostgreSQL, testing and privacy. No payments." \
  --workspace /absolute/path/to/project --platforms claude,codex,antigravity
```

1. **Connect your current model.** Use the returned session ID with `stratagent serve --workspace /absolute/path/to/project --orchestration SESSION_ID` in your host's MCP configuration. The scoped bridge lets the model read project context and submit research/architecture proposals; StratAgent does not call an LLM API itself.
2. **Approve live research.** Review the proposed public search terms, destinations and budgets. Run `session-search` with the exact approval returned by `session-request`. The model then compares fresh candidates, explains missing resources and may request clarification or a separately approved refinement.
3. **Review the blueprint.** Inspect `blueprint --session SESSION_ID --content`, source findings and generated files. Resolve blockers and allow individual repositories only after review.
4. **Stage, approve and verify.** Stage the exact file diff, approve its complete hash, then check the installed outputs:

```sh
stratagent stage blueprint --session SESSION_ID --workspace /absolute/path/to/project
stratagent apply STAGE_ID --approve EXACT_APPROVAL_HASH --workspace /absolute/path/to/project
stratagent verify --workspace /absolute/path/to/project
```

IDs and hashes above are placeholders from your own command results. Use the same workspace throughout. **Search approval is not installation approval.** The model cannot grant either approval through the scoped bridge.

Follow the [complete model → research → review walkthrough](docs/orchestration.md) for host setup and exact commands. Prefer a simpler CLI entry point? [`prepare`](docs/discovery.md) performs live discovery with a disclosed rule-based draft unless you supply a model/human proposal; it never silently applies the environment.

## Portable by design, cautious by default

| Target | Current output |
| --- | --- |
| Claude Code | Skill and role files; separate, inactive MCP proposals |
| Codex | Agent Skills, including exported role instructions; disabled MCP proposals |
| Antigravity | Skill and role files; disabled MCP proposals |
| Generic | Portable instruction bundles and MCP review evidence; no universal host configuration assumed |

**Model-agnostic** means structured proposals from your existing model or a human, not a mandatory provider SDK. **Platform-agnostic** means adapters share the same planning and approval core—not that every host/version has been certified. Codex role exports are not native multi-agent orchestration.

- **Reviewed content only:** installation currently supports eligible text-only skill/subagent bundles. Unsupported code/assets and unknown licenses block installation. Source hashes and scans reduce risk; they do not prove safety.
- **MCP stays inactive:** server proposals never overwrite active host settings or launch packages. Optional npm artifact/tool audits are separate from Registry metadata review, not permission to execute.
- **No silent changes:** approvals bind exact content and outputs; identical setup verifies/no-ops, while collisions, drift and stale/partial research block application. Keep local project state private.

This is a working developer preview, **not a production/GA release**. Native lifecycle CI covers macOS/Linux/Windows on Python 3.11 and 3.14; broader host interoperability and human-reviewed usefulness remain [release gates](docs/release-readiness.md).

## Go deeper

- **Build a workspace:** [existing-host orchestration](docs/orchestration.md) · [architectural decisions](docs/decision-workflow.md)
- **Understand discovery:** [GitHub/Registry coverage](docs/discovery.md) · [model-planned runtime research](docs/runtime-research.md)
- **Review trust:** [resource policy](docs/resource-assurance.md) · [artifact/tool audits](docs/artifact-assurance.md)
- **Operate safely:** [updates, removal and recovery](docs/lifecycle.md) · [OS portability](docs/os-portability.md)
- **Evaluate or contribute:** [architecture](docs/architecture.md) · [validation](docs/validation.md) · [production plan](docs/production-readiness.md)

[MIT license](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)
