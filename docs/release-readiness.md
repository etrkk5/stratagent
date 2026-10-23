# Release gate: evidence, not a version label

StratAgent is still a developer preview. The [production-readiness plan](production-readiness.md) records the explicit October 23 user scope change: three P5 field checks are waived for continuation, with documentation-based acceptance instead. Waivers are not test results. The current deliverable is an operator-approved, local workspace architect; package execution, hosted service operation and automatic host activation are not implicit scope expansions.

## Gates before a production/GA claim

| Gate | Current evidence | Required next action |
| --- | --- | --- |
| OS lifecycle — passed for declared local scope | [Six native CI jobs pass](https://github.com/etrkk5/stratagent/actions/runs/39838604544), Ubuntu/macOS/Windows × Python 3.11/3.14, source/installed suites and CLI acceptance, Windows process-death/junction checks | Retain commit-specific evidence; directory durability/ACL differences remain explicit and network filesystems/physical power loss are not certified |
| P4 resource assurance | Commit/blob provenance, typed metadata/references, bounded SRI/archive/code/license/permission audit, tool snapshots, local revocation, root npm OSV TTL/outage handling and adversarial/integration evidence | Broader real-source compatibility/false-positive evidence and supported dependency closure remain open; code/archives/binary assets cannot install or execute; tool annotations and registry popularity are not safety proof |
| P5 host interoperability — revised scope accepted | [Versioned contracts and explicit waiver](interoperability.md), [official-documentation setup review](host-setup.md), reserved-name fix, historical Codex evidence and automated checks | Real multi-host sessions and independent installation trials waived by user; not a blocker to P6. Runtime versions/enforcement remain unverified; no certification implied |
| P5 architecture usefulness — field gate waived | Six original real EN/TR P2 cases retained with honest source gaps/partial blockers | Thirty human reviews waived by user; not performed or replaced by generated labels. Human usefulness remains unmeasured and is not a blocker to continuation |
| P6 release/operations — in progress | Local wheel builds, pinned PyYAML dependency with point-in-time advisory lookup, provenance/verification; offline [health checks and redacted local reports](diagnostics.md) | Reproducible distribution/SBOM and maintained dependency review, signed release evidence, support/private security intake, incident/rollback policy, clean-machine upgrade/removal and independent pilot reproduction |

The current implementation phase is **P6 operate and release**, started with offline health diagnostics. P5 engineering is complete against its explicitly revised documentation-based acceptance; the original field checks are waived. The [continuation audit](continuation-2026-10-23.md) retains the recovered history and subsequent scope decision. Optional activation still needs its own assurance and authority; waived P5 evidence is not permission to enable it. No additional API key or paid provider was selected for this work.

## Operational stop conditions

- Partial/expired research, unsupported or unaudited sources, stale approval, user drift and ownership conflicts remain blockers; do not add a force flag to improve apparent conversion.
- A pending transaction requires reviewed `recover`, not deleting state. Preserve private backups before manual reconciliation. Close hosts that hold Windows files open and retry only with a new valid review.
- Keep `.stratagent` out of Git/telemetry and use a restricted user-owned directory, especially with inherited Windows ACLs. Never publish raw prompts, source/model logs or credentials in bug reports.
- Do not publish a package, merge main, enable a remote server or launch third-party content merely because branch CI passes. Each is a separate authorized action.

Engineering and documentation checks can be completed automatically; independent users' decisions, human evaluation and native host results cannot be invented. The three waived P5 checks are recorded as unevaluated and accepted for continuation. Other missing evidence remains missing; no fabricated approvals, customer pilots or safety claims are added.
