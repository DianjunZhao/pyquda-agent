import json
import tempfile
import unittest
from pathlib import Path

from scripts.probe_generated_workflow import build_probe
from scripts.probe_generated_workflow import main


class ProbeGeneratedWorkflowTests(unittest.TestCase):
    def test_build_probe_captures_runtime_missing_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "run.py"
            script_path.write_text(
                "raise SystemExit(\"Missing runtime dependency 'cupy'. Activate a PyQUDA environment first.\")\n",
                encoding="utf-8",
            )
            artifact = build_probe(script_path, timeout=5.0)
            self.assertEqual(artifact["status"], "runtime_missing")
            self.assertNotEqual(artifact["returncode"], 0)
            self.assertIn("cupy", artifact["stderr"] or artifact["stdout"])

    def test_main_writes_probe_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "run.py"
            output_path = Path(tmpdir) / "probe.json"
            script_path.write_text("print('ok')\n", encoding="utf-8")
            exit_code = main(["--script", str(script_path), "--output", str(output_path), "--timeout", "5"])
            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["returncode"], 0)

    def test_build_probe_records_repo_pythonpath_usage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "run.py"
            repo_path = Path(tmpdir) / "PyQUDA"
            output_path = Path(tmpdir) / "probe.json"
            repo_path.mkdir()
            script_path.write_text("print('ok')\n", encoding="utf-8")
            exit_code = main(
                [
                    "--script",
                    str(script_path),
                    "--output",
                    str(output_path),
                    "--timeout",
                    "5",
                    "--pyquda-repo",
                    str(repo_path),
                    "--use-repo-pythonpath",
                ]
            )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["used_repo_pythonpath"])
            self.assertEqual(payload["pyquda_repo"], str(repo_path.resolve()))


if __name__ == "__main__":
    unittest.main()
