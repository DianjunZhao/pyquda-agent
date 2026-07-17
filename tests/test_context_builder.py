import json
import tempfile
import unittest
from pathlib import Path

from pyquda_agent.retrieval.context_builder import build_context_bundle


class ContextBuilderTests(unittest.TestCase):
    def test_build_context_bundle_prioritizes_pyquda_workflow_references(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "examples").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_PION_2PT_SPEC.md").write_text("fixed pion workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")

            (pyquda / "examples" / "3_Pion_Proton_2pt.py").write_text("pion correlator example", encoding="utf-8")
            (pyquda / "examples" / "5_Pion_Dispersion.py").write_text("dispersion pion example", encoding="utf-8")
            (pyquda / "tests" / "test_mesonspec.py").write_text("mesonspec pion test", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("io pion test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge", encoding="utf-8")
            (pyquda / "pyquda_utils" / "source.py").write_text("wall source helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "core.py").write_text("invert core helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma matrices", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 12}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete runnable pion 2pt from gauge with wall source local sink zero momentum",
                task_type="pion_2pt",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "pion_2pt")
            self.assertEqual(bundle.index_summary["file_count"], 12)
            self.assertEqual(bundle.index_provenance["status"], "matched")
            self.assertTrue(any("3_Pion_Proton_2pt.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("test_mesonspec.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("5_Pion_Dispersion.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/io/__init__.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/source.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/gamma.py" in item.path for item in bundle.snippets))
            self.assertFalse(any(item.path.endswith("README.md") for item in bundle.snippets))

    def test_build_context_bundle_supports_pion_dispersion_task_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "examples").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_PION_2PT_SPEC.md").write_text("fixed pion workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")

            (pyquda / "examples" / "3_Pion_Proton_2pt.py").write_text("pion correlator example", encoding="utf-8")
            (pyquda / "examples" / "5_Pion_Dispersion.py").write_text("dispersion pion example", encoding="utf-8")
            (pyquda / "tests" / "test_mesonspec.py").write_text("mesonspec pion test", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("io pion test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge", encoding="utf-8")
            (pyquda / "pyquda_utils" / "source.py").write_text("point source helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "core.py").write_text("invert core helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma matrices", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 12}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete runnable pion dispersion script with nonzero momentum",
                task_type="pion_dispersion",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "pion_dispersion")
            self.assertEqual(bundle.index_provenance["status"], "matched")
            self.assertTrue(any("5_Pion_Dispersion.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("test_mesonspec.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/core.py" in item.path for item in bundle.snippets))

    def test_build_context_bundle_supports_pion_pcac_task_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "examples").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_PION_PCAC_SPEC.md").write_text("pcac workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")

            (pyquda / "examples" / "4_Pion_PCAC.py").write_text("pion pcac example", encoding="utf-8")
            (pyquda / "examples" / "3_Pion_Proton_2pt.py").write_text("pion baseline example", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("io pion test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readChromaQIOGauge", encoding="utf-8")
            (pyquda / "pyquda_utils" / "core.py").write_text("getDirac helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma matrices", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 10}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete runnable pion pcac ratio script",
                task_type="pion_pcac",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "pion_pcac")
            self.assertEqual(bundle.index_provenance["status"], "matched")
            self.assertTrue(any("4_Pion_PCAC.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/core.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/gamma.py" in item.path for item in bundle.snippets))

    def test_build_context_bundle_supports_proton_task_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "examples").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_PROTON_2PT_SPEC.md").write_text("fixed proton workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")

            (pyquda / "examples" / "3_Pion_Proton_2pt.py").write_text("proton correlator example", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("io proton test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readChromaQIOGauge", encoding="utf-8")
            (pyquda / "pyquda_utils" / "source.py").write_text("wall source helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "core.py").write_text("getDirac helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma matrices", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 9}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete runnable proton 2pt from gauge with wall source",
                task_type="proton_2pt",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "proton_2pt")
            self.assertEqual(bundle.index_provenance["status"], "matched")
            self.assertTrue(any("3_Pion_Proton_2pt.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/core.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/gamma.py" in item.path for item in bundle.snippets))

    def test_build_context_bundle_supports_proton_existing_propagator_branch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "examples").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_PROTON_2PT_SPEC.md").write_text("fixed proton workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")

            (pyquda / "examples" / "3_Pion_Proton_2pt.py").write_text("proton correlator example", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("propagator io test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOPropagator", encoding="utf-8")
            (pyquda / "pyquda_utils" / "source.py").write_text("wall source helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "core.py").write_text("LatticePropagator load helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma matrices", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 9}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete runnable proton 2pt from existing propagator /tmp/proton_prop.npy",
                task_type="proton_2pt",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "proton_2pt")
            self.assertEqual(bundle.index_provenance["status"], "matched")
            self.assertTrue(any("3_Pion_Proton_2pt.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("test_io.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/io/__init__.py" in item.path for item in bundle.snippets))

    def test_build_context_bundle_supports_rho_vector_task_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_RHO_VECTOR_SPEC.md").write_text("fixed rho workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")

            (pyquda / "tests" / "test_mesonspec.py").write_text("mesonspec rho test", encoding="utf-8")
            (pyquda / "tests" / "test_mesonspec.ini.xml").write_text("<sink_particle>rho_x</sink_particle>", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("io rho test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge", encoding="utf-8")
            (pyquda / "pyquda_utils" / "core.py").write_text("invert core helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma matrices", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 9}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete runnable rho vector script from gauge with wall source local sink",
                task_type="rho_vector",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "rho_vector")
            self.assertEqual(bundle.index_provenance["status"], "matched")
            self.assertTrue(any("test_mesonspec.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("test_mesonspec.ini.xml" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/gamma.py" in item.path for item in bundle.snippets))

    def test_build_context_bundle_supports_quark_propagator_task_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "examples").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_QUARK_PROPAGATOR_SPEC.md").write_text("quark propagator workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")

            (pyquda / "examples" / "2_Quark_Propagator.py").write_text("quark propagator example", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("propagator io test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readChromaQIOGauge", encoding="utf-8")
            (pyquda / "pyquda_utils" / "source.py").write_text("point source helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "core.py").write_text("getDirac LatticePropagator", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 8}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete quark propagator from gauge with point source",
                task_type="quark_propagator",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "quark_propagator")
            self.assertEqual(bundle.index_provenance["status"], "matched")
            self.assertTrue(any("2_Quark_Propagator.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("test_io.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/source.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/core.py" in item.path for item in bundle.snippets))

    def test_build_context_bundle_supports_meson_spec_task_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_MESON_SPEC_SPEC.md").write_text("meson spec workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")

            (pyquda / "tests" / "test_mesonspec.py").write_text("mesonspec pion test", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("io pion test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge", encoding="utf-8")
            (pyquda / "pyquda_utils" / "core.py").write_text("invert core helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma matrices", encoding="utf-8")
            (pyquda / "pyquda_utils" / "phase.py").write_text("getMomList", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 7}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete meson spectroscopy correlator script",
                task_type="meson_spec",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "meson_spec")
            self.assertEqual(bundle.index_provenance["status"], "matched")
            self.assertTrue(any("test_mesonspec.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/phase.py" in item.path for item in bundle.snippets))

    def test_build_context_bundle_supports_wilson_flow_task_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_WILSON_FLOW_SPEC.md").write_text("wilson flow workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")

            (pyquda / "tests" / "test_wflow.py").write_text("wilsonFlowChroma", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("io gauge test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge writeNPYGauge", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 5}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete wilson flow script",
                task_type="wilson_flow",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "wilson_flow")
            self.assertEqual(bundle.index_provenance["status"], "matched")
            self.assertTrue(any("test_wflow.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/io/__init__.py" in item.path for item in bundle.snippets))

    def test_build_context_bundle_supports_stout_smear_task_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_STOUT_SMEAR_SPEC.md").write_text("stout smear workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")

            (pyquda / "tests" / "test_smear.py").write_text("gauge.copy() stoutSmear(1, 0.241, 3)", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("io gauge test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge writeNPYGauge", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 5}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete stout smear script",
                task_type="stout_smear",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "stout_smear")
            self.assertEqual(bundle.index_provenance["status"], "matched")
            self.assertTrue(any("test_smear.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/io/__init__.py" in item.path for item in bundle.snippets))

    def test_build_context_bundle_supports_ape_smear_task_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_APE_SMEAR_SPEC.md").write_text("ape smear workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")

            (pyquda / "tests" / "test_smear.py").write_text("gauge.copy() apeSmearChroma(1, 2.5, 4)", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("io gauge test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge writeNPYGauge", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 5}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete ape smear script",
                task_type="ape_smear",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "ape_smear")
            self.assertEqual(bundle.index_provenance["status"], "matched")
            self.assertTrue(any("test_smear.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/io/__init__.py" in item.path for item in bundle.snippets))

    def test_build_context_bundle_marks_index_repo_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            pyquda = root / "PyQUDA"
            other_pyquda = root / "OtherPyQUDA"
            index_path = workspace / "data" / "pyquda_index.json"

            (workspace / "docs").mkdir(parents=True)
            (workspace / "data").mkdir(parents=True)
            (pyquda / "examples").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)
            other_pyquda.mkdir(parents=True)

            (workspace / "docs" / "RUNNABLE_PION_2PT_SPEC.md").write_text("fixed pion workflow", encoding="utf-8")
            (workspace / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (workspace / "docs" / "RUN_WORKFLOW.md").write_text("run workflow", encoding="utf-8")
            (pyquda / "examples" / "3_Pion_Proton_2pt.py").write_text("pion correlator example", encoding="utf-8")
            (pyquda / "examples" / "5_Pion_Dispersion.py").write_text("dispersion pion example", encoding="utf-8")
            (pyquda / "tests" / "test_mesonspec.py").write_text("mesonspec pion test", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("io pion test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge", encoding="utf-8")
            (pyquda / "pyquda_utils" / "source.py").write_text("wall source helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "core.py").write_text("invert core helper", encoding="utf-8")
            (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma matrices", encoding="utf-8")

            index_path.write_text(
                json.dumps({"repo_root": str(other_pyquda.resolve()), "summary": {"file_count": 77}}),
                encoding="utf-8",
            )

            bundle = build_context_bundle(
                task_description="generate complete runnable pion 2pt from gauge with wall source local sink zero momentum",
                task_type="pion_2pt",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )

            self.assertEqual(bundle.index_provenance["status"], "repo_mismatch")
            self.assertEqual(bundle.index_provenance["requested_repo_root"], str(pyquda.resolve()))
            self.assertEqual(bundle.index_provenance["indexed_repo_root"], str(other_pyquda.resolve()))
            self.assertEqual(bundle.index_summary["file_count"], 77)


if __name__ == "__main__":
    unittest.main()
