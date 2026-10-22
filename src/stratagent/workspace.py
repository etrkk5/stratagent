"""Local state and rollback-safe writes. Never follow workspace symlinks."""
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .common import StratagentError, safe_path
from .filesystem import LocalFilesystem


class Workspace:
    def __init__(self, root):
        self.fs = LocalFilesystem()
        raw = Path(root).absolute()
        if self.fs.redirect(raw) or (self.fs.platform == "nt" and any(self.fs.redirect(parent) for parent in raw.parents)):
            raise StratagentError("Workspace root cannot use symlinks, junctions or reparse points.")
        self.root = raw.resolve()
        if not self.root.is_dir():
            raise StratagentError("Workspace directory does not exist; create it first.")

    def path(self, relative):
        safe_path(relative)
        current = self.root
        for part in Path(relative).parts:
            current = current / part
            if self.fs.redirect(current):
                raise StratagentError(f"Symlinks, junctions and reparse points are forbidden: {relative}")
            if current.exists() and current != self.root / relative and not current.is_dir():
                raise StratagentError(f"Parent is not a directory: {relative}")
        return current

    def read(self, relative, default=None):
        path = self.path(relative)
        if not path.exists() and default is not None:
            return default
        if path.stat().st_size > 16 * 1024 * 1024:
            raise StratagentError("State file exceeds 16 MiB limit.")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise StratagentError(f"Invalid JSON state: {relative}") from exc

    def write(self, relative, value):
        self.atomic_bytes(relative, json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True).encode() + b"\n")

    def sync_directory(self, directory):
        self.fs.sync_directory(directory)

    def checkpoint(self, relative, event):
        """Internal IO fault boundary; never configured by external content."""

    def atomic_bytes(self, relative, data, mode=0o600, temporary=None):
        self.fs.require_supported()
        path = self.path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        if temporary is None:
            descriptor, temporary_path = tempfile.mkstemp(prefix=".stratagent-", dir=path.parent)
        else:
            temporary_path = self.path(temporary)
            descriptor = os.open(temporary_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                self.fs.set_mode(handle.fileno(), mode)
                handle.write(data)
                handle.flush()
                self.checkpoint(relative, "temporary-written")
                os.fsync(handle.fileno())
                self.checkpoint(relative, "temporary-synced")
            self.path(relative)
            self.fs.replace(temporary_path, path)
            self.checkpoint(relative, "replaced")
            self.sync_directory(path.parent)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    @contextmanager
    def mutation(self, recovery=False):
        def check_transaction():
            journal = ".stratagent/transaction.json"
            if not recovery and self.path(journal).exists():
                from .lifecycle import Transactions
                if Transactions(self).pending():
                    raise StratagentError("An environment transaction needs recovery; run stratagent recover before any other write.")

        state = self.path(".stratagent")
        state.mkdir(exist_ok=True)
        lock = self.path(".stratagent/.write-lock")
        if lock.exists():
            raise StratagentError("Another write is active (or a legacy .stratagent/.write-lock exists); inspect it before retrying.")
        with self.fs.mutex(self.path(".stratagent/.mutation-lock")):
            check_transaction()
            yield

    def create_files(self, files):
        """Preflight the whole transaction; refuse overwrites, even identical files."""
        for name in files:
            if self.path(name).exists():
                raise StratagentError(f"Refusing to overwrite existing file: {name}")
        created = []
        try:
            for name, data in files.items():
                path = self.path(name)
                path.parent.mkdir(parents=True, exist_ok=True)
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
                with os.fdopen(os.open(path, flags, 0o644), "wb") as f:
                    created.append(name)
                    f.write(data)
            return created
        except BaseException:
            for name in reversed(created):
                self.path(name).unlink()
            raise
