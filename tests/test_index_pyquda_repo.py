import tempfile
import unittest
from pathlib import Path

from scripts.index_pyquda_repo import build_index
from scripts.index_pyquda_repo import module_name_from_path
from scripts.index_pyquda_repo import normalize_python_module_basename
from scripts.index_pyquda_repo import validate_repo_root


class IndexPyQudaRepoTests(unittest.TestCase):
    def test_normalize_python_module_basename_handles_template_sources(self):
        self.assertEqual(normalize_python_module_basename("enum_quda.in.py"), "enum_quda")
        self.assertEqual(normalize_python_module_basename("quda_define.in.py"), "quda_define")
        self.assertEqual(normalize_python_module_basename("__init__.py"), "__init__")
        self.assertIsNone(normalize_python_module_basename("quda.pyi"))

    def test_module_name_from_path_normalizes_in_py_modules(self):
        repo_root = Path("/repo")
        module_path = repo_root / "pyquda_core" / "pyquda" / "enum_quda.in.py"
        self.assertEqual(module_name_from_path(repo_root, module_path), "pyquda.enum_quda")

    def test_validate_repo_root_fails_for_missing_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / "pyquda_core").mkdir()
            with self.assertRaises(FileNotFoundError):
                validate_repo_root(repo_root, ["pyquda_core", "pyquda_utils"])

    def test_build_index_top_level_packages_only_include_package_inits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / "pyquda_core" / "pyquda").mkdir(parents=True)
            (repo_root / "pyquda_core" / "pyquda_comm").mkdir(parents=True)
            (repo_root / "pyquda_utils").mkdir(parents=True)
            (repo_root / "pyquda_io").mkdir(parents=True)
            (repo_root / "pyquda_plugins").mkdir(parents=True)
            (repo_root / "tests").mkdir(parents=True)
            (repo_root / "examples").mkdir(parents=True)

            (repo_root / "pyquda_core" / "pyquda" / "__init__.py").write_text("", encoding="utf-8")
            (repo_root / "pyquda_core" / "pyquda" / "__main__.py").write_text("", encoding="utf-8")
            (repo_root / "pyquda_core" / "pyquda" / "enum_quda.in.py").write_text("", encoding="utf-8")
            (repo_root / "pyquda_core" / "pyquda_comm" / "__init__.py").write_text("", encoding="utf-8")
            (repo_root / "pyquda_core" / "setup.py").write_text("", encoding="utf-8")
            (repo_root / "pyquda_utils" / "__init__.py").write_text("", encoding="utf-8")
            (repo_root / "pyquda_io" / "__init__.py").write_text("", encoding="utf-8")
            (repo_root / "tests" / "test_index.py").write_text("", encoding="utf-8")

            index = build_index(
                repo_root,
                ["pyquda_core", "pyquda_utils", "pyquda_io", "pyquda_plugins", "tests", "examples"],
            )

            self.assertEqual(
                index["top_level_packages"],
                [
                    {"area": "pyquda_core", "module_name": "pyquda", "path": "pyquda_core/pyquda/__init__.py"},
                    {
                        "area": "pyquda_core",
                        "module_name": "pyquda_comm",
                        "path": "pyquda_core/pyquda_comm/__init__.py",
                    },
                    {"area": "pyquda_io", "module_name": "pyquda_io", "path": "pyquda_io/__init__.py"},
                    {"area": "pyquda_utils", "module_name": "pyquda_utils", "path": "pyquda_utils/__init__.py"},
                ],
            )

            python_modules = {item["path"]: item["module_name"] for item in index["python_modules"]}
            self.assertEqual(python_modules["pyquda_core/pyquda/enum_quda.in.py"], "pyquda.enum_quda")
            self.assertNotIn("tests/test_index.py", {item["path"] for item in index["top_level_packages"]})


if __name__ == "__main__":
    unittest.main()
