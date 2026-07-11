import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.scan_runtime_candidates import build_scan
from scripts.scan_runtime_candidates import main


class ScanRuntimeCandidatesTests(unittest.TestCase):
    def test_build_scan_reports_no_ready_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fake_python = root / "python"
            fake_python.write_text("", encoding="utf-8")

            class Completed:
                def __init__(self, returncode=1, stdout='{"ready": false}', stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            with patch("scripts.scan_runtime_candidates.subprocess.run", return_value=Completed()):
                report = build_scan([fake_python], root)

            self.assertFalse(report["any_ready"])
            self.assertEqual(len(report["interpreters"]), 2)
            self.assertEqual(report["interpreters"][0]["python"], str(fake_python))
            self.assertIn("resolved_python", report["interpreters"][0])

    def test_main_writes_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fake_python = root / "python"
            fake_python.write_text("", encoding="utf-8")
            output = root / "runtime_candidates.json"

            class Completed:
                def __init__(self, returncode=0, stdout='{"ready": true}', stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            with patch("scripts.scan_runtime_candidates.subprocess.run", return_value=Completed()):
                exit_code = main(
                    [
                        "--pyquda-repo",
                        str(root),
                        "--output",
                        str(output),
                        "--interpreters",
                        str(fake_python),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["any_ready"])
            self.assertEqual(payload["interpreters"][0]["python"], str(fake_python))


if __name__ == "__main__":
    unittest.main()
