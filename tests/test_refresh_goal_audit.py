import json
import tempfile
import unittest
from pathlib import Path

from scripts.refresh_goal_audit import build_goal_audit
from scripts.refresh_goal_audit import main


class RefreshGoalAuditTests(unittest.TestCase):
    def _write_fixture(self, root: Path) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path, Path]:
        task_path = root / "run.task.json"
        plan_path = root / "run.plan.json"
        runtime_path = root / "runtime.json"
        probe_path = root / "probe.json"
        parity_path = root / "backend_parity.json"
        backend_execution_path = root / "backend_execution.json"
        candidates_path = root / "runtime_candidates.json"
        supported_path = root / "supported_workflows_validation.json"
        v9_behavior_path = root / "v9_product_behavior.json"
        v11_task_suite_path = root / "v11_task_suite.json"

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
                    "cluster_launch": "local",
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
                        {"path": "/Users/zhaodianjun/PyQUDA/examples/2_Quark_Propagator.py"},
                        {"path": "/Users/zhaodianjun/PyQUDA/examples/4_Pion_PCAC.py"},
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
                        "cluster_launch": "parsed",
                        "script_output_path": "parsed",
                        "script_style": "parsed",
                    },
                    "validation_checks": [
                        "generated code imports real PyQUDA APIs",
                        "generated code matches local examples/tests/io helpers for the chosen workflow",
                        "generated code contains no TODO/pass/placeholder text",
                    ],
                    "unresolved_fields": [],
                    "physics_choices": {},
                    "pyquda_choices": {},
                    "runtime_choices": {},
                    "runtime_readiness": {
                        "generated_script_probe": {
                            "status": "runtime_missing",
                            "artifact_path": str(probe_path),
                        }
                    },
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
        backend_execution_path.write_text(
            json.dumps(
                {
                    "backend_summary": {
                        "states": {
                            "api": "fallback_only",
                            "codex": "fallback_only",
                        }
                    },
                    "backends": [
                        {
                            "backend": "api",
                            "coherent": True,
                            "availability_state": "fallback_only",
                            "cases": [
                                {
                                    "case_summary": {
                                        "product_status": "needs_input",
                                        "generation_phase": "blocked_on_input",
                                        "execution_phase": "blocked_by_generation",
                                    }
                                }
                            ],
                        },
                        {
                            "backend": "codex",
                            "coherent": True,
                            "availability_state": "fallback_only",
                            "cases": [
                                {
                                    "case_summary": {
                                        "product_status": "needs_input",
                                        "generation_phase": "blocked_on_input",
                                        "execution_phase": "blocked_by_generation",
                                    }
                                }
                            ],
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        candidates_path.write_text(json.dumps({"any_ready": False}), encoding="utf-8")
        supported_path.write_text(
            json.dumps(
                {
                    "workflows": [
                        {
                            "workflow": "pion_2pt",
                            "coherent": True,
                            "product_path": {
                                "rough_product_status": "needs_input",
                                "rough_generation_phase": "blocked_on_input",
                                "rough_execution_phase": "blocked_by_generation",
                                "direct_product_status": "generated_runtime_blocked",
                                "direct_generation_phase": "generated",
                                "direct_execution_phase": "runtime_missing",
                            },
                        },
                        {
                            "workflow": "pion_dispersion",
                            "coherent": True,
                            "product_path": {
                                "rough_product_status": "needs_input",
                                "rough_generation_phase": "blocked_on_input",
                                "rough_execution_phase": "blocked_by_generation",
                                "direct_product_status": "generated_runtime_blocked",
                                "direct_generation_phase": "generated",
                                "direct_execution_phase": "runtime_missing",
                            },
                        },
                        {
                            "workflow": "proton_2pt",
                            "coherent": True,
                            "product_path": {
                                "rough_product_status": "needs_input",
                                "rough_generation_phase": "blocked_on_input",
                                "rough_execution_phase": "blocked_by_generation",
                                "direct_product_status": "generated_runtime_blocked",
                                "direct_generation_phase": "generated",
                                "direct_execution_phase": "runtime_missing",
                            },
                        },
                        {
                            "workflow": "quark_propagator",
                            "coherent": True,
                            "product_path": {
                                "rough_product_status": "needs_input",
                                "rough_generation_phase": "blocked_on_input",
                                "rough_execution_phase": "blocked_by_generation",
                                "direct_product_status": "generated_runtime_blocked",
                                "direct_generation_phase": "generated",
                                "direct_execution_phase": "runtime_missing",
                            },
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        v9_behavior_path.write_text(
            json.dumps(
                {
                    "suite": "v9_product_behavior",
                    "all_passed": True,
                    "summary": {
                        "unsupported_behavior": {
                            "covered": True,
                            "primary_action_contract": {
                                "copyable_retry_kind": "retry_supported_workflow",
                                "choice_required_kind": "choose_supported_variant",
                                "backend_fix_should_not_be_primary": True,
                            },
                        }
                    },
                    "groups": [
                        {"group": "rough_request_clarification", "passed": True},
                        {"group": "backend_degradation", "passed": True},
                        {"group": "terminal_execution_awareness", "passed": True},
                        {"group": "supported_workflow_generation", "passed": True},
                        {"group": "runtime_recovery_guidance", "passed": True},
                        {"group": "explicit_unsupported_refusal", "passed": True},
                        {"group": "probe_artifact_consistency", "passed": True},
                    ],
                }
            ),
            encoding="utf-8",
        )
        v11_task_suite_path.write_text(
            json.dumps(
                {
                    "suite": "v11_task_suite",
                    "all_passed": True,
                    "summary": {
                        "case_count": 16,
                        "categories": [
                            "ambiguous_meson",
                            "explicit_supported",
                            "unsupported_baryon",
                            "unsupported_flow_variant",
                        ],
                    },
                    "cases": [
                        {"case_id": "ambiguous_meson_operator", "passed": True},
                        {"case_id": "unsupported_wilson_flow_existing_propagator", "passed": True},
                    ],
                }
            ),
            encoding="utf-8",
        )
        return (
            task_path,
            plan_path,
            runtime_path,
            probe_path,
            parity_path,
            backend_execution_path,
            candidates_path,
            supported_path,
            v9_behavior_path,
            v11_task_suite_path,
        )

    def test_build_goal_audit_aggregates_references_from_validated_workflow_plans(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (
                task_path,
                plan_path,
                runtime_path,
                probe_path,
                parity_path,
                backend_execution_path,
                candidates_path,
                supported_path,
                v9_behavior_path,
                v11_task_suite_path,
            ) = self._write_fixture(root)
            primary_plan = json.loads(plan_path.read_text(encoding="utf-8"))
            primary_plan["references"] = [
                item for item in primary_plan["references"] if item["path"] != "/Users/zhaodianjun/PyQUDA/examples/4_Pion_PCAC.py"
            ]
            plan_path.write_text(json.dumps(primary_plan), encoding="utf-8")

            pcac_plan_path = root / "validate_pion_pcac.plan.json"
            pcac_plan_path.write_text(
                json.dumps(
                    {
                        "references": [
                            {"path": "/Users/zhaodianjun/PyQUDA/examples/4_Pion_PCAC.py"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            supported = json.loads(supported_path.read_text(encoding="utf-8"))
            supported["workflows"][0]["direct"] = {
                "parsed": {
                    "artifacts": {
                        "plan": str(pcac_plan_path),
                    }
                }
            }
            supported_path.write_text(json.dumps(supported), encoding="utf-8")

            audit = build_goal_audit(
                json.loads(task_path.read_text(encoding="utf-8")),
                json.loads(plan_path.read_text(encoding="utf-8")),
                json.loads(runtime_path.read_text(encoding="utf-8")),
                json.loads(probe_path.read_text(encoding="utf-8")),
                json.loads(parity_path.read_text(encoding="utf-8")),
                json.loads(backend_execution_path.read_text(encoding="utf-8")),
                json.loads(candidates_path.read_text(encoding="utf-8")),
                json.loads(supported_path.read_text(encoding="utf-8")),
                json.loads(v9_behavior_path.read_text(encoding="utf-8")),
                json.loads(v11_task_suite_path.read_text(encoding="utf-8")),
            )
            items = {item["id"]: item for item in audit["items"]}
            self.assertEqual(items["req-1-local-retrieval"]["status"], "proved")

    def test_build_goal_audit_marks_runtime_not_proved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (
                task_path,
                plan_path,
                runtime_path,
                probe_path,
                parity_path,
                backend_execution_path,
                candidates_path,
                supported_path,
                v9_behavior_path,
                v11_task_suite_path,
            ) = self._write_fixture(root)
            audit = build_goal_audit(
                json.loads(task_path.read_text(encoding="utf-8")),
                json.loads(plan_path.read_text(encoding="utf-8")),
                json.loads(runtime_path.read_text(encoding="utf-8")),
                json.loads(probe_path.read_text(encoding="utf-8")),
                json.loads(parity_path.read_text(encoding="utf-8")),
                json.loads(backend_execution_path.read_text(encoding="utf-8")),
                json.loads(candidates_path.read_text(encoding="utf-8")),
                json.loads(supported_path.read_text(encoding="utf-8")),
                json.loads(v9_behavior_path.read_text(encoding="utf-8")),
                json.loads(v11_task_suite_path.read_text(encoding="utf-8")),
            )
            items = {item["id"]: item for item in audit["items"]}
            self.assertEqual(items["req-1-local-retrieval"]["status"], "proved")
            self.assertEqual(items["req-8-validate-against-real-interfaces"]["status"], "proved")
            self.assertEqual(items["dod-hpc-script-readiness"]["status"], "proved")
            self.assertEqual(items["env-local-runtime-readiness"]["status"], "not_proved")
            self.assertEqual(items["dod-support-api-and-codex"]["status"], "proved")
            self.assertEqual(items["multi-workflow-routing"]["status"], "proved")
            self.assertEqual(items["v8-unified-run-and-probe-reporting"]["status"], "proved")
            self.assertEqual(items["v8-product-facing-validation-chain"]["status"], "proved")
            self.assertEqual(items["v9-product-behavior-regression-surface"]["status"], "proved")
            self.assertEqual(items["v9-rough-request-clarification-routing"]["status"], "proved")
            self.assertEqual(items["v9-direct-supported-generation-consistency"]["status"], "proved")
            self.assertEqual(items["v9-actionable-recovery-guidance"]["status"], "proved")
            self.assertEqual(items["v9-unsupported-actionability-contract"]["status"], "proved")
            self.assertEqual(items["v11-realistic-task-suite-regression"]["status"], "proved")
            self.assertEqual(audit["backend_availability"]["api"], "fallback_only")
            self.assertEqual(audit["backend_availability"]["codex"], "fallback_only")

    def test_main_writes_audit_and_doc(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (
                task_path,
                plan_path,
                runtime_path,
                probe_path,
                parity_path,
                backend_execution_path,
                candidates_path,
                supported_path,
                v9_behavior_path,
                v11_task_suite_path,
            ) = self._write_fixture(root)
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
                    "--backend-execution",
                    str(backend_execution_path),
                    "--runtime-candidates",
                    str(candidates_path),
                    "--supported-validation",
                    str(supported_path),
                    "--v9-product-behavior",
                    str(v9_behavior_path),
                    "--v11-task-suite",
                    str(v11_task_suite_path),
                    "--audit-date",
                    "2026-07-16",
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
            self.assertEqual(payload["objective"], "product_like_multi_workflow_pyquda_agent")
            self.assertEqual(payload["last_audited_on"], "2026-07-16")
            self.assertIn("Requirements currently proved", doc_path.read_text(encoding="utf-8"))
            self.assertIn("Unified run/probe reporting status", doc_path.read_text(encoding="utf-8"))
            self.assertIn("Product-facing validation-chain status", doc_path.read_text(encoding="utf-8"))
            self.assertIn("V9 product-behavior regression status", doc_path.read_text(encoding="utf-8"))
            self.assertIn("V9 rough-request clarification status", doc_path.read_text(encoding="utf-8"))
            self.assertIn("V9 direct supported-generation status", doc_path.read_text(encoding="utf-8"))
            self.assertIn("V9 actionable recovery-guidance status", doc_path.read_text(encoding="utf-8"))
            self.assertIn("V9 unsupported actionability status", doc_path.read_text(encoding="utf-8"))
            self.assertIn("V11 realistic task-suite regression status", doc_path.read_text(encoding="utf-8"))
            self.assertIn("Backend execution usability summary", doc_path.read_text(encoding="utf-8"))
            self.assertIn("support surface: `11` workflow families / `17` concrete grounded workflow targets", doc_path.read_text(encoding="utf-8"))
            self.assertIn("Grounded HPC handoff readiness status", doc_path.read_text(encoding="utf-8"))
            self.assertIn("family `quark_propagator`", doc_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
