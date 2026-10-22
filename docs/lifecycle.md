# Reviewed local environment lifecycle

Version 0.5 adds CLI-only transactions for installation, reviewed updates, removal and operator request/target revisions. Version 0.5.1 adds [OS-specific filesystem backends](os-portability.md) for Windows and POSIX without changing the transaction state machine. The core remains model/provider/host independent: it consumes trusted renderer output, not model-authored commands. **No MCP server, package manager, agent process, credential prompt or host activation is executed.** Native host interoperability and artifact audits remain separate release gates.

## Review and apply

1. Obtain current evidence/decisions through the existing runtime orchestration. Keep `--run ID` or `--session ID` when staging a run-scoped blueprint; partial research still blocks application and staging does not extend its 15-minute expiry.
2. Review sources and grant each required exact repository allowance. Changing allowances invalidates earlier mutation previews, so obtain a fresh preview afterwards.
3. Run `stratagent stage blueprint --session ID --workspace PROJECT` (or `--decisions FILE --run ID`). The result includes an immutable stage ID, per-file create/replace/delete/unchanged classification, old/new hashes/sizes/modes, exact unified diff and full approval hash. It writes only private stage metadata, not managed outputs.
4. Inspect the complete proposal. Run `stratagent apply STAGE_ID --approve HASH --workspace PROJECT` only after approval. Apply re-renders and re-inspects the selected source snapshots, current policy/context/targets/generator, entire lock revision and observed managed files. It does not blindly trust a serialized file bundle.
5. Run `stratagent verify --workspace PROJECT`. Keep clients from loading managed instructions while an update/recovery is in progress: individual replacements are atomic, but the full multi-file update is not atomically visible to readers.

`stage` supports `blueprint`, `configure`, `install --candidate-id ID`, `configure-mcp --candidate-id ID --option N`, `remove --key KEY` and `revise --prompt TEXT --platforms TARGETS`. Only options relevant to that operation are accepted. The existing `blueprint`, `configure`, `install` and `configure-mcp` direct dry-run/`--apply --approve` paths use the same transaction engine; `--content` also returns exact diffs. Staging is recommended for a durable review artifact. Stages contain no authority by themselves. The default read-only MCP tools and two scoped orchestration tools gain no lifecycle permission.

## Revise, research, update

An existing environment need not be discarded for a changed idea or target selection:

```sh
stratagent stage revise --workspace ./project \
  --prompt "Small Python API with privacy and synthetic tests. No frontend or payments." \
  --platforms generic
stratagent apply REVISION_STAGE_ID --approve REVISION_HASH --workspace ./project
stratagent session-start "Small Python API with privacy and synthetic tests. No frontend or payments." \
  --workspace ./project --platforms generic
# Continue model proposal, separately approved live search and comparison.
stratagent stage blueprint --session NEW_SESSION_ID --workspace ./project
stratagent apply BLUEPRINT_STAGE_ID --approve BLUEPRINT_HASH --workspace ./project
stratagent verify --workspace ./project
```

Revision is an explicit operator planning-context change, journaled separately from environment updates. It preserves cached evidence and all installed files, but old decision/run/search approvals are stale. Installed architecture can temporarily be out of sync with the new request; `status.approved_blueprint.context_current` discloses this. New research must inspect a fresh cohort; no old cached ranking is silently treated as live. Before installation, `session-answer` still handles a model's questions within P2 budgets. After installation, use a separately reviewed complete `revise` request, then a new session; the model cannot rewrite the operator's installed scope through its proposal tool.

An updated blueprint can add resources/roles, replace owned instructions and remove obsolete blueprint-owned output. Shared standalone resources are not silently taken over. If a task configuration or blueprint still references a separately owned resource, changing/removing its files is blocked (`resource-in-use`); first review removal/replacement of the dependent configuration. There is no force flag or automatic cascade. To convert standalone task configuration into a blueprint, remove the managed `task-configuration` first after review; arbitrary cross-owner adoption is refused.

## Ownership, conflicts and state migration

