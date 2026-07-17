import os
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import TimeoutExpired
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pyquda_agent.backends.base import BackendInvocationError
from pyquda_agent.backends.codex import CodexBackend
from pyquda_agent.backends.factory import build_llm_backend
from pyquda_agent.config import RunConfig


class BackendFactoryTests(unittest.TestCase):
    def test_auto_backend_prefers_codex_when_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="test",
                backend="auto",
                model="openai/gpt-5-mini",
                api_key_file=Path(tmpdir) / "api.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            with patch("pyquda_agent.backends.factory._discover_codex_executable", return_value="/opt/homebrew/bin/codex"):
                with patch("pyquda_agent.backends.codex.CodexBackend.preflight", return_value=None):
                    backend, status = build_llm_backend(config)
        self.assertIsNotNone(backend)
        self.assertEqual(status["requested_backend"], "auto")
        self.assertEqual(status["selected_backend"], "codex")
        self.assertTrue(status["codex_preflight_attempted"])
        self.assertEqual(status["codex_preflight_status"], "ok")

    def test_auto_backend_falls_back_to_api_when_codex_preflight_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="test",
                backend="auto",
                model="deepseek/deepseek-chat",
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            with patch("pyquda_agent.backends.factory._discover_codex_executable", return_value="/opt/homebrew/bin/codex"):
                with patch(
                    "pyquda_agent.backends.codex.CodexBackend.preflight",
                    side_effect=BackendInvocationError("mock preflight failure", category="authentication_error"),
                ):
                    with patch("pyquda_agent.backends.factory.resolve_api_key", return_value="secret"):
                        backend, status = build_llm_backend(config)
        self.assertIsNotNone(backend)
        self.assertEqual(status["requested_backend"], "auto")
        self.assertEqual(status["selected_backend"], "api")
        self.assertTrue(status["codex_preflight_attempted"])
        self.assertEqual(status["codex_preflight_status"], "failed")
        self.assertEqual(status["codex_preflight_category"], "authentication_error")

    def test_auto_backend_falls_back_to_api_when_codex_is_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="test",
                backend="auto",
                model="deepseek/deepseek-chat",
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            with patch("pyquda_agent.backends.factory._discover_codex_executable", return_value=None):
                with patch("pyquda_agent.backends.factory.resolve_api_key", return_value="secret"):
                    backend, status = build_llm_backend(config)
        self.assertIsNotNone(backend)
        self.assertEqual(status["requested_backend"], "auto")
        self.assertEqual(status["selected_backend"], "api")

    def test_auto_backend_reuses_session_backend_memory_to_prefer_api(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="test",
                backend="auto",
                model="openai/gpt-5-mini",
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            prior_backend_assistance = {
                "selected_backend": "codex",
                "fallback": True,
                "fallback_category": "timeout",
                "fallback_reason": "Initial LLM attempt timed out.",
            }
            with patch("pyquda_agent.backends.factory.resolve_api_key", return_value="secret"):
                with patch(
                    "pyquda_agent.backends.codex.CodexBackend.preflight",
                    side_effect=AssertionError("codex preflight should be skipped"),
                ):
                    backend, status = build_llm_backend(config, prior_backend_assistance=prior_backend_assistance)
        self.assertIsNotNone(backend)
        self.assertEqual(status["requested_backend"], "auto")
        self.assertEqual(status["selected_backend"], "api")
        self.assertTrue(status["session_backend_memory_considered"])
        self.assertTrue(status["session_backend_memory_used"])
        self.assertEqual(status["session_backend_prior_category"], "timeout")
        self.assertIn("resumed session", status["selection_reason"])

    def test_auto_backend_reuses_session_backend_memory_after_explicit_codex_failed_to_rules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="test",
                backend="auto",
                model="openai/gpt-5-mini",
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            prior_backend_assistance = {
                "requested_backend": "codex",
                "selected_backend": "rules",
                "fallback": True,
                "fallback_category": "authentication_error",
                "fallback_reason": "Explicit codex backend failed preflight because local authentication was unavailable.",
            }
            with patch("pyquda_agent.backends.factory.resolve_api_key", return_value="secret"):
                with patch(
                    "pyquda_agent.backends.codex.CodexBackend.preflight",
                    side_effect=AssertionError("codex preflight should be skipped"),
                ):
                    backend, status = build_llm_backend(config, prior_backend_assistance=prior_backend_assistance)
        self.assertIsNotNone(backend)
        self.assertEqual(status["requested_backend"], "auto")
        self.assertEqual(status["selected_backend"], "api")
        self.assertTrue(status["session_backend_memory_considered"])
        self.assertTrue(status["session_backend_memory_used"])
        self.assertEqual(status["session_backend_prior_category"], "authentication_error")
        self.assertEqual(status["session_backend_prior_selected_backend"], "rules")
        self.assertIn("codex-targeting attempt", status["selection_reason"])

    def test_auto_backend_records_session_backend_memory_even_if_api_retry_is_unusable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="test",
                backend="auto",
                model="openai/gpt-5-mini",
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            prior_backend_assistance = {
                "selected_backend": "codex",
                "fallback": True,
                "fallback_category": "timeout",
                "fallback_reason": "Initial LLM attempt timed out.",
            }
            with patch("pyquda_agent.backends.factory._discover_codex_executable", return_value=None):
                backend, status = build_llm_backend(config, prior_backend_assistance=prior_backend_assistance)
        self.assertIsNone(backend)
        self.assertEqual(status["selected_backend"], "rules")
        self.assertTrue(status["session_backend_memory_considered"])
        self.assertFalse(status["session_backend_memory_used"])
        self.assertEqual(status["session_backend_prior_category"], "timeout")
        self.assertIn("configured API backend was not usable", status["session_backend_memory_reason"])

    def test_auto_backend_can_transparently_fallback_to_rules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="test",
                backend="auto",
                model=None,
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            with patch.dict(os.environ, {}, clear=True):
                with patch("pyquda_agent.backends.factory._discover_codex_executable", return_value="/opt/homebrew/bin/codex"):
                    with patch(
                        "pyquda_agent.backends.codex.CodexBackend.preflight",
                        side_effect=BackendInvocationError("mock timeout", category="timeout"),
                    ):
                        backend, status = build_llm_backend(config)
        self.assertIsNotNone(backend)
        self.assertFalse(status["fallback"])
        self.assertEqual(status["requested_backend"], "auto")
        self.assertEqual(status["selected_backend"], "codex")
        self.assertEqual(status["codex_preflight_status"], "failed")
        self.assertTrue(status["codex_preflight_soft_failed"])
        self.assertEqual(status["codex_preflight_soft_failure_reason"], "mock timeout")

    def test_explicit_codex_backend_falls_back_to_rules_after_short_preflight_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="test",
                backend="codex",
                model=None,
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            with patch("pyquda_agent.backends.factory._discover_codex_executable", return_value="/opt/homebrew/bin/codex"):
                with patch(
                    "pyquda_agent.backends.codex.CodexBackend.preflight",
                    side_effect=BackendInvocationError("mock timeout", category="timeout"),
                ):
                    backend, status = build_llm_backend(config)
        self.assertIsNotNone(backend)
        self.assertEqual(status["requested_backend"], "codex")
        self.assertEqual(status["selected_backend"], "codex")
        self.assertFalse(status["fallback"])
        self.assertTrue(status["codex_preflight_attempted"])
        self.assertEqual(status["codex_preflight_status"], "failed")
        self.assertTrue(status["codex_preflight_soft_failed"])
        self.assertEqual(status["codex_preflight_soft_failure_reason"], "mock timeout")

    def test_explicit_codex_backend_can_skip_preflight_for_normalization_only_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="write a simple PyQUDA script for pi meson two-point",
                backend="codex",
                model=None,
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            with patch("pyquda_agent.backends.factory._discover_codex_executable", return_value="/opt/homebrew/bin/codex"):
                with patch(
                    "pyquda_agent.backends.codex.CodexBackend.preflight",
                    side_effect=AssertionError("codex preflight should be skipped"),
                ):
                    backend, status = build_llm_backend(
                        config,
                        request_profile_hint={
                            "codex_preflight_policy": "skip",
                            "codex_preflight_skip_reason": "mock skip reason",
                        },
                    )
        self.assertIsNotNone(backend)
        self.assertEqual(status["requested_backend"], "codex")
        self.assertEqual(status["selected_backend"], "codex")
        self.assertFalse(status["codex_preflight_attempted"])
        self.assertTrue(status["codex_preflight_skipped"])
        self.assertEqual(status["codex_preflight_status"], "skipped")
        self.assertEqual(status["codex_preflight_skip_reason"], "mock skip reason")

    def test_backend_can_be_intentionally_skipped_for_explicit_direct_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description=(
                    "please compute the pion two-point correlator from gauge /tmp/weak_field.lime "
                    "lattice size 4 4 4 8 grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 "
                    "coeff_t=0.8549165664 coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed "
                    "source timeslice 0 outputs/pion.npy outputs/pion.py resource_path=.cache/quda cluster_launch=local"
                ),
                backend="codex",
                model=None,
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            backend, status = build_llm_backend(
                config,
                request_profile_hint={
                    "backend_policy": "skip",
                    "backend_skip_reason": "mock explicit direct request skip",
                },
            )
        self.assertIsNone(backend)
        self.assertEqual(status["requested_backend"], "codex")
        self.assertEqual(status["selected_backend"], "rules")
        self.assertFalse(status["fallback"])
        self.assertEqual(status["selection_reason"], "mock explicit direct request skip")

    def test_auto_backend_can_skip_codex_preflight_for_normalization_only_profile_without_api_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="write a simple PyQUDA script for pi meson two-point",
                backend="auto",
                model=None,
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            with patch.dict(os.environ, {}, clear=True):
                with patch("pyquda_agent.backends.factory._discover_codex_executable", return_value="/opt/homebrew/bin/codex"):
                    with patch(
                        "pyquda_agent.backends.codex.CodexBackend.preflight",
                        side_effect=AssertionError("codex preflight should be skipped"),
                    ):
                        backend, status = build_llm_backend(
                            config,
                            request_profile_hint={
                                "auto_codex_preflight_policy": "skip",
                                "auto_codex_preflight_skip_reason": "mock auto skip reason",
                            },
                        )
        self.assertIsNotNone(backend)
        self.assertEqual(status["requested_backend"], "auto")
        self.assertEqual(status["selected_backend"], "codex")
        self.assertFalse(status["codex_preflight_attempted"])
        self.assertTrue(status["codex_preflight_skipped"])
        self.assertEqual(status["codex_preflight_status"], "skipped")
        self.assertEqual(status["codex_preflight_skip_reason"], "mock auto skip reason")

    def test_auto_backend_does_not_skip_codex_preflight_when_api_fallback_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="write a simple PyQUDA script for pi meson two-point",
                backend="auto",
                model="openai/gpt-5-mini",
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            with patch("pyquda_agent.backends.factory._discover_codex_executable", return_value="/opt/homebrew/bin/codex"):
                with patch("pyquda_agent.backends.codex.CodexBackend.preflight", return_value=None) as preflight:
                    backend, status = build_llm_backend(
                        config,
                        request_profile_hint={
                            "auto_codex_preflight_policy": "skip",
                            "auto_codex_preflight_skip_reason": "mock auto skip reason",
                        },
                    )
        self.assertIsNotNone(backend)
        self.assertEqual(status["requested_backend"], "auto")
        self.assertEqual(status["selected_backend"], "codex")
        self.assertTrue(status["codex_preflight_attempted"])
        self.assertFalse(status["codex_preflight_skipped"])
        self.assertEqual(status["codex_preflight_status"], "ok")
        preflight.assert_called_once()

    def test_api_backend_resolves_deepseek_base_url(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="test",
                backend="api",
                model="deepseek/deepseek-chat",
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            with patch("pyquda_agent.backends.factory.resolve_api_key", return_value="secret"):
                backend, status = build_llm_backend(config)
        self.assertIsNotNone(backend)
        assert backend is not None
        self.assertEqual(backend.name, "api:deepseek/deepseek-chat")
        self.assertEqual(getattr(backend, "base_url"), "https://api.deepseek.com/v1")
        self.assertEqual(getattr(backend, "timeout_seconds"), 30.0)
        self.assertTrue(status["configured"])
        self.assertEqual(status["resolved_base_url"], "https://api.deepseek.com/v1")

    def test_codex_backend_uses_homebrew_fallback_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="test",
                backend="codex",
                model=None,
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
            )
            with patch("pyquda_agent.backends.factory.shutil.which", side_effect=lambda candidate: "/opt/homebrew/bin/codex" if candidate == "/opt/homebrew/bin/codex" else None):
                with patch("pyquda_agent.backends.codex.CodexBackend.preflight", return_value=None):
                    backend, status = build_llm_backend(config)
        self.assertIsNotNone(backend)
        self.assertTrue(status["configured"])
        self.assertEqual(status["backend_executable"], "/opt/homebrew/bin/codex")
        assert backend is not None
        self.assertEqual(getattr(backend, "timeout_seconds"), 30.0)

    def test_backend_factory_passes_configured_llm_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RunConfig(
                task_description="test",
                backend="codex",
                model=None,
                api_key_file=Path(tmpdir) / "missing.key",
                base_url=None,
                pyquda_repo=Path(tmpdir) / "PyQUDA",
                output=Path(tmpdir) / "out.py",
                output_explicit=False,
                interactive=False,
                max_questions=0,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
                llm_timeout=9.0,
            )
            with patch("pyquda_agent.backends.factory._discover_codex_executable", return_value="/opt/homebrew/bin/codex"):
                with patch("pyquda_agent.backends.codex.CodexBackend.preflight", return_value=None):
                    backend, status = build_llm_backend(config)
        self.assertTrue(status["configured"])
        assert backend is not None
        self.assertEqual(getattr(backend, "timeout_seconds"), 9.0)

    def test_codex_backend_timeout_is_classified(self):
        backend = CodexBackend(executable="codex", timeout_seconds=1)
        with patch("pyquda_agent.backends.codex.shutil.which", return_value="/usr/bin/codex"):
            with patch("pyquda_agent.backends.codex.subprocess.run", side_effect=TimeoutExpired(cmd=["codex"], timeout=1)):
                with self.assertRaises(BackendInvocationError) as ctx:
                    backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "timeout")

    def test_codex_backend_authentication_failure_is_classified(self):
        class Completed:
            returncode = 1
            stdout = ""
            stderr = "Authentication failed: login required"

        backend = CodexBackend(executable="codex", timeout_seconds=1)
        with patch("pyquda_agent.backends.codex.shutil.which", return_value="/usr/bin/codex"):
            with patch("pyquda_agent.backends.codex.subprocess.run", return_value=Completed()):
                with self.assertRaises(BackendInvocationError) as ctx:
                    backend.generate_text(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.category, "authentication_error")


if __name__ == "__main__":
    unittest.main()
