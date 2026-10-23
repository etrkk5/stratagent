"""Offline, read-only health checks with fixed, shareable diagnostics."""
from importlib import metadata, util
import stat
import sys

from . import __version__
from .common import StratagentError, digest
from .filesystem import LocalFilesystem
from .hosts import catalog
from .workspace import Workspace

STATE_FILES = (".stratagent/manifest.json", ".stratagent/policy.json", ".stratagent/lock.json",
               ".stratagent/transaction.json")
MAX_STATE_BYTES = 16 * 1024 * 1024
MAX_VERIFY_BYTES = 16 * 1024 * 1024
LOCAL_ERRORS = (StratagentError, OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError)


def _state_snapshot(workspace):
    result = {}
    for relative in STATE_FILES:
        path = workspace.path(relative)
        if not path.exists():
            result[relative] = None
            continue
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_STATE_BYTES:
            raise StratagentError("Expected bounded regular workspace metadata.")
        with path.open("rb") as handle:
            content = handle.read(MAX_STATE_BYTES + 1)
        if len(content) > MAX_STATE_BYTES:
            raise StratagentError("Workspace metadata grew beyond the diagnostic limit.")
        result[relative] = digest(content)
    return result


def _dependency_ready():
    try:
        return metadata.version("PyYAML") == "6.0.3" and util.find_spec("yaml") is not None
    except (metadata.PackageNotFoundError, ImportError, OSError, ValueError):
        return False


def diagnose(root, check_files=False):
    checks = []

    def add(identifier, status, message, action="none"):
        checks.append({"id": identifier, "status": status, "message": message, "action": action})

    runtime_ok = sys.version_info >= (3, 11)
    add("python-runtime", "pass" if runtime_ok else "fail", "Python 3.11 or newer is required.",
        "none" if runtime_ok else "Install Python 3.11+ and recreate the virtual environment.")
    dependency_ok = _dependency_ready()
    add("pyyaml-runtime", "pass" if dependency_ok else "fail",
        "Pinned PyYAML 6.0.3 metadata and module are available." if dependency_ok else "Pinned PyYAML 6.0.3 is missing, mismatched or undiscoverable.",
        "none" if dependency_ok else "Install the reviewed StratAgent package and its dependencies in this same virtual environment.")
    try:
        installed = metadata.version("stratagent-cli")
        add("package-metadata", "pass" if installed == __version__ else "warn",
            "Installed package metadata matches running code." if installed == __version__ else "Installed package metadata differs from running code.",
            "none" if installed == __version__ else "Use one reviewed source/package version in the same virtual environment.")
    except metadata.PackageNotFoundError:
        add("package-metadata", "skip", "No installed package metadata; source-only execution is possible.")
    except (OSError, ValueError):
        add("package-metadata", "warn", "Installed package metadata could not be read.", "Check the local package installation.")

    filesystem = LocalFilesystem().capabilities()
    supported = filesystem["local_transactions"]
    add("filesystem-backend", "pass" if supported else "fail", "Local filesystem backend is supported." if supported else "Local filesystem backend is unsupported.",
        "none" if supported else "Use a supported local macOS, Linux or Windows filesystem.")
    try:
        catalog()
        add("adapter-contracts", "pass", "Built-in adapter contracts are valid; native host loading is not checked.")
    except LOCAL_ERRORS:
        add("adapter-contracts", "fail", "A built-in adapter contract is invalid.", "Restore a consistent reviewed StratAgent installation.")

    try:
        workspace = Workspace(root)
        add("workspace-directory", "pass", "Workspace directory exists and passes the local path policy.")
    except LOCAL_ERRORS:
        add("workspace-directory", "fail", "Workspace directory is missing, redirected or inaccessible.",
            "Select an existing local directory without unsupported redirects.")
        workspace = None
    if workspace is not None:
        try:
            _workspace_checks(workspace, runtime_ok and dependency_ok, check_files, add)
        except LOCAL_ERRORS:
            add("workspace-validation", "fail", "Workspace state could not be safely inspected.",
                "Inspect private local state; preserve existing files before repair.")

    counts = {status: sum(item["status"] == status for item in checks) for status in ("pass", "warn", "fail", "skip")}
    return {"schema_version": 1, "tool": "StratAgent", "version": __version__,
            "ok": counts["fail"] == 0, "status": "unhealthy" if counts["fail"] else "attention" if counts["warn"] else "healthy",
            "summary": counts, "checks": checks, "filesystem": filesystem,
            "scope": "offline-installation-and-workspace-health", "production_ready": False,
            "network_calls": 0, "writes": False,
            "coverage": {"managed_outputs_requested": check_files, "host_runtime": "not-checked",
                         "network_connectivity": "not-checked", "write_access": "not-probed",
                         "active_writer_lock": "not-probed", "resource_security": "use-security-status-separately"},
            "notes": ["The report omits paths, prompts, source text, credentials and raw exceptions; nothing is uploaded.",
                      "Package metadata/discoverability and file hashes are not dependency or resource safety certification.",
                      "No write probe or mutation lock is taken; stop concurrent writers and retry if state changes.",
                      "Windows inherits ACLs; filesystem capabilities are not a production-readiness claim."]}


