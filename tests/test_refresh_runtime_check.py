import json
import tempfile
import unittest
from pathlib import Path

from scripts.refresh_runtime_check import main


class RefreshRuntimeCheckTests(unittest.TestCase):
    def test_refresh_runtime_check_writes_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "runtime.json"
            exit_code = main(["--pyquda-repo", tmpdir, "--output", str(output)])
            self.assertNotEqual(exit_code, 0)
            self.assertTrue(output.exists())
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("checks", payload)
            self.assertIn("ready", payload)


if __name__ == "__main__":
    unittest.main()
