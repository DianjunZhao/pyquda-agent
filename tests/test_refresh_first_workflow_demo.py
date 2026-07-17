import json
import tempfile
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
            stdout = f"ok:{cmd[1] if len(cmd) > 1 else cmd[0]}"
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 8)
        self.assertEqual(calls[0][1], "scripts/refresh_pyquda_analysis.py")
        self.assertEqual(calls[1][1], "scripts/refresh_physics_citations.py")
        self.assertEqual(calls[2][1], "scripts/refresh_runtime_check.py")
        self.assertEqual(calls[3][1], "scripts/scan_runtime_candidates.py")
        self.assertEqual(calls[4][1:4], ["-m", "pyquda_agent.cli", "run"])
        self.assertIn("pi meson two-point", calls[4][4])
        self.assertIn("--dry-run", calls[4])
        self.assertIn("--result-format", calls[4])
        self.assertIn("summary", calls[4])
        self.assertEqual(calls[5][1:4], ["-m", "pyquda_agent.cli", "run"])
        self.assertIn("codex", calls[5])
        self.assertIn("--runtime-probe", calls[5])
        self.assertIn("--result-format", calls[5])
        self.assertIn("summary", calls[5])
        self.assertEqual(calls[6][1], "scripts/check_backend_parity.py")
        self.assertEqual(calls[7][1], "scripts/refresh_goal_audit.py")

    def test_demo_script_supports_dispersion_refresh(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            stdout = ""
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex", "--workflow", "pion_dispersion"])

        self.assertEqual(exit_code, 0)
        self.assertIn("pion dispersion with nonzero momentum", calls[4][4])
        self.assertIn("pion dispersion from gauge", calls[5][4])
        self.assertIn("--workflow", calls[6])
        self.assertIn("pion_dispersion", calls[6])

    def test_demo_script_supports_pcac_refresh(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            stdout = ""
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex", "--workflow", "pion_pcac"])

        self.assertEqual(exit_code, 0)
        self.assertIn("pion pcac ratio", calls[4][4])
        self.assertIn("pion pcac ratio from gauge", calls[5][4])
        self.assertIn("--workflow", calls[6])
        self.assertIn("pion_pcac", calls[6])

    def test_demo_script_supports_proton_refresh(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            stdout = ""
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex", "--workflow", "proton_2pt"])

        self.assertEqual(exit_code, 0)
        self.assertIn("proton two-point correlator", calls[4][4])
        self.assertIn("proton two-point correlator from gauge", calls[5][4])
        self.assertIn("--workflow", calls[6])
        self.assertIn("proton_2pt", calls[6])

    def test_demo_script_supports_rho_vector_refresh(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            stdout = ""
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex", "--workflow", "rho_vector"])

        self.assertEqual(exit_code, 0)
        self.assertIn("rho meson two-point correlator", calls[4][4])
        self.assertIn("rho meson two-point correlator from gauge", calls[5][4])
        self.assertIn("--workflow", calls[6])
        self.assertIn("rho_vector", calls[6])

    def test_demo_script_supports_meson_spec_refresh(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            stdout = ""
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex", "--workflow", "meson_spec"])

        self.assertEqual(exit_code, 0)
        self.assertIn("meson spectroscopy correlators", calls[4][4])
        self.assertIn("meson spectroscopy correlators from gauge", calls[5][4])
        self.assertIn("--workflow", calls[6])
        self.assertIn("meson_spec", calls[6])

    def test_demo_script_supports_wilson_flow_refresh(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            stdout = ""
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex", "--workflow", "wilson_flow"])

        self.assertEqual(exit_code, 0)
        self.assertIn("wilson flow on this gauge configuration", calls[4][4])
        self.assertIn("run wilson flow from gauge", calls[5][4])
        self.assertIn("--workflow", calls[6])
        self.assertIn("wilson_flow", calls[6])

    def test_demo_script_supports_quark_propagator_refresh(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            stdout = ""
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex", "--workflow", "quark_propagator"])

        self.assertEqual(exit_code, 0)
        self.assertIn("please generate a quark propagator", calls[4][4])
        self.assertIn("please generate a quark propagator from gauge", calls[5][4])
        self.assertIn(".h5", calls[5][4])
        self.assertIn("--workflow", calls[6])
        self.assertIn("quark_propagator", calls[6])

    def test_demo_script_supports_ape_smear_refresh(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            stdout = ""
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex", "--workflow", "ape_smear"])

        self.assertEqual(exit_code, 0)
        self.assertIn("APE-smeared gauge configuration", calls[4][4])
        self.assertIn("APE-smeared gauge from gauge", calls[5][4])
        self.assertIn("--workflow", calls[6])
        self.assertIn("ape_smear", calls[6])

    def test_demo_script_supports_hyp_smear_refresh(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            stdout = ""
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex", "--workflow", "hyp_smear"])

        self.assertEqual(exit_code, 0)
        self.assertIn("HYP-smeared gauge configuration", calls[4][4])
        self.assertIn("HYP-smeared gauge from gauge", calls[5][4])
        self.assertIn("--workflow", calls[6])
        self.assertIn("hyp_smear", calls[6])

    def test_demo_script_supports_stout_smear_refresh(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            stdout = ""
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "codex", "--workflow", "stout_smear"])

        self.assertEqual(exit_code, 0)
        self.assertIn("stout-smear this gauge configuration", calls[4][4])
        self.assertIn("stout-smeared gauge from gauge", calls[5][4])
        self.assertIn("--workflow", calls[6])
        self.assertIn("stout_smear", calls[6])

    def test_demo_script_ignores_local_runtime_failures_by_default(self):
        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        counter = {"n": 0}

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            counter["n"] += 1
            if counter["n"] in {3, 4}:
                return Completed(returncode=1, stderr="generation failed")
            stdout = ""
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                stdout = json.dumps(
                    {
                        "status": "ok",
                        "product_status": "generated_runtime_blocked",
                        "execution_status": "runtime_missing",
                        "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                        "generation_result": {"phase": "generated"},
                        "execution_result": {"phase": "runtime_missing"},
                        "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                    }
                )
            elif cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                stdout = json.dumps(
                    {
                        "status": "needs_input",
                        "product_status": "needs_input",
                        "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                        "generation_result": {"phase": "blocked_on_input"},
                        "execution_result": {"phase": "blocked_by_generation"},
                        "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                    }
                )
            return Completed(returncode=0, stdout=stdout)

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
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                return Completed(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "status": "ok",
                            "product_status": "generated_runtime_blocked",
                            "execution_status": "runtime_missing",
                            "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                            "generation_result": {"phase": "generated"},
                            "execution_result": {"phase": "runtime_missing"},
                            "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                        }
                    ),
                )
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                return Completed(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "status": "needs_input",
                            "product_status": "needs_input",
                            "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                            "generation_result": {"phase": "blocked_on_input"},
                            "execution_result": {"phase": "blocked_by_generation"},
                            "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                        }
                    ),
                )
            return Completed(returncode=0)

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "api", "--require-local-runtime-proof"])

        self.assertEqual(exit_code, 1)

    def test_demo_summary_keeps_product_facing_run_probe_fields(self):
        calls: list[list[str]] = []

        class Completed:
            def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            calls.append(list(cmd))
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"] and "--dry-run" not in cmd:
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                    encoding="utf-8",
                )
                return Completed(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "status": "ok",
                            "product_status": "generated_runtime_blocked",
                            "execution_status": "runtime_missing",
                            "workflow_outcome": {"phase": "generated_and_probed", "runtime_probe_status": "runtime_missing"},
                            "generation_result": {"phase": "generated"},
                            "execution_result": {"phase": "runtime_missing"},
                            "delivery_status": {"generation": {"phase": "generated"}, "execution": {"phase": "runtime_missing"}},
                        }
                    ),
                )
            if cmd[1:4] == ["-m", "pyquda_agent.cli", "run"]:
                return Completed(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "status": "needs_input",
                            "product_status": "needs_input",
                            "workflow_outcome": {"phase": "clarification", "runtime_probe_status": "pending_generation"},
                            "generation_result": {"phase": "blocked_on_input"},
                            "execution_result": {"phase": "blocked_by_generation"},
                            "delivery_status": {"generation": {"phase": "blocked_on_input"}, "execution": {"phase": "blocked_by_generation"}},
                        }
                    ),
                )
            return Completed(returncode=0, stdout="")

        with patch("scripts.refresh_first_workflow_demo.subprocess.run", side_effect=fake_run):
            with tempfile.TemporaryDirectory() as tmpdir:
                output = Path(tmpdir) / "outputs" / "run_pion_api.py"
                exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--backend", "api", "--script-output", str(output)])
                summary = json.loads((output.parent / "summary.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["preview_rough_request"]["product_status"], "needs_input")
        self.assertEqual(summary["preview_rough_request"]["generation_result"]["phase"], "blocked_on_input")
        self.assertEqual(summary["preview_rough_request"]["execution_result"]["phase"], "blocked_by_generation")
        self.assertEqual(summary["generate_workflow"]["product_status"], "generated_runtime_blocked")
        self.assertEqual(summary["generate_workflow"]["generation_result"]["phase"], "generated")
        self.assertEqual(summary["generate_workflow"]["execution_result"]["phase"], "runtime_missing")


if __name__ == "__main__":
    unittest.main()