- Lock v2 has a monotonic transaction revision, an exact path → installation ownership index and per-output content/mode records. Duplicate/case-colliding owners, unknown versions and non-generated paths are refused. Generated paths come from trusted host adapters plus the task plan, blueprint and inert proposal/notice directories; active host settings cannot be adopted as outputs.
- Valid v1 locks are readable without writes. The next approved mutation shows `lock_migration: {from: 1, to: 2}`, validates recorded paths and actual file state, records current supported modes, and commits migration together with the change. Failed migration restores the original lock bytes/mode. Migration does not silently adopt unowned files.
- Unowned destination files block installation even when identical. Missing/changed managed files or permissions block updates/removal. Expected modes are 0600 or 0644; executable/special modes, symlinks and non-regular files are refused. No user-authored settings, hooks or project files are removed. Empty directories created by an interrupted transaction are removed only when still empty.
- An identical applied stage or identical approved installed effect verifies/no-ops. A repeated removal of an absent installation no-ops under a fresh preview; replay of an older stage after unrelated commits is refused rather than resetting newer state. Stale stages must be recreated/reviewed, not force-applied.

## Journal and recovery

The exclusive workspace mutex is acquired before revalidation. Before any output change, `.stratagent/transaction.json` durably records the exact original and proposed bytes/modes, original lock bytes, deterministic temporary paths and absent parent directories. Normal writes fsync file contents, atomically replace each file and fsync its directory. Lockfile replacement is last and is the **commit point**. POSIX process death releases the advisory mutex without deleting its persistent inode.

Before the commit point, ordinary failures attempt to roll back all files and the exact original lock. An interrupted process or failed rollback leaves a pending journal; all ordinary workspace mutations refuse until recovery. Terminal journals/backups are retained, with previous records archived under `.stratagent/transactions/ID.json` before the next transaction. `stratagent transactions` lists IDs/states without exposing backup contents. Backups/stages contain private project prompts and source instructions, use private state files and must not be published or treated as telemetry. Retention is manual; archives are not an automatic user-facing time-travel restore service.

```sh
stratagent recover --workspace ./project
# Inspect pending action, observed hashes/modes, known temporary files and conflicts.
stratagent recover --workspace ./project --apply --approve EXACT_RECOVERY_HASH
stratagent verify --workspace ./project
```

Recovery revalidates the journal and exact current observations under the mutex. With the original lock it restores pretransaction state, even if some outputs already changed. With the committed lock and all outputs matching proposed state it finalizes, never rolls back a successful commit. Changed user content/modes, unknown temporary bytes, symlinks or a committed lock with inconsistent files block recovery without overwriting those files. Do not delete the journal/lock marker to bypass a conflict; preserve backups and reconcile the affected paths deliberately with the recorded state before reviewing recovery again. Interrupted rollback is itself repeatable.

## Supported boundary and limits

- Version 0.5.0's original validation covered local POSIX filesystems. Version 0.5.1 implements local Windows/POSIX backends and native OS CI; consult [actual measured results](validation.md) before inferring tested support. Windows uses inherited ACLs/writable attributes, not private POSIX mode enforcement, and does not claim directory fsync. NFS/network filesystems and physical power loss are not certified. Do not mix old/new writers on one workspace or remove the persistent mutation-lock inode.
- The local OS/user and filesystem are trusted. Hashes detect accidental drift, not a malicious user rewriting all state or hostile concurrent directory replacement. Stop host readers before changing instruction files; filesystem-wide atomic visibility and activation rollback are not provided.
- Each output/lock backup is bounded at 4 MiB, each rendered transaction at 4 MiB/600 affected output paths (including obsolete paths), and journal serialization at 15 MiB (below the 16 MiB state-reader bound). Limits are checked before journaling/output writes. History listing is capped at 1000 archives and fails with an archive instruction rather than silently truncating. Disk-full/permission failures can leave recoverable pending work; an inaccessible disk or corrupted/missing journal cannot be automatically repaired. A process killed inside an atomic state-metadata write can leave an unreferenced private `.stratagent-*` temporary file; managed-output recovery does not publish or automatically collect unrelated state temporaries.
- No host activation was added. Proposals remain inert; separately enabling a remote MCP/npm package requires its own source/artifact/tool/credential review. P4 audits, P5 actual host sessions and P6 clean-machine/release/independent-pilot gates remain open.

## Reproduce the offline acceptance

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p test_lifecycle.py -v
python3 scripts/validate_lifecycle.py
# Or retain evidence in a NEW disposable directory:
python3 scripts/validate_lifecycle.py --workspace /tmp/stratagent-lifecycle-example
```

The CLI acceptance uses original generated roles only: four targets → approved revision → generic-only update → removal, preserving four original user files/settings. It performs no source/model network calls or third-party execution. Fault tests use real POSIX SIGKILL at every update output/commit boundary, within atomic file writes, during initial install, request revision, removal and rollback; ordinary injected failures check exact restoration and conflict refusal. These are automated local acceptance checks, not independent customer pilots or evidence of native host loading.
