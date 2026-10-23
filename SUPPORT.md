# Support

For usage and setup, start with the [README](README.md), [host setup](docs/host-setup.md)
and [offline demo](docs/demo-0.8.0.md). Python 3.11+ and supported local filesystems on
macOS, Linux and Windows are the current developer-preview scope.

Report non-sensitive bugs or feature requests through
[GitHub Issues](https://github.com/etrkk5/stratagent/issues/new/choose).
Include the package/Python/OS version, command, fixed `doctor` check IDs and a
minimal synthetic reproduction. Inspect everything before sharing. Do not attach
`.stratagent/`, transaction backups, private prompts, raw model/session logs or
credentials. Use [private reporting](SECURITY.md#report-privately) for security issues.

Support is best effort; no paid support plan or response SLA is offered. Run
`stratagent doctor --workspace /absolute/path/to/project --check-files` locally.
Do not delete state or force an update to bypass a failed check. Review
[diagnostics](docs/diagnostics.md) and [recovery](docs/lifecycle.md) before changing files.
