import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_v12_execution_readiness import main


class ValidateV12ExecutionReadinessTests(unittest.TestCase):
    def test_main_writes_v12_execution_readiness_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            backend_execution = root / "backend_execution.json"
            supported_workflows = root / "supported_workflows_validation.json"
            v11_task_suite = root / "v11_task_suite.json"
            output = root / "v12_execution_readiness.json"
            pyquda_repo = root / "PyQUDA"
            pyquda_repo.mkdir()

            backend_execution.write_text(
                json.dumps(
                    {
                        "backend_summary": {
                            "states": {
                                "api": "usable",
                                "codex": "fallback_only",
                            },
                            "usable_backends": ["api"],
                            "fallback_only_backends": ["codex"],
                        },
                        "backends": [
                            {
                                "backend": "codex",
                                "availability_state": "fallback_only",
                                "repair_contract": {
                                    "category": "local_environment_error",
                                    "repair_action_state": "conditional",
                                    "repair_actionable": False,
                                    "verification_command": "codex exec 'Reply with exactly: OK'",
                                    "repair_action_command": "codex exec 'Reply with exactly: OK'",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            supported_workflows.write_text(
                json.dumps(
                    {
                        "summary": {
                            "report_status": "coherent_but_runtime_blocked",
                            "hpc_handoff_coherent_count": 17,
                            "direct_execution_status_counts": {"runtime_missing": 17},
                        }
                    }
                ),
                encoding="utf-8",
            )
            v11_task_suite.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "case_id": "ambiguous_meson_operator",
                                "category": "ambiguous_meson",
                                "passed": True,
                                "observed": {
                                    "product_status": "needs_input",
                                    "clarification_mode": "physics_confirmation",
                                    "primary_action_kind": "continue_by_reply",
                                },
                            },
                            {
                                "case_id": "explicit_pion_2pt",
                                "category": "explicit_supported",
                                "passed": True,
                                "observed": {
                                    "product_status": "needs_input",
                                    "clarification_mode": "task_fields",
                                    "primary_action_kind": "continue_by_set",
                                },
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "--backend-execution",
                    str(backend_execution),
                    "--supported-workflows",
                    str(supported_workflows),
                    "--v11-task-suite",
                    str(v11_task_suite),
                    "--output",
                    str(output),
                    "--pyquda-repo",
                    str(pyquda_repo),
                ]
            )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["suite"], "v12_execution_readiness")
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["summary"]["contract"], "execution_readiness_v12")
            self.assertIn("backend truly usable", payload["summary"]["coverage"])
            self.assertIn("runtime blocked due to probe harness failure", payload["summary"]["coverage"])
            self.assertTrue(payload["answers"]["backend_truly_usable"]["answer"])
            self.assertTrue(payload["answers"]["real_tasks_less_reliant_on_manual_fallback"]["answer"])
            observed = {case["case_id"]: case for case in payload["cases"]}
            self.assertTrue(observed["backend_usable"]["passed"])
            self.assertTrue(observed["backend_repair_path"]["passed"])
            self.assertTrue(observed["runtime_blocked_due_to_probe_harness_failure"]["passed"])
            self.assertTrue(observed["runtime_blocked_subclassification"]["passed"])
            self.assertTrue(observed["real_tasks_need_less_manual_fallback"]["passed"])

    def test_main_accepts_all_backends_usable_without_degraded_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            backend_execution = root / "backend_execution.json"
            supported_workflows = root / "supported_workflows_validation.json"
            v11_task_suite = root / "v11_task_suite.json"
            output = root / "v12_execution_readiness.json"
            pyquda_repo = root / "PyQUDA"
            pyquda_repo.mkdir()

            backend_execution.write_text(
                json.dumps(
                    {
                        "backend_summary": {
                            "states": {
                                "api": "usable",
                                "auto": "usable",
                                "codex": "usable",
                            },
                            "usable_backends": ["api", "auto", "codex"],
                            "fallback_only_backends": [],
                        },
                        "backends": [
                            {"backend": "api", "availability_state": "usable", "repair_contract": None},
                            {"backend": "auto", "availability_state": "usable", "repair_contract": None},
                            {"backend": "codex", "availability_state": "usable", "repair_contract": None},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            supported_workflows.write_text(
                json.dumps(
                    {
                        "summary": {
                            "report_status": "coherent_but_runtime_blocked",
                            "hpc_handoff_coherent_count": 17,
                            "direct_execution_status_counts": {"runtime_missing": 17},
                        }
                    }
                ),
                encoding="utf-8",
            )
            v11_task_suite.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "case_id": "ambiguous_meson_operator",
                                "category": "ambiguous_meson",
                                "passed": True,
                                "observed": {
                                    "product_status": "needs_input",
                                    "clarification_mode": "physics_confirmation",
                                    "primary_action_kind": "continue_by_reply",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "--backend-execution",
                    str(backend_execution),
                    "--supported-workflows",
                    str(supported_workflows),
                    "--v11-task-suite",
                    str(v11_task_suite),
                    "--output",
                    str(output),
                    "--pyquda-repo",
                    str(pyquda_repo),
                ]
            )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            observed = {case["case_id"]: case for case in payload["cases"]}
            self.assertTrue(observed["backend_usable"]["passed"])
            self.assertTrue(observed["backend_degraded_but_continueable"]["passed"])
            self.assertEqual(observed["backend_degraded_but_continueable"]["observed"]["state"], "not_needed")
            self.assertTrue(observed["backend_repair_path"]["passed"])
            self.assertEqual(observed["backend_repair_path"]["observed"]["state"], "not_needed")


if __name__ == "__main__":
    unittest.main()
