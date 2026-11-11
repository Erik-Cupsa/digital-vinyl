import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "project", Path(__file__).resolve().parents[1] / "tools/project.py")
project = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project)


class UploadGateTest(unittest.TestCase):
    def test_missing_backup_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                project.verified_backup(tmp)

    def test_matching_backup_accepted_but_corruption_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            binary = folder / "factory.bin"
            payload = b"A" * 16777216
            binary.write_bytes(payload)
            record = {"bytes":len(payload),"matching_reads":2,
                      "sha256":hashlib.sha256(payload).hexdigest()}
            (folder / "VERIFIED.json").write_text(json.dumps(record))
            self.assertEqual(project.verified_backup(folder), binary)
            with binary.open("r+b") as stream:
                stream.write(b"B")
            with self.assertRaises(RuntimeError):
                project.verified_backup(folder)
            binary.write_bytes(b"A")
            with self.assertRaises(RuntimeError):
                project.verified_backup(folder)

    def test_single_read_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "VERIFIED.json").write_text(json.dumps({"matching_reads":1}))
            with self.assertRaises(RuntimeError):
                project.verified_backup(folder)
