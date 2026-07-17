import unittest
from subprocess import TimeoutExpired
import os
from unittest.mock import patch

from pyquda_agent.backends.base import BackendInvocationError
from pyquda_agent.backends.codex import CodexBackend


class _Completed:
    def __init__(self, *, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class CodexBackendTests(unittest.TestCase):
    def _backend(self) -> CodexBackend:
        return CodexBackend(executable="codex", timeout_seconds=1.0)

    def test_codex_backend_classifies_network_error(self):
        backend = self._backend()
        completed = _Completed(returncode=1, stderr="Error sending request for url: connection refused")
        with patch("pyquda_agent.backends.codex.shutil.which", return_value="/usr/bin/codex"):
            with patch("pyquda_agent.backends.codex.subprocess.run", return_value=completed):
                with self.assertRaises(BackendInvocationError) as ctx:
                    backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "network_error")
        self.assertEqual(ctx.exception.detail_category, "connection_refused")

    def test_codex_backend_classifies_rate_limited(self):
        backend = self._backend()
        completed = _Completed(returncode=1, stderr="429 Too Many Requests")
        with patch("pyquda_agent.backends.codex.shutil.which", return_value="/usr/bin/codex"):
            with patch("pyquda_agent.backends.codex.subprocess.run", return_value=completed):
                with self.assertRaises(BackendInvocationError) as ctx:
                    backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "rate_limited")

    def test_codex_backend_classifies_upstream_service_error(self):
        backend = self._backend()
        completed = _Completed(returncode=1, stderr="503 Service Unavailable")
        with patch("pyquda_agent.backends.codex.shutil.which", return_value="/usr/bin/codex"):
            with patch("pyquda_agent.backends.codex.subprocess.run", return_value=completed):
                with self.assertRaises(BackendInvocationError) as ctx:
                    backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "upstream_service_error")

    def test_codex_backend_classifies_local_environment_error(self):
        backend = self._backend()
        completed = _Completed(returncode=1, stderr="failed to initialize in-process app-server client")
        with patch("pyquda_agent.backends.codex.shutil.which", return_value="/usr/bin/codex"):
            with patch("pyquda_agent.backends.codex.subprocess.run", return_value=completed):
                with self.assertRaises(BackendInvocationError) as ctx:
                    backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "local_environment_error")
        self.assertEqual(ctx.exception.detail_category, "codex_app_client_init_failed")

    def test_codex_backend_classifies_backend_process_error(self):
        backend = self._backend()
        completed = _Completed(returncode=7, stderr="some unexpected stderr")
        with patch("pyquda_agent.backends.codex.shutil.which", return_value="/usr/bin/codex"):
            with patch("pyquda_agent.backends.codex.subprocess.run", return_value=completed):
                with self.assertRaises(BackendInvocationError) as ctx:
                    backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "backend_process_error")

    def test_codex_backend_classifies_empty_response(self):
        backend = self._backend()
        completed = _Completed(returncode=0, stdout="   ")
        with patch("pyquda_agent.backends.codex.shutil.which", return_value="/usr/bin/codex"):
            with patch("pyquda_agent.backends.codex.subprocess.run", return_value=completed):
                with self.assertRaises(BackendInvocationError) as ctx:
                    backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "empty_response")

    def test_codex_backend_preflight_classifies_timeout(self):
        backend = self._backend()
        with patch("pyquda_agent.backends.codex.shutil.which", return_value="/usr/bin/codex"):
            with patch("pyquda_agent.backends.codex.subprocess.run", side_effect=TimeoutExpired(cmd=["codex"], timeout=1)):
                with self.assertRaises(BackendInvocationError) as ctx:
                    backend.preflight(timeout_seconds=1.0)
        self.assertEqual(ctx.exception.category, "timeout")
        self.assertEqual(ctx.exception.detail_category, "codex_preflight_timeout")

    def test_codex_backend_generate_text_timeout_has_detail_category(self):
        backend = self._backend()
        with patch("pyquda_agent.backends.codex.shutil.which", return_value="/usr/bin/codex"):
            with patch("pyquda_agent.backends.codex.subprocess.run", side_effect=TimeoutExpired(cmd=["codex"], timeout=1)):
                with self.assertRaises(BackendInvocationError) as ctx:
                    backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "timeout")
        self.assertEqual(ctx.exception.detail_category, "codex_backend_timeout")

    def test_codex_backend_generate_text_does_not_pass_output_schema(self):
        backend = self._backend()
        completed = _Completed(returncode=0, stdout='{"ok": true}')
        with patch("pyquda_agent.backends.codex.shutil.which", return_value="/usr/bin/codex"):
            with patch("pyquda_agent.backends.codex.subprocess.run", return_value=completed) as run:
                result = backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(result, '{"ok": true}')
        command = run.call_args.kwargs.get("args") or run.call_args.args[0]
        self.assertNotIn("--output-schema", command)
        self.assertIn("model_reasoning_effort=\"low\"", command)
        self.assertIn("model_reasoning_summary=\"none\"", command)

    def test_codex_backend_preserves_user_home_and_codex_home(self):
        backend = self._backend()
        with patch.dict(os.environ, {"HOME": "/tmp/home-user", "CODEX_HOME": "/tmp/codex-home"}, clear=False):
            env = backend._build_exec_env(home_root=os.environ.get("HOME"), code_home=None if not os.environ.get("CODEX_HOME") else None)
        self.assertEqual(env["HOME"], "/tmp/home-user")
        self.assertEqual(env["CODEX_HOME"], "/tmp/codex-home")
        self.assertEqual(env["OTEL_SDK_DISABLED"], "true")


if __name__ == "__main__":
    unittest.main()
