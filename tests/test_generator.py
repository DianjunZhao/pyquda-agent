import unittest
from pathlib import Path

from pyquda_agent.generator.plan import build_implementation_plan
from pyquda_agent.generator.templates import render_complete_script
from pyquda_agent.generator.templates import render_pion_2pt_script
from pyquda_agent.generator.validate import validate_generated_script
from pyquda_agent.intent.interpreter import interpret_request
from pyquda_agent.models import ContextBundle
from pyquda_agent.models import ContextSnippet
from pyquda_agent.tasks.pion_2pt import finalize_task
from pyquda_agent.tasks.schema import Pion2ptTask
from pyquda_agent.tasks.schema import Pion2ptTaskDraft
from pyquda_agent.workflows.matcher import match_supported_workflow


class GeneratorTests(unittest.TestCase):
    def test_validate_generated_script_rejects_missing_handoff_contract_tokens(self):
        code = '''#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
TASK_ARTIFACT = SCRIPT_PATH.with_suffix(".task.json")
PHYSICS_ARTIFACT = SCRIPT_PATH.with_suffix(".physics.json")
PLAN_ARTIFACT = SCRIPT_PATH.with_suffix(".plan.json")
PROBE_ARTIFACT = SCRIPT_PATH.with_suffix(".probe.json")
RESOURCE_PATH = ".cache/quda"
CLUSTER_LAUNCH = "local"

def _validate_handoff_contract() -> None:
    if not CLUSTER_LAUNCH:
        raise ValueError("CLUSTER_LAUNCH must be a non-empty string.")

def _print_handoff_summary() -> None:
    print("Launch assumption: local")
    print("QUDA resource path assumption: .cache/quda")
    print("Probe artifact path: demo.probe.json")
    print("Output contract: rank 0 writes the final artifact.")

def _load_runtime_modules():
    import numpy as np
    import cupy as cp
    from pyquda_utils import core, gamma, io
    return np, cp, core, gamma, io

def main() -> None:
    _validate_handoff_contract()
    _print_handoff_summary()
    np, cp, core, gamma, io = _load_runtime_modules()
    dirac = core.getClover(None, 0.0, 1e-12, 1000, 1.0, 1.0, 1.0)
    gauge = io.readQIOGauge("cfg.lime")
    t_src = 0
    propagator = core.invert(dirac, "wall", t_src)
    gathered = core.gatherLattice(propagator, [0, -1, -1, -1])
    np.save("out.npy", gathered)

if __name__ == "__main__":
    main()
'''
        validate_generated_script(code)
        missing_launch = code.replace('CLUSTER_LAUNCH = "local"\n', "")
        with self.assertRaisesRegex(ValueError, "CLUSTER_LAUNCH ="):
            validate_generated_script(missing_launch)
        missing_summary = code.replace('    print("QUDA resource path assumption: .cache/quda")\n', "")
        with self.assertRaisesRegex(ValueError, "QUDA resource path assumption:"):
            validate_generated_script(missing_summary)

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
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="wall",
            sink_type="local",
            gamma_insertions=[],
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
        physics = interpret_request("please compute the pion two-point correlator")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        self.assertTrue(plan.convention_decisions)
        self.assertEqual(plan.clarification_trace, [])
        self.assertIsNotNone(plan.runtime_readiness)
        self.assertIn("probe_policy", plan.runtime_readiness)
        self.assertFalse(plan.runtime_readiness["probe_policy"]["auto_run"])
        self.assertIn("_resolution_buckets", plan.field_resolution)
        self.assertTrue(any(item["decision"].startswith("Use wall source") for item in plan.convention_decisions))
        code = render_pion_2pt_script(task, plan)
        validate_generated_script(code)
        self.assertIn("core.getClover", code)
        self.assertIn("core.init(GRID_SIZE, LATTICE_SIZE, resource_path=RESOURCE_PATH)", code)
        self.assertIn('core.invert(dirac, "wall", t_src)', code)
        self.assertIn("io.readQIOGauge", code)
        self.assertIn("core.gatherLattice", code)
        self.assertIn("np.save", code)
        self.assertIn("import os", code)
        self.assertIn("vol = latt_info.volume", code)
        self.assertIn("ns = 4", code)
        self.assertIn("nc = 3", code)
        self.assertIn("if not GAUGE_PATH.exists()", code)
        self.assertIn("Current pion two-point workflow requires GAUGE_FORMAT='chroma_qio'", code)
        self.assertIn("Current pion two-point workflow requires SOURCE_TYPE='wall'", code)
        self.assertIn("Current pion two-point workflow requires SINK_TYPE='local'", code)
        self.assertIn("CLUSTER_LAUNCH must be a non-empty string.", code)
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
        self.assertIn("Review the sibling .physics.json, .task.json, and .plan.json artifacts", code)
        self.assertIn("launch mode assumption: hpc", code)
        self.assertIn("TASK_ARTIFACT = SCRIPT_PATH.with_suffix(\".task.json\")", code)
        self.assertIn("PHYSICS_ARTIFACT = SCRIPT_PATH.with_suffix(\".physics.json\")", code)
        self.assertIn("PLAN_ARTIFACT = SCRIPT_PATH.with_suffix(\".plan.json\")", code)
        self.assertIn("PROBE_ARTIFACT = SCRIPT_PATH.with_suffix(\".probe.json\")", code)
        self.assertIn("def _validate_handoff_contract() -> None:", code)
        self.assertIn("def _print_handoff_summary() -> None:", code)
        self.assertIn("enumerate(zip(LATTICE_SIZE, GRID_SIZE, strict=True))", code)
        self.assertIn("must be divisible by GRID_SIZE[{axis}]={grid_extent}", code)
        self.assertIn("Launch assumption: {CLUSTER_LAUNCH}", code)
        self.assertIn("Gauge input path:", code)
        self.assertIn("Input directories:", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Gauge format contract:", code)
        self.assertIn("Source/sink contract:", code)
        self.assertIn("Source timeslices:", code)
        self.assertIn("QUDA resource path assumption:", code)
        self.assertIn("Probe artifact path:", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn("CORRELATOR_OUTPUT must not reuse the gauge input path.", code)
        self.assertIn('_validate_output_parent_writable(CORRELATOR_OUTPUT, label="Correlator output")', code)
        self.assertIn("Output contract:", code)
        self.assertIn("Filesystem contract: gauge input must be visible to all ranks", code)
        self.assertIn("Input mutability contract: treat gauge inputs as read-only handoff artifacts", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the correlator output path is writable before launch.", code)

    def test_render_and_validate_quark_propagator_script(self):
        task = Pion2ptTask(
            task_type="quark_propagator",
            workflow_id="quark_propagator_chroma_point_hdf5_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            propagator_format=None,
            propagator_paths=[],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=-0.2770,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.160920226,
            coeff_r=1.160920226,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[[6, 6, 6, 4], [4, 4, 4, 9]],
            stout_smear_steps=1,
            stout_smear_rho=0.125,
            stout_smear_ndim=4,
            source_type="point",
            sink_type="propagator",
            gamma_insertions=[],
            momentum_projection="none",
            momenta=[],
            source_timeslices=[0],
            gauge_fixed=False,
            correlator_output_format="hdf5",
            correlator_output_path="/tmp/pt_prop.h5",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/quark_propagator.py",
            script_style="complete",
            field_sources={"mass": "user"},
            notes="quark test",
        )
        context = ContextBundle(
            task_type="quark_propagator",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/examples/2_Quark_Propagator.py", 3.0, "quark", "quark"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 2.0, "io", "io"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/source.py", 1.0, "source", "source"),
            ],
        )
        physics = interpret_request("please generate a quark propagator")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("core.init(GRID_SIZE, resource_path=RESOURCE_PATH)", code)
        self.assertIn("io.readChromaQIOGauge", code)
        self.assertIn("gauge.stoutSmear", code)
        self.assertIn("core.getDirac", code)
        self.assertIn("source.point(", code)
        self.assertIn("dirac.invert(b)", code)
        self.assertIn("propagator.saveH5", code)
        self.assertIn("import os", code)
        self.assertIn("Propagator output path:", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Point-source spatial origin: {SOURCE_SPATIAL_ORIGIN}", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the propagator output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(PROPAGATOR_OUTPUT, label="Propagator output")', code)
        self.assertIn("Current quark-propagator workflow requires SOURCE_TYPE='point'", code)
        self.assertIn("Current quark-propagator workflow requires SINK_TYPE='propagator'", code)

    def test_render_and_validate_gaussian_shell_quark_propagator_script(self):
        task = Pion2ptTask(
            task_type="quark_propagator",
            workflow_id="quark_propagator_gaussian_shell_chroma_hdf5_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            propagator_format=None,
            propagator_paths=[],
            lattice_size=[4, 4, 4, 8],
            grid_size=[1, 1, 1, 1],
            fermion_action="clover",
            mass=0.3478260869565215,
            xi_0=2.464,
            nu=0.95,
            coeff_t=1.07,
            coeff_r=0.91,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="point",
            sink_type="propagator",
            gamma_insertions=[],
            momentum_projection="none",
            momenta=[],
            source_timeslices=[0],
            gauge_fixed=False,
            correlator_output_format="hdf5",
            correlator_output_path="/tmp/pt_prop_shell.h5",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/quark_shell.py",
            script_style="complete",
            field_sources={"mass": "user"},
            notes="gaussian shell quark test",
            source_smearing_kind="gaussian_shell",
            source_smearing_rho=2.0,
            source_smearing_steps=5,
        )
        context = ContextBundle(
            task_type="quark_propagator",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_gaussian.py", 3.0, "gaussian", "gaussian"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 2.0, "io", "io"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/source.py", 1.0, "source", "source"),
            ],
        )
        physics = interpret_request("please generate a gaussian-shell quark propagator")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("io.readQIOGauge", code)
        self.assertIn("source.propagator(", code)
        self.assertIn("source.gaussianSmear(point_source, gauge, SOURCE_SMEARING_RHO, SOURCE_SMEARING_STEPS)", code)
        self.assertIn("core.getClover", code)
        self.assertIn("core.invertPropagator", code)
        self.assertIn("propagator.saveH5", code)
        self.assertIn("Source smearing contract:", code)
        self.assertIn("SOURCE_SMEARING_KIND = 'gaussian_shell'", code)
        self.assertIn("Current gaussian-shell quark-propagator workflow requires SOURCE_SMEARING_KIND='gaussian_shell'", code)
        self.assertNotIn("TODO", code)

    def test_render_and_validate_wilson_flow_script(self):
        task = Pion2ptTask(
            task_type="wilson_flow",
            workflow_id="wilson_flow_chroma_qio_energy_npy_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            propagator_format=None,
            propagator_paths=[],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=0.0,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.0,
            coeff_r=1.0,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="none",
            sink_type="gauge",
            gamma_insertions=[],
            momentum_projection="none",
            momenta=[],
            source_timeslices=[],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/wflow.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/wilson_flow.py",
            script_style="complete",
            field_sources={"flow_steps": "user"},
            notes="wflow test",
            flow_steps=100,
            flow_epsilon=1.0,
        )
        context = ContextBundle(
            task_type="wilson_flow",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_wflow.py", 3.0, "wflow", "wflow"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 2.0, "io", "io"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/io/__init__.py", 1.0, "io init", "io init"),
            ],
        )
        physics = interpret_request("please run wilson flow on this gauge configuration")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("wilsonFlowChroma", code)
        self.assertIn("io.readQIOGauge", code)
        self.assertIn("np.save", code)
        self.assertIn("import os", code)
        self.assertIn("FLOW_STEPS = 100", code)
        self.assertIn("FLOW_EPSILON = 1.0", code)
        self.assertIn("Current Wilson-flow workflow requires GAUGE_FORMAT='chroma_qio'", code)
        self.assertIn("Energy-history output path:", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the energy-history output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(ENERGY_OUTPUT, label="Energy-history output")', code)
        self.assertIn("test_wflow.py", code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)
        self.assertNotIn("fake_", code)

    def test_render_and_validate_ape_smear_script(self):
        task = Pion2ptTask(
            task_type="ape_smear",
            workflow_id="ape_smear_chroma_qio_npy_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            propagator_format=None,
            propagator_paths=[],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=0.0,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.0,
            coeff_r=1.0,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="none",
            sink_type="gauge",
            gamma_insertions=[],
            momentum_projection="none",
            momenta=[],
            source_timeslices=[],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/ape_smeared_gauge.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/ape_smear.py",
            script_style="complete",
            field_sources={"gauge_path": "user"},
            notes="ape test",
        )
        context = ContextBundle(
            task_type="ape_smear",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_smear.py", 3.0, "smear", "smear"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 2.0, "io", "io"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/io/__init__.py", 1.0, "io init", "io init"),
            ],
        )
        physics = interpret_request("please generate an APE-smeared gauge configuration")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("io.readQIOGauge", code)
        self.assertIn("gauge.copy()", code)
        self.assertIn("apeSmearChroma(APE_STEPS, APE_ALPHA, APE_DIR_IGNORE)", code)
        self.assertIn("APE_ALPHA = 2.5", code)
        self.assertIn("io.writeNPYGauge", code)
        self.assertIn("SMEARED_GAUGE_OUTPUT", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the smeared-gauge output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(SMEARED_GAUGE_OUTPUT, label="Smeared-gauge output")', code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)
        self.assertNotIn("fake_", code)

    def test_render_and_validate_hyp_smear_script(self):
        task = Pion2ptTask(
            task_type="hyp_smear",
            workflow_id="hyp_smear_chroma_qio_npy_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            propagator_format=None,
            propagator_paths=[],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=0.0,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.0,
            coeff_r=1.0,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="none",
            sink_type="gauge",
            gamma_insertions=[],
            momentum_projection="none",
            momenta=[],
            source_timeslices=[],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/hyp_smeared_gauge.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/hyp_smear.py",
            script_style="complete",
            field_sources={"gauge_path": "user"},
            notes="hyp test",
        )
        context = ContextBundle(
            task_type="hyp_smear",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_smear.py", 3.0, "smear", "smear"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 2.0, "io", "io"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/io/__init__.py", 1.0, "io init", "io init"),
            ],
        )
        physics = interpret_request("please generate a HYP-smeared gauge configuration")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("io.readQIOGauge", code)
        self.assertIn("gauge.copy()", code)
        self.assertIn("hypSmear(HYP_STEPS, HYP_ALPHA1, HYP_ALPHA2, HYP_ALPHA3, HYP_DIR_IGNORE)", code)
        self.assertIn("HYP_ALPHA1 = 0.75", code)
        self.assertIn("io.writeNPYGauge", code)
        self.assertIn("SMEARED_GAUGE_OUTPUT", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the smeared-gauge output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(SMEARED_GAUGE_OUTPUT, label="Smeared-gauge output")', code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)
        self.assertNotIn("fake_", code)

    def test_finalize_hyp_smear_task_without_fermion_action(self):
        draft = Pion2ptTaskDraft(
            task_type="hyp_smear",
            workflow_id="hyp_smear_chroma_qio_npy_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            source_type="none",
            sink_type="gauge",
            momentum_projection="none",
            momenta=[],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/hyp_smeared_gauge.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/hyp_smear.py",
            script_style="complete",
            field_sources={"gauge_path": "user"},
        )
        task = finalize_task(draft)
        self.assertEqual(task.workflow_id, "hyp_smear_chroma_qio_npy_v1")
        self.assertEqual(task.gauge_path, "/tmp/cfg_0001.lime")
        self.assertEqual(task.source_type, "none")

    def test_render_and_validate_stout_smear_script(self):
        task = Pion2ptTask(
            task_type="stout_smear",
            workflow_id="stout_smear_chroma_qio_npy_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            propagator_format=None,
            propagator_paths=[],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=0.0,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.0,
            coeff_r=1.0,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[],
            stout_smear_steps=1,
            stout_smear_rho=0.241,
            stout_smear_ndim=3,
            source_type="none",
            sink_type="gauge",
            gamma_insertions=[],
            momentum_projection="none",
            momenta=[],
            source_timeslices=[],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/stout_smeared_gauge.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/stout_smear.py",
            script_style="complete",
            field_sources={"gauge_path": "user"},
            notes="stout test",
        )
        context = ContextBundle(
            task_type="stout_smear",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_smear.py", 3.0, "smear", "smear"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 2.0, "io", "io"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/io/__init__.py", 1.0, "io init", "io init"),
            ],
        )
        physics = interpret_request("please generate a stout-smeared gauge")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("io.readQIOGauge", code)
        self.assertIn("gauge.copy()", code)
        self.assertIn("stoutSmear(1, 0.241, 3)", code)
        self.assertIn("io.writeNPYGauge", code)
        self.assertIn("SMEARED_GAUGE_OUTPUT", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the smeared-gauge output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(SMEARED_GAUGE_OUTPUT, label="Smeared-gauge output")', code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)
        self.assertNotIn("fake_", code)
        self.assertIn("Current stout-smear workflow requires GAUGE_FORMAT='chroma_qio'", code)
        self.assertIn("Smeared-gauge output path:", code)
        self.assertIn("test_smear.py", code)

    def test_render_and_validate_pion_dispersion_script(self):
        task = Pion2ptTask(
            task_type="pion_dispersion",
            workflow_id="pion_dispersion_chroma_point_momentum_npy_v1",
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
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="point",
            sink_type="local",
            gamma_insertions=[],
            momentum_projection="explicit",
            momenta=[[0, 0, 0], [0, 0, 1], [0, 1, 1], [1, 1, 1], [0, 0, 2], [0, 1, 2], [1, 1, 2], [0, 2, 2], [1, 2, 2]],
            source_timeslices=[0],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/pion_dispersion.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/pion_dispersion.py",
            script_style="complete",
            field_sources={"mass": "user"},
            notes="dispersion test",
        )
        context = ContextBundle(
            task_type="pion_dispersion",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet(
                    source="pyquda",
                    path="/tmp/PyQUDA/examples/5_Pion_Dispersion.py",
                    score=3.0,
                    summary="pion dispersion example",
                    excerpt="pion dispersion example",
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
                    path="/tmp/PyQUDA/pyquda_utils/gamma.py",
                    score=1.0,
                    summary="gamma example",
                    excerpt="gamma example",
                ),
            ],
        )
        physics = interpret_request("please compute pion dispersion with nonzero momentum")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("point source at [0, 0, 0, t_src]", code)
        self.assertIn("MOMENTUM_LIST =", code)
        self.assertIn("MomentumPhase", code)
        self.assertIn("CLUSTER_LAUNCH =", code)
        self.assertIn("GAUGE_FORMAT =", code)
        self.assertIn("SOURCE_TYPE =", code)
        self.assertIn("SINK_TYPE =", code)
        self.assertIn('core.invert(dirac, "point", [SOURCE_SPATIAL_ORIGIN[0], SOURCE_SPATIAL_ORIGIN[1], SOURCE_SPATIAL_ORIGIN[2], t_src])', code)
        self.assertIn("from opt_einsum import contract", code)
        self.assertIn("np.save", code)
        self.assertIn("import os", code)
        self.assertIn("Current pion-dispersion workflow requires SOURCE_TYPE='point'", code)
        self.assertIn("Current pion-dispersion workflow requires SINK_TYPE='local'", code)
        self.assertIn("Current pion-dispersion workflow requires GAUGE_FORMAT='chroma_qio'", code)
        self.assertIn("CLUSTER_LAUNCH must be a non-empty string.", code)
        self.assertIn("Each momentum component must be an integer", code)
        self.assertIn("QUDA resource path assumption:", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the correlator output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(CORRELATOR_OUTPUT, label="Correlator output")', code)
        self.assertIn("5_Pion_Dispersion.py", code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)
        self.assertNotIn("fake_", code)

    def test_render_and_validate_pion_pcac_script(self):
        task = Pion2ptTask(
            task_type="pion_pcac",
            workflow_id="pion_pcac_chroma_wall_local_zero_momentum_npy_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            propagator_format=None,
            propagator_paths=[],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=-0.2770,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.160920226,
            coeff_r=1.160920226,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[[6, 6, 6, 4], [4, 4, 4, 9]],
            stout_smear_steps=1,
            stout_smear_rho=0.125,
            stout_smear_ndim=4,
            source_type="wall",
            sink_type="local",
            gamma_insertions=[],
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            source_timeslices=[0],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/pion_pcac.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/pion_pcac.py",
            script_style="complete",
            field_sources={"mass": "user"},
            notes="pcac test",
        )
        context = ContextBundle(
            task_type="pion_pcac",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/examples/4_Pion_PCAC.py", 3.0, "pcac", "pcac"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/core.py", 2.0, "core", "core"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/gamma.py", 1.0, "gamma", "gamma"),
            ],
        )
        physics = interpret_request("please compute pion pcac ratio")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("core.getDirac", code)
        self.assertIn("io.readChromaQIOGauge", code)
        self.assertIn("gauge.stoutSmear", code)
        self.assertIn('core.invert(dirac, "wall", t_src)', code)
        self.assertIn("pion_a4", code)
        self.assertIn("gamma5 @ gamma5 @ gamma4", code)
        self.assertIn("Channel order: [pion, pionA4, ratio]", code)
        self.assertIn("Output contract: save a three-channel array ordered as [pion, pionA4, ratio].", code)
        self.assertIn("Current pion PCAC workflow requires GAUGE_FORMAT='chroma_qio'", code)
        self.assertIn("Current pion PCAC workflow requires SOURCE_TYPE='wall'", code)
        self.assertIn("Current pion PCAC workflow requires SINK_TYPE='local'", code)
        self.assertIn("MULTIGRID_BLOCKS must contain only positive block extents", code)
        self.assertIn("STOUT_SMEAR_STEPS must be strictly positive", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the correlator output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(CORRELATOR_OUTPUT, label="Correlator output")', code)
        self.assertIn("4_Pion_PCAC.py", code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)
        self.assertNotIn("fake_", code)

    def test_render_and_validate_pion_pcac_from_existing_propagator_script(self):
        task = Pion2ptTask(
            task_type="pion_pcac",
            workflow_id="pion_pcac_existing_propagator_local_zero_momentum_npy_v1",
            start_from="propagator",
            has_existing_propagators=True,
            gauge_format="chroma_qio",
            gauge_path="",
            propagator_format="npy",
            propagator_paths=["/tmp/pcac_prop_0.npy"],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=0.0,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.0,
            coeff_r=1.0,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="wall",
            sink_type="local",
            gamma_insertions=[],
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            source_timeslices=[0],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/pion_pcac_prop.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/pion_pcac_from_propagator.py",
            script_style="complete",
            field_sources={"propagator_paths": "user"},
            notes="pcac propagator test",
        )
        context = ContextBundle(
            task_type="pion_pcac",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/examples/4_Pion_PCAC.py", 3.0, "pcac", "pcac"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 2.0, "io", "io"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/io/__init__.py", 1.0, "io helpers", "io helpers"),
            ],
        )
        physics = interpret_request("please compute pion pcac ratio")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        self.assertEqual(plan.handoff_contract["input_mutability_policy"], "immutable_inputs_never_overwritten")
        self.assertEqual(plan.handoff_contract["input_manifest"][0]["source_timeslice"], 0)
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("PROPAGATOR_PATHS =", code)
        self.assertIn("SOURCE_TIMESLICES =", code)
        self.assertIn("_load_propagator", code)
        self.assertIn("io.readNPYPropagator", code)
        self.assertIn("core.init(GRID_SIZE, LATTICE_SIZE, resource_path=RESOURCE_PATH)", code)
        self.assertIn("Current propagator-entry pion PCAC workflow requires SOURCE_TYPE='wall'", code)
        self.assertIn("Current propagator-entry pion PCAC workflow requires SINK_TYPE='local'", code)
        self.assertIn("Current propagator-entry pion PCAC workflow is only grounded for GAUGE_FIXED=False", code)
        self.assertIn("Expected len(SOURCE_TIMESLICES) == len(PROPAGATOR_PATHS)", code)
        self.assertIn("Duplicate propagator paths are not allowed in the input manifest.", code)
        self.assertIn("CORRELATOR_OUTPUT must not reuse a propagator input path.", code)
        self.assertIn("Input manifest:", code)
        self.assertIn("Input mutability contract:", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Directory convention: prefer a dedicated writable results directory", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the correlator output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(CORRELATOR_OUTPUT, label="Correlator output")', code)
        self.assertIn("import os", code)
        self.assertIn("Channel order: [pion, pionA4, ratio]", code)
        self.assertIn("Propagator-entry workflow references:", code)
        self.assertIn("4_Pion_PCAC.py", code)
        self.assertIn("test_io.py", code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)
        self.assertNotIn("fake_", code)

    def test_render_and_validate_pion_2pt_from_existing_propagator_script(self):
        task = Pion2ptTask(
            task_type="pion_2pt",
            workflow_id="pion_2pt_existing_propagator_local_zero_momentum_npy_v1",
            start_from="propagator",
            has_existing_propagators=True,
            gauge_format="chroma_qio",
            gauge_path="",
            propagator_format="npy",
            propagator_paths=["/tmp/pt_prop_1.npy"],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=0.0,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.0,
            coeff_r=1.0,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="wall",
            sink_type="local",
            gamma_insertions=[],
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            source_timeslices=[0],
            gauge_fixed=True,
            correlator_output_format="npy",
            correlator_output_path="/tmp/pion_prop.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/pion_prop.py",
            script_style="complete",
            field_sources={"propagator_paths": "user"},
            notes="propagator-entry test",
        )
        context = ContextBundle(
            task_type="pion_2pt",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 3.0, "io", "io"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_mesonspec.py", 2.0, "mesonspec", "mesonspec"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/io/__init__.py", 1.0, "io helpers", "io helpers"),
            ],
        )
        physics = interpret_request("please compute the pion two-point correlator")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("io.readNPYPropagator", code)
        self.assertIn("PROPAGATOR_PATHS", code)
        self.assertIn("SOURCE_TYPE =", code)
        self.assertIn("Launch assumption:", code)
        self.assertIn("launch mode assumption: hpc", code)
        self.assertIn("QUDA resource path assumption:", code)
        self.assertIn("Probe artifact path:", code)
        self.assertIn("Output contract:", code)
        self.assertIn("CLUSTER_LAUNCH must be a non-empty string.", code)
        self.assertIn("Lattice/grid contract:", code)
        self.assertIn("Gauge-fixed assumption on loaded propagators:", code)
        self.assertIn("Duplicate propagator paths are not allowed in the input manifest.", code)
        self.assertIn("CORRELATOR_OUTPUT must not reuse a propagator input path.", code)
        self.assertIn("Input manifest:", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Input mutability contract:", code)
        self.assertIn("Directory convention: prefer a dedicated writable results directory", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the correlator output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(CORRELATOR_OUTPUT, label="Correlator output")', code)
        self.assertIn("import os", code)
        self.assertIn("Unable to import 'pyquda'. The PyQUDA core bindings are not available", code)
        self.assertIn("PROPAGATOR_FORMAT in {'npy', 'hdf5', 'chroma_qio'}", code)
        self.assertNotIn("TODO", code)

    def test_render_and_validate_meson_spec_script(self):
        task = Pion2ptTask(
            task_type="meson_spec",
            workflow_id="meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            propagator_format=None,
            propagator_paths=[],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 1],
            fermion_action="clover",
            mass=0.09253,
            xi_0=4.8965,
            nu=0.86679,
            coeff_t=0.8549165664,
            coeff_r=2.32582045,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="wall",
            sink_type="local",
            gamma_insertions=["gamma5_gamma5", "gamma4gamma5_gamma4gamma5"],
            momentum_projection="explicit",
            momenta=[[0, 0, 0], [1, 1, 1]],
            source_timeslices=[],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/meson_spec.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/meson_spec.py",
            script_style="complete",
            field_sources={"mass": "user"},
            notes="meson spec test",
        )
        context = ContextBundle(
            task_type="meson_spec",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_mesonspec.py", 3.0, "mesonspec", "mesonspec"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/phase.py", 2.0, "phase", "phase"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/gamma.py", 1.0, "gamma", "gamma"),
            ],
        )
        physics = interpret_request("please compute meson spectroscopy correlators")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("meson_spec = np.zeros", code)
        self.assertIn("MomentumPhase", code)
        self.assertIn("phase.getPhases", code)
        self.assertIn("GAMMA_INSERTION_LABELS", code)
        self.assertIn("core.invert(dirac, \"wall\", t_src)", code)
        self.assertIn("Current meson-spectroscopy workflow is only grounded for GRID_SIZE[3] == 1", code)
        self.assertIn("CLUSTER_LAUNCH must be a non-empty string.", code)
        self.assertIn("Gauge format contract:", code)
        self.assertIn("Source/sink contract:", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the correlator output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(CORRELATOR_OUTPUT, label="Correlator output")', code)
        self.assertIn("Saved meson spectroscopy correlator tensor", code)
        self.assertIn("Probe artifact path:", code)
        self.assertIn("test_mesonspec.py", code)
        self.assertIn("pyquda_utils/phase.py", code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)

    def test_render_and_validate_meson_spec_from_propagator_script(self):
        task = Pion2ptTask(
            task_type="meson_spec",
            workflow_id="meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1",
            start_from="propagator",
            has_existing_propagators=True,
            gauge_format=None,
            gauge_path=None,
            propagator_format="npy",
            propagator_paths=["/tmp/meson_prop_0.npy", "/tmp/meson_prop_8.npy"],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 1],
            fermion_action=None,
            mass=0.0,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.0,
            coeff_r=1.0,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="wall",
            sink_type="local",
            gamma_insertions=["gamma5_gamma5", "gamma4gamma5_gamma4gamma5"],
            momentum_projection="explicit",
            momenta=[[0, 0, 0], [1, 1, 1]],
            source_timeslices=[0, 8],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/meson_spec_prop.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/meson_spec_from_prop.py",
            script_style="complete",
            field_sources={"propagator_paths": "user"},
            notes="meson spec propagator test",
        )
        context = ContextBundle(
            task_type="meson_spec",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_mesonspec.py", 3.0, "mesonspec", "mesonspec"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 2.0, "io", "io"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/io/__init__.py", 1.0, "io helpers", "io helpers"),
            ],
        )
        physics = interpret_request("please compute meson spectroscopy correlators")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("PROPAGATOR_PATHS", code)
        self.assertIn("SOURCE_TIMESLICES", code)
        self.assertIn("io.readNPYPropagator", code)
        self.assertIn("Current propagator-entry mesonspec workflow requires SOURCE_TYPE='wall'", code)
        self.assertIn("Current propagator-entry mesonspec workflow requires SINK_TYPE='local'", code)
        self.assertIn("Current propagator-entry mesonspec workflow is only grounded for GRID_SIZE[3] == 1", code)
        self.assertIn("len(SOURCE_TIMESLICES) == len(PROPAGATOR_PATHS)", code)
        self.assertIn("Input manifest:", code)
        self.assertIn("Input mutability contract:", code)
        self.assertIn("Gauge-fixed assumption on loaded propagators:", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Directory convention: prefer a dedicated writable results directory", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the correlator output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(CORRELATOR_OUTPUT, label="Correlator output")', code)
        self.assertIn("import os", code)
        self.assertIn("MomentumPhase", code)
        self.assertIn("Saved meson spectroscopy correlator tensor", code)
        self.assertIn("test_mesonspec.py", code)
        self.assertIn("test_io.py", code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)

    def test_finalize_task_accepts_minimal_propagator_entry_fields(self):
        draft = Pion2ptTaskDraft(
            task_type="pion_2pt",
            workflow_id="pion_2pt_existing_propagator_local_zero_momentum_npy_v1",
            start_from="propagator",
            has_existing_propagators=True,
            propagator_format="hdf5",
            propagator_paths=["/tmp/pt_prop_1.h5"],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            source_type="wall",
            sink_type="local",
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            gauge_fixed=True,
            correlator_output_format="npy",
            correlator_output_path="/tmp/pion_prop.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/pion_prop.py",
            script_style="complete",
            field_sources={"propagator_paths": "user"},
        )
        task = finalize_task(draft)
        self.assertEqual(task.workflow_id, "pion_2pt_existing_propagator_local_zero_momentum_npy_v1")
        self.assertEqual(task.propagator_format, "hdf5")
        self.assertEqual(task.mass, 0.0)

    def test_render_and_validate_proton_script(self):
        task = Pion2ptTask(
            task_type="proton_2pt",
            workflow_id="proton_2pt_chroma_wall_local_zero_momentum_npy_v1",
            start_from="gauge",
            has_existing_propagators=False,
            gauge_format="chroma_qio",
            gauge_path="/tmp/cfg_0001.lime",
            propagator_format=None,
            propagator_paths=[],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=-0.2770,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.160920226,
            coeff_r=1.160920226,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[[6, 6, 6, 4], [4, 4, 4, 9]],
            stout_smear_steps=1,
            stout_smear_rho=0.125,
            stout_smear_ndim=4,
            source_type="wall",
            sink_type="local",
            gamma_insertions=[],
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            source_timeslices=[0],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/proton_2pt.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/proton_2pt.py",
            script_style="complete",
            field_sources={"mass": "user"},
            notes="proton test",
        )
        context = ContextBundle(
            task_type="proton_2pt",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet(
                    source="pyquda",
                    path="/tmp/PyQUDA/examples/3_Pion_Proton_2pt.py",
                    score=3.0,
                    summary="proton correlator example",
                    excerpt="proton correlator example",
                ),
                ContextSnippet(
                    source="pyquda",
                    path="/tmp/PyQUDA/pyquda_utils/core.py",
                    score=2.0,
                    summary="core helper",
                    excerpt="core helper",
                ),
                ContextSnippet(
                    source="pyquda",
                    path="/tmp/PyQUDA/pyquda_utils/gamma.py",
                    score=1.0,
                    summary="gamma helper",
                    excerpt="gamma helper",
                ),
            ],
        )
        physics = interpret_request("please compute the proton two-point correlator")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("core.getDirac", code)
        self.assertIn("Probe artifact path:", code)
        self.assertIn("Output contract:", code)
        self.assertIn("gauge.stoutSmear", code)
        self.assertIn('core.invert(dirac, "wall", t_src)', code)
        self.assertIn("contract_proton_zero_momentum", code)
        self.assertIn("from itertools import permutations", code)
        self.assertIn("readChromaQIOGauge", code)
        self.assertIn("MULTIGRID_BLOCKS =", code)
        self.assertIn("STOUT_SMEAR_RHO =", code)
        self.assertIn("CLUSTER_LAUNCH =", code)
        self.assertIn("GAUGE_FORMAT =", code)
        self.assertIn("SOURCE_TYPE =", code)
        self.assertIn("SINK_TYPE =", code)
        self.assertIn("Current proton workflow requires SOURCE_TYPE='wall'", code)
        self.assertIn("Current proton workflow requires SINK_TYPE='local'", code)
        self.assertIn("Current proton workflow requires GAUGE_FORMAT='chroma_qio'", code)
        self.assertIn("MULTIGRID_BLOCKS must contain only positive block extents", code)
        self.assertIn("STOUT_SMEAR_STEPS must be strictly positive", code)
        self.assertIn("QUDA resource path assumption:", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the correlator output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(CORRELATOR_OUTPUT, label="Correlator output")', code)
        self.assertIn("import os", code)
        self.assertIn("3_Pion_Proton_2pt.py", code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)
        self.assertNotIn("fake_", code)

    def test_render_and_validate_proton_from_existing_propagator_script(self):
        task = Pion2ptTask(
            task_type="proton_2pt",
            workflow_id="proton_2pt_existing_propagator_local_zero_momentum_npy_v1",
            start_from="propagator",
            has_existing_propagators=True,
            gauge_format="chroma_qio",
            gauge_path="",
            propagator_format="npy",
            propagator_paths=["/tmp/proton_prop_0.npy", "/tmp/proton_prop_12.npy"],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=0.0,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.0,
            coeff_r=1.0,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="wall",
            sink_type="local",
            gamma_insertions=[],
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            source_timeslices=[0, 12],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/proton_prop.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/proton_prop.py",
            script_style="complete",
            field_sources={"propagator_paths": "user"},
            notes="proton propagator-entry test",
        )
        context = ContextBundle(
            task_type="proton_2pt",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/examples/3_Pion_Proton_2pt.py", 3.0, "proton example", "proton example"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 2.0, "io test", "io test"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/io/__init__.py", 1.0, "io helper", "io helper"),
            ],
        )
        physics = interpret_request("please compute the proton two-point correlator")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("PROPAGATOR_PATHS", code)
        self.assertIn("SOURCE_TIMESLICES", code)
        self.assertIn("io.readNPYPropagator", code)
        self.assertIn("contract_proton_zero_momentum", code)
        self.assertIn("Expected len(SOURCE_TIMESLICES) == len(PROPAGATOR_PATHS)", code)
        self.assertIn("Current propagator-entry proton workflow requires SOURCE_TYPE='wall'", code)
        self.assertIn("Current propagator-entry proton workflow requires SINK_TYPE='local'", code)
        self.assertIn("Current propagator-entry proton workflow is only grounded for GAUGE_FIXED=False", code)
        self.assertIn("Input manifest:", code)
        self.assertIn("Input mutability contract:", code)
        self.assertIn("Gauge-fixed assumption on loaded propagators:", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Directory convention: prefer a dedicated writable results directory", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the correlator output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(CORRELATOR_OUTPUT, label="Correlator output")', code)
        self.assertIn("import os", code)
        self.assertIn("3_Pion_Proton_2pt.py", code)
        self.assertIn("test_io.py", code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)

    def test_render_and_validate_rho_vector_script(self):
        task = Pion2ptTask(
            task_type="rho_vector",
            workflow_id="rho_vector_chroma_wall_local_zero_momentum_npy_v1",
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
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="wall",
            sink_type="local",
            gamma_insertions=["gamma1_gamma1", "gamma2_gamma2", "gamma3_gamma3"],
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            source_timeslices=[0],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/rho_vector.npy",
            resource_path=".cache/quda",
            cluster_launch="slurm",
            script_output_path="/tmp/rho_vector.py",
            script_style="complete",
            field_sources={"mass": "user"},
            notes="rho test",
        )
        context = ContextBundle(
            task_type="rho_vector",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_mesonspec.py", 3.0, "mesonspec", "mesonspec"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_mesonspec.ini.xml", 2.0, "rho xml", "rho_x"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 1.5, "io", "io"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/io/__init__.py", 1.0, "io helpers", "readQIOGauge"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/core.py", 1.0, "core helpers", "invert"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/gamma.py", 1.0, "gamma helpers", "gamma"),
            ],
        )
        physics = interpret_request("please compute the rho meson two-point correlator")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        self.assertTrue(any("gamma_i" in item["decision"] or "gamma.gamma(1/2/4)" in item["decision"] for item in plan.convention_decisions))
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("core.getClover", code)
        self.assertIn('core.invert(dirac, "wall", t_src)', code)
        self.assertIn("io.readQIOGauge", code)
        self.assertIn("GAMMA_INSERTION_LABELS = ['gamma1_gamma1', 'gamma2_gamma2', 'gamma3_gamma3']", code)
        self.assertIn("Gamma-axis order: ['gamma1_gamma1', 'gamma2_gamma2', 'gamma3_gamma3']", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the correlator output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(CORRELATOR_OUTPUT, label="Correlator output")', code)
        self.assertIn("import os", code)
        self.assertIn("test_mesonspec.py", code)
        self.assertIn("test_mesonspec.ini.xml", code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)
        self.assertNotIn("fake_", code)
        self.assertNotIn("fake_", code)

    def test_render_and_validate_rho_vector_from_propagator_script(self):
        task = Pion2ptTask(
            task_type="rho_vector",
            workflow_id="rho_vector_existing_propagator_local_zero_momentum_npy_v1",
            start_from="propagator",
            has_existing_propagators=True,
            gauge_format="chroma_qio",
            gauge_path="",
            propagator_format="npy",
            propagator_paths=["/tmp/rho_prop_0.npy"],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            fermion_action="clover",
            mass=0.0,
            xi_0=1.0,
            nu=1.0,
            coeff_t=1.0,
            coeff_r=1.0,
            solver_tol=1e-12,
            solver_maxiter=1000,
            multigrid_blocks=[],
            stout_smear_steps=None,
            stout_smear_rho=None,
            stout_smear_ndim=None,
            source_type="wall",
            sink_type="local",
            gamma_insertions=["gamma1_gamma1", "gamma2_gamma2", "gamma3_gamma3"],
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            source_timeslices=[0],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/rho_vector.npy",
            resource_path=".cache/quda",
            cluster_launch="slurm",
            script_output_path="/tmp/rho_vector_from_prop.py",
            script_style="complete",
            field_sources={"propagator_paths": "user"},
            notes="rho propagator-entry test",
        )
        context = ContextBundle(
            task_type="rho_vector",
            index_summary={"file_count": 1},
            snippets=[
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_mesonspec.py", 3.0, "mesonspec", "vector channel"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/tests/test_io.py", 1.5, "io", "io"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/io/__init__.py", 1.0, "io helpers", "readQIOPropagator"),
                ContextSnippet("pyquda", "/tmp/PyQUDA/pyquda_utils/gamma.py", 1.0, "gamma helpers", "gamma"),
            ],
        )
        physics = interpret_request("please compute the rho meson two-point correlator")
        match = match_supported_workflow(physics, task)  # type: ignore[arg-type]
        plan = build_implementation_plan(task, physics, match, context, pyquda_repo=Path("/tmp/PyQUDA"))  # type: ignore[arg-type]
        self.assertTrue(any("stored propagators" in item["decision"] or "IO helpers" in item["decision"] for item in plan.convention_decisions))
        code = render_complete_script(task, plan)
        validate_generated_script(code)
        self.assertIn("PROPAGATOR_PATHS", code)
        self.assertIn("SOURCE_TIMESLICES", code)
        self.assertIn("GAMMA_INSERTION_LABELS = ['gamma1_gamma1', 'gamma2_gamma2', 'gamma3_gamma3']", code)
        self.assertIn("io.readNPYPropagator", code)
        self.assertIn("Expected len(SOURCE_TIMESLICES) == len(PROPAGATOR_PATHS)", code)
        self.assertIn("Current propagator-entry rho/vector workflow requires SOURCE_TYPE='wall'", code)
        self.assertIn("Current propagator-entry rho/vector workflow requires SINK_TYPE='local'", code)
        self.assertIn("Current propagator-entry rho/vector workflow is only grounded for GAUGE_FIXED=False", code)
        self.assertIn("Input manifest:", code)
        self.assertIn("Input mutability contract:", code)
        self.assertIn("Gamma-axis order: ['gamma1_gamma1', 'gamma2_gamma2', 'gamma3_gamma3']", code)
        self.assertIn("Output parent directory:", code)
        self.assertIn("Directory convention: prefer a dedicated writable results directory", code)
        self.assertIn("Submission precheck: confirm the nearest existing parent of the correlator output path is writable before launch.", code)
        self.assertIn("def _nearest_existing_parent(path: Path) -> Path:", code)
        self.assertIn("def _validate_output_parent_writable(path: Path, *, label: str) -> None:", code)
        self.assertIn('_validate_output_parent_writable(CORRELATOR_OUTPUT, label="Correlator output")', code)
        self.assertIn("import os", code)
        self.assertIn("test_mesonspec.py", code)
        self.assertIn("test_io.py", code)
        self.assertNotIn("TODO", code)
        self.assertNotIn("pass", code)
        self.assertNotIn("placeholder", code)
        self.assertNotIn("fake_", code)

    def test_finalize_task_accepts_minimal_proton_propagator_entry_fields(self):
        draft = Pion2ptTaskDraft(
            task_type="proton_2pt",
            workflow_id="proton_2pt_existing_propagator_local_zero_momentum_npy_v1",
            start_from="propagator",
            has_existing_propagators=True,
            propagator_format="hdf5",
            propagator_paths=["/tmp/proton_prop_0.h5"],
            lattice_size=[24, 24, 24, 72],
            grid_size=[1, 1, 1, 2],
            source_type="wall",
            sink_type="local",
            momentum_projection="zero",
            momenta=[[0, 0, 0]],
            source_timeslices=[0],
            gauge_fixed=False,
            correlator_output_format="npy",
            correlator_output_path="/tmp/proton_prop.npy",
            resource_path=".cache/quda",
            cluster_launch="hpc",
            script_output_path="/tmp/proton_prop.py",
            script_style="complete",
            field_sources={"propagator_paths": "user"},
        )
        task = finalize_task(draft)
        self.assertEqual(task.workflow_id, "proton_2pt_existing_propagator_local_zero_momentum_npy_v1")
        self.assertEqual(task.propagator_format, "hdf5")
        self.assertEqual(task.mass, 0.0)


if __name__ == "__main__":
    unittest.main()
