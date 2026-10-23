# Security policy

StratAgent 0.8.x is a developer preview. Security fixes target the latest preview;
older versions have no maintenance commitment. Do not use it as a security sandbox
or treat a policy pass as proof that third-party instructions or code are safe.

## Report privately

Use [GitHub private vulnerability reporting](https://github.com/etrkk5/stratagent/security/advisories/new).
Private reporting was enabled and verified on October 23, 2026. Include the exact
version/commit, affected command, a minimal synthetic reproduction and impact.
Keep real credentials, private prompts, workspaces and raw model logs out of the
report. Never put sensitive details in a public issue. If the private form becomes
unavailable, open a non-sensitive issue requesting a private contact without the
vulnerability details.

Maintainer @etrkk5 handles reports on a best-effort basis. No staffed response team
or guaranteed response time is claimed. Preserve private evidence, pause affected
activation/publication and follow the [incident/rollback procedure](docs/releasing.md#support-and-incident-handling).

## Scope and dependency checks

Source review, exact approval, workspace transactions and generated configuration
are in scope. Host permission enforcement, arbitrary third-party execution,
physical power loss and network filesystems are outside the declared assurance.

The scheduled read-only [dependency audit](.github/workflows/dependency-audit.yml)
queries OSV for the four declared PyPI runtime/build pins weekly and on relevant
pull requests. Findings or an unavailable/incomplete response fail the check;
maintainers must monitor GitHub Actions notifications and triage it. The audit
does not update packages or create dependency PRs. It excludes native libraries,
vendored/transitive build tooling and discovered skills/MCP resources. Resource
revocation and advisory checks have their [own scope](docs/artifact-assurance.md).

GitHub build attestations identify the release workflow and source commit. They
do not prove that the program, host or dependencies are safe.
