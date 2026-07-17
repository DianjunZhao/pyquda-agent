import io
import json
import tempfile
import unittest
from contextlib import ExitStack
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pyquda_agent.cli import main


class SummaryContractTests(unittest.TestCase):
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
        (root / "docs" / "RUNNABLE_MESON_SPEC_SPEC.md").write_text("meson spec helper", encoding="utf-8")
        (root / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
        (root / "docs" / "RUN_WORKFLOW.md").write_text("workflow", encoding="utf-8")

        (pyquda / "examples" / "3_Pion_Proton_2pt.py").write_text("pion example", encoding="utf-8")
        (pyquda / "examples" / "5_Pion_Dispersion.py").write_text("dispersion", encoding="utf-8")
        (pyquda / "tests" / "test_mesonspec.py").write_text("mesonspec", encoding="utf-8")
        (pyquda / "tests" / "test_io.py").write_text("io test", encoding="utf-8")
        (pyquda / "pyquda_utils" / "source.py").write_text("wall source", encoding="utf-8")
        (pyquda / "pyquda_utils" / "core.py").write_text("invert core", encoding="utf-8")
        (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma", encoding="utf-8")
        (pyquda / "pyquda_utils" / "phase.py").write_text("phase", encoding="utf-8")
        (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge", encoding="utf-8")

        index_path.write_text(
            json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 3}}),
            encoding="utf-8",
        )
        return pyquda, output, index_path

    def _run_summary(self, root: Path, request: str, *, extra_args: list[str], backend_patch, extra_patches=None):
        pyquda, output, index_path = self._prepare_repo_fixture(root)
        stdout = io.StringIO()
        argv = [
            "run",
            request,
            "--summary-only",
            "--no-interactive",
            "--pyquda-repo",
            str(pyquda),
            "--output",
            str(output),
            *extra_args,
        ]
        extra_patches = list(extra_patches or [])
        with ExitStack() as stack:
            stack.enter_context(patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path))
            stack.enter_context(backend_patch)
            for item in extra_patches:
                stack.enter_context(item)
            with redirect_stdout(stdout):
                exit_code = main(argv)
        return exit_code, json.loads(stdout.getvalue())

    def test_contract_needs_input_backend_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exit_code, payload = self._run_summary(
                root,
                "please compute the pion two-point correlator",
                extra_args=["--dry-run"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "codex",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked test fallback",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["schema_family"], "pyquda_agent.result_summary")
            self.assertEqual(payload["schema_version"], "2026-07-v1")
            self.assertEqual(payload["product_status"], "needs_input")
            self.assertEqual(payload["delivery_status"]["generation"]["phase"], "blocked_on_input")
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "blocked_by_generation")
            self.assertEqual(payload["generation_result"]["phase"], "blocked_on_input")
            self.assertFalse(payload["generation_result"]["ready"])
            self.assertFalse(payload["generation_result"]["emitted"])
            self.assertEqual(
                payload["clarification_gap_summary"]["sentence"],
                "Current missing conditions by scope: Physics: source_timeslices, gauge_fixed; Implementation: mass, xi_0, nu, coeff_t, coeff_r, solver_tol, solver_maxiter. Additional fields remain after this batch.",
            )
            self.assertEqual(
                payload["clarification_batch_card"]["current_batch_display_fields"],
                [
                    "source_timeslices",
                    "gauge_fixed",
                    "mass",
                    "xi_0",
                    "nu",
                    "coeff_t",
                    "coeff_r",
                    "solver_tol",
                    "solver_maxiter",
                ],
            )
            self.assertEqual(payload["clarification_batch_card"]["remaining_after_batch_count"], 3)
            self.assertEqual(payload["clarification_batch_card"]["field_group_ids"], ["clover_solver_parameters"])
            self.assertEqual(payload["clarification_batch_card"]["next_milestone"], "further_clarification")
            self.assertEqual(payload["execution_result"]["phase"], "blocked_by_generation")
            self.assertEqual(payload["workflow_lifecycle"]["stage"], "needs_input")
            self.assertEqual(payload["workflow_lifecycle"]["blocking_kind"], "backend_fallback")
            self.assertEqual(payload["workflow_lifecycle"]["generation"]["phase"], "blocked_on_input")
            self.assertEqual(payload["workflow_lifecycle"]["runtime"]["phase"], "blocked_by_generation")
            self.assertEqual(payload["workflow_lifecycle"]["next"]["action_kind"], "continue_by_set")
            self.assertEqual(payload["primary_action"]["priority"], "primary")
            self.assertEqual(payload["workflow_outcome"]["recommended_command"], payload["workflow_lifecycle"]["next"]["command"])
            self.assertFalse(payload["execution_result"]["attempted"])
            self.assertEqual(payload["execution_result"]["runtime_level"], "structurally_grounded")
            self.assertEqual(payload["execution_result"]["evidence_level"], "structurally_grounded")
            self.assertEqual(payload["runtime_diagnostic"]["runtime_level"], "structurally_grounded")
            self.assertEqual(payload["runtime_diagnostic"]["evidence_level"], "structurally_grounded")
            self.assertEqual(payload["capability_summary"]["runtime"]["level"], "structurally_grounded")
            self.assertEqual(payload["capability_summary"]["runtime"]["evidence_level"], "structurally_grounded")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "backend_fallback")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_fallback")
            self.assertEqual(payload["frontend_profile"]["status_card"]["product_status"], "needs_input")
            self.assertEqual(payload["frontend_profile"]["status_card"]["blocking_kind"], "backend_fallback")
            self.assertEqual(payload["frontend_profile"]["status_card"]["blocking_reason_category"], "backend_fallback")

    def test_contract_ambiguous_meson_summary_exposes_formula_preview(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exit_code, payload = self._run_summary(
                root,
                "I want a meson correlator script but I am not sure about the exact operator",
                extra_args=["--dry-run"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "codex",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked test fallback",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "needs_input")
            self.assertTrue(payload["physics_candidate_preview"])
            self.assertEqual(
                payload["physics_candidate_preview"][0]["target_id"],
                "meson_two_point_correlator_unspecified",
            )
            self.assertTrue(payload["physics_formula_preview"])
            self.assertEqual(
                payload["physics_formula_preview"][0]["proposal_id"],
                "meson_operator_needs_channel_choice",
            )
            self.assertEqual(
                payload["physics_formula_preview"][0]["operator"],
                "Underspecified",
            )
            self.assertEqual(
                payload["physics_formula_preview"][0]["provenance"],
                "model_inference",
            )
            self.assertTrue(payload["physics_formula_preview_truncated"])
            self.assertIn("channel/operator choice", payload["physics_formula_preview"][0]["label"])
            self.assertTrue(payload["physics_workflow_preview"])
            self.assertEqual(
                payload["physics_workflow_preview"][0]["target_id"],
                "meson_two_point_correlator_unspecified",
            )
            self.assertEqual(payload["physics_workflow_preview"][0]["availability"], "grounded")
            self.assertIn(
                "pion_2pt_chroma_wall_local_zero_momentum_npy_v1",
                payload["physics_workflow_preview"][0]["grounded_workflow_targets"],
            )
            self.assertIn(
                "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1",
                payload["physics_workflow_preview"][0]["grounded_workflow_targets"],
            )
            self.assertIn("Confirm the physics target", payload["next_action"])
            self.assertIn("Candidates: meson_two_point_correlator_unspecified", payload["next_action"])
            self.assertIn("Formula hints:", payload["next_action"])
            self.assertIn("Workflow hints:", payload["next_action"])
            self.assertIn("meson_two_point_correlator_unspecified -> pion_2pt_chroma_wall_local_zero_momentum_npy_v1", payload["next_action"])
            self.assertIn("meson: Meson two-point correlator requires channel/operator choice", payload["next_action"])
            self.assertNotIn("候选公式/operator/假设包括", payload["next_action"])

    def test_contract_rough_gauge_smear_summary_exposes_candidate_smear_families(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exit_code, payload = self._run_summary(
                root,
                "please smear this gauge field and save the result",
                extra_args=["--dry-run"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "codex",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked test fallback",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "needs_input")
            self.assertEqual(
                [item["target_id"] for item in payload["physics_candidate_preview"][:3]],
                [
                    "stout_smeared_gauge_configuration",
                    "ape_smeared_gauge_configuration",
                    "hyp_smeared_gauge_configuration",
                ],
            )
            self.assertTrue(payload["physics_formula_preview"])
            self.assertEqual(
                [item["target_id"] for item in payload["physics_workflow_preview"][:3]],
                [
                    "stout_smeared_gauge_configuration",
                    "ape_smeared_gauge_configuration",
                    "hyp_smeared_gauge_configuration",
                ],
            )
            self.assertTrue(
                all(item["availability"] == "grounded" for item in payload["physics_workflow_preview"][:3])
            )
            self.assertIn("Formula hints:", payload["next_action"])
            self.assertIn("Workflow hints:", payload["next_action"])
            self.assertIn("Candidates: stout_smeared_gauge_configuration, ape_smeared_gauge_configuration, hyp_smeared_gauge_configuration.", payload["next_action"])
            self.assertIn("stout smear: One-step stout-smeared gauge configuration", payload["next_action"])

    def test_contract_backend_fallback_keeps_session_backend_memory_considered(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exit_code, payload = self._run_summary(
                root,
                "please compute the pion two-point correlator",
                extra_args=["--backend", "auto", "--model", "openai/gpt-5-mini", "--dry-run"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "auto",
                            "selected_backend": "rules",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_category": "credentials_missing",
                            "fallback_reason": "API backend requested for openai/gpt-5-mini, but no API key was configured.",
                            "session_backend_memory_considered": True,
                            "session_backend_memory_used": False,
                            "session_backend_memory_reason": "Auto mode reused backend memory from the resumed session and preferred the configured API backend because the last codex-assisted attempt degraded with timeout.",
                            "session_backend_prior_category": "timeout",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["llm_session_backend_memory_considered"])
            self.assertFalse(payload["llm_session_backend_memory_used"])
            self.assertEqual(payload["llm_session_backend_prior_category"], "timeout")
            self.assertTrue(payload["backend_diagnostic"]["session_backend_memory_considered"])
            self.assertFalse(payload["backend_diagnostic"]["session_backend_memory_used"])
            self.assertEqual(payload["backend_diagnostic"]["session_backend_prior_category"], "timeout")

    def test_contract_ready_to_generate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request = (
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda"
            )
            exit_code, payload = self._run_summary(
                root,
                request,
                extra_args=["--dry-run"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "codex",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked test fallback",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "ready_to_generate")
            self.assertEqual(payload["delivery_status"]["generation"]["phase"], "ready_to_generate")
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "blocked_by_generation")
            self.assertEqual(payload["generation_result"]["phase"], "ready_to_generate")
            self.assertTrue(payload["generation_result"]["ready"])
            self.assertFalse(payload["generation_result"]["emitted"])
            self.assertEqual(payload["execution_result"]["phase"], "blocked_by_generation")
            self.assertEqual(payload["workflow_lifecycle"]["stage"], "ready_to_generate")
            self.assertEqual(payload["workflow_lifecycle"]["generation"]["phase"], "ready_to_generate")
            self.assertEqual(payload["workflow_lifecycle"]["runtime"]["phase"], "blocked_by_generation")
            self.assertEqual(payload["workflow_lifecycle"]["next"]["action_kind"], "generate_script")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "backend_fallback")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_fallback")

    def test_contract_generated_probe_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request = (
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda"
            )
            exit_code, payload = self._run_summary(
                root,
                request,
                extra_args=["--backend", "api"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "generated_probe_available")
            self.assertEqual(payload["delivery_status"]["generation"]["phase"], "generated")
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "probe_available")
            self.assertEqual(payload["generation_result"]["phase"], "generated")
            self.assertTrue(payload["generation_result"]["emitted"])
            self.assertEqual(payload["execution_result"]["phase"], "probe_available")
            self.assertTrue(payload["execution_result"]["probe_available"])
            self.assertEqual(payload["execution_closure"]["state"], "generated_not_probed")
            self.assertEqual(payload["execution_closure"]["next_artifact"], "script")
            self.assertEqual(payload["execution_checkpoint"]["state"], "generated_not_probed")
            self.assertEqual(payload["execution_checkpoint"]["runtime_probe_status"], "not_requested")
            self.assertTrue(payload["execution_checkpoint"]["hpc_handoff_ready"])
            self.assertEqual(payload["hpc_handoff"]["output_writer_policy"], "rank0_only")
            self.assertEqual(payload["hpc_handoff"]["input_path_count"], 1)
            self.assertEqual(payload["hpc_handoff"]["input_manifest"][0]["kind"], "gauge")
            self.assertEqual(
                payload["hpc_handoff"]["input_directory_policy"],
                "treat_gauge_input_directories_as_shared_read_only_storage_when_possible",
            )
            self.assertEqual(payload["hpc_handoff"]["input_mutability_policy"], "immutable_inputs_never_overwritten")
            self.assertEqual(payload["hpc_handoff"]["output_directory_count"], 1)
            self.assertEqual(
                payload["hpc_handoff"]["output_directory_policy"],
                "write_new_outputs_to_explicit_writable_results_directory",
            )
            self.assertFalse(payload["hpc_handoff"]["output_input_overlap_forbidden"])
            self.assertTrue(payload["hpc_handoff"]["probe_artifact"].endswith(".probe.json"))
            self.assertEqual(payload["workflow_lifecycle"]["stage"], "generated_probe_available")
            self.assertEqual(payload["workflow_lifecycle"]["generation"]["phase"], "generated")
            self.assertEqual(payload["workflow_lifecycle"]["runtime"]["phase"], "probe_available")
            self.assertEqual(payload["workflow_lifecycle"]["next"]["action_kind"], "run_probe")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "runtime_probe_optional")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "runtime_probe_not_run")
            self.assertEqual(payload["frontend_profile"]["status_card"]["product_status"], "generated_probe_available")
            self.assertEqual(payload["frontend_profile"]["capabilities"]["runtime_state"], "probe_available")
            self.assertEqual(payload["frontend_profile"]["next"]["action_kind"], "run_probe")
            self.assertEqual(payload["frontend_profile"]["inspect"]["artifact_key"], "probe")

    def test_contract_propagator_entry_handoff_exposes_input_manifest_and_immutability(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request = (
                "generate complete pion 2pt from existing propagator /tmp/pt_prop_0.npy /tmp/pt_prop_8.npy "
                "wall source local sink zero momentum timeslice 0 timeslice 8 lattice size 24 24 24 72 "
                "grid 1 1 1 2 gauge fixed outputs/pion_prop.npy outputs/run_pion_prop.py "
                "resource_path=.cache/quda cluster_launch=local"
            )
            exit_code, payload = self._run_summary(
                root,
                request,
                extra_args=["--backend", "api"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "generated_probe_available")
            self.assertEqual(payload["workflow_target"], "pion_2pt_existing_propagator_local_zero_momentum_npy_v1")
            self.assertEqual(payload["hpc_handoff"]["start_from"], "propagator")
            self.assertEqual(payload["hpc_handoff"]["input_path_count"], 2)
            self.assertEqual(
                payload["hpc_handoff"]["input_directory_policy"],
                "treat_input_directories_as_read_only_handoff_storage",
            )
            self.assertEqual(payload["hpc_handoff"]["input_mutability_policy"], "immutable_inputs_never_overwritten")
            self.assertEqual(
                payload["hpc_handoff"]["output_directory_policy"],
                "prefer_dedicated_writable_results_directory",
            )
            self.assertTrue(payload["hpc_handoff"]["output_input_overlap_forbidden"])
            self.assertEqual(
                [item["source_timeslice"] for item in payload["hpc_handoff"]["input_manifest"]],
                [0, 8],
            )
            self.assertTrue(all(item["kind"] == "propagator" for item in payload["hpc_handoff"]["input_manifest"]))
            self.assertIn("Stored propagators are the handoff boundary", payload["hpc_handoff"]["handoff_boundary"])
            self.assertTrue(any("immutable handoff artifacts" in item for item in payload["hpc_handoff"]["preflight_checks"]))
            self.assertTrue(any("nearest existing parent" in item for item in payload["hpc_handoff"]["preflight_checks"]))
            self.assertTrue(any("dedicated writable results directory" in item for item in payload["hpc_handoff"]["preflight_checks"]))

    def test_contract_rho_propagator_entry_handoff_exposes_input_manifest_and_immutability(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request = (
                "generate complete rho vector correlator from existing propagator /tmp/rho_prop_0.npy /tmp/rho_prop_8.npy "
                "wall source local sink zero momentum timeslice 0 timeslice 8 lattice size 24 24 24 72 "
                "grid 1 1 1 2 outputs/rho_vector.npy outputs/run_rho_vector.py "
                "resource_path=.cache/quda cluster_launch=local"
            )
            exit_code, payload = self._run_summary(
                root,
                request,
                extra_args=["--backend", "api"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "generated_probe_available")
            self.assertEqual(payload["workflow_target"], "rho_vector_existing_propagator_local_zero_momentum_npy_v1")
            self.assertEqual(payload["hpc_handoff"]["start_from"], "propagator")
            self.assertEqual(payload["hpc_handoff"]["input_path_count"], 2)
            self.assertEqual(
                payload["hpc_handoff"]["input_directory_policy"],
                "treat_input_directories_as_read_only_handoff_storage",
            )
            self.assertEqual(payload["hpc_handoff"]["input_mutability_policy"], "immutable_inputs_never_overwritten")
            self.assertEqual(
                payload["hpc_handoff"]["output_directory_policy"],
                "prefer_dedicated_writable_results_directory",
            )
            self.assertTrue(payload["hpc_handoff"]["output_input_overlap_forbidden"])
            self.assertEqual(
                [item["source_timeslice"] for item in payload["hpc_handoff"]["input_manifest"]],
                [0, 8],
            )
            self.assertTrue(all(item["kind"] == "propagator" for item in payload["hpc_handoff"]["input_manifest"]))
            self.assertIn("Stored propagators are the handoff boundary", payload["hpc_handoff"]["handoff_boundary"])
            self.assertTrue(any("immutable handoff artifacts" in item for item in payload["hpc_handoff"]["preflight_checks"]))
            self.assertTrue(any("nearest existing parent" in item for item in payload["hpc_handoff"]["preflight_checks"]))
            self.assertTrue(any("dedicated writable results directory" in item for item in payload["hpc_handoff"]["preflight_checks"]))
            self.assertEqual(payload["execution_checkpoint"]["state"], "generated_not_probed")
            self.assertTrue(payload["execution_checkpoint"]["hpc_handoff_ready"])

    def test_contract_generated_runtime_blocked_environment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request = (
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda"
            )
            probe_payload = {
                "status": "runtime_missing",
                "runtime_level": "environment_missing",
                "evidence_levels": {
                    "runtime_ready": False,
                    "runtime_proved": False,
                    "current_level": "environment_missing",
                    "blockers": ["Missing runtime dependency 'cupy'"],
                },
            }
            exit_code, payload = self._run_summary(
                root,
                request,
                extra_args=["--backend", "api", "--runtime-probe"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ),
                extra_patches=[
                    patch("pyquda_agent.app.build_generated_probe", return_value=probe_payload),
                ],
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "generated_runtime_blocked")
            self.assertEqual(payload["delivery_status"]["generation"]["phase"], "generated")
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "runtime_missing")
            self.assertEqual(payload["generation_result"]["phase"], "generated")
            self.assertEqual(payload["execution_result"]["phase"], "runtime_missing")
            self.assertTrue(payload["execution_result"]["attempted"])
            self.assertTrue(payload["execution_result"]["blocked"])
            self.assertEqual(payload["execution_closure"]["state"], "runtime_environment_missing")
            self.assertEqual(payload["execution_closure"]["next_artifact"], "probe")
            self.assertEqual(payload["execution_checkpoint"]["state"], "runtime_environment_missing")
            self.assertEqual(payload["execution_checkpoint"]["diagnostic_category"], "environment_missing")
            self.assertTrue(payload["execution_checkpoint"]["hpc_handoff_ready"])
            self.assertEqual(payload["workflow_lifecycle"]["stage"], "generated_runtime_blocked")
            self.assertEqual(payload["workflow_lifecycle"]["runtime"]["phase"], "runtime_missing")
            self.assertEqual(payload["workflow_lifecycle"]["next"]["action_kind"], "retry_probe")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "runtime_environment")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "runtime_dependencies_missing")

    def test_contract_runtime_proved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request = (
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda"
            )
            probe_payload = {
                "status": "ok",
                "runtime_level": "runtime_proved",
                "evidence_levels": {
                    "runtime_ready": True,
                    "runtime_proved": True,
                    "current_level": "runtime_proved",
                    "blockers": [],
                },
            }
            exit_code, payload = self._run_summary(
                root,
                request,
                extra_args=["--backend", "api", "--runtime-probe"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ),
                extra_patches=[
                    patch("pyquda_agent.app.build_generated_probe", return_value=probe_payload),
                ],
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "runtime_proved")
            self.assertEqual(payload["delivery_status"]["generation"]["phase"], "generated")
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "runtime_proved")
            self.assertEqual(payload["generation_result"]["phase"], "generated")
            self.assertEqual(payload["execution_result"]["phase"], "runtime_proved")
            self.assertTrue(payload["execution_result"]["attempted"])
            self.assertTrue(payload["execution_result"]["succeeded"])
            self.assertEqual(payload["workflow_outcome"]["runtime_probe_status"], "ok")
            self.assertEqual(payload["workflow_lifecycle"]["stage"], "runtime_proved")
            self.assertEqual(payload["workflow_lifecycle"]["runtime"]["phase"], "runtime_proved")
            self.assertEqual(payload["execution_checkpoint"]["state"], "runtime_proved")
            self.assertEqual(payload["execution_checkpoint"]["runtime_level"], "runtime_proved")
            self.assertTrue(payload["execution_checkpoint"]["hpc_handoff_ready"])
            self.assertEqual(payload["run_overview"]["blocking_kind"], "none")
            self.assertIsNone(payload["run_overview"]["primary_action_kind"])
            self.assertIsNone(payload["primary_action"])
            self.assertEqual(payload["action_queue"], [])
            self.assertIsNone(payload["blocking_reason_detail"])
            self.assertEqual(payload["inspection_hint"]["artifact_key"], "probe")
            self.assertEqual(payload["frontend_profile"]["status_card"]["product_status"], "runtime_proved")
            self.assertEqual(payload["frontend_profile"]["capabilities"]["runtime_state"], "runtime_proved")
            self.assertTrue(payload["frontend_profile"]["capabilities"]["runtime_proved"])
            self.assertEqual(payload["frontend_profile"]["inspect"]["artifact_key"], "probe")

    def test_contract_backend_credentials_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exit_code, payload = self._run_summary(
                root,
                "please compute the pion two-point correlator",
                extra_args=["--backend", "api", "--dry-run"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "API backend requested for openai/gpt-5-mini, but no API key was configured.",
                            "fallback_category": "credentials_missing",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "needs_input")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "backend_fallback")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_credentials_missing")
            self.assertEqual(payload["backend_path"]["category"], "credentials_missing")
            self.assertTrue(payload["backend_path"]["continue_with_current_result"])

    def test_contract_backend_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exit_code, payload = self._run_summary(
                root,
                "please compute the pion two-point correlator",
                extra_args=["--backend", "codex", "--dry-run", "--llm-timeout", "5"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "codex",
                            "selected_backend": "rules",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "Explicit codex backend failed preflight (mock timeout), so the run will use the rule-based path.",
                            "fallback_category": "timeout",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "needs_input")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "backend_fallback")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_timeout")

    def test_contract_backend_endpoint_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exit_code, payload = self._run_summary(
                root,
                "please compute the pion two-point correlator",
                extra_args=["--backend", "api", "--model", "openai/gpt-5-mini", "--dry-run"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": True,
                            "backend_name": "api:openai/gpt-5-mini",
                            "fallback": True,
                            "fallback_reason": "API request failed with status 404",
                            "fallback_category": "endpoint_not_found",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "needs_input")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "backend_fallback")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_endpoint_not_found")

    def test_contract_backend_response_parse_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exit_code, payload = self._run_summary(
                root,
                "please compute the pion two-point correlator",
                extra_args=["--backend", "api", "--model", "openai/gpt-5-mini", "--dry-run"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": True,
                            "backend_name": "api:openai/gpt-5-mini",
                            "fallback": True,
                            "fallback_reason": "API response did not contain choices[0].message.content",
                            "fallback_category": "response_parse_error",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "needs_input")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "backend_fallback")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_response_parse_error")

    def test_contract_backend_local_environment_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exit_code, payload = self._run_summary(
                root,
                "please compute the pion two-point correlator",
                extra_args=["--backend", "codex", "--dry-run"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "codex",
                            "selected_backend": "rules",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "Codex backend failed during local app-client initialization.",
                            "fallback_category": "local_environment_error",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "needs_input")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "backend_fallback")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_local_environment_error")

    def test_contract_backend_service_unavailable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exit_code, payload = self._run_summary(
                root,
                "please compute the pion two-point correlator",
                extra_args=["--backend", "api", "--model", "openai/gpt-5-mini", "--dry-run"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": True,
                            "backend_name": "api:openai/gpt-5-mini",
                            "fallback": True,
                            "fallback_reason": "API request failed with status 503",
                            "fallback_category": "upstream_service_error",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "needs_input")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "backend_fallback")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_service_unavailable")

    def test_contract_runtime_probe_harness_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request = (
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda"
            )
            probe_payload = {
                "status": "probe_driver_failed",
                "runtime_level": "probe_driver_failed",
                "evidence_levels": {
                    "runtime_ready": False,
                    "runtime_proved": False,
                    "current_level": "probe_driver_failed",
                    "blockers": ["mock probe harness failure"],
                },
                "probe_driver_error": {"type": "RuntimeError", "message": "mock probe harness failure"},
            }
            exit_code, payload = self._run_summary(
                root,
                request,
                extra_args=["--backend", "api", "--runtime-probe"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ),
                extra_patches=[
                    patch("pyquda_agent.app.build_generated_probe", return_value=probe_payload),
                ],
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "generated_runtime_blocked")
            self.assertEqual(payload["delivery_status"]["generation"]["phase"], "generated")
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "probe_driver_failed")
            self.assertEqual(payload["generation_result"]["phase"], "generated")
            self.assertEqual(payload["execution_result"]["phase"], "probe_driver_failed")
            self.assertTrue(payload["execution_result"]["attempted"])
            self.assertTrue(payload["execution_result"]["blocked"])
            self.assertEqual(payload["execution_closure"]["state"], "probe_harness_failed")
            self.assertEqual(payload["execution_closure"]["next_artifact"], "probe")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "probe_driver")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "runtime_probe_harness_failed")

    def test_contract_unsupported(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            request = (
                "generate complete pion 2pt from existing propagator /tmp/prop_a.npy volume source "
                "local sink zero momentum gauge fixed lattice size 4 4 4 8 grid 1 1 1 1 "
                "resource_path=.cache/quda cluster_launch=local"
            )
            exit_code, payload = self._run_summary(
                root,
                request,
                extra_args=["--backend", "api", "--dry-run"],
                backend_patch=patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "API backend requested but no model was configured via --model or PYQUDA_AGENT_API_MODEL/OPENAI_MODEL.",
                            "fallback_category": "configuration_missing",
                        },
                    ),
                ),
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["product_status"], "unsupported")
            self.assertEqual(payload["delivery_status"]["generation"]["phase"], "unsupported")
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "unsupported")
            self.assertEqual(payload["generation_result"]["phase"], "unsupported")
            self.assertEqual(payload["execution_result"]["phase"], "unsupported")
            self.assertEqual(payload["execution_closure"]["state"], "unsupported")
            self.assertEqual(payload["execution_closure"]["next_artifact"], "physics")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "unsupported")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "unsupported_request")


if __name__ == "__main__":
    unittest.main()
