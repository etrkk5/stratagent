# Release gate: evidence, not a version label

StratAgent is still a developer preview. Completing OS portability does not silently waive the existing [production-readiness plan](production-readiness.md). The current deliverable is an operator-approved, local workspace architect; package execution, hosted service operation and automatic host activation are not implicit scope expansions.

## Blocking evidence before a production/GA claim

| Gate | Current evidence | Required next action |
| --- | --- | --- |
| OS lifecycle | Local macOS unit/process-kill/installed CLI checks; native POSIX/Windows implementation | Run and inspect all six native CI jobs; retain commit-specific results, including Windows process-death/junction coverage |
| P4 resource assurance | Commit/blob provenance, conservative documentation checks and Registry metadata review | Complete real Agent Skills metadata/reference handling, read-only artifact/tool/license/permission audit, revocation/vulnerability policy and adversarial corpus; never treat metadata popularity as executable safety |
| P5 host interoperability | Bounded real Codex P2 evidence; host renderers tested offline | Record actual Claude Code/Codex/Antigravity host versions/capabilities and clean-session load tests; generic exports are not native host certification |
| P5 architecture usefulness | Six original real EN/TR P2 cases with honest source gaps/partial blockers | At least 30 human-reviewed project cases, scope/exclusion evaluation and reported false positives/gaps; generated labels are not human approval |
| P6 release/operations | Local wheel builds, no third-party runtime dependencies, provenance/verification | Reproducible distribution/SBOM and dependency review, signed release evidence, support/private security intake, incident/rollback policy, clean-machine upgrade/removal and independent pilot reproduction |

The next implementation phase after native OS validation is **P4**, not changing README to say production-ready. Use the same sequence: implement, test adversarial/real cases, record failures and residual risks, obtain any required human/host evidence, then advance. Optional activation stays disabled until its independent assurance and authority gates are met. No additional API key or paid provider was selected for this work.

## Operational stop conditions

- Partial/expired research, unsupported or unaudited sources, stale approval, user drift and ownership conflicts remain blockers; do not add a force flag to improve apparent conversion.
- A pending transaction requires reviewed `recover`, not deleting state. Preserve private backups before manual reconciliation. Close hosts that hold Windows files open and retry only with a new valid review.
- Keep `.stratagent` out of Git/telemetry and use a restricted user-owned directory, especially with inherited Windows ACLs. Never publish raw prompts, source/model logs or credentials in bug reports.
- Do not publish a package, merge main, enable a remote server or launch third-party content merely because branch CI passes. Each is a separate authorized action.

OS engineering and this checklist can be completed automatically; independent users' decisions, human evaluation and native hosts' credentials/consent cannot. Missing evidence must be reported as missing, not replaced by invented approvals, customer pilots or safe-resource claims.
