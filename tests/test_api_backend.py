import io
import socket
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.error import URLError
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pyquda_agent.backends.api import OpenAICompatibleBackend
from pyquda_agent.backends.base import BackendInvocationError


class _Response:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class ApiBackendTests(unittest.TestCase):
    def _backend(self) -> OpenAICompatibleBackend:
        return OpenAICompatibleBackend(
            provider="openai",
            model_name="gpt-5-mini",
            api_key="secret",
            base_url="https://api.openai.com/v1",
            timeout_seconds=5.0,
        )

    def test_api_backend_returns_stripped_content(self):
        backend = self._backend()
        with patch(
            "pyquda_agent.backends.api.request.urlopen",
            return_value=_Response('{"choices":[{"message":{"content":"  hello  "}}]}'),
        ):
            text = backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(text, "hello")

    def test_api_backend_classifies_endpoint_not_found(self):
        backend = self._backend()
        error = HTTPError("https://api.openai.com/v1/chat/completions", 404, "Not Found", hdrs=None, fp=io.BytesIO(b""))
        with patch("pyquda_agent.backends.api.request.urlopen", side_effect=error):
            with self.assertRaises(BackendInvocationError) as ctx:
                backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "endpoint_not_found")
        self.assertEqual(ctx.exception.detail_category, "chat_completions_endpoint_not_found")

    def test_api_backend_classifies_request_error(self):
        backend = self._backend()
        error = HTTPError("https://api.openai.com/v1/chat/completions", 400, "Bad Request", hdrs=None, fp=io.BytesIO(b""))
        with patch("pyquda_agent.backends.api.request.urlopen", side_effect=error):
            with self.assertRaises(BackendInvocationError) as ctx:
                backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "request_error")

    def test_api_backend_classifies_network_error(self):
        backend = self._backend()
        with patch(
            "pyquda_agent.backends.api.request.urlopen",
            side_effect=URLError("temporary failure in name resolution"),
        ):
            with self.assertRaises(BackendInvocationError) as ctx:
                backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "network_error")
        self.assertEqual(ctx.exception.detail_category, "dns_resolution_failure")

    def test_api_backend_classifies_timeout(self):
        backend = self._backend()
        with patch(
            "pyquda_agent.backends.api.request.urlopen",
            side_effect=URLError(socket.timeout("timed out")),
        ):
            with self.assertRaises(BackendInvocationError) as ctx:
                backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "timeout")

    def test_api_backend_classifies_response_parse_error(self):
        backend = self._backend()
        with patch(
            "pyquda_agent.backends.api.request.urlopen",
            return_value=_Response('{"choices":[{"message":{}}]}'),
        ):
            with self.assertRaises(BackendInvocationError) as ctx:
                backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "response_parse_error")
        self.assertEqual(ctx.exception.detail_category, "chat_completions_schema_mismatch")

    def test_api_backend_classifies_empty_response(self):
        backend = self._backend()
        with patch(
            "pyquda_agent.backends.api.request.urlopen",
            return_value=_Response('{"choices":[{"message":{"content":"   "}}]}'),
        ):
            with self.assertRaises(BackendInvocationError) as ctx:
                backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "empty_response")
        self.assertEqual(ctx.exception.detail_category, "empty_message_content")


if __name__ == "__main__":
    unittest.main()
