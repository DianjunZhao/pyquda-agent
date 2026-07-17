"""Codex backend wrapper."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .base import BackendInvocationError
from .base import LLMBackend


class CodexBackend(LLMBackend):
    """Call the local codex CLI when available."""

    def __init__(self, executable: str = "codex", timeout_seconds: float = 30.0) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "codex"

    def _build_exec_env(self, *, home_root: str | None, code_home: Path | None) -> dict[str, str]:
        env = dict(os.environ)
        env["OTEL_SDK_DISABLED"] = "true"
        if home_root:
            env["HOME"] = home_root
        if code_home:
            env["CODEX_HOME"] = str(code_home)
        return env

    def _run_exec(self, *, prompt: str, timeout_seconds: float, output_schema_path: Path | None) -> subprocess.CompletedProcess[str]:
        command = [
            self.executable,
            "exec",
            prompt,
            "-c",
            "model_reasoning_effort=\"low\"",
            "-c",
            "model_reasoning_summary=\"none\"",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "--ephemeral",
            "-C",
            str(Path.cwd()),
        ]
        if output_schema_path is not None:
            command.extend(["--output-schema", str(output_schema_path)])
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=self._build_exec_env(
                home_root=os.environ.get("HOME", ""),
                code_home=Path(os.environ["CODEX_HOME"]) if os.environ.get("CODEX_HOME") else None,
            ),
            timeout=timeout_seconds,
        )

    def _classify_failure(self, stderr: str, returncode: int) -> tuple[str, str, str | None]:
        lowered = stderr.lower()
        if any(token in lowered for token in ("failed to lookup address information", "temporary failure in name resolution", "name resolution")):
            return (
                "network_error",
                "Codex backend could start locally but could not reach the upstream service from the current environment.",
                "dns_resolution_failure",
            )
        if any(token in lowered for token in ("error sending request for url", "connection refused")):
            return (
                "network_error",
                "Codex backend could start locally but could not reach the upstream service from the current environment.",
                "connection_refused",
            )
        if any(
            token in lowered
            for token in (
                "not logged in",
                "authentication",
                "unauthorized",
                "forbidden",
                "api key",
                "login required",
            )
        ):
            return (
                "authentication_error",
                "Codex backend is installed locally but authentication is not ready in the current environment.",
                "codex_login_required",
            )
        if any(token in lowered for token in ("429", "rate limit", "too many requests")):
            return (
                "rate_limited",
                "Codex backend reached an upstream rate limit.",
                "provider_rate_limited",
            )
        if any(token in lowered for token in ("503", "502", "504", "upstream service", "service unavailable")):
            return (
                "upstream_service_error",
                "Codex backend reached the upstream service, but the service was unavailable.",
                "service_unavailable",
            )
        if "failed to initialize in-process app-server client" in lowered:
            return (
                "local_environment_error",
                "Codex backend failed during local app-client initialization in the current environment.",
                "codex_app_client_init_failed",
            )
        if any(token in lowered for token in ("permission denied", "operation not permitted")):
            return (
                "local_environment_error",
                "Codex backend could not execute correctly because local permissions blocked the CLI runtime.",
                "local_permission_error",
            )
        return (
            "backend_process_error",
            f"Codex backend exited with status {returncode}: {stderr or 'no stderr'}",
            "unexpected_process_exit",
        )

    def preflight(self, *, timeout_seconds: float) -> None:
        if shutil.which(self.executable) is None:  # pragma: no cover - environment dependent
            raise BackendInvocationError(
                "Codex backend requested but no local `codex` executable is available.",
                category="local_executable_missing",
            )
        try:
            result = self._run_exec(
                prompt="Reply with exactly: OK",
                timeout_seconds=timeout_seconds,
                output_schema_path=None,
            )
        except subprocess.TimeoutExpired as exc:
            raise BackendInvocationError(
                f"Codex auto-preflight timed out after {timeout_seconds:g} seconds.",
                category="timeout",
            ) from exc
        if result.returncode != 0:
            stderr = result.stderr.strip()
            category, message, detail_category = self._classify_failure(stderr, result.returncode)
            raise BackendInvocationError(message, category=category, detail_category=detail_category)

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        if shutil.which(self.executable) is None:  # pragma: no cover - environment dependent
            raise RuntimeError("backend='codex' requires a local `codex` executable.")
        prompt = f"{system_prompt}\n\n{user_prompt}"
        try:
            result = self._run_exec(
                prompt=prompt,
                timeout_seconds=self.timeout_seconds,
                output_schema_path=None,
            )
        except subprocess.TimeoutExpired as exc:
            raise BackendInvocationError(
                f"Codex backend timed out after {self.timeout_seconds:g} seconds.",
                category="timeout",
            ) from exc
        if result.returncode != 0:
            stderr = result.stderr.strip()
            category, message, detail_category = self._classify_failure(stderr, result.returncode)
            raise BackendInvocationError(message, category=category, detail_category=detail_category)
        if not result.stdout.strip():
            raise BackendInvocationError(
                "Codex backend returned an empty response.",
                category="empty_response",
            )
        return result.stdout.strip()
