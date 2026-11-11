import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "backup", Path(__file__).resolve().parents[1] / "tools/backup_factory.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "factory"
        self.size = 1024 * 1024
        self.calls = []

    def run_backup(self):
        module.backup("/dev/example-test-only", self.size, "Test fixture", self.output)

    def fake_read(self, cmd, check):
        self.assertTrue(check)
        self.assertIn("read-flash", cmd)
        self.assertNotIn("write-flash", cmd)
        self.calls.append(cmd)
        Path(cmd[-1]).write_bytes(b"A" * self.size)

    def test_matching_reads_and_no_overwrite(self):
        with patch.object(module.subprocess, "run", self.fake_read):
            self.run_backup()
            with self.assertRaises(FileExistsError):
                self.run_backup()
        self.assertEqual(len(self.calls), 2)
        self.assertIn("no-reset", self.calls[0])
        self.assertEqual(self.calls[1][self.calls[1].index("--before") + 1], "no-reset")
        self.assertEqual(self.calls[1][self.calls[1].index("--after") + 1], "hard-reset")
        record = json.loads((self.output / "VERIFIED.json").read_text())
        self.assertFalse(record["restoration_tested"])
        self.assertEqual(record["matching_reads"], 2)

    def test_mismatch_is_not_verified(self):
        def mismatch(cmd, check):
            self.fake_read(cmd, check)
            if len(self.calls) == 2:
                Path(cmd[-1]).write_bytes(b"B" * self.size)
        with patch.object(module.subprocess, "run", mismatch), self.assertRaises(ValueError):
            self.run_backup()
        self.assertFalse((self.output / "VERIFIED.json").exists())

    def test_short_read_is_not_verified(self):
        def short(cmd, check):
            Path(cmd[-1]).write_bytes(b"A")
        with patch.object(module.subprocess, "run", short), self.assertRaises(ValueError):
            self.run_backup()
        self.assertFalse((self.output / "VERIFIED.json").exists())

    def test_failed_read_is_not_verified(self):
        with patch.object(module.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "esptool")):
            with self.assertRaises(subprocess.CalledProcessError):
                self.run_backup()
        self.assertFalse((self.output / "VERIFIED.json").exists())


if __name__ == "__main__":
    unittest.main()
