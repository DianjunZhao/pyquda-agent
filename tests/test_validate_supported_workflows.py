import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pyquda_agent.intent.resolver import INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS
from pyquda_agent.intent.resolver import INTENT_TIMEOUT_RECOVERY_TIMEOUT_SECONDS

from scripts.validate_supported_workflows import main


class ValidateSupportedWorkflowsTests(unittest.TestCase):
    def test_main_writes_coherent_validation_report(self):
        class Completed:
            def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
                self.stdout = stdout
                self.returncode = returncode
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None):
            self.assertIn("--result-format", cmd)
            self.assertIn("summary", cmd)
            output_path = Path(cmd[cmd.index("--output") + 1])
            request = cmd[4]
            lowered_request = request.lower()
            output_path.with_suffix(".physics.json").write_text(json.dumps({}), encoding="utf-8")
            output_path.with_suffix(".task.json").write_text(json.dumps({}), encoding="utf-8")
            output_path.with_suffix(".plan.json").write_text(
                json.dumps(
                    {
                        "runtime_readiness": {
                            "ready": False,
                            "evidence_levels": {
                                "current_level": "structurally_grounded",
                                "runtime_ready": False,
                                "runtime_proved": False,
                            },
                            "generated_script_probe": {
                                "status": "requested" if "lattice size" not in lowered_request else "runtime_missing"
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            if "--dry-run" not in cmd and "lattice size" in cmd[4]:
                probe_status = "runtime_missing"
                probe_runtime_level = "environment_missing"
                if "pion two-point correlator" in lowered_request:
                    probe_status = "failed"
                    probe_runtime_level = "probe_failed"
                output_path.with_suffix(".probe.json").write_text(
                    json.dumps({"status": probe_status, "runtime_level": probe_runtime_level}),
                    encoding="utf-8",
                )
            if "gaussian-shell quark propagator" in lowered_request or "gaussian shell quark propagator" in lowered_request:
                workflow = "quark_propagator_gaussian_shell"
                target_id = "quark_propagator"
                workflow_id = "quark_propagator_gaussian_shell_chroma_hdf5_v1"
            elif "quark propagator" in lowered_request:
                workflow = "quark_propagator"
                target_id = "quark_propagator"
                workflow_id = "quark_propagator_chroma_point_hdf5_v1"
            elif "ape-smeared" in lowered_request or "ape smeared" in lowered_request or "ape-smear" in lowered_request:
                workflow = "ape_smear"
                target_id = "ape_smeared_gauge_configuration"
                workflow_id = "ape_smear_chroma_qio_npy_v1"
            elif "hyp-smeared" in lowered_request or "hyp smeared" in lowered_request or "hyp-smear" in lowered_request:
                workflow = "hyp_smear"
                target_id = "hyp_smeared_gauge_configuration"
                workflow_id = "hyp_smear_chroma_qio_npy_v1"
            elif "stout-smear" in lowered_request or "stout smear" in lowered_request:
                workflow = "stout_smear"
                target_id = "stout_smeared_gauge_configuration"
                workflow_id = "stout_smear_chroma_qio_npy_v1"
            elif "wilson flow" in lowered_request or "gradient flow" in lowered_request:
                workflow = "wilson_flow"
                target_id = "wilson_flow_energy_observable"
                workflow_id = "wilson_flow_chroma_qio_energy_npy_v1"
            elif "pion two-point correlator" in lowered_request and "existing propagator" in lowered_request:
                workflow = "pion_2pt_existing_propagator"
                target_id = "pion_two_point_correlator"
                workflow_id = "pion_2pt_existing_propagator_local_zero_momentum_npy_v1"
            elif "meson spect" in lowered_request and "existing propagator" in lowered_request:
                workflow = "meson_spec_existing_propagator"
                target_id = "meson_spectrum_correlator"
                workflow_id = "meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1"
            elif "proton" in lowered_request:
                workflow = "proton_2pt"
                target_id = "proton_two_point_correlator"
                workflow_id = "proton_2pt_chroma_wall_local_zero_momentum_npy_v1"
                if "existing propagator" in lowered_request:
                    workflow = "proton_2pt_existing_propagator"
                    workflow_id = "proton_2pt_existing_propagator_local_zero_momentum_npy_v1"
            elif "rho meson" in lowered_request or "rho/vector" in lowered_request or "vector meson" in lowered_request:
                workflow = "rho_vector"
                target_id = "rho_vector_meson_correlator"
                workflow_id = "rho_vector_chroma_wall_local_zero_momentum_npy_v1"
                if "existing propagator" in lowered_request:
                    workflow = "rho_vector_existing_propagator"
                    workflow_id = "rho_vector_existing_propagator_local_zero_momentum_npy_v1"
            elif "pcac" in lowered_request:
                workflow = "pion_pcac"
                target_id = "pion_pcac_ratio_correlator"
                workflow_id = "pion_pcac_chroma_wall_local_zero_momentum_npy_v1"
                if "existing propagator" in lowered_request:
                    workflow = "pion_pcac_existing_propagator"
                    workflow_id = "pion_pcac_existing_propagator_local_zero_momentum_npy_v1"
            elif "meson spect" in lowered_request:
                workflow = "meson_spec"
                target_id = "meson_spectrum_correlator"
                workflow_id = "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1"
            elif "dispersion" in lowered_request:
                workflow = "pion_dispersion"
                target_id = "pion_dispersion_correlator"
                workflow_id = "pion_dispersion_chroma_point_momentum_npy_v1"
            else:
                workflow = "pion_2pt"
                target_id = "pion_two_point_correlator"
                workflow_id = "pion_2pt_chroma_wall_local_zero_momentum_npy_v1"
            llm_assistance = {"used": True, "fallback": False, "fallback_reason": None}
            backend_diagnostic = {
                "status": "used",
                "category": None,
                "failure_origin": None,
                "recovery_mode": "continue",
                "retryable_now": True,
            }
            if "lattice size" in request:
                output_path.write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")
                status = "ok"
                execution_status = "runtime_missing"
                execution_phase = "runtime_missing"
                probe_status = "runtime_missing"
                if "pion two-point correlator" in lowered_request:
                    execution_status = "failed"
                    execution_phase = "failed"
                    probe_status = "failed"
                product_status = "generated_runtime_blocked"
                workflow_outcome = {
                    "phase": "generated_and_probed",
                    "generation_succeeded": True,
                    "execution_attempted": True,
                    "runtime_probe_status": probe_status,
                }
                generation_result = {"phase": "generated"}
                execution_result = {"phase": execution_phase}
                delivery_status = {
                    "generation": {"phase": "generated"},
                    "execution": {"phase": execution_phase},
                }
                if "existing propagator" in lowered_request:
                    hpc_handoff = {
                        "start_from": "propagator",
                        "input_path_count": 2,
                        "input_directory_policy": "treat_input_directories_as_read_only_handoff_storage",
                        "input_mutability_policy": "immutable_inputs_never_overwritten",
                        "output_directory_count": 1,
                        "output_directory_policy": "prefer_dedicated_writable_results_directory",
                        "output_writer_policy": "rank0_only",
                        "output_input_overlap_forbidden": True,
                        "required_modules": ["numpy", "cupy", "pyquda_utils", "pyquda"],
                        "preflight_checks": ["a", "b", "c"],
                        "probe_artifact": str(output_path.with_suffix(".probe.json")),
                    }
                else:
                    hpc_handoff = {
                        "start_from": "gauge",
                        "input_path_count": 1,
                        "input_directory_policy": "treat_gauge_input_directories_as_shared_read_only_storage_when_possible",
                        "input_mutability_policy": "immutable_inputs_never_overwritten",
                        "output_directory_count": 1,
                        "output_directory_policy": "write_new_outputs_to_explicit_writable_results_directory",
                        "output_writer_policy": "rank0_only",
                        "output_input_overlap_forbidden": False,
                        "required_modules": ["numpy", "cupy", "pyquda_utils", "pyquda"],
                        "preflight_checks": ["a", "b", "c"],
                        "probe_artifact": str(output_path.with_suffix(".probe.json")),
                    }
            else:
                status = "needs_input"
                execution_status = None
                product_status = "needs_input"
                workflow_outcome = {
                    "phase": "clarification",
                    "generation_succeeded": False,
                    "execution_attempted": False,
                    "runtime_probe_status": "pending_generation",
                }
                generation_result = {"phase": "blocked_on_input"}
                execution_result = {"phase": "blocked_by_generation"}
                delivery_status = {
                    "generation": {"phase": "blocked_on_input"},
                    "execution": {"phase": "blocked_by_generation"},
                }
                hpc_handoff = None
            payload = {
                "status": status,
                "product_status": product_status,
                "execution_status": execution_status,
                "physics_target": target_id,
                "workflow_target": workflow_id,
                "hpc_handoff": hpc_handoff,
                "artifacts": {
                    "physics": str(output_path.with_suffix(".physics.json")),
                    "task": str(output_path.with_suffix(".task.json")),
                    "plan": str(output_path.with_suffix(".plan.json")),
                },
                "workflow_outcome": workflow_outcome,
                "generation_result": generation_result,
                "execution_result": execution_result,
                "delivery_status": delivery_status,
                "llm_attempted": True,
                "llm_used": True,
                "llm_fallback": False,
                "llm_fallback_reason": None,
                "requested_backend": "codex",
                "selected_backend": "codex",
                "llm_codex_preflight_attempted": True,
                "llm_codex_preflight_status": "failed",
                "llm_codex_preflight_category": "timeout",
                "llm_codex_preflight_reason": "mock timeout",
                "llm_codex_preflight_soft_failed": True,
                "llm_codex_preflight_soft_failure_reason": "mock timeout",
                "llm_session_backend_memory_considered": True,
                "llm_session_backend_memory_used": workflow == "pion_dispersion",
                "llm_session_backend_memory_reason": "mock session memory reason",
                "llm_session_backend_prior_category": "timeout",
                "llm_intent_primary_timeout_seconds": INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS,
                "llm_timeout_recovery_attempted": True,
                "llm_timeout_recovery_used": True,
                "llm_timeout_recovery_failed": False,
                "llm_timeout_recovery_trigger_category": "timeout",
                "llm_timeout_recovery_timeout_seconds": INTENT_TIMEOUT_RECOVERY_TIMEOUT_SECONDS,
                "llm_timeout_recovery_failure_category": None,
                "backend_diagnostic": backend_diagnostic,
            }
            return Completed(stdout=json.dumps(payload))

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "data" / "supported_workflows_validation.json"
            with patch("scripts.validate_supported_workflows.subprocess.run", side_effect=fake_run):
                exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--output", str(report_path)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["all_coherent"])
            self.assertEqual(len(payload["workflows"]), 17)
            self.assertTrue(all(item["coherent"] for item in payload["workflows"]))
            self.assertEqual(payload["summary"]["report_status"], "coherent_but_runtime_blocked")
            self.assertEqual(payload["summary"]["workflow_count"], 17)
            self.assertEqual(payload["summary"]["coherent_count"], 17)
            self.assertEqual(payload["summary"]["rough_product_status_counts"], {"needs_input": 17})
            self.assertEqual(payload["summary"]["direct_product_status_counts"], {"generated_runtime_blocked": 17})
            self.assertEqual(payload["summary"]["direct_execution_status_counts"], {"failed": 2, "runtime_missing": 15})
            self.assertEqual(payload["summary"]["direct_probe_status_counts"], {"failed": 2, "runtime_missing": 15})
            self.assertEqual(payload["summary"]["hpc_handoff_coherent_count"], 17)
            self.assertEqual(payload["summary"]["hpc_handoff_start_from_counts"], {"gauge": 12, "propagator": 5})
            self.assertEqual(
                payload["summary"]["hpc_handoff_input_directory_policy_counts"],
                {
                    "treat_gauge_input_directories_as_shared_read_only_storage_when_possible": 12,
                    "treat_input_directories_as_read_only_handoff_storage": 5,
                },
            )
            self.assertEqual(
                payload["summary"]["hpc_handoff_output_directory_policy_counts"],
                {
                    "prefer_dedicated_writable_results_directory": 5,
                    "write_new_outputs_to_explicit_writable_results_directory": 12,
                },
            )
            self.assertEqual(payload["summary"]["rough_backend_fallback_count"], 0)
            self.assertEqual(payload["summary"]["direct_backend_fallback_count"], 0)
            self.assertEqual(payload["summary"]["direct_backend_category_counts"], {})
            self.assertFalse(payload["summary"]["unsupported_actionability_boundary"]["covered_here"])
            self.assertEqual(
                payload["summary"]["unsupported_actionability_boundary"]["source_of_truth"],
                "data/v9_product_behavior.json",
            )
            self.assertEqual(
                payload["summary"]["unsupported_actionability_boundary"]["copyable_retry_kind"],
                "retry_supported_workflow",
            )
            self.assertEqual(
                payload["summary"]["unsupported_actionability_boundary"]["choice_required_kind"],
                "choose_supported_variant",
            )
            self.assertIn(
                "supported-workflow routing and lifecycle coherence",
                payload["summary"]["unsupported_actionability_boundary"]["note"],
            )
            self.assertIn("Fix the runtime environment", payload["summary"]["next_action"])
            self.assertTrue(all(item["rough"]["artifacts_exist"] for item in payload["workflows"]))
            self.assertTrue(all(item["direct"]["script_exists"] for item in payload["workflows"]))
            self.assertTrue(all(item["direct"]["probe_exists"] for item in payload["workflows"]))
            self.assertTrue(all(item["rough"]["probe_status"] == "requested" for item in payload["workflows"]))
            self.assertTrue(all("handoff" in item for item in payload["workflows"]))
            self.assertTrue(all(item["handoff"]["present"] is True for item in payload["workflows"]))
            self.assertTrue(all(item["handoff"]["coherent"] is True for item in payload["workflows"]))
            self.assertTrue(all(item["product_path"]["rough_product_status"] == "needs_input" for item in payload["workflows"]))
            self.assertTrue(all(item["product_path"]["direct_product_status"] == "generated_runtime_blocked" for item in payload["workflows"]))
            self.assertTrue(all(item["product_path"]["direct_generation_phase"] == "generated" for item in payload["workflows"]))
            self.assertTrue(
                all(item["product_path"]["direct_execution_phase"] in {"runtime_missing", "failed"} for item in payload["workflows"])
            )
            self.assertTrue(all(item["product_path"]["rough_backend"]["backend_status"] == "used" for item in payload["workflows"]))
            self.assertTrue(all(item["product_path"]["direct_backend"]["recovery_mode"] == "continue" for item in payload["workflows"]))
            self.assertTrue(all(item["product_path"]["rough_backend"]["codex_preflight_soft_failed"] for item in payload["workflows"]))
            self.assertTrue(all(item["product_path"]["direct_backend"]["codex_preflight_attempted"] for item in payload["workflows"]))
            self.assertTrue(all(item["product_path"]["rough_backend"]["session_backend_memory_considered"] for item in payload["workflows"]))
            self.assertTrue(all(item["product_path"]["rough_backend"]["session_backend_prior_category"] == "timeout" for item in payload["workflows"]))
            pion_rows = [item for item in payload["workflows"] if item["workflow"] in {"pion_2pt", "pion_2pt_existing_propagator"}]
            self.assertTrue(all(item["direct"]["execution_status"] == "failed" for item in pion_rows))
            self.assertTrue(all(item["direct"]["probe_status"] == "failed" for item in pion_rows))
            self.assertTrue(all(item["product_path"]["rough_backend"]["intent_primary_timeout_seconds"] == INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS for item in payload["workflows"]))
            self.assertTrue(all(item["product_path"]["rough_backend"]["timeout_recovery_used"] for item in payload["workflows"]))
            self.assertTrue(all(item["product_path"]["direct_backend"]["timeout_recovery_attempted"] for item in payload["workflows"]))


if __name__ == "__main__":
    unittest.main()
