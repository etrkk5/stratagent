# Assess before adding — 0.9.0 developer preview

StratAgent can now conclude that the existing setup is enough. The current coding
host makes a grounded assessment of needs, existing/host coverage, concrete gaps
and alternatives. A no-change assessment goes to operator review; acceptance
retains the environment instead of generating a new set of role/tool files.

This is a usable decision path, not a measured task-performance improvement.
Model judgment and metadata remain untrusted claims; structural validation cannot
prove exhaustive semantic coverage or actual host loading.

## Two useful outcomes

- **Keep:** explain why the existing setup/current host suffices and what could
  justify a different choice. Show the relevant observed definition paths. The
  agent asks for acceptance when not already authorized, then carries the exact
  review digest to `session-accept-fit`. No external search, staged installation,
  new role files or activation is needed. Planning/session metadata is still saved.
- **Research:** identify a concrete gap or uncertainty before searching. The
  assessment is included in subsequent research/comparison requests and workspace
  review, so the agent can connect proposed additions to actual needs. Exact
  outbound-query approval and existing stage/apply boundaries remain unchanged.

Both paths use the existing `start` / `next` experience. Default read-only MCP and
scoped session request/submit transports expose the live assessment schema. No
extra model account or direct LLM transport is introduced. Existing clients can
still propose research directly; the packaged skill prioritizes assessment when
it is available. A fresh research request explicitly authorized by the user can
continue through the existing protocol.

## Grounding and current observations

Every assessed need quotes and cites the actual user request. Keep requires no
unresolved gap/unknown and no incomplete inventory. Existing coverage must cite
current observed skill/role definitions with usable metadata and paths covering
all selected hosts. Matching names do not prove equivalent behavior. Host coverage
is explicitly model judgment; it does not assert permission, completed application
work, executed tests or native-host certification. Root guidance alone cannot be
relabelled as a verified installed skill.

The proposal binds the current project digest, full bounded environment observation
and exact validated ownership-lock bytes, including non-definition ownership
changes. A keep review also binds the workspace, session, complete assessment and
selected existing definitions. Changed files/metadata invalidate old reviews.
Before acceptance the managed outputs are verified again, with a 16 MiB budget;
drift or a pending transaction cannot be hidden by choosing keep. Larger managed
setups need explicit inspection rather than an automatic acceptance claim.

`init --no-scan-project` remains respected: host-only assessment is possible
without inspecting local definitions, with that limitation visible. State metadata
is still validated. No assessment gives ownership over a user file, installs a
resource, approves a network request or starts a host/tool process.

## State and operator boundary

The optional strict fit proposal adds `assess` at the initial model phase. It uses
the existing model-turn budget. A research assessment retains `research-needed`
with its gaps attached. A keep assessment moves to `fit-review-required` and can
be accepted only through the operator CLI:

```text
session-submit → next (fit-review) → session-accept-fit → next (kept)
```

The agent reads the command/digest from the current JSON card; users need not copy
IDs or hashes. Only the exact operator acceptance moves to `complete-no-change`.
The scoped MCP still has two proposal-only tools and cannot accept assessments.
Default MCP remains read-only. Accepted keep is not a blueprint: the existing
stage/install path cannot treat it as approval to change the environment.

Cancellation/resume, expiry and clarification retain their existing budgets and
scope boundaries. A cancelled assessment needs deliberate resume; expiry prevents
new acceptance. Resume/clarification clears the old fit proposal. A previously
accepted result can be reported after its planning deadline only while its bound
observations remain current; this is historical setup acceptance, not fresh
research. Repeating the same current acceptance is a no-op.

New optional state fields and states are for current development code. Older
clients may refuse the new state; installed-file verification/removal remains
independent. No automatic state reset or downgrade migration is performed.

## Evidence and remaining work

The CLI acceptance script executes a controlled original proposal through real
subprocess start/request/stdin-submit/review/accept/next commands: one proposal,
zero searches, zero new environment files and the existing user file retained.
This fixture does not launch a model or represent a human evaluation. Unit tests
also exercise the gap → research → compare → stage/apply/verify path, EN/TR needs,
strict evidence/host boundaries, stale approvals and drift refusal. Native CI runs
both source and installed packages; outcomes are recorded in [validation](validation.md).

Actual same-host outcome comparisons, measured relevance/retention, automatic
semantic deduplication and seamless host handoff remain further product work.
Previously waived field trials remain waived, not fabricated passes or new release
gates. Published 0.8.0 and PyPI publication are unchanged.
