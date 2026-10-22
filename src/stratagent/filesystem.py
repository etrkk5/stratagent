"""Local filesystem capabilities; OS details never enter the planning engine."""
import errno
import os
import stat
import time
from contextlib import contextmanager

from .common import StratagentError


class LocalFilesystem:
    def __init__(self, platform=None):
        self.platform = os.name if platform is None else platform

    def capabilities(self):
        supported = self.platform in ("posix", "nt")
        return {"schema_version": 1, "os_family": self.platform, "local_transactions": supported,
                "locking": "flock" if self.platform == "posix" else "msvcrt-byte-range" if self.platform == "nt" else "unsupported",
                "file_sync": supported, "atomic_replace": supported, "directory_sync": self.platform == "posix",
                "permission_model": "posix-mode" if self.platform == "posix" else "windows-readonly-inherited-acl" if self.platform == "nt" else "unsupported",
                "state_acl_managed": False, "physical_power_loss_certified": False, "network_filesystems_certified": False}

    def require_supported(self):
        if not self.capabilities()["local_transactions"]:
            raise StratagentError("Unsupported filesystem backend; local transactions require Windows, macOS or Linux.")

    def redirect(self, path):
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            return False
        return stat.S_ISLNK(metadata.st_mode) or bool(getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))

    def mode(self, metadata):
        if self.platform == "nt":
            readonly = getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_READONLY", 1)
            return 0o444 if readonly or not metadata.st_mode & stat.S_IWRITE else 0o644
        return stat.S_IMODE(metadata.st_mode)

    def set_mode(self, descriptor, mode):
        if self.platform == "posix":
            os.fchmod(descriptor, mode)

    def sync_directory(self, directory):
        if self.platform == "posix":
            descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def replace(self, source, destination):
        for attempt in range(4):
            try:
                os.replace(source, destination)
                return
            except OSError as exc:
                if self.platform != "nt" or getattr(exc, "winerror", None) not in (32, 33) or attempt == 3:
                    raise
                time.sleep(0.05 * (2 ** attempt))

    @contextmanager
    def mutex(self, path):
        self.require_supported()
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        descriptor = os.open(path, flags, 0o600)
        locked = False
        try:
            if self.redirect(path) or not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise StratagentError("Workspace mutation lock must be a regular, non-redirected file.")
            try:
                if self.platform == "posix":
                    import fcntl
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    import msvcrt
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                locked = True
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise StratagentError("Another write is active; no changes made.") from exc
                raise
            yield
        finally:
            try:
                if locked and self.platform == "nt":
                    import msvcrt
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            finally:
                os.close(descriptor)
