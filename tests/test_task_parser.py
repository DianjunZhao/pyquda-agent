import unittest

from pyquda_agent.tasks.parser import parse_task_description


class TaskParserTests(unittest.TestCase):
    def test_parse_pion_2pt_description(self):
        draft = parse_task_description(
            "请生成完整可运行的 pion 2pt 脚本，从 gauge configuration /tmp/cfg_0001.lime 开始，"
            "使用 clover，wall source，local sink，zero momentum，source timeslice 12，"
            "lattice size 24 24 24 72，grid 1 1 1 2，mass=0.09253，xi_0=4.8965，nu=0.86679，"
            "coeff_t=0.8549165664，coeff_r=2.32582045，tol=1e-12，maxiter=1000，"
            "输出 outputs/pion.npy，脚本 outputs/run_pion.py，gauge fixed，resource_path=.cache/quda。"
        )
        self.assertEqual(draft.task_type, "pion_2pt")
        self.assertIsNone(draft.workflow_id)
        self.assertFalse(draft.has_existing_propagators)
        self.assertEqual(draft.start_from, "gauge")
        self.assertEqual(draft.gauge_format, "chroma_qio")
        self.assertEqual(draft.gauge_path, "/tmp/cfg_0001.lime")
        self.assertEqual(draft.source_type, "wall")
        self.assertEqual(draft.sink_type, "local")
        self.assertEqual(draft.momenta, [[0, 0, 0]])
        self.assertEqual(draft.source_timeslices, [12])
        self.assertEqual(draft.lattice_size, [24, 24, 24, 72])
        self.assertEqual(draft.grid_size, [1, 1, 1, 2])
        self.assertEqual(draft.fermion_action, "clover")
        self.assertAlmostEqual(draft.mass or 0.0, 0.09253)
        self.assertTrue(draft.gauge_fixed)
        self.assertEqual(draft.correlator_output_format, "npy")
        self.assertEqual(draft.correlator_output_path, "outputs/pion.npy")
        self.assertEqual(draft.script_output_path, "outputs/run_pion.py")
        self.assertEqual(draft.script_style, "complete")
        self.assertEqual(draft.user_confirmed_fields["gauge_path"], "/tmp/cfg_0001.lime")

    def test_parse_existing_propagator_request_keeps_structured_fields(self):
        draft = parse_task_description(
            "generate complete pion 2pt from existing propagator /tmp/prop_a.npy /tmp/prop_b.npy "
            "lattice size 24 24 24 72 grid 1 1 1 2 cluster_launch=slurm outputs/run_pion.py"
        )
        self.assertEqual(draft.start_from, "propagator")
        self.assertTrue(draft.has_existing_propagators)
        self.assertEqual(draft.propagator_format, "npy")
        self.assertEqual(draft.propagator_paths, ["/tmp/prop_a.npy", "/tmp/prop_b.npy"])
        self.assertEqual(draft.cluster_launch, "slurm")

    def test_parse_chroma_qio_existing_propagator_without_extension(self):
        draft = parse_task_description(
            "generate complete pion 2pt from existing chroma qio propagator /tmp/pt_prop_1 "
            "lattice size 24 24 24 72 grid 1 1 1 2 outputs/run_pion.py"
        )
        self.assertEqual(draft.start_from, "propagator")
        self.assertTrue(draft.has_existing_propagators)
        self.assertEqual(draft.propagator_format, "chroma_qio")
        self.assertEqual(draft.propagator_paths, ["/tmp/pt_prop_1"])

    def test_existing_propagator_request_does_not_treat_output_npy_as_input_propagator(self):
        draft = parse_task_description(
            "generate complete proton 2pt from existing propagator /tmp/proton_prop.npy "
            "wall source zero momentum timeslice 0 lattice size 24 24 24 72 grid 1 1 1 2 "
            "outputs/proton.npy outputs/run_proton.py"
        )
        self.assertEqual(draft.start_from, "propagator")
        self.assertEqual(draft.propagator_paths, ["/tmp/proton_prop.npy"])
        self.assertEqual(draft.correlator_output_path, "outputs/proton.npy")

    def test_existing_propagator_request_recognizes_absolute_output_npy_path(self):
        draft = parse_task_description(
            "generate complete proton 2pt from existing propagator /tmp/proton_prop.npy "
            "wall source zero momentum timeslice 0 lattice size 24 24 24 72 grid 1 1 1 2 "
            "/Users/zhaodianjun/pyquda-agent/outputs/proton.npy "
            "/Users/zhaodianjun/pyquda-agent/outputs/run_proton.py"
        )
        self.assertEqual(draft.propagator_paths, ["/tmp/proton_prop.npy"])
        self.assertEqual(draft.correlator_output_path, "/Users/zhaodianjun/pyquda-agent/outputs/proton.npy")
        self.assertEqual(draft.script_output_path, "/Users/zhaodianjun/pyquda-agent/outputs/run_proton.py")

    def test_not_gauge_fixed_phrase_sets_false(self):
        draft = parse_task_description("generate complete proton 2pt not gauge fixed")
        self.assertFalse(draft.gauge_fixed)

    def test_two_point_phrase_does_not_imply_point_source(self):
        draft = parse_task_description("please compute the pion two-point correlator")
        self.assertIsNone(draft.source_type)
        self.assertEqual(draft.task_type, "pion_2pt")
        self.assertEqual(draft.parser_guesses["task_type"], "pion_2pt")

    def test_dispersion_phrase_sets_dispersion_task_type(self):
        draft = parse_task_description("write a simple pion dispersion script with nonzero momentum")
        self.assertEqual(draft.task_type, "pion_dispersion")
        self.assertEqual(draft.parser_guesses["task_type"], "pion_dispersion")

    def test_pcac_phrase_sets_pcac_task_type(self):
        draft = parse_task_description("write a simple pion pcac ratio script")
        self.assertEqual(draft.task_type, "pion_pcac")
        self.assertEqual(draft.parser_guesses["task_type"], "pion_pcac")

    def test_proton_phrase_sets_proton_task_type(self):
        draft = parse_task_description("please compute the proton two-point correlator")
        self.assertEqual(draft.task_type, "proton_2pt")
        self.assertEqual(draft.parser_guesses["task_type"], "proton_2pt")

    def test_meson_spectrum_phrase_sets_meson_spec_task_type(self):
        draft = parse_task_description("write a meson spectrum correlator script")
        self.assertEqual(draft.task_type, "meson_spec")
        self.assertEqual(draft.parser_guesses["task_type"], "meson_spec")

    def test_quark_propagator_phrase_sets_quark_propagator_task_type(self):
        draft = parse_task_description("please generate a quark propagator from gauge /tmp/cfg_0001.lime")
        self.assertEqual(draft.task_type, "quark_propagator")
        self.assertEqual(draft.parser_guesses["task_type"], "quark_propagator")

    def test_gaussian_shell_quark_propagator_phrase_sets_source_smearing_kind(self):
        draft = parse_task_description(
            "please generate a gaussian-shell quark propagator from gauge /tmp/cfg_0001.lime "
            "lattice size 24 24 24 72 grid 1 1 1 2 source timeslice 0 outputs/pt_prop.h5 outputs/run_quark.py"
        )
        self.assertEqual(draft.task_type, "quark_propagator")
        self.assertEqual(draft.source_smearing_kind, "gaussian_shell")

    def test_wilson_flow_phrase_sets_wilson_flow_task_type_and_parameters(self):
        draft = parse_task_description(
            "please run wilson flow from gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 "
            "grid 1 1 1 2 flow_steps=100 flow_epsilon=1.0 outputs/wflow.npy outputs/run_wflow.py"
        )
        self.assertEqual(draft.task_type, "wilson_flow")
        self.assertEqual(draft.parser_guesses["task_type"], "wilson_flow")
        self.assertEqual(draft.gauge_path, "/tmp/cfg_0001.lime")
        self.assertEqual(draft.flow_steps, 100)
        self.assertEqual(draft.flow_epsilon, 1.0)
        self.assertEqual(draft.correlator_output_path, "outputs/wflow.npy")

    def test_ape_smear_phrase_sets_ape_smear_task_type(self):
        draft = parse_task_description(
            "please generate an APE-smeared gauge from gauge /tmp/cfg_0001.lime "
            "lattice size 24 24 24 72 grid 1 1 1 2 outputs/ape.npy outputs/run_ape.py"
        )
        self.assertEqual(draft.task_type, "ape_smear")
        self.assertEqual(draft.parser_guesses["task_type"], "ape_smear")
        self.assertEqual(draft.gauge_path, "/tmp/cfg_0001.lime")
        self.assertEqual(draft.correlator_output_path, "outputs/ape.npy")

    def test_h5_output_is_normalized_to_hdf5(self):
        draft = parse_task_description(
            "please generate a quark propagator from gauge /tmp/cfg_0001.lime "
            "lattice size 24 24 24 72 grid 1 1 1 2 outputs/pt_prop.h5 outputs/run_quark.py"
        )
        self.assertEqual(draft.correlator_output_format, "hdf5")
        self.assertEqual(draft.correlator_output_path, "outputs/pt_prop.h5")


if __name__ == "__main__":
    unittest.main()
