import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pyquda_agent.config import parse_api_model
from pyquda_agent.config import RunConfig
from pyquda_agent.config import resolve_api_model
from pyquda_agent.config import resolve_base_url


class ConfigTests(unittest.TestCase):
    def test_parse_api_model_accepts_plain_model_name(self):
        provider, model_name = parse_api_model("gpt-5-mini")
        self.assertEqual(provider, "openai")
        self.assertEqual(model_name, "gpt-5-mini")

    def test_resolve_api_model_uses_provider_specific_env(self):
        with patch.dict(os.environ, {"DEEPSEEK_MODEL": "deepseek-chat"}, clear=False):
            self.assertEqual(resolve_api_model(None), "deepseek/deepseek-chat")

    def test_resolve_api_model_falls_back_to_provider_default_when_only_key_exists(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "secret"}, clear=True):
            self.assertEqual(resolve_api_model(None), "deepseek/deepseek-chat")

    def test_resolve_api_model_falls_back_to_openai_default_when_only_openai_key_exists(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}, clear=True):
            self.assertEqual(resolve_api_model(None), "openai/gpt-5-mini")

    def test_resolve_base_url_uses_provider_default(self):
        self.assertEqual(resolve_base_url("deepseek", None), "https://api.deepseek.com/v1")

    def test_run_config_defaults_cover_runtime_probe_flags(self):
        config = RunConfig(
            task_description="test",
            backend="codex",
            model=None,
            api_key_file=Path("api.key"),
            base_url=None,
            pyquda_repo=Path("/tmp/PyQUDA"),
            output=Path("/tmp/out.py"),
            output_explicit=False,
            interactive=False,
            max_questions=0,
            save_session=None,
            resume_session=None,
            print_context=False,
            dry_run=True,
            verbose=False,
        )
        self.assertEqual(config.result_format, "full")
        self.assertEqual(config.llm_timeout, 30.0)
        self.assertFalse(config.runtime_probe)
        self.assertEqual(config.probe_timeout, 30.0)
        self.assertFalse(config.probe_use_repo_pythonpath)
        self.assertFalse(config.output_explicit)


if __name__ == "__main__":
    unittest.main()
