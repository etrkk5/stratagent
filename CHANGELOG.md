# Changelog

## Unreleased — 0.9.0 agent-first experience

- Project-local first-party skill integration with exact review, create-only file writes and conflict preservation.
- A concise welcome, idempotent `start` and read-only `next` guidance for humans and coding agents.
- Progressive model schemas, exact search review, explained roles/resources/file changes, and verified completion.
- Direct bounded proposal input on stdin; returned command arrays preserve the running virtual environment.
- A read-only `stratagent_next` MCP entry point. Existing session tools retain their proposal-only scope.
- Explicit handling of ambiguous sessions, expiry, context drift, output conflicts and transaction recovery.


## 0.8.0 — Developer Preview

- Build project-aware agent workspaces using an existing coding host/model,
  reviewed research, scoped source inspection and exact approval.
- Preserve user files during staged updates/removal, with ownership, drift,
  transaction recovery and provenance records.
- Version host renderer contracts and handle Claude's reserved skill names.
- Diagnose missing runtime dependencies and workspace health offline with `doctor`.
- Produce repeatable source/wheel bundles, complete RECORD/checksum inventories
  and a CycloneDX 1.6 Python-distribution SBOM.
- Promote only a successful six-job main CI run to an attested GitHub preview;
  verify source/workflow identity and uploaded bytes before publication.
- Add private security reporting, support forms and a read-only declared-dependency
  advisory check. PyPI publishing is separately configured and manually triggered.

See [release notes](docs/releases/0.8.0.md) for installation and limitations.
Automated OS checks do not certify native host sessions. The explicitly waived
field checks are not represented as performed or passed.
