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
        self.assertEqual(draft.workflow_id, "pion_2pt_chroma_wall_local_zero_momentum_npy_v1")
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


if __name__ == "__main__":
    unittest.main()
