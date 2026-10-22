"""Reviewed, local-only transactions for managed files; never activate a host."""
import base64
import copy
import difflib
import re
import stat
import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath

from . import __version__
from .common import StratagentError, canonical, digest, identity, safe_path
from . import hosts

LOCK = ".stratagent/lock.json"
MANIFEST = ".stratagent/manifest.json"
JOURNAL = ".stratagent/transaction.json"
TERMINAL = ("committed", "rolled-back")
MAX_BYTES = 4 * 1024 * 1024
MAX_OUTPUTS = 600


def managed_path(relative):
    safe_path(relative)
    roots = {adapter.skill_root for adapter in hosts.ADAPTERS.values()}
    roots.update(adapter.agent_root for adapter in hosts.ADAPTERS.values() if adapter.agent_root)
    roots.update((".stratagent/proposals", ".stratagent/notices"))
    if relative not in (".stratagent/task-plan.json", ".stratagent/blueprint.json") and not any(relative.startswith(root + "/") for root in roots):
        raise StratagentError(f"Not a managed output path: {relative}")
    return relative


def ownership(installations):
    result, folded = {}, set()
    for key, installation in installations.items():
        if (not isinstance(key, str) or not key or not isinstance(installation, dict) or not isinstance(installation.get("outputs"), list)
                or not isinstance(installation.get("source", {}), dict)):
            raise StratagentError("Invalid lockfile installation record.")
        for output in installation["outputs"]:
            if (not isinstance(output, dict) or not isinstance(output.get("path"), str)
                    or type(output.get("size")) is not int or not 0 <= output["size"] <= MAX_BYTES
                    or not isinstance(output.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", output["sha256"])
                    or ("mode" in output and (type(output["mode"]) is not int or output["mode"] not in (0o600, 0o644)))):
                raise StratagentError("Invalid lockfile output record.")
            path = managed_path(output["path"])
            if path.casefold() in folded:
                raise StratagentError("Duplicate or case-colliding lockfile ownership; manual review required.")
            folded.add(path.casefold())
            result[path] = key
    if len(result) > MAX_OUTPUTS:
        raise StratagentError("Managed output count exceeds the supported limit.")
    return result


def validate_lock(value):
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] not in (1, 2) or not isinstance(value.get("installations"), dict):
        raise StratagentError("Invalid lockfile schema; expected version 1 or 2.")
    owners = ownership(value["installations"])
    if value["schema_version"] == 2 and (type(value.get("revision")) is not int or value["revision"] < 0 or value.get("owners") != owners):
        raise StratagentError("Invalid version 2 lockfile ownership/revision.")
    return value


def upgraded_lock(value):
    result = copy.deepcopy(validate_lock(value))
    result.update(schema_version=2, generator_version=__version__, revision=result.get("revision", 0), owners=ownership(result["installations"]))
    return result


def encoded(data, mode):
    if len(data) > MAX_BYTES:
        raise StratagentError("Transaction file or lock exceeds the 4 MiB backup limit; no output writes permitted.")
    return {"data": base64.b64encode(data).decode(), "sha256": digest(data), "size": len(data), "mode": mode}


def decoded(record):
    try:
        data = base64.b64decode(record["data"], validate=True)
    except (ValueError, TypeError, KeyError) as exc:
        raise StratagentError("Invalid transaction backup encoding.") from exc
    if (len(data) > MAX_BYTES or record.get("sha256") != digest(data) or record.get("size") != len(data)
            or type(record.get("mode")) is not int or record["mode"] not in (0o600, 0o644)):
        raise StratagentError("Transaction backup integrity or mode mismatch.")
    return data


def summary(record):
    return {key: value for key, value in record.items() if key != "data"} if record is not None else None


