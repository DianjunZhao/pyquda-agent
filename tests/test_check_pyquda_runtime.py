import tempfile
import unittest
from pathlib import Path

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

            report = build_report(repo, use_repo_pythonpath=True)
            self.assertFalse(report["ready"])
            checks = {item["module"]: item for item in report["checks"]}
            self.assertTrue(checks["numpy"]["ok"])
            self.assertFalse(checks["cupy"]["ok"])


if __name__ == "__main__":
    unittest.main()
