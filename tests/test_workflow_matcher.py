import unittest

from pyquda_agent.intent.interpreter import interpret_request
from pyquda_agent.tasks.parser import parse_task_description
from pyquda_agent.workflows.matcher import apply_workflow_match
from pyquda_agent.workflows.matcher import match_supported_workflow


class WorkflowMatcherTests(unittest.TestCase):
    def test_confirmed_pion_target_matches_supported_workflow(self):
        physics = interpret_request("please compute the pion two-point correlator")
        draft = parse_task_description("gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "pion_2pt_chroma_wall_local_zero_momentum_npy_v1")
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.sink_type, "local")

    def test_pion_like_request_without_confirmation_does_not_silently_match(self):
        physics = interpret_request("write a simple PyQUDA script for pi meson two-point")
        draft = parse_task_description("outputs/run_pion.py")
        match = match_supported_workflow(physics, draft)
        self.assertFalse(match.matched)
        self.assertIn("not confirmed", match.unsupported_reasons[0])

    def test_confirmed_pion_dispersion_target_matches_supported_workflow(self):
        physics = interpret_request("please compute pion dispersion with nonzero momentum")
        draft = parse_task_description("gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "pion_dispersion_chroma_point_momentum_npy_v1")
        self.assertEqual(draft.source_type, "point")
        self.assertEqual(draft.momentum_projection, "explicit")
        self.assertEqual(len(draft.momenta), 9)

    def test_confirmed_pion_pcac_target_matches_supported_workflow(self):
        physics = interpret_request("please compute pion pcac ratio")
        draft = parse_task_description("gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "pion_pcac_chroma_wall_local_zero_momentum_npy_v1")
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.stout_smear_steps, 1)
        self.assertEqual(draft.multigrid_blocks, [[6, 6, 6, 4], [4, 4, 4, 9]])

    def test_pion_pcac_existing_propagator_matches_grounded_branch(self):
        physics = interpret_request("please compute pion pcac ratio")
        draft = parse_task_description(
            "compute pion pcac ratio from existing propagator /tmp/pcac_prop_0.npy "
            "wall source zero momentum not gauge fixed timeslice 0 lattice size 24 24 24 72 grid 1 1 1 2 "
            "outputs/pion_pcac.npy outputs/run_pion_pcac.py"
        )
        draft.correlator_output_format = "npy"
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "pion_pcac_existing_propagator_local_zero_momentum_npy_v1")
        self.assertEqual(draft.start_from, "propagator")
        self.assertTrue(draft.has_existing_propagators)
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.sink_type, "local")
        self.assertEqual(draft.momenta, [[0, 0, 0]])

    def test_pion_pcac_existing_propagator_without_paths_still_matches_for_clarification(self):
        physics = interpret_request("please compute pion pcac ratio from existing propagator")
        draft = parse_task_description("generate complete pion pcac ratio from existing propagator outputs/run_pion_pcac.py")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        self.assertEqual(match.workflow_target, "pion_pcac_existing_propagator_local_zero_momentum_npy_v1")

    def test_confirmed_pion_dispersion_target_accepts_grounded_momentum_subset(self):
        physics = interpret_request("please compute pion dispersion with nonzero momentum")
        draft = parse_task_description(
            "gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2 "
            "momentum [0,0,0] momentum [1,1,1]"
        )
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "pion_dispersion_chroma_point_momentum_npy_v1")
        self.assertEqual(draft.momenta, [[0, 0, 0], [1, 1, 1]])

    def test_confirmed_pion_dispersion_target_rejects_ungrounded_momentum(self):
        physics = interpret_request("please compute pion dispersion with nonzero momentum")
        draft = parse_task_description(
            "gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2 "
            "momentum [3,0,0]"
        )
        match = match_supported_workflow(physics, draft)
        self.assertFalse(match.matched)
        self.assertTrue(any("9-momentum family" in reason for reason in match.unsupported_reasons))

    def test_confirmed_meson_spec_target_matches_supported_workflow(self):
        physics = interpret_request("please compute meson spectroscopy correlators")
        draft = parse_task_description("gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 1")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1")
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.sink_type, "local")
        self.assertEqual(draft.gamma_insertions, ["gamma5_gamma5", "gamma4gamma5_gamma4gamma5"])
        self.assertEqual(draft.momentum_projection, "explicit")
        self.assertEqual(len(draft.momenta), 123)

    def test_confirmed_meson_spec_target_accepts_grounded_momentum_subset(self):
        physics = interpret_request("please compute meson spectroscopy correlators")
        draft = parse_task_description(
            "gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 1 "
            "momentum [0,0,0] momentum [1,1,1]"
        )
        draft.momentum_projection = "explicit"
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.momenta, [[0, 0, 0], [1, 1, 1]])

    def test_confirmed_rho_target_matches_narrow_grounded_workflow(self):
        physics = interpret_request("please compute the rho meson two-point correlator")
        draft = parse_task_description("outputs/run_rho.py")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        self.assertEqual(match.workflow_target, "rho_vector_chroma_wall_local_zero_momentum_npy_v1")
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.task_type, "rho_vector")
        self.assertEqual(draft.gamma_insertions, ["gamma1_gamma1", "gamma2_gamma2", "gamma3_gamma3"])
        self.assertEqual(draft.momenta, [[0, 0, 0]])

    def test_confirmed_rho_target_matches_existing_propagator_branch(self):
        physics = interpret_request("please compute the rho meson two-point correlator")
        draft = parse_task_description(
            "compute the rho meson two-point correlator from existing propagator /tmp/rho_prop_0.npy "
            "wall source zero momentum not gauge fixed timeslice 0 lattice size 24 24 24 72 grid 1 1 1 2 "
            "outputs/rho.npy outputs/run_rho.py"
        )
        draft.correlator_output_format = "npy"
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        self.assertEqual(match.workflow_target, "rho_vector_existing_propagator_local_zero_momentum_npy_v1")
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.start_from, "propagator")
        self.assertTrue(draft.has_existing_propagators)
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.gamma_insertions, ["gamma1_gamma1", "gamma2_gamma2", "gamma3_gamma3"])
        self.assertEqual(draft.momenta, [[0, 0, 0]])

    def test_rho_existing_propagator_rejects_point_source(self):
        physics = interpret_request("please compute the rho meson two-point correlator")
        draft = parse_task_description(
            "compute the rho meson two-point correlator from existing propagator /tmp/rho_prop_0.npy "
            "point source zero momentum not gauge fixed timeslice 0 lattice size 24 24 24 72 grid 1 1 1 2 "
            "outputs/rho.npy outputs/run_rho.py"
        )
        draft.correlator_output_format = "npy"
        match = match_supported_workflow(physics, draft)
        self.assertFalse(match.matched)
        self.assertTrue(any("source_type" in reason for reason in match.unsupported_reasons))

    def test_confirmed_neutron_target_is_explicitly_unsupported_with_nearest_grounded_baryons(self):
        physics = interpret_request("please compute the neutron two-point correlator")
        draft = parse_task_description("outputs/run_neutron.py")
        match = match_supported_workflow(physics, draft)
        self.assertFalse(match.matched)
        self.assertTrue(any("neutron two-point correlator target" in reason.lower() for reason in match.unsupported_reasons))
        self.assertTrue(any("proton_2pt_chroma_wall_local_zero_momentum_npy_v1" in reason for reason in match.unsupported_reasons))

    def test_confirmed_meson_spec_target_rejects_ungrounded_momentum(self):
        physics = interpret_request("please compute meson spectroscopy correlators")
        draft = parse_task_description(
            "gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 1 "
            "momentum [4,0,0]"
        )
        draft.momentum_projection = "explicit"
        match = match_supported_workflow(physics, draft)
        self.assertFalse(match.matched)
        self.assertTrue(any("|p|^2<=9 family" in reason for reason in match.unsupported_reasons))

    def test_meson_spec_existing_propagator_matches_grounded_branch(self):
        physics = interpret_request("please compute meson spectroscopy correlators")
        draft = parse_task_description(
            "compute meson spectroscopy correlators from existing propagator /tmp/meson_prop_0.npy "
            "wall source momentum [0,0,0] momentum [1,1,1] timeslice 0 "
            "lattice size 24 24 24 72 grid 1 1 1 1 outputs/meson_spec.npy outputs/run_meson_spec.py"
        )
        draft.momentum_projection = "explicit"
        draft.gauge_fixed = False
        draft.correlator_output_format = "npy"
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1")
        self.assertEqual(draft.start_from, "propagator")
        self.assertTrue(draft.has_existing_propagators)
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.gamma_insertions, ["gamma5_gamma5", "gamma4gamma5_gamma4gamma5"])
        self.assertEqual(draft.momenta, [[0, 0, 0], [1, 1, 1]])

    def test_meson_spec_existing_propagator_without_paths_still_matches_for_clarification(self):
        physics = interpret_request("please compute meson spectroscopy correlators from existing propagator")
        draft = parse_task_description("generate complete meson spectroscopy correlators from existing propagator outputs/run_meson_spec.py")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        self.assertEqual(match.workflow_target, "meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1")

    def test_meson_spec_existing_propagator_rejects_point_source(self):
        physics = interpret_request("please compute meson spectroscopy correlators")
        draft = parse_task_description(
            "compute meson spectroscopy correlators from existing propagator /tmp/meson_prop_0.npy "
            "point source momentum [0,0,0] timeslice 0 lattice size 24 24 24 72 grid 1 1 1 1 "
            "outputs/meson_spec.npy outputs/run_meson_spec.py"
        )
        draft.momentum_projection = "explicit"
        draft.gauge_fixed = False
        draft.correlator_output_format = "npy"
        match = match_supported_workflow(physics, draft)
        self.assertFalse(match.matched)
        self.assertTrue(any("source_type" in reason for reason in match.unsupported_reasons))

    def test_confirmed_proton_target_matches_supported_workflow(self):
        physics = interpret_request("please compute the proton two-point correlator")
        draft = parse_task_description("gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "proton_2pt_chroma_wall_local_zero_momentum_npy_v1")
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.stout_smear_steps, 1)
        self.assertEqual(draft.multigrid_blocks, [[6, 6, 6, 4], [4, 4, 4, 9]])

    def test_confirmed_quark_propagator_target_matches_supported_workflow(self):
        physics = interpret_request("please generate a quark propagator")
        draft = parse_task_description(
            "generate quark propagator from gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 "
            "grid 1 1 1 2 source timeslice 0 outputs/pt_prop.h5 outputs/run_quark.py"
        )
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "quark_propagator_chroma_point_hdf5_v1")
        self.assertEqual(draft.source_type, "point")
        self.assertEqual(draft.sink_type, "propagator")
        self.assertEqual(draft.momentum_projection, "none")
        self.assertEqual(draft.correlator_output_format, "hdf5")
        self.assertEqual(draft.stout_smear_steps, 1)
        self.assertEqual(draft.multigrid_blocks, [[6, 6, 6, 4], [4, 4, 4, 9]])

    def test_confirmed_gaussian_shell_quark_target_matches_supported_workflow(self):
        physics = interpret_request("please generate a gaussian-shell quark propagator")
        draft = parse_task_description(
            "generate gaussian-shell quark propagator from gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 "
            "grid 1 1 1 2 source timeslice 0 outputs/pt_prop.h5 outputs/run_quark_shell.py"
        )
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "quark_propagator_gaussian_shell_chroma_hdf5_v1")
        self.assertEqual(draft.source_smearing_kind, "gaussian_shell")
        self.assertEqual(draft.source_smearing_rho, 2.0)
        self.assertEqual(draft.source_smearing_steps, 5)
        self.assertEqual(draft.source_type, "point")
        self.assertEqual(draft.sink_type, "propagator")

    def test_confirmed_wilson_flow_target_matches_supported_workflow(self):
        physics = interpret_request("please run wilson flow on this gauge configuration")
        draft = parse_task_description("gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "wilson_flow_chroma_qio_energy_npy_v1")
        self.assertEqual(draft.start_from, "gauge")
        self.assertEqual(draft.source_type, "none")
        self.assertEqual(draft.momentum_projection, "none")

    def test_confirmed_stout_smear_target_matches_supported_workflow(self):
        physics = interpret_request("please generate a stout-smeared gauge")
        draft = parse_task_description("gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "stout_smear_chroma_qio_npy_v1")
        self.assertEqual(draft.source_type, "none")
        self.assertEqual(draft.sink_type, "gauge")
        self.assertEqual(draft.stout_smear_steps, 1)
        self.assertEqual(draft.stout_smear_rho, 0.241)
        self.assertEqual(draft.stout_smear_ndim, 3)

    def test_stout_smear_rejects_conflicting_smear_parameters(self):
        physics = interpret_request("please generate a stout-smeared gauge")
        draft = parse_task_description("gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2 stout rho=0.3")
        match = match_supported_workflow(physics, draft)
        self.assertFalse(match.matched)
        self.assertTrue(any("stout_smear_rho=0.241" in reason for reason in match.unsupported_reasons))

    def test_confirmed_ape_smear_target_matches_supported_workflow(self):
        physics = interpret_request("please generate an APE-smeared gauge")
        draft = parse_task_description("gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "ape_smear_chroma_qio_npy_v1")
        self.assertEqual(draft.source_type, "none")
        self.assertEqual(draft.sink_type, "gauge")

    def test_confirmed_hyp_smear_target_matches_supported_workflow(self):
        physics = interpret_request("please generate a HYP-smeared gauge")
        draft = parse_task_description("gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "hyp_smear_chroma_qio_npy_v1")
        self.assertEqual(draft.source_type, "none")
        self.assertEqual(draft.sink_type, "gauge")

    def test_conflicting_request_is_reported_instead_of_downgrading(self):
        physics = interpret_request("please compute the pion two-point correlator")
        draft = parse_task_description("pion 2pt point source")
        match = match_supported_workflow(physics, draft)
        self.assertFalse(match.matched)
        self.assertTrue(any("source_type" in reason for reason in match.unsupported_reasons))

    def test_pion_existing_propagator_matches_parameterized_family(self):
        physics = interpret_request("please compute the pion two-point correlator")
        draft = parse_task_description(
            "generate complete pion 2pt from existing propagator /tmp/prop_a.npy /tmp/prop_b.npy "
            "lattice size 24 24 24 72 grid 1 1 1 2 outputs/pion.npy outputs/run_pion.py"
        )
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "pion_2pt_existing_propagator_local_zero_momentum_npy_v1")
        self.assertEqual(draft.start_from, "propagator")
        self.assertTrue(draft.has_existing_propagators)

    def test_pion_existing_propagator_supports_hdf5_family_branch(self):
        physics = interpret_request("please compute the pion two-point correlator")
        draft = parse_task_description(
            "generate complete pion 2pt from existing propagator /tmp/prop_a.h5 "
            "lattice size 24 24 24 72 grid 1 1 1 2 outputs/pion.h5 outputs/run_pion.py"
        )
        draft.correlator_output_format = "npy"
        draft.correlator_output_path = "outputs/pion.npy"
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        self.assertEqual(match.workflow_target, "pion_2pt_existing_propagator_local_zero_momentum_npy_v1")

    def test_pion_existing_propagator_supports_point_source_branch_when_explicit(self):
        physics = interpret_request("please compute the pion two-point correlator")
        draft = parse_task_description(
            "generate complete pion 2pt from existing propagator /tmp/prop_a.npy "
            "source type: point lattice size 24 24 24 72 grid 1 1 1 2 outputs/pion.npy outputs/run_pion.py"
        )
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "pion_2pt_existing_propagator_local_zero_momentum_npy_v1")
        self.assertEqual(draft.source_type, "point")

    def test_pion_existing_propagator_supports_chroma_qio_path_without_extension(self):
        physics = interpret_request("please compute the pion two-point correlator")
        draft = parse_task_description(
            "generate complete pion 2pt from existing chroma qio propagator /tmp/pt_prop_1 "
            "source type: wall lattice size 24 24 24 72 grid 1 1 1 2 outputs/pion.npy outputs/run_pion.py"
        )
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        self.assertEqual(match.workflow_target, "pion_2pt_existing_propagator_local_zero_momentum_npy_v1")

    def test_pion_existing_propagator_without_paths_still_matches_family_for_clarification(self):
        physics = interpret_request("please compute the pion two-point correlator from existing propagator")
        draft = parse_task_description("generate complete pion 2pt from existing propagator outputs/run_pion.py")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        self.assertEqual(match.workflow_target, "pion_2pt_existing_propagator_local_zero_momentum_npy_v1")

    def test_pion_existing_propagator_rejects_ungrounded_source_variant(self):
        physics = interpret_request("please compute the pion two-point correlator")
        draft = parse_task_description(
            "generate complete pion 2pt from existing propagator /tmp/prop_a.npy "
            "volume source lattice size 24 24 24 72 grid 1 1 1 2 outputs/pion.npy outputs/run_pion.py"
        )
        match = match_supported_workflow(physics, draft)
        self.assertFalse(match.matched)
        self.assertTrue(any("source_type" in reason for reason in match.unsupported_reasons))

    def test_proton_existing_propagator_matches_grounded_branch(self):
        physics = interpret_request("please compute the proton two-point correlator")
        draft = parse_task_description(
            "generate complete proton 2pt from existing propagator /tmp/proton_prop.npy "
            "wall source zero momentum timeslice 0 lattice size 24 24 24 72 grid 1 1 1 2 "
            "outputs/proton.npy outputs/run_proton.py"
        )
        draft.gauge_fixed = False
        draft.correlator_output_format = "npy"
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        apply_workflow_match(draft, physics, match)
        self.assertEqual(draft.workflow_id, "proton_2pt_existing_propagator_local_zero_momentum_npy_v1")
        self.assertEqual(draft.start_from, "propagator")
        self.assertTrue(draft.has_existing_propagators)
        self.assertEqual(draft.source_type, "wall")

    def test_proton_existing_propagator_without_paths_still_matches_family_for_clarification(self):
        physics = interpret_request("please compute the proton two-point correlator from existing propagator")
        draft = parse_task_description("generate complete proton 2pt from existing propagator outputs/run_proton.py")
        match = match_supported_workflow(physics, draft)
        self.assertTrue(match.matched)
        self.assertEqual(match.workflow_target, "proton_2pt_existing_propagator_local_zero_momentum_npy_v1")

    def test_proton_existing_propagator_rejects_point_source(self):
        physics = interpret_request("please compute the proton two-point correlator")
        draft = parse_task_description(
            "generate complete proton 2pt from existing propagator /tmp/proton_prop.npy "
            "point source zero momentum timeslice 0 lattice size 24 24 24 72 grid 1 1 1 2 "
            "outputs/proton.npy outputs/run_proton.py"
        )
        draft.gauge_fixed = False
        draft.correlator_output_format = "npy"
        match = match_supported_workflow(physics, draft)
        self.assertFalse(match.matched)
        self.assertTrue(any("source_type" in reason for reason in match.unsupported_reasons))


if __name__ == "__main__":
    unittest.main()
