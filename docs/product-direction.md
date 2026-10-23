# StratAgent product direction — October 23, 2026

## Decision

The user wants StratAgent to become an obvious choice for developers and agents,
and valuable enough that a major model/platform provider could want to integrate
or acquire it. Acquisition is an aspiration, not a forecast, an expression of
buyer interest or a release gate. The immediate product goal is a repeatable,
measurable improvement over using the same coding host without StratAgent.

Primary users are developers working in an existing repository through their
current coding agent. First earn preference in that workflow; do not expand to
all users, all hosts and all tasks at once. The selected natural-language entry
point remains unchanged. Existing P0–P6 engineering evidence and field waivers
remain recorded in production-readiness.md; this product track does not replace
that historical plan or fabricate completion.

## Why integrations alone are insufficient

Official sources reviewed October 23, 2026:

- [Codex customization](https://learn.chatgpt.com/docs/customization/overview)
  already combines project guidance, skills, MCP and subagents.
- [Claude Code extensions](https://code.claude.com/docs/en/features-overview)
  already provides skills, subagents, MCP and plugin packaging.
- [Build with Google](https://www.antigravity.google/docs/build-with-google/)
  provides curated bundles of skills, MCP servers and editor extensions.
- [xAI remote MCP](https://docs.x.ai/developers/tools/remote-mcp) documents an
  API integration with external MCP tools. This does not establish native
  StratAgent support: the current local stdio server is not a remote HTTP
  service, and no xAI-specific adapter/integration was tested or added.

Our inference: provider-neutral packaging is useful distribution infrastructure,
but insufficient differentiation on its own. Do not claim that these providers
lack discovery/orchestration features or would prefer purchasing StratAgent to
building an alternative. Their integration/adoption decisions are unknown.

## Product promise to earn

For this repository and task, explain which agent capabilities are needed, reuse
what already works, propose the smallest justified change, preserve the user's
work, and make the result portable and maintainable across supported hosts.

A successful recommendation can be **add nothing**. More roles, tools, searches
or generated files are not success metrics. Abstain when evidence is inadequate;
show the gap instead of inventing a useful resource or overstating assurance.
Native host permission/activation differences must remain visible.

## Current position, checked against the code

| Capability | Evidence | Remaining product gap |
| --- | --- | --- |
| Natural-language host entry | Unreleased 0.9.0 first-party skill and connect/start/next in experience.py | Actual new host loading and user preference are not measured |
| Project grounding | project.py inspects bounded dependency manifests; blueprint.py accepts grounded model decisions and exclusions | Not a general source/architecture understanding engine or a complete inventory of existing host capabilities |
| Current resource research | research/service/orchestration modules bind bounded observations, review and session state | Useful eligible coverage and recommendation advantage are not established by passing tests |
| Portable, reviewed changes | Host contracts, provenance, stage/apply/verify and lifecycle recovery | Portable outputs do not prove equivalent runtime behavior or successful task handoff |
| Reliability | Source/installed regressions, six-platform CI and disposable upgrade evidence linked in PR #4 | These establish engineering behavior, not outcome quality, retention or acquisition value |

[PR #4](https://github.com/etrkk5/stratagent/pull/4) merged the agent-first foundation; published
0.8.0 is unchanged. No task-quality advantage is inferred from that PR. The next
[bounded inventory increment](existing-environment.md) adds local observations;
semantic coverage and outcome-quality improvements remain unmeasured.

## Next implementation order

1. **Understand and reuse the existing environment.** Add a bounded, read-only
   inventory of relevant project-local agent guidance/skills and StratAgent-owned
   outputs before recommending additions. Distinguish observed, managed,
   user-owned, conflicting and unknown capabilities; do not adopt existing files
   or imply trust/activation from their presence. Bind inventory changes into
   subsequent context/review identities. Avoid scanning secrets, global settings,
   private conversations or arbitrary source trees. Inventory text is untrusted
   evidence, never instructions. First acceptance: a prepared project keeps its
   user-owned setup and explains duplication/gaps without resetting or installing.
2. **Make recommendation quality visible.** For each material proposed addition,
   connect the actual need, observed evidence, existing coverage, reason for the
   choice, a reasonable alternative (including no addition), and remaining gaps.
   Use the existing model-neutral decision contract; extend it only where the
   current evidence cannot express the decision. Compare against the same host,
   task, repository and comparable budget without StratAgent. Separate structural
   fixture checks, actual task results and human judgments; model self-ratings
   are not independent proof. Do not publish invented scores or latency savings.
3. **Earn repeated use through maintenance.** Present one concise account of what
   changed in the project/environment, what still fits and what needs review.
   Reuse immutable evidence where valid, obtain fresh evidence when required and
   preserve existing egress/approval boundaries. Host handoff must preserve scope,
   decisions and source provenance while stating unsupported runtime features.
   Do not transfer private chats or silently promise cross-host memory.

The first bounded vertical slice now implements project-local observations,
possible overlaps and context binding as documented in [existing environment](existing-environment.md).
The [workspace-fit increment](workspace-fit.md) adds grounded needs/coverage and
alternative assessments, a reviewed no-addition outcome and gap-guided research.
These model judgments are not measured task-quality improvements. Broader semantic
deduplication, outcome comparisons and maintenance/handoff improvements remain planned.
Do not use this direction to justify an autonomous agent-execution service.

## Measure the benefit, not the amount of machinery

Use explicit denominators and raw observations. Do not announce numeric targets
as measured results. Controlled project fixtures can check exclusions, duplication,
change scope and preservation immediately; native model/user outcomes require
actual observations when authorized. Previously waived field trials remain waived,
not reinstated as mandatory launch work.

- Time and user interventions to the first reviewed useful result, separating
  installation, reasoning, network search and approval waiting time.
- Task acceptance or meaningful defects under the same-host comparison; record
  inconclusive/failing cases and overhead, not just favorable examples.
- Needed capabilities covered versus unnecessary/duplicate recommendations,
  unsupported resources and explicit abstentions.
- Actual maintenance/handoff success with preserved files and decision context.
- Voluntary repeat use, where observable with user consent. Local saved state,
  test runs, downloads and GitHub stars do not establish retention.

No implicit telemetry or private-data collection is authorized by these metrics.

## Strategic assets worth developing

The hypothesis is that providers could value proven task improvement, adoption,
maintained compatibility, a trustworthy resource/evidence evaluation corpus and
an easily embedded provider-independent engine. Each asset must actually exist
and have clear provenance and appropriate usage rights. A corpus must not be
assembled by collecting private repositories, prompts or outcomes by default.

The existing CLI/MCP/core separation is the starting point for integration.
Add a new SDK, service or native marketplace package for a concrete consumer
need, not to imitate platform scale. Stronger claims, a dashboard, more adapters,
a public catalog, stars or an acquisition pitch do not substitute for measured
benefit. This is a strategic hypothesis, not evidence of a defensible advantage
or current interest from OpenAI, Anthropic, xAI or Google.
