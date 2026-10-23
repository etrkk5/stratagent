# Existing project environment — unreleased 0.9.0

StratAgent can now inspect project-local agent definitions before proposing an
addition. This first product increment supplies observations and possible overlaps
to the existing host model. It does not automatically decide that a resource is
useful, unnecessary or equivalent, or adopt a user's definitions into its lock.

## User experience

Ask the coding agent to inspect the existing environment and explain what is
already present before preparing additions. No initialization is required:

```sh
stratagent environment
stratagent environment --json
```

The concise output identifies local guidance, skills and roles; user-owned,
managed and unknown ownership; recorded managed-output counts; possible overlaps
and incomplete observations. The agent uses bounded JSON metadata when needed.
Existing `next` cards also show the counts and possible overlaps; `next --details
--json` includes the detailed report. Default MCP exposes the same read-only
`stratagent_environment` tool; session-scoped MCP retains only its two existing
proposal tools.

Research and decision requests include the observations so the existing model can
consider current coverage before proposing additions. Local evidence IDs have the
form `environment:RELATIVE_PATH`. These IDs cite observations, not installable
candidate resources. Existing public-query grounding still requires the actual
user request; local descriptions do not authorize outbound terms or a search.

## Fixed project-local scope

| Kind | Paths |
| --- | --- |
| Guidance | `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md` |
| Skills | `.agents/skills/*/SKILL.md`, `.claude/skills/*/SKILL.md`, `.stratagent/portable/skills/*/SKILL.md` |
| Roles | `.claude/agents/*.md`, `.agents/agents/*.md` |
| Recorded ownership | Validated `.stratagent/lock.json` output records |

The shared Codex/Antigravity skill directory is enumerated once. Supported layouts
follow the repository's existing adapter contracts; observation does not prove
that a specific host/version loaded a file. Root-local scope intentionally does
not include parent/global guidance, nested source-tree instructions, legacy host
layouts or every IDE's extension format. An absent definition is absent within
this scope, not proof that the host lacks the capability.

Definition bytes are read to hash their content and extract only bounded YAML
`name`/`description` metadata. Instruction bodies and guidance bodies are not
returned. The reader never follows referenced files, imports modules, runs scripts
or interprets tool/permission declarations as authority. References, assets,
`.env`, active MCP/host settings, credentials, private chats and global config are
not scanned. Private information can still occur in a user-authored description;
metadata remains local untrusted context, not public search text or telemetry.
Recognized credential-like metadata and control/bidi text are withheld; this is
not universal secret detection. YAML aliases, anchors and explicit tags are
refused by the existing bounded parser.

## Ownership, overlap and incomplete evidence

- **User-owned:** an observed definition has no recorded StratAgent owner. It is
  preserved; neither name matching nor inclusion in model context adopts it.
- **Managed:** a validated local lock records the output. Inspected native
  definitions are compared with their recorded bytes/size/mode; drift and missing
  definitions are reported. Counts for all other owned outputs are recorded
  metadata only. Use `verify` for complete managed-output verification.
- **Unknown:** ownership metadata is invalid, unreadable or redirected. The
  report states the gap and does not infer ownership or repair anything.
- **Possible overlap:** two observed definitions have identical content or the
  same declared name. These are review hints across project roots, not semantic
  equivalence, source trust, a duplication score or permission to delete/replace.

Malformed/unavailable descriptions remain visibly unknown. Directory/read limits,
unsafe paths, oversized/unreadable/changing files and missing managed definitions
produce incomplete observations. Do not turn that into a successful coverage
claim. Presence and matching lock bytes do not prove capability, security,
permission, activation or runtime behavior.

## Bounds and context binding

The reader enumerates at most 1,024 entries per fixed root and reads at most 96
present definitions / 2 MiB separately for user-owned/unknown and managed groups.
Each definition is at most 256 KiB; the lock is a bounded regular file of at most
16 MiB. Symlinks, Windows reparse points, nonregular files and changed read
snapshots are refused. No filesystem writes, network or active-writer probe occurs.
The report is a bounded observation, not an atomic filesystem snapshot or defense
against a hostile local user rewriting the workspace.

When project scanning is enabled, unowned observations, hashes, metadata, modes
and warnings enter project/research/decision identities and lifecycle approval
context. Adding, editing or removing a user definition invalidates old proposals,
search reviews and exact file approvals. Existing sessions may therefore require
an explicitly reviewed new plan after upgrading; no automatic reset or migration
is attempted. Previously installed files can still be verified/removed normally.

Managed definitions are reported separately and excluded from that project
fingerprint. Their state is already bound by the ownership/transaction engine;
creating an approved managed output must not invalidate its own project plan.
The model request identity additionally binds the current detailed observations:
if managed observations change between request and submission, reload the request.
Drift remains a verification/lifecycle failure, never a silently accepted edit.

`init --no-scan-project` remains respected by automatic research/decision/guidance.
The explicit `environment` command/tool is an independent request to inspect the
local scope. Read-only `plan` still requires `--scan-project` to inspect the project.

## Remaining product work

This increment enables evidence-informed reuse and review; automatic semantic
coverage analysis, suppression of every redundant proposed role, outcome-quality
comparisons, no-addition decisions across the complete blueprint and seamless
host handoff remain future work. Engineering fixtures do not establish real
native-host loading or human preference. Existing field-evaluation waivers remain
unchanged. See [product direction](product-direction.md) and [validation](validation.md).