class Transactions:
    def __init__(self, workspace):
        self.ws = workspace

    def snapshot(self, relative):
        path = self.ws.path(relative)
        if not path.exists():
            return None
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_BYTES:
            raise StratagentError(f"Expected a bounded regular file: {relative}")
        mode = self.ws.fs.mode(metadata)
        if mode not in (0o600, 0o644):
            raise StratagentError(f"Unexpected file permissions; review before writing: {relative}")
        data = path.read_bytes()
        if len(data) > MAX_BYTES:
            raise StratagentError("File grew beyond the transaction limit.")
        return encoded(data, mode)

    def pending(self):
        if not self.ws.path(JOURNAL).exists():
            return None
        journal = self.load_journal()
        return journal if journal["state"] not in TERMINAL else None

    def preview(self, key, files, context, remove=False):
        if self.pending():
            raise StratagentError("An environment transaction needs recovery; run stratagent recover first.")
        lock = validate_lock(self.ws.read(LOCK))
        owners = ownership(lock["installations"])
        previous = lock["installations"].get(key)
        old = {output["path"]: output for output in previous["outputs"]} if previous else {}
        if len(set(old) | set(files)) > MAX_OUTPUTS or sum(len(data) for data in files.values()) > MAX_BYTES:
            raise StratagentError("Transaction output limit exceeded.")
        for path in files:
            if key == "workspace-request" and path == MANIFEST:
                continue
            managed_path(path)
        if len({path.casefold() for path in files}) != len(files):
            raise StratagentError("Case-colliding outputs are forbidden.")
        observations, blockers = {}, []
        for path in sorted(set(owners) | set(files)):
            try:
                observations[path] = summary(self.snapshot(path))
            except StratagentError:
                observations[path] = {"unsafe": True}
                blockers.append({"rule": "unsafe-output", "path": path})
                continue
            owner = owners.get(path)
            if owner:
                expected = next(output for output in lock["installations"][owner]["outputs"] if output["path"] == path)
                actual = observations[path]
                if actual is None or any(actual.get(field) != expected[field] for field in ("size", "sha256")) or ("mode" in expected and actual["mode"] != expected["mode"]):
                    blockers.append({"rule": "managed-output-drift", "path": path})
            if path in files and path != MANIFEST:
                if owner and owner != key:
                    blockers.append({"rule": "owned-by-another-installation", "path": path, "owner": owner})
                elif owner is None and observations[path] is not None:
                    blockers.append({"rule": "existing-output", "path": path})
                elif any(other.casefold() == path.casefold() and other != path for other in owners):
                    blockers.append({"rule": "case-colliding-ownership", "path": path})
        changes = []
        for path in sorted(set(old) | set(files)):
            before = observations[path]
            after = summary(encoded(files[path], (before or {}).get("mode", 0o644))) if path in files else None
            action = "unchanged" if before == after else "delete" if after is None else "create" if before is None else "replace"
            changes.append({"path": path, "action": action, "before": before, "after": after})
        changed = {entry["path"] for entry in changes if entry["action"] != "unchanged"}
        for other_key, installation in lock["installations"].items():
            if other_key == key:
                continue
            source = installation.get("source", {})
            references = [entry["path"] for entry in source.get("reused_outputs", [])]
            task_plan = source.get("task_plan", source.get("blueprint", {}))
            for assignment in task_plan.get("assignments", []):
                for resource in assignment.get("resources", []) + assignment.get("mcp_proposals", []):
                    references.extend(resource.get("paths", []))
            if changed.intersection(references):
                blockers.append({"rule": "resource-in-use", "installation": other_key})
        return {"schema_version": 1, "operation": "remove" if remove else "revise" if key == "workspace-request" else "update" if previous else "install",
                "key": key, "base_lock": identity(lock), "context": identity(context), "observed": observations,
                "lock_migration": {"from": lock["schema_version"], "to": 2}, "changes": changes, "blockers": blockers}

    def diff(self, plan, files):
        result = {}
        for change in plan["lifecycle"]["changes"]:
            if change["action"] == "unchanged" or plan["lifecycle"]["blockers"]:
                continue
            path = change["path"]
            before = self.snapshot(path)
            old = decoded(before).decode("utf-8", errors="replace") if before else ""
            new = files.get(path, b"").decode("utf-8", errors="replace")
            result[path] = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile="before/" + path, tofile="after/" + path))
        return result

    def checkpoint(self, event):
        """Fault-injection boundary; production has no external callbacks."""

    def _save_journal(self, value):
        value["digest"] = identity({key: item for key, item in value.items() if key != "digest"})
        self.ws.write(JOURNAL, value)

    def load_journal(self):
        value = self.ws.read(JOURNAL)
        if (not isinstance(value, dict) or value.get("schema_version") != 1 or not isinstance(value.get("id"), str)
                or not re.fullmatch(r"[0-9a-f]{32}", value["id"]) or value.get("workspace") != str(self.ws.root)
                or value.get("state") not in (*TERMINAL, "prepared", "writing", "rolling-back")
                or value.get("digest") != identity({key: item for key, item in value.items() if key != "digest"})
                or not isinstance(value.get("entries"), list) or len(value["entries"]) > MAX_OUTPUTS + 1):
            raise StratagentError("Invalid environment transaction journal; no recovery writes permitted.")
        seen = set()
        for index, entry in enumerate(value["entries"]):
            path = entry["path"]
            if path not in (LOCK, MANIFEST):
                managed_path(path)
            if path.casefold() in seen or entry["temporary"] != f"{PurePosixPath(path).parent}/.stratagent-{value['id']}-{index}.tmp":
                raise StratagentError("Invalid transaction path or duplicate entry.")
            seen.add(path.casefold())
            for state in ("before", "after"):
                if entry[state] is not None:
                    decoded(entry[state])
        if not value["entries"] or value["entries"][-1]["path"] != LOCK:
            raise StratagentError("Transaction has no final lockfile commit point.")
        for directory in value["directories"]:
            safe_path(directory)
            if not any(entry["path"].startswith(directory + "/") for entry in value["entries"]):
                raise StratagentError("Invalid transaction directory.")
        return value

    def _write_entry(self, entry, state):
        current = self.snapshot(entry["path"])
        expected = entry[state]
        if summary(current) == summary(expected):
            return
        if summary(current) not in (summary(entry["before"]), summary(entry["after"])):
            raise StratagentError("Transaction output changed externally; recovery refuses to overwrite it.")
        if expected is None:
            path = self.ws.path(entry["path"])
            path.unlink()
            self.ws.sync_directory(path.parent)
        else:
            self.ws.atomic_bytes(entry["path"], decoded(expected), expected["mode"], entry["temporary"])

    def _clean(self, journal):
        for entry in journal["entries"]:
            path = self.ws.path(entry["temporary"])
            if path.exists():
                if not self._temporary_valid(entry):
                    raise StratagentError("Transaction temporary file changed externally; inspect before recovery.")
                path.unlink()
                self.ws.sync_directory(path.parent)
        for relative in reversed(journal["directories"]):
            path = self.ws.path(relative)
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
                self.ws.sync_directory(path.parent)

    def _temporary_valid(self, entry):
        current = self.snapshot(entry["temporary"])
        if current is None:
            return True
        data = decoded(current)
        return any(state is not None and decoded(state).startswith(data) and current["mode"] == state["mode"] for state in (entry["before"], entry["after"]))

    def _rollback(self, journal):
        for entry in journal["entries"]:
            if summary(self.snapshot(entry["path"])) not in (summary(entry["before"]), summary(entry["after"])):
                raise StratagentError("Transaction output changed externally; recovery refuses to overwrite it.")
        journal["state"] = "rolling-back"
        self._save_journal(journal)
        self._clean(journal)
        for index, entry in enumerate(journal["entries"]):
            self._write_entry(entry, "before")
            self.checkpoint(f"rollback:{index}")
        self._clean(journal)
        journal["state"] = "rolled-back"
        self._save_journal(journal)

    def execute(self, plan, files, key, lock, stage_id=None):
        self.ws.fs.require_supported()
        if self.pending():
            raise StratagentError("Recover the pending environment transaction before applying.")
        if plan["lifecycle"]["blockers"]:
            raise StratagentError("Managed output conflicts: refusing to overwrite user files, drift or resources in use.")
        if not plan["lifecycle"]["changes"] and key not in lock["installations"] and plan["lifecycle"]["operation"] == "remove":
            return {"applied": False, "already_removed": True, "approval": plan["approval"]}
        transaction_id = uuid.uuid4().hex
        changed = [entry for entry in plan["lifecycle"]["changes"] if entry["action"] != "unchanged"]
        updated = upgraded_lock(lock)
        if plan["lifecycle"]["operation"] == "remove":
            updated["installations"].pop(key, None)
        elif key != "workspace-request":
            updated["installations"][key] = {**plan, "dry_run": False, "installed_at": datetime.now(timezone.utc).isoformat(),
                "outputs": [{**output, "mode": (plan["lifecycle"]["observed"].get(output["path"]) or {}).get("mode", 0o644)} for output in plan["outputs"]],
                "transaction_id": transaction_id, "provenance": {"tool": "StratAgent", "version": __version__, "execution": "none"}}
        updated["owners"] = ownership(updated["installations"])
        for installation in updated["installations"].values():
            for output in installation["outputs"]:
                if "mode" not in output:
                    output["mode"] = plan["lifecycle"]["observed"][output["path"]]["mode"]
        updated["revision"] += 1
        payloads = {entry["path"]: files.get(entry["path"]) for entry in changed}
        payloads[LOCK] = canonical(updated) + b"\n"
        entries, directories = [], set()
        for index, (relative, data) in enumerate(payloads.items()):
            before = self.snapshot(relative)
            mode = before["mode"] if before else 0o644
            parent = self.ws.path(relative).parent
            while parent != self.ws.root and not parent.exists():
                directories.add(parent.relative_to(self.ws.root).as_posix())
                parent = parent.parent
            temporary = f"{self.ws.path(relative).parent.relative_to(self.ws.root).as_posix()}/.stratagent-{transaction_id}-{index}.tmp"
            if self.ws.path(temporary).exists():
                raise StratagentError("Transaction temporary path already exists.")
            entries.append({"path": relative, "before": before, "after": encoded(data, mode) if data is not None else None, "temporary": temporary})
        journal = {"schema_version": 1, "id": transaction_id, "workspace": str(self.ws.root), "state": "prepared", "approval": plan["approval"],
                   "stage_id": stage_id, "key": key, "entries": entries, "directories": sorted(directories, key=lambda name: (name.count("/"), name))}
        if len(canonical(journal)) > 15 * 1024 * 1024:
            raise StratagentError("Transaction journal exceeds its size limit.")
        if self.ws.path(JOURNAL).exists():
            previous = self.load_journal()
            self.ws.write(f".stratagent/transactions/{previous['id']}.json", previous)
        self._save_journal(journal)
        try:
            self.checkpoint("prepared")
            for relative in journal["directories"]:
                self.ws.path(relative).mkdir()
                self.ws.sync_directory(self.ws.path(relative).parent)
            journal["state"] = "writing"
            self._save_journal(journal)
            self.checkpoint("writing")
            for index, entry in enumerate(entries):
                self._write_entry(entry, "after")
                self.checkpoint(f"output:{index}" if entry["path"] != LOCK else "lock-committed")
            journal["state"] = "committed"
            self._save_journal(journal)
            self.checkpoint("committed")
        except BaseException:
            if summary(self.snapshot(LOCK)) != summary(entries[-1]["after"]):
                try:
                    self._rollback(journal)
                except (OSError, StratagentError):
                    raise StratagentError("Transaction interrupted and rollback could not finish; run stratagent recover. Backups are retained.") from None
            raise
        return {"applied": True, "approval": plan["approval"], "transaction_id": transaction_id,
                "written": [entry["path"] for entry in changed if entry["after"] is not None],
                "removed": [entry["path"] for entry in changed if entry["after"] is None], "lockfile": LOCK, "activation": "none"}

    def recovery(self, approval=None, apply=False):
        if apply:
            self.ws.fs.require_supported()
        if not self.ws.path(JOURNAL).exists():
            return {"pending": False}
        journal = self.load_journal()
        if journal["state"] in TERMINAL:
            return {"pending": False, "transaction_id": journal["id"], "state": journal["state"]}
        observed = {entry["path"]: summary(self.snapshot(entry["path"])) for entry in journal["entries"]}
        conflicts = [entry["path"] for entry in journal["entries"] if observed[entry["path"]] not in (summary(entry["before"]), summary(entry["after"]))]
        temporary = {entry["temporary"]: summary(self.snapshot(entry["temporary"])) for entry in journal["entries"]}
        conflicts.extend(entry["temporary"] for entry in journal["entries"] if not self._temporary_valid(entry))
        complete = all(observed[entry["path"]] == summary(entry["after"]) for entry in journal["entries"])
        committed_lock = observed[LOCK] == summary(journal["entries"][-1]["after"])
        if committed_lock and not complete:
            conflicts.append(LOCK)
        proposal = {"schema_version": 1, "pending": True, "transaction_id": journal["id"], "workspace": str(self.ws.root),
                    "journal_digest": journal["digest"], "observed": observed, "temporary": temporary,
                    "action": "finalize" if committed_lock else "rollback", "conflicts": conflicts}
        proposal["approval"] = identity(proposal)
        if not apply:
            return proposal
        if approval != proposal["approval"] or conflicts:
            raise StratagentError("Recovery approval is stale or files changed externally; no recovery writes permitted.")
        if committed_lock:
            self._clean(journal)
            journal["state"] = "committed"
            self._save_journal(journal)
        else:
            self._rollback(journal)
        return {"recovered": True, "transaction_id": journal["id"], "state": journal["state"], "activation": "none"}

    def history(self):
        directory = self.ws.path(".stratagent/transactions")
        paths = sorted(directory.glob("*.json")) if directory.exists() else []
        if len(paths) > 1000:
            raise StratagentError("Transaction history exceeds 1000 records; archive private history before listing.")
        records = []
        def append(record):
            records.append({"id": record["id"], "state": record["state"], "key": record["key"],
                            "approval": record["approval"], "stage_id": record["stage_id"]})
        for path in paths:
            append(self.ws.read(path.relative_to(self.ws.root).as_posix()))
        if self.ws.path(JOURNAL).exists():
            append(self.load_journal())
        return {"transactions": records}
