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
            (root / "run_pion_api.physics.json").write_text(
                json.dumps({"user_request": "api request", "normalized_request": "api normalized"}),
                encoding="utf-8",
            )
            (root / "run_pion_codex.physics.json").write_text(
                json.dumps({"user_request": "codex request", "normalized_request": "codex normalized"}),
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
            (root / "run_pion_api.probe.json").write_text(
                json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                encoding="utf-8",
            )
            (root / "run_pion_codex.probe.json").write_text(
                json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
                encoding="utf-8",
            )

            class Completed:
                def __init__(self, returncode=0, stdout="", stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            report = build_report(root, Completed(), Completed(), "pion_2pt")
            self.assertTrue(report["comparisons"]["script"]["identical"])
            self.assertTrue(report["comparisons"]["physics"]["identical"])
            self.assertTrue(report["comparisons"]["task"]["identical"])
            self.assertTrue(report["comparisons"]["plan"]["identical"])
            self.assertTrue(report["comparisons"]["probe"]["identical"])
            self.assertTrue(report["equivalence"]["implementation_equivalent"])

    def test_main_writes_report(self):
        class Completed:
            def __init__(self, returncode=0, stdout="", stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run_backend(backend, pyquda_repo, script_output, correlator_output, resource_path, workflow, api_model):
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
            script_output.with_suffix(".physics.json").write_text(
                json.dumps({"user_request": backend, "normalized_request": backend}),
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
            script_output.with_suffix(".probe.json").write_text(
                json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
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
            self.assertEqual(payload["workflow"], "pion_2pt")
            self.assertTrue(payload["comparisons"]["script"]["identical"])
            self.assertTrue(payload["comparisons"]["physics"]["identical"])
            self.assertTrue(payload["equivalence"]["implementation_equivalent"])

    def test_main_supports_quark_propagator_workflow(self):
        class Completed:
            def __init__(self, returncode=0, stdout="", stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        seen_outputs = []

        def fake_run_backend(backend, pyquda_repo, script_output, correlator_output, resource_path, workflow, api_model):
            seen_outputs.append((workflow, str(script_output), str(correlator_output)))
            script_output.write_text(f"PROPAGATOR_OUTPUT = Path('{correlator_output}')\n", encoding="utf-8")
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
            script_output.with_suffix(".physics.json").write_text(
                json.dumps({"user_request": backend, "normalized_request": backend}),
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
            script_output.with_suffix(".probe.json").write_text(
                json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
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
                        "--workflow",
                        "quark_propagator",
                        "--output-dir",
                        str(output_dir),
                        "--report",
                        str(report),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(all(item[0] == "quark_propagator" for item in seen_outputs))
            self.assertTrue(all(item[1].endswith("run_quark_propagator_api.py") or item[1].endswith("run_quark_propagator_codex.py") for item in seen_outputs))
            self.assertTrue(all(item[2].endswith(".h5") for item in seen_outputs))

    def test_main_supports_wilson_flow_workflow(self):
        class Completed:
            def __init__(self, returncode=0, stdout="", stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        seen_outputs = []

        def fake_run_backend(backend, pyquda_repo, script_output, correlator_output, resource_path, workflow, api_model):
            seen_outputs.append((workflow, str(script_output), str(correlator_output)))
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
            script_output.with_suffix(".physics.json").write_text(
                json.dumps({"user_request": backend, "normalized_request": backend}),
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
            script_output.with_suffix(".probe.json").write_text(
                json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
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
                        "--workflow",
                        "wilson_flow",
                        "--output-dir",
                        str(output_dir),
                        "--report",
                        str(report),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(all(item[0] == "wilson_flow" for item in seen_outputs))
            self.assertTrue(all(item[1].endswith("run_wilson_flow_api.py") or item[1].endswith("run_wilson_flow_codex.py") for item in seen_outputs))
            self.assertTrue(all(item[2].endswith(".npy") for item in seen_outputs))

    def test_main_supports_ape_smear_workflow(self):
        class Completed:
            def __init__(self, returncode=0, stdout="", stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        seen_outputs = []

        def fake_run_backend(backend, pyquda_repo, script_output, correlator_output, resource_path, workflow, api_model):
            seen_outputs.append((workflow, str(script_output), str(correlator_output)))
            script_output.write_text(f"SMEARED_GAUGE_OUTPUT = Path('{correlator_output}')\n", encoding="utf-8")
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
            script_output.with_suffix(".physics.json").write_text(
                json.dumps({"user_request": backend, "normalized_request": backend}),
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
            script_output.with_suffix(".probe.json").write_text(
                json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
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
                        "--workflow",
                        "ape_smear",
                        "--output-dir",
                        str(output_dir),
                        "--report",
                        str(report),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(all(item[0] == "ape_smear" for item in seen_outputs))
            self.assertTrue(all(item[1].endswith("run_ape_smear_api.py") or item[1].endswith("run_ape_smear_codex.py") for item in seen_outputs))
            self.assertTrue(all(item[2].endswith(".npy") for item in seen_outputs))

    def test_main_supports_rho_vector_workflow(self):
        class Completed:
            def __init__(self, returncode=0, stdout="", stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        seen_outputs = []

        def fake_run_backend(backend, pyquda_repo, script_output, correlator_output, resource_path, workflow, api_model):
            seen_outputs.append((workflow, str(script_output), str(correlator_output)))
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
            script_output.with_suffix(".physics.json").write_text(
                json.dumps({"user_request": backend, "normalized_request": backend}),
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
            script_output.with_suffix(".probe.json").write_text(
                json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
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
                        "--workflow",
                        "rho_vector",
                        "--output-dir",
                        str(output_dir),
                        "--report",
                        str(report),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(all(item[0] == "rho_vector" for item in seen_outputs))
            self.assertTrue(all(item[1].endswith("run_rho_vector_api.py") or item[1].endswith("run_rho_vector_codex.py") for item in seen_outputs))
            self.assertTrue(all(item[2].endswith(".npy") for item in seen_outputs))

    def test_main_supports_hyp_smear_workflow(self):
        class Completed:
            def __init__(self, returncode=0, stdout="", stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        seen_outputs = []

        def fake_run_backend(backend, pyquda_repo, script_output, correlator_output, resource_path, workflow, api_model):
            seen_outputs.append((workflow, str(script_output), str(correlator_output)))
            script_output.write_text(f"SMEARED_GAUGE_OUTPUT = Path('{correlator_output}')\n", encoding="utf-8")
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
            script_output.with_suffix(".physics.json").write_text(
                json.dumps({"user_request": backend, "normalized_request": backend}),
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
            script_output.with_suffix(".probe.json").write_text(
                json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
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
                        "--workflow",
                        "hyp_smear",
                        "--output-dir",
                        str(output_dir),
                        "--report",
                        str(report),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(all(item[0] == "hyp_smear" for item in seen_outputs))
            self.assertTrue(all(item[1].endswith("run_hyp_smear_api.py") or item[1].endswith("run_hyp_smear_codex.py") for item in seen_outputs))
            self.assertTrue(all(item[2].endswith(".npy") for item in seen_outputs))

    def test_main_supports_stout_smear_workflow(self):
        class Completed:
            def __init__(self, returncode=0, stdout="", stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        seen_outputs = []

        def fake_run_backend(backend, pyquda_repo, script_output, correlator_output, resource_path, workflow, api_model):
            seen_outputs.append((workflow, str(script_output), str(correlator_output)))
            script_output.write_text(f"SMEARED_GAUGE_OUTPUT = Path('{correlator_output}')\n", encoding="utf-8")
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
            script_output.with_suffix(".physics.json").write_text(
                json.dumps({"user_request": backend, "normalized_request": backend}),
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
            script_output.with_suffix(".probe.json").write_text(
                json.dumps({"status": "runtime_missing", "runtime_level": "environment_missing"}),
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
                        "--workflow",
                        "stout_smear",
                        "--output-dir",
                        str(output_dir),
                        "--report",
                        str(report),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(all(item[0] == "stout_smear" for item in seen_outputs))
            self.assertTrue(all(item[1].endswith("run_stout_smear_api.py") or item[1].endswith("run_stout_smear_codex.py") for item in seen_outputs))
            self.assertTrue(all(item[2].endswith(".npy") for item in seen_outputs))


if __name__ == "__main__":
    unittest.main()
