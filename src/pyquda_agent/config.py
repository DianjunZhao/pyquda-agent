"""CLI configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PYQUDA_REPO = Path.home() / "PyQUDA"
DEFAULT_INDEX_PATH = DEFAULT_WORKSPACE_ROOT / "data" / "pyquda_index.json"
DEFAULT_OUTPUT_PATH = DEFAULT_WORKSPACE_ROOT / "outputs" / "pion_2pt.py"
DEFAULT_API_KEY_FILE = DEFAULT_WORKSPACE_ROOT / "api.key"

API_KEY_ENVS = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
}
API_BASE_URL_ENVS = {
    "deepseek": "DEEPSEEK_BASE_URL",
    "openai": "OPENAI_BASE_URL",
}
DEFAULT_PROVIDER_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
}
DEFAULT_PROVIDER_MODELS = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-5-mini",
}
COMBINED_API_MODEL_ENVS = ("PYQUDA_AGENT_API_MODEL",)
PROVIDER_MODEL_ENVS = {
    "deepseek": "DEEPSEEK_MODEL",
    "openai": "OPENAI_MODEL",
}


def parse_api_model(model_spec: str) -> tuple[str, str]:
    if "/" not in model_spec:
        model_name = model_spec.strip()
        if not model_name:
            raise ValueError("--model must have the form provider/model_id or a non-empty model id.")
        return "openai", model_name
    provider, model_name = model_spec.split("/", 1)
    provider = provider.strip().lower()
    model_name = model_name.strip()
    if not provider or not model_name:
        raise ValueError("--model must have the form provider/model_id or a non-empty model id.")
    return provider, model_name


def resolve_api_key(provider: str, api_key_file: Path) -> str | None:
    if api_key_file.exists():
        value = api_key_file.read_text(encoding="utf-8").strip()
        if value:
            return value
    env_name = API_KEY_ENVS.get(provider, "OPENAI_API_KEY")
    return os.environ.get(env_name)


def resolve_api_model(model_spec: str | None) -> str | None:
    if model_spec:
        value = model_spec.strip()
        return value or None
    for env_name in COMBINED_API_MODEL_ENVS:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    for provider, env_name in PROVIDER_MODEL_ENVS.items():
        value = os.environ.get(env_name, "").strip()
        if not value:
            continue
        if "/" in value:
            return value
        return f"{provider}/{value}"
    for provider, env_name in API_KEY_ENVS.items():
        if os.environ.get(env_name, "").strip():
            default_model = DEFAULT_PROVIDER_MODELS.get(provider)
            if default_model:
                return f"{provider}/{default_model}"
    return None


def resolve_base_url(provider: str, base_url: str | None) -> str | None:
    if base_url:
        value = base_url.strip()
        return value or None
    env_name = API_BASE_URL_ENVS.get(provider)
    if env_name:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return DEFAULT_PROVIDER_BASE_URLS.get(provider)


@dataclass
class RunConfig:
    task_description: str
    backend: str
    model: str | None
    api_key_file: Path
    base_url: str | None
    pyquda_repo: Path
    output: Path
    output_explicit: bool
    interactive: bool
    max_questions: int
    save_session: Path | None
    resume_session: Path | None
    print_context: bool
    dry_run: bool
    verbose: bool
    result_format: str = "full"
    set_fields: list[str] | None = None
    reply_answers: list[str] | None = None
    enable_external_lookup: bool = False
    llm_timeout: float = 30.0
    runtime_probe: bool = False
    probe_timeout: float = 30.0
    probe_use_repo_pythonpath: bool = False
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT

    @property
    def effective_model(self) -> str | None:
        if self.backend == "codex":
            return None
        return resolve_api_model(self.model)

    @property
    def provider(self) -> str | None:
        model_spec = self.effective_model
        if self.backend == "codex" or not model_spec:
            return None
        provider, _ = parse_api_model(model_spec)
        return provider

    @property
    def model_name(self) -> str | None:
        model_spec = self.effective_model
        if self.backend == "codex" or not model_spec:
            return None
        _, model_name = parse_api_model(model_spec)
        return model_name
