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

            index_path.write_text(json.dumps({"summary": {"file_count": 12}}), encoding="utf-8")

            bundle = build_context_bundle(
                task_description="generate complete runnable pion 2pt from gauge with wall source local sink zero momentum",
                task_type="pion_2pt",
                workspace_root=workspace,
                pyquda_repo=pyquda,
                index_path=index_path,
            )
            self.assertEqual(bundle.task_type, "pion_2pt")
            self.assertEqual(bundle.index_summary["file_count"], 12)
            self.assertTrue(any("3_Pion_Proton_2pt.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("test_mesonspec.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("5_Pion_Dispersion.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/io/__init__.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/source.py" in item.path for item in bundle.snippets))
            self.assertTrue(any("pyquda_utils/gamma.py" in item.path for item in bundle.snippets))
            self.assertFalse(any(item.path.endswith("README.md") for item in bundle.snippets))


if __name__ == "__main__":
    unittest.main()
