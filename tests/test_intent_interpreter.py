import unittest

from pyquda_agent.intent.clarifier import build_physics_questions
from pyquda_agent.intent.clarifier import apply_physics_answer
from pyquda_agent.intent.interpreter import interpret_request


class IntentInterpreterTests(unittest.TestCase):
    def test_rough_pi_meson_request_produces_candidate_pion_target(self):
        physics = interpret_request("write a simple PyQUDA script for pi meson two-point")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "pion_two_point_correlator")
        self.assertIsNone(physics.confirmed_interpretation)
        self.assertTrue(physics.formula_proposals)
        self.assertTrue(physics.external_citations)

    def test_explicit_stout_smear_request_is_not_reinterpreted_as_quark_propagator_by_propagator_wording(self):
        physics = interpret_request(
            "please generate a stout-smeared gauge from existing propagator /tmp/q.npy and save the result"
        )
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "stout_smeared_gauge_configuration")
        self.assertEqual(physics.task_type_hint, "stout_smear")
        self.assertTrue(any(item["proposal_id"] == "stout_smear_one_step_rho0241_dirignore3" for item in physics.formula_proposals))

    def test_explicit_wilson_flow_request_is_not_reinterpreted_as_quark_propagator_by_propagator_wording(self):
        physics = interpret_request(
            "please run wilson flow from existing propagator /tmp/q.npy and save the result"
        )
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "wilson_flow_energy_observable")
        self.assertEqual(physics.task_type_hint, "wilson_flow")
        self.assertTrue(any(item["proposal_id"] == "wilson_flow_energy_density_history" for item in physics.formula_proposals))

    def test_ambiguous_meson_request_generates_physics_question(self):
        physics = interpret_request("I want a meson correlator script but I am not sure about the exact operator")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(
            [item["target_id"] for item in physics.candidate_targets],
            [
                "meson_two_point_correlator_unspecified",
                "pion_two_point_correlator",
                "meson_spectrum_correlator",
                "pion_dispersion_correlator",
            ],
        )
        self.assertTrue(any(item["proposal_id"] == "meson_operator_needs_channel_choice" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "pion_pseudoscalar_gamma5_twopt" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "pion_dispersion_gamma5_momentum_projected_twopt" for item in physics.formula_proposals))
        self.assertTrue(physics.local_references)
        self.assertTrue(physics.external_citations)
        questions = build_physics_questions(physics, max_questions=2)
        self.assertTrue(questions)
        self.assertEqual(questions[0].category, "physics")
        self.assertEqual(questions[0].scope, "physics")
        self.assertIn(
            "当前支持 pion two-point correlator、pion pcac ratio correlator、pion dispersion correlator、meson spectrum correlator、rho/vector meson correlator、proton two-point correlator",
            questions[0].prompt,
        )
        self.assertIn("当前候选包括：", questions[0].prompt)
        self.assertIn("候选公式/operator/假设包括：", questions[0].prompt)
        self.assertIn("当前 grounded workflow 假设包括：", questions[0].prompt)
        self.assertIn("rho/vector -> wall/local/spatial gamma_i/zero momentum", questions[0].prompt)
        self.assertIn("pion: pion two-point correlator", questions[0].prompt)
        self.assertIn("operator=Underspecified", questions[0].prompt)
        self.assertIn("operator=O_\\pi(x) = \\bar d(x) \\gamma_5 u(x)", questions[0].prompt)
        self.assertIn("meson spectrum: meson spectroscopy correlator", questions[0].prompt)
        self.assertIn("如果你要 rho/vector meson，请回答 rho", questions[0].prompt)
        self.assertIn("完整公式和来源见 physics_formula_preview 与 .physics.json", questions[0].prompt)
        self.assertIn("如果你实际不是 hadron correlator，也可以直接回答 quark propagator", questions[0].prompt)

    def test_generic_pyquda_request_generates_capability_chooser_prompt(self):
        physics = interpret_request("write a simple PyQUDA script")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "hadron_two_point_correlator_unspecified")
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("当前系统支持的 grounded workflow family 分为两类", questions[0].prompt)
        self.assertIn("Hadron correlators:", questions[0].prompt)
        self.assertIn("Gauge/solver utilities:", questions[0].prompt)
        self.assertIn("quark propagator -> gauge entry + one stout-smear step + Clover point source + HDF5 propagator", questions[0].prompt)
        self.assertIn("Wilson flow -> gauge entry + wilsonFlowChroma(flow_steps, flow_epsilon) + npy energy history", questions[0].prompt)
        self.assertIn("如果你要 quark propagator，请回答 quark propagator", questions[0].prompt)
        self.assertIn("如果你要 gauge smearing，请明确回答 stout smear、ape smear 或 hyp smear", questions[0].prompt)

    def test_rough_hadron_request_surfaces_meson_and_baryon_candidates(self):
        physics = interpret_request("please compute a hadron correlator")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "hadron_two_point_correlator_unspecified")
        self.assertEqual(
            [item["target_id"] for item in physics.candidate_targets],
            [
                "hadron_two_point_correlator_unspecified",
                "meson_two_point_correlator_unspecified",
                "baryon_two_point_correlator_unspecified",
                "pion_two_point_correlator",
                "proton_two_point_correlator",
            ],
        )
        self.assertTrue(any(item["proposal_id"] == "hadron_operator_needs_channel_choice" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "meson_operator_needs_channel_choice" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "baryon_operator_needs_channel_choice" for item in physics.formula_proposals))
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("还没有说明是 meson 还是 baryon", questions[0].prompt)
        self.assertIn("如果你要先走 meson 侧澄清，请回答 meson", questions[0].prompt)
        self.assertIn("如果你要先走 baryon / nucleon 侧澄清，请回答 baryon", questions[0].prompt)

    def test_mixed_meson_baryon_request_stays_at_hadron_level(self):
        physics = interpret_request("I need a nucleon or meson correlator but I am not sure which one")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "hadron_two_point_correlator_unspecified")
        self.assertEqual(
            [item["target_id"] for item in physics.candidate_targets],
            [
                "hadron_two_point_correlator_unspecified",
                "meson_two_point_correlator_unspecified",
                "baryon_two_point_correlator_unspecified",
            ],
        )
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("multiple hadron-channel families", physics.candidate_targets[0]["summary"])
        self.assertIn("如果你要先走 meson 侧澄清，请回答 meson", questions[0].prompt)
        self.assertIn("如果你要先走 baryon / nucleon 侧澄清，请回答 baryon", questions[0].prompt)

    def test_mixed_specific_meson_and_proton_request_surfaces_specific_branches(self):
        physics = interpret_request("I am not sure if I need a meson spectrum or proton correlator")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "hadron_two_point_correlator_unspecified")
        self.assertEqual(
            [item["target_id"] for item in physics.candidate_targets],
            [
                "hadron_two_point_correlator_unspecified",
                "meson_spectrum_correlator",
                "proton_two_point_correlator",
            ],
        )
        self.assertTrue(any(item["proposal_id"] == "meson_spec_gamma5_wall_momentum_family" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "proton_nucleon_gamma5_twopt" for item in physics.formula_proposals))
        self.assertEqual(
            [item["proposal_id"] for item in physics.formula_proposals[:4]],
            [
                "hadron_operator_needs_channel_choice",
                "meson_spec_gamma5_wall_momentum_family",
                "meson_spec_gamma4gamma5_wall_momentum_family",
                "proton_nucleon_gamma5_twopt",
            ],
        )
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("请先确认更具体的 hadron target", questions[0].prompt)
        self.assertIn("请直接回答 meson spectrum / proton", questions[0].prompt)

    def test_mixed_pion_and_proton_request_prioritizes_matching_formula_candidates(self):
        physics = interpret_request("I am not sure if I need pion or proton correlator")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "hadron_two_point_correlator_unspecified")
        self.assertEqual(
            [item["proposal_id"] for item in physics.formula_proposals[:4]],
            [
                "hadron_operator_needs_channel_choice",
                "pion_pseudoscalar_gamma5_twopt",
                "proton_nucleon_gamma5_twopt",
                "meson_operator_needs_channel_choice",
            ],
        )
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("请先确认更具体的 hadron target", questions[0].prompt)
        self.assertIn("请直接回答 pion / proton", questions[0].prompt)

    def test_hadron_level_answer_mesons_refines_to_meson_clarification(self):
        physics = interpret_request("I need a nucleon or meson correlator but I am not sure which one")
        apply_physics_answer(physics, "confirmed_target_id", "meson")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "meson_two_point_correlator_unspecified")
        self.assertEqual(physics.clarified_fields["target_id"], "meson_two_point_correlator_unspecified")
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("当前支持 pion two-point correlator", questions[0].prompt)

    def test_hadron_level_answer_baryon_refines_to_baryon_clarification(self):
        physics = interpret_request("I need a nucleon or meson correlator but I am not sure which one")
        apply_physics_answer(physics, "confirmed_target_id", "baryon")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "baryon_two_point_correlator_unspecified")
        self.assertEqual(physics.clarified_fields["target_id"], "baryon_two_point_correlator_unspecified")
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("当前本地可运行 baryon workflow 只有 proton two-point correlator", questions[0].prompt)

    def test_hadron_level_answer_mesonspectrum_branch_keeps_specific_candidate(self):
        physics = interpret_request("I am not sure if I need a meson spectrum or proton correlator")
        apply_physics_answer(physics, "confirmed_target_id", "meson")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "meson_spectrum_correlator")
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("当前推断目标是 meson spectrum correlator", questions[0].prompt)

    def test_ambiguous_meson_request_with_momentum_prioritizes_dispersion_candidate(self):
        physics = interpret_request("I want a meson correlator script with momentum projection but I am not sure about the exact operator")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "pion_dispersion_correlator")
        self.assertEqual(
            [item["target_id"] for item in physics.candidate_targets],
            [
                "meson_two_point_correlator_unspecified",
                "pion_dispersion_correlator",
                "pion_two_point_correlator",
            ],
        )
        self.assertIn("momentum-like language", physics.candidate_targets[0]["summary"])
        self.assertIn("Momentum/dispersive wording", physics.candidate_targets[1]["summary"])
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("当前推断目标是 pion dispersion correlator", questions[0].prompt)

    def test_axial_meson_request_prefers_meson_spec_confirmation(self):
        physics = interpret_request("write a simple PyQUDA script for axial meson correlator")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "meson_spectrum_correlator")
        self.assertEqual(
            [item["target_id"] for item in physics.candidate_targets],
            [
                "meson_two_point_correlator_unspecified",
                "meson_spectrum_correlator",
                "pion_two_point_correlator",
            ],
        )
        self.assertIn("axial/gamma4gamma5 meson correlator", physics.candidate_targets[0]["summary"])
        self.assertTrue(any(item["proposal_id"].startswith("meson_spec_") for item in physics.formula_proposals))
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("当前推断目标是 meson spectrum correlator", questions[0].prompt)

    def test_pseudoscalar_meson_request_prefers_pion_confirmation(self):
        physics = interpret_request("write a simple PyQUDA script for pseudoscalar meson correlator")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "pion_two_point_correlator")
        self.assertEqual(
            [item["target_id"] for item in physics.candidate_targets],
            [
                "meson_two_point_correlator_unspecified",
                "pion_two_point_correlator",
                "meson_spectrum_correlator",
            ],
        )
        self.assertIn("pseudoscalar/gamma5 meson correlator", physics.candidate_targets[0]["summary"])
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("当前推断目标是 pion two-point correlator", questions[0].prompt)

    def test_explicit_pion_dispersion_request_is_confirmed(self):
        physics = interpret_request("write a simple PyQUDA script for pion dispersion with nonzero momentum")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "pion_dispersion_correlator")
        self.assertEqual(physics.task_type_hint, "pion_dispersion")
        self.assertTrue(physics.formula_proposals)
        self.assertTrue(physics.local_references)

    def test_explicit_pion_pcac_request_is_confirmed(self):
        physics = interpret_request("write a simple PyQUDA script for pion pcac ratio")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "pion_pcac_ratio_correlator")
        self.assertEqual(physics.task_type_hint, "pion_pcac")
        self.assertTrue(any(item["proposal_id"] == "pion_pcac_gamma5_gamma4_ratio" for item in physics.formula_proposals))
        self.assertTrue(any(ref.endswith("examples/4_Pion_PCAC.py") for ref in physics.local_references))

    def test_explicit_meson_spectrum_request_is_confirmed(self):
        physics = interpret_request("write a simple PyQUDA meson spectrum script with wall source")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "meson_spectrum_correlator")
        self.assertEqual(physics.task_type_hint, "meson_spec")
        self.assertTrue(any(item["proposal_id"].startswith("meson_spec_") for item in physics.formula_proposals))
        self.assertTrue(any(ref.endswith("pyquda_utils/phase.py") for ref in physics.local_references))

    def test_uncertain_meson_spectrum_request_stays_in_physics_confirmation(self):
        physics = interpret_request("write a simple PyQUDA script for meson spectrum but I am not sure which gamma insertion to use")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "meson_spectrum_correlator")
        self.assertIsNone(physics.confirmed_interpretation)
        self.assertTrue(any(item["proposal_id"] == "meson_spec_gamma5_wall_momentum_family" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "meson_spec_gamma4gamma5_wall_momentum_family" for item in physics.formula_proposals))
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("gamma5 / gamma4gamma5 插入族", questions[0].prompt)

    def test_zero_momentum_pion_request_does_not_escalate_to_dispersion(self):
        physics = interpret_request("please compute the pion two-point correlator at zero momentum")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "pion_two_point_correlator")

    def test_yes_confirms_current_dispersion_inference(self):
        physics = interpret_request("write a PyQUDA script for pion with momentum projection")
        self.assertEqual(physics.inferred_interpretation["target_id"], "pion_dispersion_correlator")
        apply_physics_answer(physics, "confirmed_target_id", "yes")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "pion_dispersion_correlator")

    def test_yes_confirms_current_pcac_inference(self):
        physics = interpret_request("write a PyQUDA script for pion pcac")
        self.assertEqual(physics.inferred_interpretation["target_id"], "pion_pcac_ratio_correlator")
        apply_physics_answer(physics, "confirmed_target_id", "yes")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "pion_pcac_ratio_correlator")

    def test_yes_confirms_current_meson_spec_inference(self):
        physics = interpret_request("write a meson spectroscopy script")
        self.assertEqual(physics.inferred_interpretation["target_id"], "meson_spectrum_correlator")
        apply_physics_answer(physics, "confirmed_target_id", "yes")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "meson_spectrum_correlator")

    def test_explicit_proton_request_is_confirmed_and_supported(self):
        physics = interpret_request("please compute the proton two-point correlator")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "proton_two_point_correlator")
        self.assertEqual(physics.task_type_hint, "proton_2pt")
        self.assertTrue(physics.formula_proposals)
        self.assertFalse(physics.unsupported_reasons)

    def test_explicit_quark_propagator_request_is_confirmed_and_grounded_locally(self):
        physics = interpret_request("please generate a quark propagator")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "quark_propagator")
        self.assertEqual(physics.task_type_hint, "quark_propagator")
        self.assertTrue(any(item["proposal_id"] == "quark_propagator_point_source_clover" for item in physics.formula_proposals))
        self.assertTrue(any(ref.endswith("examples/2_Quark_Propagator.py") for ref in physics.local_references))
        self.assertFalse(physics.external_citations)

    def test_rough_propagator_request_prefers_quark_propagator_family(self):
        physics = interpret_request("please generate a propagator script")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "quark_propagator")
        self.assertEqual([item["target_id"] for item in physics.candidate_targets], ["quark_propagator"])
        self.assertTrue(any(item["proposal_id"] == "quark_propagator_point_source_clover" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "quark_propagator_gaussian_shell_source_clover" for item in physics.formula_proposals))
        self.assertTrue(any(ref.endswith("examples/2_Quark_Propagator.py") for ref in physics.local_references))
        self.assertTrue(any(ref.endswith("tests/test_gaussian.py") for ref in physics.local_references))
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("当前本地有两条可运行分支", questions[0].prompt)
        self.assertIn("gaussianSmear(rho=2.0, n_steps=5)", questions[0].prompt)
        self.assertIn("如果你要 gaussian-shell branch，请回答 gaussian shell propagator", questions[0].prompt)

    def test_uncertain_quark_branch_request_stays_in_physics_confirmation(self):
        physics = interpret_request("please compute a quark propagator but I am not sure whether I need point or gaussian shell")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "quark_propagator")
        self.assertIsNone(physics.confirmed_interpretation)
        self.assertTrue(any(item["proposal_id"] == "quark_propagator_point_source_clover" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "quark_propagator_gaussian_shell_source_clover" for item in physics.formula_proposals))
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("当前本地有两条可运行分支", questions[0].prompt)

    def test_quark_propagator_confirmation_prompt_surfaces_narrow_grounded_scope(self):
        physics = interpret_request("please generate a quark propagator")
        physics.confirmed_interpretation = None
        physics.status = "needs_confirmation"
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("one stout-smear step", questions[0].prompt)
        self.assertIn("当前 grounded quark-propagator family 被锁定为 gauge entry、单一 point source、单一 propagator 输出", questions[0].prompt)

    def test_explicit_gaussian_shell_quark_request_is_confirmed_and_grounded_locally(self):
        physics = interpret_request("please generate a gaussian-shell quark propagator")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "quark_propagator")
        self.assertTrue(any(item["proposal_id"] == "quark_propagator_gaussian_shell_source_clover" for item in physics.formula_proposals))
        self.assertTrue(any(ref.endswith("tests/test_gaussian.py") for ref in physics.local_references))
        self.assertEqual(physics.inferred_fields["source_smearing_kind"], "gaussian_shell")

    def test_gaussian_shell_quark_confirmation_prompt_surfaces_fixed_gaussian_branch(self):
        physics = interpret_request("please generate a gaussian-shell quark propagator")
        physics.confirmed_interpretation = None
        physics.status = "needs_confirmation"
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("gaussianSmear(rho=2.0, n_steps=5)", questions[0].prompt)
        self.assertIn("当前 grounded gaussian-shell quark-propagator family", questions[0].prompt)

    def test_gaussian_shell_propagator_answer_records_branch_hint(self):
        physics = interpret_request("please generate a propagator script")
        apply_physics_answer(physics, "confirmed_target_id", "gaussian shell propagator")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "quark_propagator")
        self.assertEqual(physics.clarified_fields["source_smearing_kind"], "gaussian_shell")
        self.assertEqual(physics.inferred_fields["source_smearing_kind"], "gaussian_shell")

    def test_explicit_wilson_flow_request_is_confirmed_and_grounded_locally(self):
        physics = interpret_request("please run wilson flow on this gauge configuration")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "wilson_flow_energy_observable")
        self.assertEqual(physics.task_type_hint, "wilson_flow")
        self.assertTrue(any(item["proposal_id"] == "wilson_flow_energy_density_history" for item in physics.formula_proposals))
        self.assertTrue(any(ref.endswith("tests/test_wflow.py") for ref in physics.local_references))

    def test_explicit_stout_smear_request_is_confirmed_and_grounded_locally(self):
        physics = interpret_request("please generate a stout-smeared gauge configuration")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "stout_smeared_gauge_configuration")
        self.assertEqual(physics.task_type_hint, "stout_smear")
        self.assertTrue(any(item["proposal_id"].startswith("stout_smear_") for item in physics.formula_proposals))
        self.assertTrue(any(ref.endswith("tests/test_smear.py") for ref in physics.local_references))

    def test_explicit_ape_smear_request_is_confirmed_and_grounded_locally(self):
        physics = interpret_request("please generate an APE-smeared gauge configuration")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "ape_smeared_gauge_configuration")
        self.assertEqual(physics.task_type_hint, "ape_smear")
        self.assertTrue(any(item["proposal_id"] == "ape_smear_one_step_alpha25_dirignore4" for item in physics.formula_proposals))
        self.assertTrue(any(ref.endswith("tests/test_smear.py") for ref in physics.local_references))
        self.assertFalse(physics.unsupported_reasons)

    def test_explicit_hyp_smear_request_is_confirmed_and_grounded_locally(self):
        physics = interpret_request("please generate a HYP-smeared gauge configuration")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "hyp_smeared_gauge_configuration")
        self.assertEqual(physics.task_type_hint, "hyp_smear")
        self.assertTrue(any(item["proposal_id"] == "hyp_smear_one_step_075_06_03_dirignore4" for item in physics.formula_proposals))
        self.assertTrue(any(ref.endswith("tests/test_smear.py") for ref in physics.local_references))
        self.assertFalse(physics.unsupported_reasons)

    def test_rough_gauge_smear_request_requires_stout_confirmation(self):
        physics = interpret_request("please smear this gauge field and save the result")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "stout_smeared_gauge_configuration")
        self.assertEqual(
            [item["target_id"] for item in physics.candidate_targets],
            [
                "stout_smeared_gauge_configuration",
                "ape_smeared_gauge_configuration",
                "hyp_smeared_gauge_configuration",
            ],
        )
        self.assertTrue(any(item["proposal_id"] == "stout_smear_one_step_rho0241_dirignore3" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "ape_smear_one_step_alpha25_dirignore4" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "hyp_smear_one_step_075_06_03_dirignore4" for item in physics.formula_proposals))
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("stout smear", questions[0].prompt.lower())
        self.assertIn("ape smear", questions[0].prompt.lower())
        self.assertIn("hyp smear", questions[0].prompt.lower())
        self.assertIn("ape smear，系统会切到对应的 runnable APE workflow", questions[0].prompt)
        self.assertIn("hyp smear，系统会切到对应的 runnable HYP workflow", questions[0].prompt)
        self.assertIn("单步固定参数 smearing、单一 npy 输出", questions[0].prompt)

    def test_explicit_rho_request_is_confirmed_and_grounded_for_narrow_workflow(self):
        physics = interpret_request("please compute the rho meson two-point correlator")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "rho_vector_meson_correlator")
        self.assertEqual(physics.task_type_hint, "rho_vector")
        self.assertTrue(any(item["proposal_id"] == "rho_vector_gammai_twopt" for item in physics.formula_proposals))
        self.assertTrue(physics.local_references)
        self.assertFalse(physics.unsupported_reasons)

    def test_rough_gauge_flow_request_requires_confirmation(self):
        physics = interpret_request("please evolve this gauge field and save the flow history")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "wilson_flow_energy_observable")
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("Wilson flow / gradient flow", questions[0].prompt)
        self.assertIn("gauge entry + energy-history 输出", questions[0].prompt)

    def test_vector_meson_request_with_operator_uncertainty_stays_in_clarification(self):
        physics = interpret_request("I want a vector meson correlator script but I am not sure about the exact operator")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "rho_vector_meson_correlator")
        self.assertTrue(any(item["proposal_id"] == "rho_vector_gammai_twopt" for item in physics.formula_proposals))
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("rho/vector meson correlator", questions[0].prompt)
        self.assertIn("gamma_i", questions[0].prompt)

    def test_rough_nucleon_request_requires_channel_confirmation(self):
        physics = interpret_request("write a simple PyQUDA script for the nucleon correlator")
        self.assertEqual(physics.status, "needs_confirmation")
        self.assertEqual(physics.inferred_interpretation["target_id"], "baryon_two_point_correlator_unspecified")
        self.assertEqual(
            [item["target_id"] for item in physics.candidate_targets],
            [
                "baryon_two_point_correlator_unspecified",
                "proton_two_point_correlator",
                "neutron_two_point_correlator",
            ],
        )
        self.assertTrue(any(item["proposal_id"] == "baryon_operator_needs_channel_choice" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "proton_nucleon_gamma5_twopt" for item in physics.formula_proposals))
        self.assertTrue(any(item["proposal_id"] == "neutron_nucleon_gamma5_twopt" for item in physics.formula_proposals))
        self.assertTrue(physics.local_references)
        self.assertTrue(physics.external_citations)
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertIn("当前本地可运行 baryon workflow 只有 proton two-point correlator", questions[0].prompt)
        self.assertIn("当前 grounded proton workflow 被锁定为", questions[0].prompt)
        self.assertIn("如果你指的是 neutron，请回答 neutron", questions[0].prompt)
        self.assertIn("候选公式/operator/假设包括：", questions[0].prompt)
        self.assertIn("完整公式和来源见 physics_formula_preview 与 .physics.json", questions[0].prompt)

    def test_proton_answer_confirms_rough_nucleon_request(self):
        physics = interpret_request("write a simple PyQUDA script for the nucleon correlator")
        apply_physics_answer(physics, "confirmed_target_id", "proton")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "proton_two_point_correlator")

    def test_explicit_neutron_request_is_confirmed_but_marked_unimplemented(self):
        physics = interpret_request("please compute the neutron two-point correlator")
        self.assertEqual(physics.status, "confirmed")
        self.assertEqual(physics.confirmed_interpretation["target_id"], "neutron_two_point_correlator")
        self.assertIsNone(physics.task_type_hint)
        self.assertTrue(any(item["proposal_id"] == "neutron_nucleon_gamma5_twopt" for item in physics.formula_proposals))
        self.assertTrue(any("neutron two-point correlators are not implemented" in reason.lower() for reason in physics.unsupported_reasons))

    def test_unresolved_physics_answer_keeps_confirmation_question_active(self):
        physics = interpret_request("I want a meson correlator script but I am not sure about the exact operator")
        apply_physics_answer(physics, "confirmed_target_id", "meson")
        self.assertEqual(physics.status, "needs_confirmation")
        questions = build_physics_questions(physics, max_questions=1)
        self.assertTrue(questions)
        self.assertEqual(questions[0].field_name, "confirmed_target_id")


if __name__ == "__main__":
    unittest.main()
