import unittest
from pathlib import Path

from pyquda_agent.generator.plan import build_implementation_plan
from pyquda_agent.generator.templates import render_pion_2pt_script
from pyquda_agent.generator.validate import validate_generated_script
from pyquda_agent.models import ContextBundle
from pyquda_agent.models import ContextSnippet
from pyquda_agent.tasks.schema import Pion2ptTask


class GeneratorTests(unittest.TestCase):
    def test_render_and_validate_complete_script(self):
        task = Pion2ptTask(
            task_type="pion_2pt",
            workflow_id="pion_2pt_chroma_wall_local_zero_momentum_npy_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            propagator_format=None,
            propagator_paths=[],
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
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            source_timeslices=[0],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/pion_2pt.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/pion_2pt.py",
            script_style="complete",
            field_sources={"mass": "user"},
            notes="test",
        )
        context = ContextBundle(
            task_type="pion_2pt",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet(
                    source="pyquda",
                    path="/tmp/PyQUDA/examples/3_Pion_Proton_2pt.py",
                    score=3.0,
                    summary="pion correlator example",
                    excerpt="pion correlator example",
                ),
                ContextSnippet(
                    source="pyquda",
                    path="/tmp/PyQUDA/tests/test_mesonspec.py",
                    score=2.0,
                    summary="mesonspec example",
                    excerpt="mesonspec example",
                ),
                ContextSnippet(
                    source="pyquda",
                    path="/tmp/PyQUDA/tests/test_io.py",
                    score=1.0,
                    summary="io example",
                    excerpt="io example",
                ),
            ],
        )
        plan = build_implementation_plan(task, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        self.assertTrue(plan.convention_decisions)
        self.assertEqual(plan.clarification_trace, [])
        self.assertIsNotNone(plan.runtime_readiness)
        self.assertTrue(any(item["decision"].startswith("Use wall source") for item in plan.convention_decisions))
        code = render_pion_2pt_script(task, plan)
        validate_generated_script(code)
        self.assertIn("core.getClover", code)
        self.assertIn("core.init(GRID_SIZE, LATTICE_SIZE, resource_path=RESOURCE_PATH)", code)
        self.assertIn('core.invert(dirac, "wall", t_src)', code)
        self.assertIn("io.readQIOGauge", code)
        self.assertIn("core.gatherLattice", code)
        self.assertIn("np.save", code)
        self.assertIn("vol = latt_info.volume", code)
        self.assertIn("ns = 4", code)
        self.assertIn("nc = 3", code)
        self.assertIn("if not GAUGE_PATH.exists()", code)
        self.assertIn("Missing runtime dependency 'numpy'", code)
        self.assertIn("Missing runtime dependency 'cupy'", code)
        self.assertIn("Unable to import 'pyquda_utils'", code)
        self.assertIn("Unable to import 'pyquda'", code)
        self.assertIn("3_Pion_Proton_2pt.py", code)
        self.assertIn("test_mesonspec.py", code)
        self.assertIn("test_io.py", code)
        self.assertNotIn("README.md", code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)
        self.assertNotIn("fake_", code)
        self.assertNotIn("mock_", code)
        self.assertIn("Review the sibling .task.json and .plan.json artifacts", code)
        self.assertIn("Cluster/runtime assumption: hpc", code)


if __name__ == "__main__":
    unittest.main()
