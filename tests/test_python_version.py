import unittest

from pyquda_agent.python_version import python_version_ok
from pyquda_agent.python_version import supported_python_version_string
from pyquda_agent.python_version import unsupported_python_message


class PythonVersionTests(unittest.TestCase):
    def test_supported_python_version_string(self):
        self.assertEqual(supported_python_version_string(), "3.10")

    def test_python_version_ok(self):
        self.assertTrue(python_version_ok((3, 10, 0)))
        self.assertTrue(python_version_ok((3, 13, 1)))
        self.assertFalse(python_version_ok((3, 9, 18)))

    def test_unsupported_python_message(self):
        message = unsupported_python_message(context="pyquda-agent")
        self.assertIn("Python >= 3.10", message)
        self.assertIn("pyquda-agent", message)
        self.assertIn("virtualenv/conda/pyenv Python path", message)
        self.assertIn("do not assume bare `python3` is new enough", message)


if __name__ == "__main__":
    unittest.main()
