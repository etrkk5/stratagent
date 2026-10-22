"""Local state and rollback-safe writes. Never follow workspace symlinks."""
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .common import StratagentError, safe_path


class Workspace:
    def __init__(self, root):
        raw = Path(root).absolute()
        if raw.is_symlink():
            raise StratagentError("Workspace root cannot be a symlink.")
        self.root = raw.resolve()
        if not self.root.is_dir():
            raise StratagentError("Workspace directory does not exist; create it first.")

    def path(self, relative):
        safe_path(relative)
        current = self.root
        for part in Path(relative).parts:
            current = current / part
            if current.is_symlink():
                raise StratagentError(f"Symlinks are forbidden: {relative}")
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
        path = self.path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".stratagent-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=True, indent=2, sort_keys=True)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            self.path(relative)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    @contextmanager
    def mutation(self):
        state = self.path(".stratagent")
        state.mkdir(exist_ok=True)
        lock = self.path(".stratagent/.write-lock")
        if os.name == "posix":
            import fcntl
            if lock.exists():
                raise StratagentError("Another write is active (or a legacy .stratagent/.write-lock exists); inspect it before retrying.")
            mutex = self.path(".stratagent/.mutation-lock")
            descriptor = os.open(mutex, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise StratagentError("Workspace mutation lock must be a regular file.")
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise StratagentError("Another write is active; no changes made.") from exc
                yield
            finally:
                os.close(descriptor)
            return
        try:
            lock.mkdir()
        except FileExistsError as exc:
            raise StratagentError("Another write is active (or stale .stratagent/.write-lock); no changes made.") from exc
        try:
            yield
        finally:
            lock.rmdir()

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
