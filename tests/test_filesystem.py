import errno
import io
import json
import os
from pathlib import Path, PureWindowsPath
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

from stratagent.cli import main
from stratagent.common import StratagentError, safe_path
from stratagent.filesystem import LocalFilesystem
from stratagent.workspace import Workspace
from test_stratagent import file_state


class FilesystemTests(unittest.TestCase):
    def test_snapshot_keys_are_portable_even_for_windows_relative_paths(self):
        child = Mock()
        child.is_file.return_value = True
        child.relative_to.return_value = PureWindowsPath(".stratagent/runs/example.json")
        child.read_bytes.return_value = b"original"
        root = Mock()
        root.rglob.return_value = [child]
        with patch("test_stratagent.Path", return_value=root):
            self.assertEqual(file_state(root), {".stratagent/runs/example.json": b"original"})

    def test_capabilities_distinguish_durability_and_permission_models(self):
        posix = LocalFilesystem("posix").capabilities()
        windows = LocalFilesystem("nt").capabilities()
        self.assertEqual(posix["locking"], "flock")
        self.assertTrue(posix["directory_sync"])
        self.assertEqual(windows["locking"], "msvcrt-byte-range")
        self.assertFalse(windows["directory_sync"])
        self.assertEqual(windows["permission_model"], "windows-readonly-inherited-acl")
        self.assertFalse(windows["state_acl_managed"])
        for platform in ("posix", "nt"):
            self.assertTrue(LocalFilesystem(platform).capabilities()["local_transactions"])
            self.assertFalse(LocalFilesystem(platform).capabilities()["physical_power_loss_certified"])

    def test_unsupported_os_fails_closed(self):
        filesystem = LocalFilesystem("unsupported")
        self.assertFalse(filesystem.capabilities()["local_transactions"])
        with self.assertRaises(StratagentError):
            filesystem.require_supported()

    def test_windows_modes_are_readonly_attributes_not_fake_posix_permissions(self):
        filesystem = LocalFilesystem("nt")
        self.assertEqual(filesystem.mode(SimpleNamespace(st_mode=stat.S_IFREG | 0o666, st_file_attributes=0)), 0o644)
        self.assertEqual(filesystem.mode(SimpleNamespace(st_mode=stat.S_IFREG | 0o666, st_file_attributes=1)), 0o444)
        self.assertEqual(filesystem.mode(SimpleNamespace(st_mode=stat.S_IFREG | 0o444, st_file_attributes=0)), 0o444)
        self.assertEqual(LocalFilesystem("posix").mode(SimpleNamespace(st_mode=stat.S_IFREG | 0o600)), 0o600)

    def test_reparse_points_are_rejected_even_without_symlink_mode(self):
        path = Mock()
        path.lstat.return_value = SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_file_attributes=0x400)
        self.assertTrue(LocalFilesystem("nt").redirect(path))
        path.lstat.side_effect = FileNotFoundError()
        self.assertFalse(LocalFilesystem("nt").redirect(path))

    def test_special_windows_device_aliases_are_never_portable_paths(self):
        for relative in ("skills/CONIN$", "skills/conout$.md", "skills/NUL .txt", "skills/COM1 .md"):
            with self.subTest(relative=relative), self.assertRaises(StratagentError):
                safe_path(relative)

    def test_windows_only_retries_bounded_sharing_violations(self):
        error = PermissionError(errno.EACCES, "sharing violation")
        error.winerror = 32
        with patch("stratagent.filesystem.os.replace", side_effect=[error, error, None]) as replace, patch("stratagent.filesystem.time.sleep") as sleep:
            LocalFilesystem("nt").replace("source", "target")
        self.assertEqual(replace.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(0.05), call(0.1)])
        with patch("stratagent.filesystem.os.replace", side_effect=error) as replace, patch("stratagent.filesystem.time.sleep"):
            with self.assertRaises(PermissionError):
                LocalFilesystem("nt").replace("source", "target")
        self.assertEqual(replace.call_count, 4)
        for platform in ("posix", "nt"):
            denied = PermissionError(errno.EACCES, "permanent permission denial")
            denied.winerror = 5
            with patch("stratagent.filesystem.os.replace", side_effect=denied) as replace:
                with self.assertRaises(PermissionError):
                    LocalFilesystem(platform).replace("source", "target")
            self.assertEqual(replace.call_count, 1)

    def test_windows_mutex_uses_one_persistent_byte_and_releases_on_exception(self):
        with tempfile.TemporaryDirectory() as temporary:
            mutex = Path(temporary) / "mutex"
            runtime = SimpleNamespace(LK_NBLCK=2, LK_UNLCK=0, locking=Mock())
            with patch.dict(sys.modules, {"msvcrt": runtime}):
                with self.assertRaisesRegex(RuntimeError, "failure"):
                    with LocalFilesystem("nt").mutex(mutex):
                        raise RuntimeError("failure")
            self.assertEqual([entry.args[1:] for entry in runtime.locking.call_args_list], [(2, 1), (0, 1)])
            self.assertTrue(mutex.exists())
            self.assertEqual(mutex.stat().st_size, 0)

    def test_windows_mutex_contention_does_not_unlock_another_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = SimpleNamespace(LK_NBLCK=2, LK_UNLCK=0, locking=Mock(side_effect=OSError(errno.EACCES, "locked")))
            with patch.dict(sys.modules, {"msvcrt": runtime}):
                with self.assertRaisesRegex(StratagentError, "Another write"):
                    with LocalFilesystem("nt").mutex(Path(temporary) / "mutex"):
                        self.fail("Contended mutex entered")
            self.assertEqual(runtime.locking.call_count, 1)

    def test_doctor_reads_capabilities_without_initialization_or_writes(self):
        with tempfile.TemporaryDirectory() as temporary, patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(main(["doctor", "--workspace", temporary]), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["filesystem"]["os_family"], os.name)
            self.assertFalse(result["production_ready"])
            self.assertEqual(list(Path(temporary).iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Native Windows junction regression")
    def test_native_windows_junction_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            outside = Path(temporary) / "outside"
            root.mkdir()
            outside.mkdir()
            junction = root / "redirect"
            subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(junction), str(outside)], check=True, capture_output=True)
            try:
                with self.assertRaises(StratagentError):
                    Workspace(root).path("redirect/secret.txt")
                with self.assertRaises(StratagentError):
                    Workspace(junction)
            finally:
                junction.rmdir()
            self.assertFalse(list(outside.iterdir()))
