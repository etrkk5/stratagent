# OS-independent core, explicit filesystem capabilities

Version 0.5.1 moves OS-specific behavior into `filesystem.py`. Requirements, runtime research, model proposals, resource review, host adapters and transaction state transitions are not tied to Windows/macOS/Linux. This is **capability-based portability**, not pretending all filesystems have identical guarantees. No new runtime dependency, shell command or executable plugin is introduced.

## Backends

| Capability | macOS/Linux (`posix`) | Windows (`nt`) |
| --- | --- | --- |
| Native exclusive mutex | `fcntl.flock`, nonblocking | `msvcrt.locking`, nonblocking byte range at offset 0 |
| Process-death release | Kernel releases descriptor lock | Kernel releases byte-range lock |
| Lock path | Persistent `.stratagent/.mutation-lock`; never unlink/replace | Same; no stale directory-lock guessing |
| Atomic output | fsynced temporary file, same-filesystem `os.replace` | fsynced temporary file, same-filesystem `os.replace` |
| Directory sync | Explicit directory `fsync` | Not claimed; exposed as `directory_sync: false` |
| Permission observation | Exact supported POSIX mode (0600/0644) | Writable/read-only attribute; inherited Windows ACLs |
| Redirect rejection | Symlink components | Symlinks, junctions and all reparse-point components |
| Sharing violations | Fail normally | Only errors 32/33 retry, four attempts, at most 350 ms total backoff; no copy/delete fallback |

The Windows mutex can lock a byte beyond EOF, so it never writes/truncates an existing lock inode merely to initialize it. Normal release explicitly unlocks it; process termination is tested separately. Legacy `.write-lock` directories are refused on every OS. Unknown backends fail closed. A Windows read-only target is never made writable or deleted to bypass an error. Permanent permission errors are not retried as successful changes.

Windows does **not** implement POSIX 0600 privacy through `chmod`. Writable files have a normalized logical mode of 0644 in its local journal; read-only files are conflicts. Windows DACLs are inherited from the parent workspace and not rewritten. Keep private prompts, caches, stages and backups in a restricted user-owned directory; do not assume group/world POSIX bits describe Windows access. POSIX permissions still detect exact mode drift. Approval binds the active filesystem capabilities, and staged/locked local state is not a cross-OS transfer format: regenerate approvals in the destination workspace.

`Workspace` checks reparse points using `lstat` attributes, including on Python 3.11 (without relying on 3.12's `Path.is_junction`). Root junctions/Windows redirected ancestors and relative redirected components are refused. Cloud-placeholder/reparse workspaces, junction-mounted folders and network filesystems are outside the supported local-filesystem contract. Device aliases such as `CONIN$`, `CONOUT$` and whitespace-obfuscated `NUL` are also rejected as portable output names.

## Inspect and install without shell assumptions

```sh
python -m stratagent doctor --workspace PATH
python -m stratagent stage blueprint --workspace PATH
python -m stratagent apply STAGE_ID --approve EXACT_HASH --workspace PATH
python -m stratagent verify --workspace PATH
```

Windows PowerShell source installation:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install .
.venv\Scripts\python -m stratagent doctor
```

macOS/Linux source installation:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m stratagent doctor
```

The product never uses `bash`, PowerShell or `cmd` for setup. The native Windows junction regression test alone invokes `cmd /c mklink /J` on original temporary directories; it never executes downloaded content. CLI smoke/acceptance scripts use argument arrays, `sys.executable` and `tempfile`, not `/tmp`, shell expansion or POSIX-only pipe polling. Git source fixtures use LF consistently; test subprocesses use Python UTF-8 mode in CI.

## Validation and release boundary

The CI matrix runs **Ubuntu, macOS and Windows × Python 3.11 and 3.14**. Each job builds/installs a wheel, runs source and installed-wheel suites, original lifecycle acceptance, portable CLI smoke, `pip check` and compilation. A bounded test runner emits all-thread diagnostics and fails at a 600-second suite deadline; each job is capped at 25 minutes. Process-death tests use `Popen.kill()` (SIGKILL on POSIX, TerminateProcess on Windows) and a bounded threaded readiness queue; they are not skipped on Windows. A native Windows junction test runs only on Windows, with an explicit skip elsewhere. Backend simulation tests do not replace these native jobs.

The [accepted native matrix](https://github.com/etrkk5/stratagent/actions/runs/39838604544) for implementation commit `e9befa5` passes **all six jobs**. Each source/installed suite runs 275 tests: all pass on Windows; POSIX skips only the explicitly Windows-native junction regression. Native Windows process-death, rollback, reparse rejection and both CLI acceptances are exercised, not inferred from simulation. [Validation](validation.md) retains the earlier failures/cancelled run and measured results. Green OS CI closes the declared local OS lifecycle gate, not the [remaining production gates](release-readiness.md): third-party artifact/tool assurance, actual host loading, human-reviewed project evaluations and independent release pilots cannot be fabricated by unit tests.

Assumptions remain: trusted local OS/user, no hostile directory replacement, sufficient disk access for recovery and quiescent host readers. Directory durability/ACL differences are visible in `doctor`; neither backend claims filesystem-wide atomic visibility, arbitrary ACL preservation across replacement or physical-power-loss certification. Open/locked Windows files can require closing the host before explicitly reviewing recovery. Never delete a pending journal to force a new write.

## Primary implementation references

- [Python `msvcrt.locking`](https://docs.python.org/3/library/msvcrt.html#msvcrt.locking): nonblocking modes and ranges beyond EOF.
- [Microsoft byte-range locking](https://learn.microsoft.com/en-us/windows/win32/fileio/locking-and-unlocking-byte-ranges-in-files) and [process/handle lock release](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex).
- [Python OS operations](https://docs.python.org/3.11/library/os.html#os.replace) and [Windows `chmod` semantics](https://docs.python.org/3.11/library/os.html#os.chmod).
