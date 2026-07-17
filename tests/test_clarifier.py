import unittest

from pyquda_agent.tasks.clarifier import apply_answer
from pyquda_agent.tasks.clarifier import build_questions
from pyquda_agent.tasks.clarifier import determine_missing_fields
from pyquda_agent.tasks.schema import Pion2ptTaskDraft
from pyquda_agent.workflows.matcher import apply_workflow_match
from pyquda_agent.workflows.matcher import match_supported_workflow
from pyquda_agent.intent.interpreter import interpret_request


class ClarifierTests(unittest.TestCase):
    def test_missing_fields_and_answers(self):
        draft = Pion2ptTaskDraft(
            task_type="pion_2pt",
        )
        physics = interpret_request("generate complete pion two-point correlator")
        match = match_supported_workflow(physics, draft)
        apply_workflow_match(draft, physics, match)
        missing = determine_missing_fields(draft)
        self.assertIn("gauge_path", missing)
        self.assertEqual(draft.resource_path, ".cache/quda")
        self.assertEqual(draft.cluster_launch, "local")
        questions = build_questions(draft, max_questions=3)
        self.assertEqual(questions[0].field_name, "source_timeslices")
        self.assertEqual(questions[1].field_name, "gauge_fixed")
        self.assertEqual(questions[2].field_name, "mass")

        apply_answer(draft, "gauge_path", "/tmp/cfg_0001.lime")
        apply_answer(draft, "lattice_size", "24 24 24 72")
        apply_answer(draft, "grid_size", "1 1 1 2")
        apply_answer(draft, "mass", "0.09253")
        apply_answer(draft, "xi_0", "4.8965")
        apply_answer(draft, "nu", "0.86679")
        apply_answer(draft, "coeff_t", "0.8549165664")
        apply_answer(draft, "coeff_r", "2.32582045")
        apply_answer(draft, "solver_tol", "1e-12")
        apply_answer(draft, "solver_maxiter", "1000")
        apply_answer(draft, "source_timeslices", "0")
        apply_answer(draft, "gauge_fixed", "no")
        apply_answer(draft, "correlator_output_path", "outputs/pion.npy")
        apply_answer(draft, "resource_path", ".cache/quda")
        apply_answer(draft, "cluster_launch", "local")
        apply_answer(draft, "script_output_path", "outputs/run_pion.py")

        self.assertEqual(determine_missing_fields(draft), [])
        self.assertEqual(draft.momenta, [[0, 0, 0]])
        self.assertFalse(draft.gauge_fixed)
        self.assertEqual(draft.correlator_output_format, "npy")
        self.assertEqual(draft.cluster_launch, "local")
        self.assertEqual(draft.fixed_fields["source_type"], "wall")

    def test_dispersion_workflow_applies_point_source_and_fixed_momentum_list(self):
        draft = Pion2ptTaskDraft(
            task_type="pion_dispersion",
        )
        physics = interpret_request("please compute pion dispersion with nonzero momentum")
        match = match_supported_workflow(physics, draft)
        apply_workflow_match(draft, physics, match)
        missing = determine_missing_fields(draft)
        self.assertIn("gauge_path", missing)
        self.assertEqual(draft.source_type, "point")
        self.assertEqual(draft.momentum_projection, "explicit")
        self.assertEqual(len(draft.momenta), 9)
        self.assertFalse(draft.gauge_fixed)

    def test_pcac_workflow_applies_fixed_smear_and_zero_momentum_fields(self):
        draft = Pion2ptTaskDraft(task_type="pion_pcac")
        physics = interpret_request("please compute pion pcac ratio")
        match = match_supported_workflow(physics, draft)
        apply_workflow_match(draft, physics, match)
        missing = determine_missing_fields(draft)
        self.assertIn("gauge_path", missing)
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.momentum_projection, "zero")
        self.assertEqual(draft.momenta, [[0, 0, 0]])
        self.assertEqual(draft.stout_smear_steps, 1)
        self.assertEqual(draft.stout_smear_rho, 0.125)
        self.assertEqual(draft.multigrid_blocks, [[6, 6, 6, 4], [4, 4, 4, 9]])
        self.assertFalse(draft.gauge_fixed)

    def test_proton_workflow_applies_fixed_smear_and_multigrid_fields(self):
        draft = Pion2ptTaskDraft(
            task_type="proton_2pt",
        )
        physics = interpret_request("please compute the proton two-point correlator")
        match = match_supported_workflow(physics, draft)
        apply_workflow_match(draft, physics, match)
        missing = determine_missing_fields(draft)
        self.assertIn("gauge_path", missing)
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.momentum_projection, "zero")
        self.assertEqual(draft.stout_smear_steps, 1)
        self.assertEqual(draft.stout_smear_rho, 0.125)
        self.assertEqual(draft.stout_smear_ndim, 4)
        self.assertEqual(draft.multigrid_blocks, [[6, 6, 6, 4], [4, 4, 4, 9]])
        self.assertFalse(draft.gauge_fixed)

    def test_rho_workflow_applies_fixed_gamma_family_and_zero_momentum(self):
        draft = Pion2ptTaskDraft(task_type="rho_vector")
        physics = interpret_request("please compute the rho meson two-point correlator")
        match = match_supported_workflow(physics, draft)
        apply_workflow_match(draft, physics, match)
        missing = determine_missing_fields(draft)
        self.assertIn("gauge_path", missing)
        self.assertIn("source_timeslices", missing)
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.sink_type, "local")
        self.assertEqual(draft.gamma_insertions, ["gamma1_gamma1", "gamma2_gamma2", "gamma3_gamma3"])
        self.assertEqual(draft.momentum_projection, "zero")
        self.assertEqual(draft.momenta, [[0, 0, 0]])
        self.assertFalse(draft.gauge_fixed)

    def test_rho_propagator_entry_requires_source_timeslice_and_propagator_manifest(self):
        draft = Pion2ptTaskDraft(
            task_type="rho_vector",
            workflow_id="rho_vector_existing_propagator_local_zero_momentum_npy_v1",
            chosen_workflow_target="rho_vector_existing_propagator_local_zero_momentum_npy_v1",
            start_from="propagator",
            has_existing_propagators=True,
            propagator_paths=["/tmp/rho_prop_0.npy"],
            propagator_format="npy",
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            source_type="wall",
            sink_type="local",
            gamma_insertions=["gamma1_gamma1", "gamma2_gamma2", "gamma3_gamma3"],
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="outputs/rho.npy",
            script_style="complete",
        )
        missing = determine_missing_fields(draft)
        self.assertIn("source_timeslices", missing)
        self.assertNotIn("gauge_path", missing)
        self.assertNotIn("mass", missing)
        questions = build_questions(draft, max_questions=5)
        self.assertTrue(any(question.field_name == "source_timeslices" for question in questions))

        draft.source_timeslices = [0]
        draft.resource_path = ".cache/quda"
        draft.cluster_launch = "slurm"
        draft.script_output_path = "outputs/run_rho.py"
        self.assertEqual(determine_missing_fields(draft), [])

    def test_meson_spec_workflow_applies_fixed_gamma_family_and_skips_source_timeslice(self):
        draft = Pion2ptTaskDraft(task_type="meson_spec")
        physics = interpret_request("please compute meson spectroscopy correlators")
        match = match_supported_workflow(physics, draft)
        apply_workflow_match(draft, physics, match)
        missing = determine_missing_fields(draft)
        self.assertIn("gauge_path", missing)
        self.assertNotIn("source_timeslices", missing)
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.sink_type, "local")
        self.assertEqual(draft.gamma_insertions, ["gamma5_gamma5", "gamma4gamma5_gamma4gamma5"])
        self.assertEqual(draft.momentum_projection, "explicit")
        self.assertEqual(len(draft.momenta), 123)
        self.assertFalse(draft.gauge_fixed)

    def test_wilson_flow_workflow_requires_flow_parameters_but_not_solver_or_timeslice(self):
        draft = Pion2ptTaskDraft(task_type="wilson_flow")
        physics = interpret_request("please run wilson flow on this gauge configuration")
        match = match_supported_workflow(physics, draft)
        apply_workflow_match(draft, physics, match)
        missing = determine_missing_fields(draft)
        self.assertIn("gauge_path", missing)
        self.assertIn("flow_steps", missing)
        self.assertIn("flow_epsilon", missing)
        self.assertNotIn("source_timeslices", missing)
        self.assertNotIn("mass", missing)
        self.assertEqual(draft.source_type, "none")
        self.assertEqual(draft.momentum_projection, "none")

    def test_ape_smear_workflow_requires_gauge_entry_fields_but_not_solver_or_timeslice(self):
        draft = Pion2ptTaskDraft(task_type="ape_smear")
        physics = interpret_request("please generate an APE-smeared gauge configuration")
        match = match_supported_workflow(physics, draft)
        apply_workflow_match(draft, physics, match)
        missing = determine_missing_fields(draft)
        self.assertIn("gauge_path", missing)
        self.assertNotIn("source_timeslices", missing)
        self.assertNotIn("mass", missing)
        self.assertEqual(draft.source_type, "none")
        self.assertEqual(draft.sink_type, "gauge")
        self.assertEqual(draft.momentum_projection, "none")

    def test_hyp_smear_workflow_does_not_require_fermion_action(self):
        draft = Pion2ptTaskDraft(task_type="hyp_smear")
        physics = interpret_request("please generate a HYP-smeared gauge configuration")
        match = match_supported_workflow(physics, draft)
        apply_workflow_match(draft, physics, match)
        missing = determine_missing_fields(draft)
        self.assertIn("gauge_path", missing)
        self.assertNotIn("fermion_action", missing)
        self.assertNotIn("source_timeslices", missing)
        self.assertNotIn("mass", missing)
        self.assertEqual(draft.source_type, "none")
        self.assertEqual(draft.sink_type, "gauge")
        self.assertEqual(draft.momentum_projection, "none")

    def test_meson_spec_requires_temporal_grid_size_one(self):
        draft = Pion2ptTaskDraft(
            task_type="meson_spec",
            workflow_id="meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1",
            chosen_workflow_target="meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=0.09253,
            xi_0=4.8965,
            nu=0.86679,
            coeff_t=0.8549165664,
            coeff_r=2.32582045,
            solver_tol=1e-12,
            solver_maxiter=1000,
            source_type="wall",
            sink_type="local",
            gamma_insertions=["gamma5_gamma5", "gamma4gamma5_gamma4gamma5"],
            momentum_projection="explicit",
            momenta=[[0, 0, 0]],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="outputs/meson_spec.npy",
            resource_path=".cache/quda",
            cluster_launch="slurm",
            script_output_path="outputs/meson_spec.py",
            script_style="complete",
        )
        missing = determine_missing_fields(draft)
        self.assertEqual(missing, [])
        self.assertTrue(any("GRID_SIZE[3] == 1" in reason for reason in draft.unsupported_reasons))

    def test_propagator_entry_questions_skip_irrelevant_source_timeslice(self):
        draft = Pion2ptTaskDraft(
            task_type="pion_2pt",
            workflow_id="pion_2pt_existing_propagator_local_zero_momentum_npy_v1",
            chosen_workflow_target="pion_2pt_existing_propagator_local_zero_momentum_npy_v1",
            start_from="propagator",
            has_existing_propagators=True,
            propagator_paths=["/tmp/prop.npy"],
            propagator_format="npy",
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            source_type="wall",
            sink_type="local",
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            gauge_fixed=True,
            correlator_output_format="npy",
            correlator_output_path="outputs/pion.npy",
            script_style="complete",
        )
        missing = determine_missing_fields(draft)
        self.assertNotIn("source_timeslices", missing)
        questions = build_questions(draft, max_questions=5)
        self.assertFalse(any(question.field_name == "source_timeslices" for question in questions))
        self.assertEqual(questions[0].field_name, "script_output_path")

    def test_propagator_entry_accepts_point_source_but_not_volume_source(self):
        draft = Pion2ptTaskDraft(
            task_type="pion_2pt",
            workflow_id="pion_2pt_existing_propagator_local_zero_momentum_npy_v1",
            chosen_workflow_target="pion_2pt_existing_propagator_local_zero_momentum_npy_v1",
            start_from="propagator",
            has_existing_propagators=True,
            propagator_paths=["/tmp/prop.npy"],
            propagator_format="npy",
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            source_type="point",
            sink_type="local",
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            gauge_fixed=True,
            correlator_output_format="npy",
            correlator_output_path="outputs/pion.npy",
            resource_path=".cache/quda",
            cluster_launch="slurm",
            script_output_path="outputs/run_pion.py",
            script_style="complete",
        )
        self.assertEqual(determine_missing_fields(draft), [])

        draft.source_type = "volume"
        missing = determine_missing_fields(draft)
        self.assertEqual(missing, [])
        self.assertTrue(any("source_type" in reason for reason in draft.unsupported_reasons))

    def test_proton_propagator_entry_requires_matching_timeslices_and_wall_source(self):
        draft = Pion2ptTaskDraft(
            task_type="proton_2pt",
            workflow_id="proton_2pt_existing_propagator_local_zero_momentum_npy_v1",
            chosen_workflow_target="proton_2pt_existing_propagator_local_zero_momentum_npy_v1",
            start_from="propagator",
            has_existing_propagators=True,
            propagator_paths=["/tmp/proton_prop_a.npy", "/tmp/proton_prop_b.npy"],
            propagator_format="npy",
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            source_type="wall",
            sink_type="local",
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            source_timeslices=[0, 12],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="outputs/proton.npy",
            resource_path=".cache/quda",
            cluster_launch="slurm",
            script_output_path="outputs/run_proton.py",
            script_style="complete",
        )
        self.assertEqual(determine_missing_fields(draft), [])

        draft.source_timeslices = [0]
        missing = determine_missing_fields(draft)
        self.assertEqual(missing, [])
        self.assertTrue(any("len(source_timeslices)" in reason for reason in draft.unsupported_reasons))

        draft.source_timeslices = [0, 12]
        draft.source_type = "point"
        missing = determine_missing_fields(draft)
        self.assertEqual(missing, [])
        self.assertTrue(any("source_type" in reason for reason in draft.unsupported_reasons))

    def test_build_questions_preserves_complete_solver_group_when_it_dominates_batch(self):
        draft = Pion2ptTaskDraft(task_type="pion_2pt")
        physics = interpret_request("please compute the pion two-point correlator")
        match = match_supported_workflow(physics, draft)
        apply_workflow_match(draft, physics, match)

        apply_answer(draft, "source_timeslices", "0")
        apply_answer(draft, "gauge_fixed", "yes")
        apply_answer(draft, "gauge_path", "/tmp/cfg_0001.lime")
        apply_answer(draft, "lattice_size", "24 24 24 72")
        apply_answer(draft, "grid_size", "1 1 1 2")
        apply_answer(draft, "resource_path", ".cache/quda")
        apply_answer(draft, "cluster_launch", "slurm")
        apply_answer(draft, "correlator_output_path", "outputs/pion.npy")
        apply_answer(draft, "script_output_path", "outputs/run_pion.py")
        apply_answer(draft, "fermion_action", "clover")

        questions = build_questions(draft, max_questions=5)
        self.assertEqual(
            [question.field_name for question in questions],
            ["mass", "xi_0", "nu", "coeff_t", "coeff_r", "solver_tol", "solver_maxiter"],
        )


if __name__ == "__main__":
    unittest.main()
