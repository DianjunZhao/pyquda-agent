import json
import tempfile
import unittest
from pathlib import Path

from scripts.refresh_goal_audit import build_goal_audit
from scripts.refresh_goal_audit import main


class RefreshGoalAuditTests(unittest.TestCase):
    def _write_fixture(self, root: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
        task_path = root / "run.task.json"
        plan_path = root / "run.plan.json"
        runtime_path = root / "runtime.json"
        probe_path = root / "probe.json"
        parity_path = root / "backend_parity.json"
        candidates_path = root / "runtime_candidates.json"

        task_path.write_text(
            json.dumps(
                {
                    "workflow_id": "pion_2pt_chroma_wall_local_zero_momentum_npy_v1",
                    "start_from": "gauge",
                    "gauge_format": "chroma_qio",
                    "gauge_path": "/Users/zhaodianjun/PyQUDA/tests/weak_field.lime",
                    "lattice_size": [4, 4, 4, 8],
                    "grid_size": [1, 1, 1, 1],
                    "fermion_action": "clover",
                    "mass": 0.1,
                    "xi_0": 4.0,
                    "nu": 0.8,
                    "coeff_t": 0.9,
                    "coeff_r": 2.3,
                    "solver_tol": 1e-12,
                    "solver_maxiter": 1000,
                    "source_type": "wall",
                    "sink_type": "local",
                    "momentum_projection": "zero",
                    "source_timeslices": [0],
                    "gauge_fixed": True,
                    "correlator_output_format": "npy",
                    "correlator_output_path": "outputs/pion.npy",
                    "resource_path": ".cache/quda",
                    "script_output_path": "outputs/run.py",
                    "script_style": "complete",
                    "missing_fields": [],
                    "unsupported_reasons": [],
                }
            ),
            encoding="utf-8",
        )
        plan_path.write_text(
            json.dumps(
                {
                    "references": [
                        {"path": "/Users/zhaodianjun/PyQUDA/examples/3_Pion_Proton_2pt.py"},
                        {"path": "/Users/zhaodianjun/PyQUDA/examples/5_Pion_Dispersion.py"},
                        {"path": "/Users/zhaodianjun/PyQUDA/tests/test_mesonspec.py"},
                        {"path": "/Users/zhaodianjun/PyQUDA/tests/test_io.py"},
                        {"path": "/Users/zhaodianjun/PyQUDA/pyquda_utils/io/__init__.py"},
                        {"path": "/Users/zhaodianjun/PyQUDA/pyquda_utils/source.py"},
                        {"path": "/Users/zhaodianjun/PyQUDA/pyquda_utils/core.py"},
                        {"path": "/Users/zhaodianjun/PyQUDA/pyquda_utils/gamma.py"},
                    ],
                    "external_citations": [{"id": "x"}],
                    "convention_decisions": [{"citations": ["x"]}],
                    "field_resolution": {
                        "workflow_id": "fixed",
                        "start_from": "parsed",
                        "gauge_format": "parsed",
                        "gauge_path": "parsed",
                        "lattice_size": "parsed",
                        "grid_size": "parsed",
                        "fermion_action": "parsed",
                        "mass": "parsed",
                        "xi_0": "parsed",
                        "nu": "parsed",
                        "coeff_t": "parsed",
                        "coeff_r": "parsed",
                        "solver_tol": "parsed",
                        "solver_maxiter": "parsed",
                        "source_type": "parsed",
                        "sink_type": "parsed",
                        "momentum_projection": "parsed",
                        "source_timeslices": "parsed",
                        "gauge_fixed": "parsed",
                        "correlator_output_format": "parsed",
                        "correlator_output_path": "parsed",
                        "resource_path": "parsed",
                        "script_output_path": "parsed",
                        "script_style": "parsed",
                    },
                    "validation_checks": [
                        "generated code imports real PyQUDA APIs",
                        "generated code matches local examples/tests/io helpers for the fixed workflow",
                        "generated code contains no TODO/pass/placeholder text",
                    ],
                    "unresolved_fields": [],
                    "physics_choices": {},
                    "pyquda_choices": {},
                    "runtime_choices": {},
                    "clarification_trace": [],
                }
            ),
            encoding="utf-8",
        )
        runtime_path.write_text(json.dumps({"ready": False}), encoding="utf-8")
        probe_path.write_text(json.dumps({"status": "runtime_missing"}), encoding="utf-8")
        parity_path.write_text(
            json.dumps(
                {
                    "comparisons": {
                        "script": {"identical": True},
                        "task": {"identical": True},
                        "plan": {"identical": True},
                    }
                }
            ),
            encoding="utf-8",
        )
        candidates_path.write_text(json.dumps({"any_ready": False}), encoding="utf-8")
        return task_path, plan_path, runtime_path, probe_path, parity_path, candidates_path

    def test_build_goal_audit_marks_runtime_not_proved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            task_path, plan_path, runtime_path, probe_path, parity_path, candidates_path = self._write_fixture(root)
            audit = build_goal_audit(
                json.loads(task_path.read_text(encoding="utf-8")),
                json.loads(plan_path.read_text(encoding="utf-8")),
                json.loads(runtime_path.read_text(encoding="utf-8")),
                json.loads(probe_path.read_text(encoding="utf-8")),
                json.loads(parity_path.read_text(encoding="utf-8")),
                json.loads(candidates_path.read_text(encoding="utf-8")),
            )
            items = {item["id"]: item for item in audit["items"]}
            self.assertEqual(items["req-1-local-retrieval"]["status"], "proved")
            self.assertEqual(items["req-8-validate-against-real-interfaces"]["status"], "proved")
            self.assertEqual(items["env-runtime-readiness"]["status"], "not_proved")
            self.assertEqual(items["dod-support-api-and-codex"]["status"], "proved")

    def test_main_writes_audit_and_doc(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            task_path, plan_path, runtime_path, probe_path, parity_path, candidates_path = self._write_fixture(root)
            audit_path = root / "goal_audit.json"
            doc_path = root / "audit.md"
            exit_code = main(
                [
                    "--task",
                    str(task_path),
                    "--plan",
                    str(plan_path),
                    "--runtime",
                    str(runtime_path),
                    "--probe",
                    str(probe_path),
                    "--backend-parity",
                    str(parity_path),
                    "--runtime-candidates",
                    str(candidates_path),
                    "--audit-output",
                    str(audit_path),
                    "--doc-output",
                    str(doc_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(audit_path.exists())
            self.assertTrue(doc_path.exists())
            payload = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["objective"], "first_workflow_pion_2pt")
            self.assertIn("Requirements currently proved", doc_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
