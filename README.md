# StratAgent

[![Tests](https://github.com/etrkk5/stratagent/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/etrkk5/stratagent/actions/workflows/tests.yml)

**Give your coding agent a workspace built for your project.**

Describe what you want to build. StratAgent helps your coding agent turn that request into clear responsibilities, relevant skills and reviewed tool proposals. See why each choice fits, what is missing and exactly which files will change before you approve them.

Work inside **Claude Code, Codex or Antigravity**, using the model you already have. No additional LLM API key is required. A generic export is available for other integrations; supported outputs and host limitations are documented below.

StratAgent is a **provider-independent agent workspace architect**: it connects your project request and local dependency evidence with current resource research, then turns the reviewed plan into portable workspace files you can verify, update and remove.

> “Build a React dashboard with a Python API and PostgreSQL. Include testing and privacy review. No payments.”

```text
Describe your project → Review the proposed workspace → Approve exact changes
                      → Verify and maintain the setup
```

**Developer preview · Python 3.11+ · macOS, Linux & Windows · MIT**

[0.8.0 preview release](https://github.com/etrkk5/stratagent/releases/tag/v0.8.0) · [Offline walkthrough](docs/demo-0.8.0.md) · [Support](SUPPORT.md) · [Security](SECURITY.md)

## What makes StratAgent useful?

- **See the existing setup.** Inspect project-local guidance, skill/role metadata, recorded ownership and possible overlaps before proposing additions. Existing files remain under their current ownership; matching names do not prove equivalent capabilities. [Inspection scope](docs/existing-environment.md).
- **Keep a sufficient setup.** In the unreleased 0.9.0 workflow, your agent assesses needs, existing/host coverage and alternatives before adding tools. You can accept a no-change outcome with no search or new environment files; concrete gaps guide research. [How assessments work](docs/workspace-fit.md).
- **A clear division of work.** Compare focused ownership with specialist roles, including responsibilities, dependencies and acceptance criteria grounded in the project request.
- **Choices you can inspect.** Research current GitHub and MCP Registry sources. Review relevance, alternatives, source provenance, license/static findings and coverage gaps before selecting resources. Search is bounded; popularity does not establish safety.
- **Changes you control.** Review the exact file changes, authorize them and verify the installed result. Existing user files, conflicting edits and stale approvals are protected by the apply/update lifecycle.
- **A setup you can maintain.** Keep one reviewed plan with host-specific outputs and recorded provenance. Update or remove managed files with drift checks and recovery as the project evolves.

StratAgent prepares the environment; your coding host builds the application. It does not autonomously launch agents or install and run arbitrary GitHub code.

## Work through your coding agent

**Unreleased 0.9.0 development workflow.** The published 0.8.0 preview retains its
original commands; use a development checkout to try the new agent-first path.

After installing StratAgent locally, tell your existing coding agent:

> Use StratAgent to prepare this project's agent workspace. Explain the roles,
> useful resources and file changes before applying anything. Keep my current
> files and excluded features intact.

[Start-to-finish setup guide](docs/quickstart.md). Your part is simple:

1. **Describe the outcome and constraints.** Explain the project, what matters and what to leave out.
2. **Review the meaningful choices.** See whether the existing setup is enough. Review needs, coverage, alternatives and gaps; public search terms and file changes follow only when needed.
3. **Keep or change the setup.** Accept the reviewed no-change assessment, or authorize exact file changes and have the agent verify the installed result.

The agent carries the commands, JSON proposals, session IDs and approval digests.
Existing session progress is reused; conflicts, stale context and interrupted
changes are explained instead of silently resetting your work.

For one-time project integration, the agent previews `stratagent connect --json`,
reviews the packaged first-party skill and applies its exact connection approval.
Only local skill files are added; host settings, permissions and MCP servers need
separate activation. A host refresh/new session may be needed for discovery.
The agent then follows `start` and `next --json`, loading detailed schemas or
full diffs when the current step needs them.

[Agent-first workflow and limits](docs/agent-first-experience.md). Advanced CLI and
session-scoped MCP integrations remain available below.

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

For the published fixed-version preview, clone with `git clone --branch v0.8.0 --depth 1 https://github.com/etrkk5/stratagent.git`. The [release verification/install guide](docs/publishing.md#verify-and-install) covers the application wheel and six native offline bundles with SBOMs. The unreleased agent-first workflow is available in [the 0.9.0 development branch/PR](https://github.com/etrkk5/stratagent/pull/4); the default clone above follows the repository's default branch. No PyPI installation command is advertised until PyPI publication is confirmed.

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

<details>
<summary>Advanced: wire the model bridge and run the review/apply steps manually</summary>

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

</details>

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

This is a working developer preview, **not a production/GA release**. Native lifecycle CI covers macOS/Linux/Windows on Python 3.11 and 3.14. Host formats are reviewed against official documentation; broader native-host and human-usefulness checks are explicitly waived for the current scope, with their evidence limits recorded in [release readiness](docs/release-readiness.md).

Use `stratagent platforms` to inspect versioned adapter capabilities. These renderer contracts are included in exact-plan approvals and installation provenance; they describe generated files, while actual host/version validation is tracked separately in the [interoperability matrix](docs/interoperability.md).

Follow the [host setup guide](docs/host-setup.md) for Claude Code, Codex and Antigravity skill/role locations and scoped local MCP bridge configurations. Claude's reserved local skill names are mapped to portable exports with an `sa-` prefix; original source evidence remains unchanged.

## Where we are taking StratAgent

Our goal is to make StratAgent worth returning to: a coding agent should produce a
more useful result with it, with less setup effort and fewer unnecessary additions.
We want the smallest justified environment for the job. An informed recommendation
to add nothing should be a successful outcome.

The **unreleased development code** now inspects the existing environment and
supports a grounded needs assessment. Keep a sufficient setup through explicit
review, or use concrete gaps to guide research and resource choices. Task-performance
improvements and exhaustive semantic coverage remain to be demonstrated.

The product track continues beyond the current inspection, reviewed setup
and lifecycle capabilities:

- **Build on existing-environment observations.** Bounded inventory and reviewed keep/research assessments are implemented; broader semantic deduplication remains further work.
- **Demonstrate recommendation value.** Needs, evidence, coverage and alternatives now have a structured review path; evaluate actual task outcomes against the same coding host without StratAgent.
- **Make ongoing work easier.** Give a concise account of what changed, what still fits and what needs review, with explicit limits when handing work between supported hosts.

We will judge progress by useful outcomes, setup effort, unnecessary recommendations
and voluntary repeat use. Broad user preference, task-performance gains and seamless
cross-host handoff have not been established. The [product direction](docs/product-direction.md)
records the strategy and evidence gaps; the [engineering plan](docs/production-readiness.md)
tracks implementation and release readiness separately.

## Go deeper

- **Prepare a distribution:** [reproducible developer bundles, SBOM and package rollback](docs/releasing.md). For the published 0.8.0 assets and their attestations, follow the [release verification guide](docs/publishing.md#verify-and-install).
- **Check a setup:** run `stratagent doctor --workspace PATH`; add `--check-files` for bounded managed-output verification. See [health checks and support reports](docs/diagnostics.md) for findings and next steps. The command makes no network calls and never repairs files.
- **Build a workspace:** [existing-host orchestration](docs/orchestration.md) · [architectural decisions](docs/decision-workflow.md)
- **Understand discovery:** [GitHub/Registry coverage](docs/discovery.md) · [model-planned runtime research](docs/runtime-research.md)
- **Review trust:** [resource policy](docs/resource-assurance.md) · [artifact/tool audits](docs/artifact-assurance.md)
- **Operate safely:** [updates, removal and recovery](docs/lifecycle.md) · [OS portability](docs/os-portability.md)
- **Evaluate or contribute:** [architecture](docs/architecture.md) · [validation](docs/validation.md) · [production plan](docs/production-readiness.md)

[MIT license](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)
