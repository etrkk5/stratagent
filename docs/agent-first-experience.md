# Agent-first product experience — 0.9.0 developer preview

## Product priority

The user chose natural-language use inside an existing IDE/coding agent as the
primary experience, before more announcement or distribution work. The intended
journey is **describe the project → understand the workspace proposal → approve
exact changes → continue or maintain the project**. The host supplies the model;
StratAgent supplies fresh reviewed evidence, consistent state and verifiable files.

A user should understand why each responsibility/resource helps, what is missing,
and what will change. They should not have to copy JSON, session IDs, approval
digests or learn the advanced command list. This is a product goal, not a claim
that every host/user has tested or prefers the workflow.

## One-time connection

The CLI must already be installed in the intended Python 3.11+ environment. PyPI
was deferred; do not claim `pip install stratagent-cli` works. Use the repository
installation from the README or reviewed release artifacts. The 0.9.0 preview contains
the new commands; the immutable 0.8.0 release is unchanged.

Ask the coding agent to connect StratAgent to this project. The agent reads:

```sh
stratagent connect --platforms codex --json
```

Select the actual host: `claude`, `codex`, `antigravity`, or `generic`. Default
connection previews the three native targets, deduplicating the shared path.
After the reviewed setup is authorized, the agent follows the returned argument
array containing the exact connection approval. No manual hash copying is needed.
The host's own tool/filesystem permissions still apply.

| Host | Project-local instruction file |
| --- | --- |
| Claude Code | `.claude/skills/stratagent/SKILL.md` |
| Codex / Antigravity | `.agents/skills/stratagent/SKILL.md` |
| Generic export | `.stratagent/portable/skills/stratagent/SKILL.md` |

This is a first-party instruction bundle, not an arbitrary installer. It never
changes global/active host settings, permissions, secrets or MCP registrations.
A refresh/new conversation may be needed for discovery; the current agent can
also read the installed skill directly. Generic consumers need their own skill
loading integration. No universal native-host certification follows.

Connection is create-only. Existing differing files block the entire setup;
matching files are preserved. Multi-file create failure rolls back newly created
files. The existing local coordination lock is retained. There is no automatic
connection-file update/removal or power-loss durability claim; new/differing
instructions require review. Project lifecycle ownership remains separate.

## Start and follow the next useful step

The agent uses the actual user request and current host:

```sh
stratagent start "Build a small Python API. Include testing and privacy. No payments." --platforms codex --json
stratagent next --json
```

Start initializes local project/session metadata only. Repeating it reuses
progress; it does not search, install, reset budgets or revise requirements.
Several sessions produce numbered choices, not a silent guess. The agent selects
the intended session; the user need not handle its ID. New sessions require the
explicit `--new-session` choice. Existing request/target changes retain the reviewed
`revise` boundary.

`next` is read-only and progressive. Ordinary output is a concise human view;
`--json` returns a typed next action and argument arrays. Those arrays use the
same Python interpreter/environment that produced them. `--details` supplies the
current model schema or full review/diff/content only at the relevant phase.
Session discovery is bounded to 128 records, 2 MiB per record/16 MiB total. Automatic
managed-output verification stops at 16 MiB and requests explicit verification
for a larger workspace. No network/write probe occurs during progress checks.

| Phase | Agent carries | User sees/decides |
| --- | --- | --- |
| Research / compare | Live schema, proposal JSON on stdin, request/session IDs | The project interpretation and material questions |
| Public search review | Exact session-bound approval and command | Actual outgoing queries, destinations and budgets |
| Workspace review | Current sources, full diff/content and staging | Role/resource reasons, missing evidence and exact file changes |
| Apply / verify | Stage ID and exact approved digest | Authorization for those changes and verified result |
| Recovery / conflict / expiry | Inspect the fixed next action | Concrete issue and continuation choice; existing work retained |

`session-submit --response-stdin` accepts one bounded 128 KiB JSON proposal, avoiding
private response files in the project root. It uses the same strict validation,
turn budgets and authority boundaries as the existing file-based proposal path.
Schemas, not arbitrary model commands, drive proposals. Model results and external
metadata remain untrusted. A model-generated reason is not proof of optimality.

The new default MCP tool `stratagent_next` exposes the same read-only guidance.
It cannot initialize, search, allow repositories, stage/apply, repair or approve.
The session-scoped MCP still exposes only request/submit, with proposal-only writes.
No mutation tool or permission shortcut is added to either MCP mode.

## Inspect the existing environment

`stratagent environment` and read-only `stratagent_environment` MCP inspect bounded
project-local guidance, skill/role metadata and recorded ownership before any
initialization. `next` shows counts/possible overlaps; details and model requests
carry the observations. User-definition changes invalidate old project/approval
context; managed outputs remain separate so apply does not invalidate itself.
No definition is adopted, executed or certified by its presence. See the
[scope, privacy and context contract](existing-environment.md).

## Assess before adding

The initial model request now offers a grounded needs/coverage assessment. The
agent can propose keeping the existing setup, with reasons and alternatives,
without searches or new role/tool files. The operator reviews and accepts that
exact no-change outcome; `next` reports `kept`, not a new installation. If a gap
exists, the assessment guides research and is shown in the workspace review.
See [fit boundaries](workspace-fit.md) and the [complete quickstart](quickstart.md).

## Review and completion

The workspace review explains the selected strategy, role responsibilities and
binding reasons, selected resource counts, open questions, source freshness and
create/replace/delete/unchanged paths. A summary is not sufficient authorization:
the agent reads the exact diff/content, resolves blockers and stages the proposal
through the existing engine. Repository trust is not inferred from popularity or
general approval. After the exact changes are authorized, it passes the returned
stage approval to `apply`, then reads `next`/`verify` again.

Ready requires the exact model proposal digest in installed provenance, current
project context, current adapter contracts, successful output verification and no
pending transaction. A different model decision at the same context is not called
installed. Ready means verified workspace files; research is not automatically
refreshed and the application/agents/MCP are not automatically built or launched.
Application work continues only if the user's actual task authorizes it.

## Acceptance and further product work

Engineering checks cover actual CLI subprocess proposal submission, read-only
CLI/MCP progress, bootstrap approval/context binding, conflict/rollback, no-budget
reset, multiple sessions, exact search disclosure, review → stage → apply → verify,
user-file preservation, stale context/decision refusal, FIFO rejection and a real
in-process post-commit interruption requiring recovery. These are controlled
fixtures, not real native-host or human-preference results.

The next product question is whether real proposals are useful and source coverage
is sufficient for the user's projects. Improve relevance, reasons, omissions and
recovery based on observed failures. Fresh model/host sessions and human feedback
can evaluate the experience when requested; the previously waived 30 reviews and
independent trials are not silently reinstated as release blockers. A GUI, native
plugin marketplace package and automatic host execution are not implied by this
increment. Broader adoption/preference remains unmeasured.

Official format references checked October 23, 2026:
[Codex skills](https://learn.chatgpt.com/docs/build-skills),
[Claude skills](https://code.claude.com/docs/en/skills),
[Antigravity skills](https://antigravity.google/docs/skills).
