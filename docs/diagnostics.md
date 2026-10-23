# Offline health checks and support reports

`stratagent doctor` checks the local installation and selected workspace without making network calls, starting hosts, taking a mutation lock or writing/repairing files. P6's first engineering increment extends the earlier filesystem-only report. It remains useful before initialization and when the pinned YAML dependency is missing; the CLI loads the diagnostic path before dependency-backed application modules.

## Run a check

```sh
stratagent doctor --workspace /absolute/path/to/project
stratagent doctor --workspace /absolute/path/to/project --check-files
```

On Windows, pass the ordinary local project path. Paths are command arguments, not fields copied into the report. The default reads selected workspace metadata and checks:

- Python 3.11+, pinned PyYAML 6.0.3 package metadata/module discovery, and agreement between running code and installed StratAgent metadata. Source-only operation without StratAgent distribution metadata is labeled skipped; a mismatched installed version is a warning.
- The declared local filesystem backend, built-in adapter contract validity and workspace path policy.
- Initialization completeness, manifest/policy/ownership-lock schemas, legacy write-lock markers and pending transaction recovery.
- Whether the selected metadata changed during diagnosis. A change is a failure requiring a retry with writers stopped; no repair or stale-lock deletion is attempted.

Managed file contents are not read by default. `--check-files` separately opts into existing locked-output hash/mode verification with a **16 MiB total expected-byte budget**. If the budget is exceeded, verification is not run and the report warns rather than calling it a pass. Use the full `verify` command privately for larger installations. Pending recovery defers file verification; run the reviewed recovery workflow first. Metadata files must be regular, nonredirected and at most 16 MiB each; directories, devices/FIFOs, symlinks/junctions/reparse points and oversized data are refused.

## Read the result

The JSON report has `schema_version: 1`, fixed check IDs, a `status`, `ok`, per-status counts, filesystem capabilities and explicit coverage. Each check includes a short message and next action.

| Result | Meaning | CLI exit |
| --- | --- | --- |
| `healthy` | No failures or warnings among the checks run; inspect skipped checks and coverage | `0` |
| `attention` | No failing checks, but a warning such as version mismatch or an exceeded hash budget | `0` |
| `unhealthy` | At least one runtime, metadata, recovery or file-verification failure | `2` |
| `skip` on an individual check | Not run, unnecessary before initialization, or deferred; never equivalent to a pass | Depends on the other checks |

Failures are still returned as structured JSON on stdout. Optional `--log-json` writes only command events/timing/exit codes to stderr. It does not include workspace arguments, prompts or raw exceptions. A malformed CLI invocation remains an ordinary argument error, outside the health-report schema. No new exit code or repair authority is introduced.

## Act on common findings

| Check | Next step |
| --- | --- |
| `pyyaml-runtime` | Activate the intended virtual environment and install the reviewed package with its pinned dependencies there. `doctor` never downloads anything or fixes the environment itself |
| `package-metadata` | Use one consistent source/package version and interpreter; avoid mixing old installed metadata with a newer source checkout |
| `workspace-directory` | Select an existing supported local directory. This is a path-policy/existence check, not a write-permission or disk-durability probe |
| `workspace-initialization` | A fresh project is valid and skipped. Partial existing state is a failure: preserve it and inspect the missing files instead of overwriting with another initialization |
| `legacy-write-lock` | Inspect active/old writers locally; never remove markers or journals merely to force another write |
| `transaction-recovery` | Review `stratagent recover --workspace PATH`, then separately approve the exact recovery plan. Keep backups and user changes intact |
| `managed-outputs` | Use `verify` locally for detailed drift/missing-file paths. Preserve user edits and use reviewed lifecycle operations for reconciliation |
| `workspace-snapshot` | Stop concurrent writers and retry. Diagnosis takes no lock and is not a filesystem-wide atomic snapshot |

For recovery details see [lifecycle.md](lifecycle.md); for OS limits see [os-portability.md](os-portability.md).

## Share a minimal report

You can intentionally save stdout locally using ordinary shell redirection. This is your shell writing the report, not an automatic product upload:

```sh
stratagent doctor --workspace /absolute/path/to/project > doctor-report.json
```

Review the JSON before attaching it to a non-sensitive issue. Reports omit absolute/relative project paths, source/prompts, discovered resource identifiers, credentials, host configuration, raw exceptions and metadata fingerprints. The known StratAgent version and pinned PyYAML requirement remain visible for troubleshooting. The tool reads selected private state locally to evaluate it, but does not copy those contents into the report. `.env` files and unrelated project files are not opened. Opt-in hash verification reads managed outputs but does not include them in the report. No telemetry, remote reporting endpoint or upload command is added.

Do not attach `.stratagent/` directories, transaction backups, model/session logs, `.env` files, active host settings or unreviewed `status`/`verify` output to public issues. The safe report is deliberately less detailed than those local investigation tools. A private security intake channel, incident response policy and maintained release-support process are not configured by this increment and remain P6 work; no response-time promise is made.

## Limits

`ok` is local operational health for the checks actually run. It does not establish resource safety, fresh vulnerability status, network/provider availability, native host compatibility, usable model output or production readiness. Run `security-status` separately for local revocation/recorded-assurance impact; that is also not a live global vulnerability audit. Dependency checks use installed metadata and top-level module discovery, not an attestation of package contents. Missing or broken application imports are reported with fixed recovery guidance.

No write permission test, active-writer lock probe, disk-capacity test, physical-power-loss check or network filesystem certification is performed. The metadata consistency observation is best effort under the trusted-local-user/OS assumptions. Windows inherits ACLs; directory sync and permission differences remain explicit. The original P5 field waivers remain in force; this diagnostic increment does not turn them into test results.