def _workspace_checks(workspace, runtime_ready, check_files, add):
    try:
        state = workspace.path(".stratagent")
        if not state.exists():
            add("workspace-initialization", "skip", "Workspace is not initialized; this is valid before first use.",
                "Initialize through the reviewed init/session-start workflow when ready.")
            add("managed-outputs", "skip", "No initialized managed outputs to verify.")
            return
        if not state.is_dir():
            raise StratagentError("Expected a state directory.")
        before = _state_snapshot(workspace)
    except LOCAL_ERRORS:
        add("workspace-metadata", "fail", "Workspace metadata is redirected, oversized, nonregular or inaccessible.",
            "Inspect private local state; preserve existing files before repair.")
        return

    legacy = workspace.path(".stratagent/.write-lock")
    if legacy.exists():
        add("legacy-write-lock", "fail", "A legacy write-lock marker blocks mutations.",
            "Inspect the local writer/state; do not automatically delete or replace lock markers.")
    else:
        add("legacy-write-lock", "pass", "No legacy write-lock marker is present; active writer locking is not probed.")
    if all(value is None for value in before.values()) and all(path.name == ".mutation-lock" for path in state.iterdir()):
        marker = workspace.path(".stratagent/.mutation-lock")
        if marker.exists() and (not stat.S_ISREG(marker.lstat().st_mode) or marker.lstat().st_size > 1):
            raise StratagentError("Invalid local coordination marker.")
        add("workspace-initialization", "skip", "Only the local coordination marker exists; no project has been initialized.",
            "Start a project when ready; the existing coordination marker is retained.")
        add("managed-outputs", "skip", "No initialized managed outputs to verify.")
        return
    if any(before[path] is None for path in STATE_FILES[:3]):
        add("workspace-initialization", "fail", "Workspace contains incomplete initialization metadata.",
            "Preserve local state and inspect the incomplete initialization; do not reinitialize over it.")
        return
    add("workspace-initialization", "pass", "All required initialization files are present.")
    if not runtime_ready:
        add("workspace-metadata", "skip", "Full workspace validation needs the supported runtime and pinned dependency.")
        add("managed-outputs", "skip", "Managed file validation was not run.")
        return
    try:
        from .service import Stratagent
        from .lifecycle import Transactions
        service = Stratagent(workspace.root)
        service.manifest()
        service.policy()
        lock = service.lock()
        add("workspace-metadata", "pass", "Manifest, policy and ownership lock schemas are valid.")
        pending = Transactions(workspace).pending()
        add("transaction-recovery", "fail" if pending else "pass",
            "An environment transaction needs recovery." if pending else "No pending environment recovery was found.",
            "Review stratagent recover locally before any new mutation; retain backups." if pending else "none")
        if pending or not check_files:
            add("managed-outputs", "skip", "Managed file verification is deferred until recovery." if pending else "Managed file contents were not read.",
                "Review recovery first." if pending else "Run doctor --check-files to verify bounded managed outputs, or use verify locally.")
        elif sum(output["size"] for item in lock["installations"].values() for output in item["outputs"]) > MAX_VERIFY_BYTES:
            add("managed-outputs", "warn", "Managed outputs exceed the diagnostic 16 MiB total hash budget; verification was not run.",
                "Use stratagent verify locally for the full managed output set.")
        else:
            verification = service.verify()
            add("managed-outputs", "pass" if verification["ok"] else "fail",
                "Managed output hashes/modes match the lock." if verification["ok"] else "Managed outputs have drift, missing content or pending recovery.",
                "none" if verification["ok"] else "Run stratagent verify locally for details; preserve user edits before a reviewed repair.")
    except ImportError:
        add("workspace-metadata", "fail", "Workspace validation modules could not load.", "Repair the reviewed runtime installation.")
    except LOCAL_ERRORS:
        add("workspace-validation", "fail", "Workspace metadata, recovery state or managed outputs could not be validated.",
            "Inspect private local state using verify/recover; preserve files and backups.")
    try:
        if before != _state_snapshot(workspace):
            add("workspace-snapshot", "fail", "Workspace metadata changed during diagnosis; results are not a stable snapshot.",
                "Stop concurrent writers and retry; no repair was attempted.")
        else:
            add("workspace-snapshot", "pass", "Required metadata stayed unchanged during this read-only check.")
    except LOCAL_ERRORS:
        add("workspace-snapshot", "fail", "Workspace metadata became unavailable during diagnosis.", "Stop concurrent writers and retry.")
