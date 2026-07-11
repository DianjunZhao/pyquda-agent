import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pyquda_agent.cli import main


class CliRunTests(unittest.TestCase):
    def _prepare_repo_fixture(self, root: Path) -> tuple[Path, Path, Path]:
        pyquda = root / "PyQUDA"
        output = root / "outputs" / "run_pion.py"
        index_path = root / "data" / "pyquda_index.json"

        (root / "data").mkdir(parents=True)
        (root / "docs").mkdir(parents=True)
        (pyquda / "examples").mkdir(parents=True)
        (pyquda / "tests").mkdir(parents=True)
        (pyquda / "pyquda_utils").mkdir(parents=True)
        (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

        (root / "docs" / "RUNNABLE_PION_2PT_SPEC.md").write_text("pion helper", encoding="utf-8")
        (root / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
        (root / "docs" / "RUN_WORKFLOW.md").write_text("workflow", encoding="utf-8")

        (pyquda / "examples" / "3_Pion_Proton_2pt.py").write_text("pion example", encoding="utf-8")
        (pyquda / "examples" / "5_Pion_Dispersion.py").write_text("dispersion", encoding="utf-8")
        (pyquda / "tests" / "test_mesonspec.py").write_text("mesonspec", encoding="utf-8")
        (pyquda / "tests" / "test_io.py").write_text("io test", encoding="utf-8")
        (pyquda / "pyquda_utils" / "source.py").write_text("wall source", encoding="utf-8")
        (pyquda / "pyquda_utils" / "core.py").write_text("invert core", encoding="utf-8")
        (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma", encoding="utf-8")
        (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge", encoding="utf-8")

        index_path.write_text(json.dumps({"summary": {"file_count": 3}}), encoding="utf-8")
        return pyquda, output, index_path

    def test_cli_run_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with redirect_stdout(stdout):
                    exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "dry_run")
            self.assertEqual(payload["pipeline"][0], "structured_task_spec")
            self.assertEqual(payload["task"]["script_output_path"], str(output.resolve()))
            self.assertEqual(payload["task"]["correlator_output_format"], "npy")
            self.assertEqual(payload["task"]["cluster_launch"], "local")
            self.assertTrue(payload["task_artifact"].endswith(".task.json"))
            self.assertTrue(payload["plan_artifact"].endswith(".plan.json"))
            self.assertTrue(Path(payload["task_artifact"]).exists())
            self.assertTrue(Path(payload["plan_artifact"]).exists())
            self.assertEqual(payload["context"]["index_summary"]["file_count"], 3)
            self.assertTrue(any(ref["path"].endswith("pyquda_utils/io/__init__.py") for ref in payload["implementation_plan"]["references"]))
            self.assertTrue(payload["implementation_plan"]["external_citations"])
            self.assertTrue(payload["implementation_plan"]["convention_decisions"])
            self.assertTrue(any(item["category"] == "physics" for item in payload["implementation_plan"]["convention_decisions"]))
            self.assertIn("runtime_readiness", payload["implementation_plan"])
            self.assertFalse(payload["implementation_plan"]["runtime_readiness"]["ready"])
            self.assertTrue(any("arxiv.org" in citation["url"] for citation in payload["implementation_plan"]["external_citations"]))
            task_artifact = json.loads(Path(payload["task_artifact"]).read_text(encoding="utf-8"))
            plan_artifact = json.loads(Path(payload["plan_artifact"]).read_text(encoding="utf-8"))
            self.assertEqual(task_artifact["workflow_id"], "pion_2pt_chroma_wall_local_zero_momentum_npy_v1")
            self.assertEqual(plan_artifact["workflow_id"], "pion_2pt_chroma_wall_local_zero_momentum_npy_v1")
            self.assertIn("runtime_readiness", plan_artifact)

    def test_cli_run_rejects_unsupported_existing_propagator_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete pion 2pt from existing propagator /tmp/pion_prop.npy outputs/run_pion.py",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with redirect_stdout(stdout):
                    exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "unsupported")
            self.assertTrue(payload["implementation_plan"]["unsupported_reasons"])

    def test_cli_run_complete_generation_supports_api_backend_without_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--backend",
                "api",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with redirect_stdout(stdout):
                    exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["generation"]["used_backend"], "api")

    def test_cli_run_complete_mode_stops_for_missing_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 outputs/pion.npy outputs/run_pion.py cluster_launch=local",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with redirect_stdout(stdout):
                    exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertIn("mass", payload["missing_fields"])
            self.assertNotIn("generation", payload)
            self.assertEqual(
                payload["next_action"],
                "Resolve missing fields in the structured task spec before complete generation.",
            )

    def test_cli_run_save_session_persists_questions_and_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "state.json"

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 outputs/pion.npy outputs/run_pion.py cluster_launch=local",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--save-session",
                str(session_path),
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with redirect_stdout(stdout):
                    exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            saved = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertIn("implementation_plan", saved)
            self.assertIn("field_resolution", saved["implementation_plan"])
            self.assertIn("clarification_trace", saved["implementation_plan"])
            self.assertEqual(saved["draft"]["field_sources"]["fermion_action"], "parsed")

    def test_clarification_trace_is_persisted_when_answers_are_applied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "state.json"

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt outputs/pion.npy outputs/run_pion.py",
                "--backend",
                "codex",
                "--dry-run",
                "--interactive",
                "--max-questions",
                "1",
                "--save-session",
                str(session_path),
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch("builtins.input", return_value="gauge"):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            saved = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertTrue(saved["implementation_plan"]["clarification_trace"])
            self.assertEqual(saved["implementation_plan"]["clarification_trace"][0]["field_name"], "start_from")


if __name__ == "__main__":
    unittest.main()
