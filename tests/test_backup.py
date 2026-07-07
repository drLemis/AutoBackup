"""Smoke tests for AutoBackup core logic (no UI)."""
import os
import sys
import tempfile
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set non-interactive mode for testing
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# Need to set up locale before importing AutoBackup
from locale_util import init_locale
init_locale("en")

# pylint: disable=wrong-import-position,protected-access
from AutoBackup import (
    BackupHandler, APP_VERSION, load_prefs, save_prefs,
    is_inside, format_size, folder_size, hide_file,
    _EXCLUDED_EXTS, _EXCLUDED_NAMES, _EXCLUDED_DIRS,
    TS_FORMAT, QUIET_SECONDS,
)
import unittest


class TestUtils(unittest.TestCase):
    def test_format_size_bytes(self):
        self.assertEqual(format_size(500), "500 B")

    def test_format_size_kb(self):
        self.assertEqual(format_size(2048), "2.0 KB")

    def test_format_size_mb(self):
        self.assertEqual(format_size(1048576 * 3), "3.0 MB")

    def test_format_size_gb(self):
        self.assertEqual(format_size(1073741824 * 2), "2.00 GB")

    def test_is_inside_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = os.path.join(tmp, "parent")
            child = os.path.join(parent, "child")
            os.makedirs(child)
            self.assertTrue(is_inside(child, parent))

    def test_is_inside_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a")
            b = os.path.join(tmp, "b")
            os.makedirs(a)
            os.makedirs(b)
            self.assertFalse(is_inside(a, b))

    def test_is_inside_same(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(is_inside(tmp, tmp))

    def test_folder_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.txt").write_text("hello", encoding="ascii")
            Path(tmp, "b.txt").write_text("world", encoding="ascii")
            size = folder_size(tmp)
            self.assertGreater(size, 0)


class TestExclusions(unittest.TestCase):
    def test_excluded_extensions(self):
        for ext in [".tmp", ".temp", ".bak", ".swp", ".lock", ".part"]:
            self.assertIn(ext, _EXCLUDED_EXTS)

    def test_excluded_names(self):
        for name in ["thumbs.db", ".ds_store", "desktop.ini"]:
            self.assertIn(name, _EXCLUDED_NAMES)

    def test_excluded_dirs(self):
        for name in [".git", "node_modules", "__pycache__"]:
            self.assertIn(name, _EXCLUDED_DIRS)

    def test_is_excluded_ext(self):
        handler = BackupHandler.__new__(BackupHandler)
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, "test.tmp")
            f.write_text("x", encoding="ascii")
            self.assertTrue(handler._is_excluded(f))

    def test_is_excluded_tilde(self):
        handler = BackupHandler.__new__(BackupHandler)
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, "backup~")
            f.write_text("x", encoding="ascii")
            self.assertTrue(handler._is_excluded(f))

    def test_is_excluded_office_lock(self):
        handler = BackupHandler.__new__(BackupHandler)
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, "~$document.docx")
            f.write_text("x", encoding="ascii")
            self.assertTrue(handler._is_excluded(f))

    def test_is_not_excluded_normal(self):
        handler = BackupHandler.__new__(BackupHandler)
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, "report.docx")
            f.write_text("x", encoding="ascii")
            self.assertFalse(handler._is_excluded(f))

    def test_is_not_excluded_psd(self):
        handler = BackupHandler.__new__(BackupHandler)
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, "design.psd")
            f.write_text("x", encoding="ascii")
            self.assertFalse(handler._is_excluded(f))


class TestFingerprint(unittest.TestCase):
    def test_fingerprint_consistency(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, "test.txt")
            f.write_text("hello world", encoding="ascii")
            fp1 = BackupHandler._fingerprint(f)
            time.sleep(0.01)
            fp2 = BackupHandler._fingerprint(f)
            self.assertEqual(fp1, fp2)

    def test_fingerprint_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, "test.txt")
            f.write_text("hello", encoding="ascii")
            fp1 = BackupHandler._fingerprint(f)
            time.sleep(0.01)
            f.write_text("hello world", encoding="ascii")
            fp2 = BackupHandler._fingerprint(f)
            self.assertNotEqual(fp1, fp2)


class TestBackupNaming(unittest.TestCase):
    def test_backup_name_format(self):
        name = BackupHandler._make_backup_name("photo.psd", "20260526_231551")
        self.assertEqual(name, "photo_20260526_231551.psd")

    def test_backup_name_no_ext(self):
        name = BackupHandler._make_backup_name("README", "20260526_231551")
        self.assertEqual(name, "README_20260526_231551")

    def test_backup_name_multi_dot(self):
        name = BackupHandler._make_backup_name("archive.tar.gz", "20260526_231551")
        self.assertEqual(name, "archive.tar_20260526_231551.gz")

    def test_is_backup_of(self):
        self.assertTrue(BackupHandler._is_backup_of("photo_20260526_231551.psd", "photo.psd"))

    def test_is_not_backup_of_wrong_name(self):
        self.assertFalse(BackupHandler._is_backup_of("other_20260526_231551.psd", "photo.psd"))

    def test_is_not_backup_of_wrong_ext(self):
        self.assertFalse(BackupHandler._is_backup_of("photo_20260526_231551.png", "photo.psd"))

    def test_is_backup_of_no_ext(self):
        self.assertTrue(BackupHandler._is_backup_of("README_20260526_231551", "README"))


class TestQuickHash(unittest.TestCase):
    def test_hash_small_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, "test.txt")
            f.write_text("hello world", encoding="ascii")
            h1 = BackupHandler._quick_hash(f)
            h2 = BackupHandler._quick_hash(f)
            self.assertEqual(h1, h2)

    def test_hash_different_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp, "a.txt")
            b = Path(tmp, "b.txt")
            a.write_text("hello", encoding="ascii")
            b.write_text("world", encoding="ascii")
            self.assertNotEqual(BackupHandler._quick_hash(a), BackupHandler._quick_hash(b))

    def test_hash_large_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, "large.bin")
            f.write_bytes(b"x" * (1024 * 1024 * 4 + 123))
            h = BackupHandler._quick_hash(f)
            self.assertIsInstance(h, str)
            self.assertEqual(len(h), 32)


class TestVersion(unittest.TestCase):
    def test_version_format(self):
        parts = APP_VERSION.split(".")
        self.assertEqual(len(parts), 3)
        for p in parts:
            int(p)


if __name__ == "__main__":
    unittest.main()
