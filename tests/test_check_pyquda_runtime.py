import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_pyquda_runtime import build_report
from scripts.check_pyquda_runtime import probe_module


class CheckPyQudaRuntimeTests(unittest.TestCase):
    def test_probe_detects_missing_runtime_modules(self):
        result = probe_module("definitely_missing_module_name")
        self.assertFalse(result["ok"])
        self.assertEqual(result["module"], "definitely_missing_module_name")

    def test_build_report_marks_minimal_repo_not_ready(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "PyQUDA"
            repo.mkdir(parents=True)
            pyquda_utils = repo / "pyquda_utils"
            pyquda_utils.mkdir()
            (pyquda_utils / "_version.py").write_text('__version__ = "0.0"\n', encoding="utf-8")
            (pyquda_utils / "__init__.py").write_text("from ._version import __version__\n", encoding="utf-8")

            fake_checks = {
                "numpy": {"module": "numpy", "ok": True, "path": "/tmp/site-packages/numpy/__init__.py"},
                "cupy": {"module": "cupy", "ok": False, "error_type": "ModuleNotFoundError", "error": "No module named 'cupy'"},
                "pyquda": {"module": "pyquda", "ok": False, "error_type": "ModuleNotFoundError", "error": "No module named 'pyquda'"},
                "pyquda_utils": {"module": "pyquda_utils", "ok": True, "path": str((pyquda_utils / "__init__.py").resolve())},
                "pyquda_utils.core": {"module": "pyquda_utils.core", "ok": False, "error_type": "ModuleNotFoundError", "error": "No module named 'pyquda_utils.core'"},
            }
            with patch("scripts.check_pyquda_runtime.probe_module", side_effect=lambda name: fake_checks[name]):
                report = build_report(repo, use_repo_pythonpath=True)
            self.assertFalse(report["ready"])
            checks = {item["module"]: item for item in report["checks"]}
            self.assertTrue(checks["numpy"]["ok"])
            self.assertFalse(checks["cupy"]["ok"])
            blockers = report["evidence_levels"]["blockers"]
            self.assertTrue(any(item["module"] == "cupy" for item in blockers))
            self.assertTrue(any("CuPy" in item["suggestion"] for item in blockers if item["module"] == "cupy"))


if __name__ == "__main__":
    unittest.main()
