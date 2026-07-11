"""Codex backend wrapper."""

from __future__ import annotations

import shutil
import subprocess

from .base import LLMBackend


class CodexBackend(LLMBackend):
    """Call the local codex CLI when available."""

    def __init__(self, executable: str = "codex") -> None:
        self.executable = executable

    @property
    def name(self) -> str:
        return "codex"

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        if shutil.which(self.executable) is None:  # pragma: no cover - environment dependent
            raise RuntimeError("backend='codex' requires a local `codex` executable.")
        prompt = f"{system_prompt}\n\n{user_prompt}"
        result = subprocess.run(
            [self.executable, "exec", prompt, "--skip-git-repo-check"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
