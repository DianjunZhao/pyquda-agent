import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_backend_parity import build_report
from scripts.check_backend_parity import main


class CheckBackendParityTests(unittest.TestCase):
    def test_build_report_detects_identical_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            api_script = root / "run_pion_api.py"
            codex_script = root / "run_pion_codex.py"
            api_script.write_text("CORRELATOR_OUTPUT = Path('/tmp/api.npy')\n", encoding="utf-8")
            codex_script.write_text("CORRELATOR_OUTPUT = Path('/tmp/codex.npy')\n", encoding="utf-8")
            (root / "run_pion_api.task.json").write_text(
                json.dumps(
                    {
                        "correlator_output_path": "/tmp/api.npy",
                        "script_output_path": "/tmp/api.py",
                        "notes": "api request",
                    }
                ),
                encoding="utf-8",
            )
            (root / "run_pion_codex.task.json").write_text(
                json.dumps(
                    {
                        "correlator_output_path": "/tmp/codex.npy",
                        "script_output_path": "/tmp/codex.py",
                        "notes": "codex request",
                    }
                ),
                encoding="utf-8",
            )
            (root / "run_pion_api.plan.json").write_text(
                json.dumps({"runtime_choices": {"correlator_output_path": "/tmp/api.npy", "script_output_path": "/tmp/api.py"}}),
                encoding="utf-8",
            )
            (root / "run_pion_codex.plan.json").write_text(
                json.dumps(
                    {"runtime_choices": {"correlator_output_path": "/tmp/codex.npy", "script_output_path": "/tmp/codex.py"}}
                ),
                encoding="utf-8",
            )

            class Completed:
                def __init__(self, returncode=0, stdout="", stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            report = build_report(root, Completed(), Completed())
            self.assertTrue(report["comparisons"]["script"]["identical"])
            self.assertTrue(report["comparisons"]["task"]["identical"])
            self.assertTrue(report["comparisons"]["plan"]["identical"])

    def test_main_writes_report(self):
        class Completed:
            def __init__(self, returncode=0, stdout="", stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run_backend(backend, pyquda_repo, script_output, correlator_output, resource_path):
            script_output.write_text(f"CORRELATOR_OUTPUT = Path('{correlator_output}')\n", encoding="utf-8")
            script_output.with_suffix(".task.json").write_text(
                json.dumps(
                    {
                        "correlator_output_path": str(correlator_output),
                        "script_output_path": str(script_output),
                        "notes": backend,
                    }
                ),
                encoding="utf-8",
            )
            script_output.with_suffix(".plan.json").write_text(
                json.dumps(
                    {
                        "runtime_choices": {
                            "correlator_output_path": str(correlator_output),
                            "script_output_path": str(script_output),
                        }
                    }
                ),
                encoding="utf-8",
            )
            return Completed(returncode=0, stdout=backend)

        with tempfile.TemporaryDirectory() as tmpdir:
            report = Path(tmpdir) / "parity.json"
            output_dir = Path(tmpdir) / "outputs"
            with patch("scripts.check_backend_parity._run_backend", side_effect=fake_run_backend):
                exit_code = main(
                    [
                        "--pyquda-repo",
                        "/tmp/PyQUDA",
                        "--output-dir",
                        str(output_dir),
                        "--report",
                        str(report),
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["api"]["stdout"], "api")
            self.assertTrue(payload["comparisons"]["script"]["identical"])


if __name__ == "__main__":
    unittest.main()
