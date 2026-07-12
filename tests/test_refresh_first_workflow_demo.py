import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.refresh_first_workflow_demo import main


class RefreshFirstWorkflowDemoTests(unittest.TestCase):
    def test_demo_script_runs_expected_steps_with_backend(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            return Completed(returncode=0, stdout=f"ok:{cmd[1] if len(cmd) > 1 else cmd[0]}")

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 8)
        self.assertEqual(calls[0][1], "scripts/refresh_pyquda_analysis.py")
        self.assertEqual(calls[1][1], "scripts/refresh_physics_citations.py")
        self.assertEqual(calls[2][1], "scripts/refresh_runtime_check.py")
        self.assertEqual(calls[3][1], "scripts/scan_runtime_candidates.py")
        self.assertEqual(calls[4][1:4], ["-m", "pyquda_agent.cli", "run"])
        self.assertIn("codex", calls[4])
        self.assertEqual(calls[5][1], "scripts/probe_generated_workflow.py")
        self.assertEqual(calls[6][1], "scripts/check_backend_parity.py")
        self.assertEqual(calls[7][1], "scripts/refresh_goal_audit.py")

    def test_demo_script_ignores_local_runtime_failures_by_default(self):
        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        counter = {"n": 0}

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            counter["n"] += 1
            if counter["n"] in {3, 4, 6}:
                return Completed(returncode=1, stderr="generation failed")
            return Completed(returncode=0)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "api"])

        self.assertEqual(exit_code, 0)

    def test_demo_script_can_require_local_runtime_proof(self):
        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        counter = {"n": 0}

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            counter["n"] += 1
            if counter["n"] == 3:
                return Completed(returncode=1, stderr="runtime missing")
            return Completed(returncode=0)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "api", "--require-local-runtime-proof"])

        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
