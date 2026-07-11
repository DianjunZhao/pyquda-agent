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


def parse_api_model(model_spec: str) -> tuple[str, str]:
    if "/" not in model_spec:
        raise ValueError("--model must have the form provider/model_id.")
    provider, model_name = model_spec.split("/", 1)
    provider = provider.strip().lower()
    model_name = model_name.strip()
    if not provider or not model_name:
        raise ValueError("--model must have the form provider/model_id.")
    return provider, model_name


def resolve_api_key(provider: str, api_key_file: Path) -> str | None:
    if api_key_file.exists():
        value = api_key_file.read_text(encoding="utf-8").strip()
        if value:
            return value
    env_name = API_KEY_ENVS.get(provider, "OPENAI_API_KEY")
    return os.environ.get(env_name)


@dataclass
class RunConfig:
    task_description: str
    backend: str
    model: str | None
    api_key_file: Path
    base_url: str | None
    pyquda_repo: Path
    output: Path
    interactive: bool
    max_questions: int
    save_session: Path | None
    resume_session: Path | None
    print_context: bool
    dry_run: bool
    verbose: bool
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT

    @property
    def provider(self) -> str | None:
        if self.backend != "api" or not self.model:
            return None
        provider, _ = parse_api_model(self.model)
        return provider

    @property
    def model_name(self) -> str | None:
        if self.backend != "api" or not self.model:
            return None
        _, model_name = parse_api_model(self.model)
        return model_name
