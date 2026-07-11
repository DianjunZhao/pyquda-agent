import unittest
from pathlib import Path


class RuntimeBootstrapDocTests(unittest.TestCase):
    def test_runtime_bootstrap_doc_mentions_required_steps(self):
        text = Path("docs/PYQUDA_RUNTIME_BOOTSTRAP.md").read_text(encoding="utf-8")
        self.assertIn("QUDA_PATH", text)
        self.assertIn("cupy", text)
        self.assertIn("pyquda", text)
        self.assertIn("pyquda_utils", text)
        self.assertIn("scan_runtime_candidates.py", text)
        self.assertIn("no compiled `*.so` or `*.dylib` artifacts", text)


if __name__ == "__main__":
    unittest.main()
