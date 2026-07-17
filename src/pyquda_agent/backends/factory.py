"""Backend construction helpers for optional LLM-assisted intent work."""

from __future__ import annotations

import shutil
from pathlib import Path

from pyquda_agent.config import RunConfig
from pyquda_agent.config import resolve_api_key
from pyquda_agent.config import resolve_base_url

from .api import OpenAICompatibleBackend
from .base import BackendInvocationError
from .base import LLMBackend
from .codex import CodexBackend


CODEX_CANDIDATES = (
    "codex",
    "/opt/homebrew/bin/codex",
    "/usr/local/bin/codex",
)
AUTO_CODEX_PREFLIGHT_TIMEOUT_SECONDS = 3.0
# Explicit codex still keeps the real backend call alive after a timeout preflight,
# so keep this probe short to avoid paying a large fixed latency tax up front.
EXPLICIT_CODEX_PREFLIGHT_TIMEOUT_SECONDS = 2.0
SESSION_MEMORY_API_PREFER_CATEGORIES = {
    "authentication_error",
    "backend_process_error",
    "local_environment_error",
    "local_executable_missing",
    "timeout",
}


def _discover_codex_executable() -> str | None:
    for candidate in CODEX_CANDIDATES:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        path = Path(candidate)
        if path.is_file() and path.exists():
            return str(path)
    return None


def _build_api_backend(config: RunConfig, status: dict) -> tuple[LLMBackend | None, dict]:
    if not config.effective_model:
        status["fallback"] = True
        status["fallback_category"] = "configuration_missing"
        status["fallback_reason"] = (
            "API backend requested but no model was configured via --model or PYQUDA_AGENT_API_MODEL/OPENAI_MODEL."
        )
        return None, status
    try:
        provider = config.provider
        model_name = config.model_name
    except ValueError as exc:
        status["fallback"] = True
        status["fallback_category"] = "configuration_invalid"
        status["fallback_reason"] = f"API backend configuration is invalid: {exc}"
        return None, status
    assert provider is not None
    assert model_name is not None
    api_key = resolve_api_key(provider, config.api_key_file)
    if not api_key:
        status["fallback"] = True
        status["fallback_category"] = "credentials_missing"
        status["fallback_reason"] = f"API backend requested for {provider}/{model_name}, but no API key was configured."
        return None, status
    base_url = resolve_base_url(provider, config.base_url)
    if not base_url:
        status["fallback"] = True
        status["fallback_category"] = "configuration_missing"
        status["fallback_reason"] = (
            f"API backend requested for provider {provider!r}, but no base URL is configured. Pass --base-url explicitly."
        )
        return None, status
    backend = OpenAICompatibleBackend(
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=config.llm_timeout,
    )
    status["configured"] = True
    status["backend_name"] = backend.name
    status["resolved_base_url"] = backend.base_url
    return backend, status


def _build_codex_backend(config: RunConfig, status: dict, *, executable: str | None = None) -> tuple[LLMBackend | None, dict]:
    resolved_executable = executable or _discover_codex_executable()
    status["backend_executable"] = resolved_executable
    if resolved_executable is None:
        status["fallback"] = True
        status["fallback_category"] = "local_executable_missing"
        status["fallback_reason"] = (
            "Codex backend requested but no local `codex` executable was found on PATH or in the standard Homebrew locations."
        )
        return None, status
    backend = CodexBackend(executable=resolved_executable, timeout_seconds=config.llm_timeout)
    status["configured"] = True
    status["backend_name"] = backend.name
    return backend, status


def _run_codex_preflight(
    *,
    backend: LLMBackend | None,
    status: dict,
    timeout_seconds: float,
) -> tuple[LLMBackend | None, dict, BackendInvocationError | None]:
    status["codex_preflight_attempted"] = True
    status["codex_preflight_timeout_seconds"] = timeout_seconds
    if backend is None:
        status["codex_preflight_status"] = "backend_unavailable"
        return backend, status, None
    try:
        assert isinstance(backend, CodexBackend)
        backend.preflight(timeout_seconds=timeout_seconds)
    except BackendInvocationError as exc:
        status["configured"] = False
        status["backend_name"] = None
        status["codex_preflight_status"] = "failed"
        status["codex_preflight_category"] = exc.category
        status["codex_preflight_detail_category"] = exc.detail_category
        status["codex_preflight_reason"] = str(exc)
        return None, status, exc
    status["codex_preflight_status"] = "ok"
    return backend, status, None


def _soft_continue_codex_after_timeout(
    *,
    config: RunConfig,
    status: dict,
    reason: str,
    executable: str,
    selection_reason: str,
) -> tuple[LLMBackend, dict]:
    backend = CodexBackend(executable=executable, timeout_seconds=config.llm_timeout)
    status.update(
        {
            "selected_backend": "codex",
            "configured": True,
            "backend_name": backend.name,
            "fallback": False,
            "fallback_reason": None,
            "fallback_category": None,
            "fallback_detail_category": None,
            "selection_reason": selection_reason,
            "codex_preflight_soft_failed": True,
            "codex_preflight_soft_failure_reason": reason,
        }
    )
    return backend, status


def _should_skip_explicit_codex_preflight(request_profile_hint: dict | None) -> tuple[bool, str | None]:
    if not isinstance(request_profile_hint, dict):
        return False, None
    if request_profile_hint.get("codex_preflight_policy") != "skip":
        return False, None
    reason = request_profile_hint.get("codex_preflight_skip_reason")
    if isinstance(reason, str) and reason.strip():
        return True, reason.strip()
    return True, "Skipped explicit codex preflight because the request is a rough normalization-only path and the real codex call is the first meaningful backend signal."


def _should_skip_auto_codex_preflight(
    *,
    config: RunConfig,
    request_profile_hint: dict | None,
) -> tuple[bool, str | None]:
    if not isinstance(request_profile_hint, dict):
        return False, None
    if request_profile_hint.get("auto_codex_preflight_policy") != "skip":
        return False, None
    if config.effective_model:
        return False, None
    reason = request_profile_hint.get("auto_codex_preflight_skip_reason")
    if isinstance(reason, str) and reason.strip():
        return True, reason.strip()
    return True, (
        "Skipped auto-mode codex preflight because the request is a rough normalization-only path and no configured API "
        "backend was available as an alternative; the real codex call is the first meaningful backend signal."
    )


def _prior_codex_failure_signal(prior_backend_assistance: dict | None) -> dict | None:
    if not isinstance(prior_backend_assistance, dict):
        return None
    if not prior_backend_assistance.get("fallback"):
        return None
    category = prior_backend_assistance.get("fallback_category")
    if category not in SESSION_MEMORY_API_PREFER_CATEGORIES:
        return None
    prior_selected_backend = prior_backend_assistance.get("selected_backend")
    prior_requested_backend = prior_backend_assistance.get("requested_backend")
    if prior_selected_backend == "codex":
        return {
            "category": category,
            "requested_backend": prior_requested_backend,
            "selected_backend": prior_selected_backend,
            "mode": "codex_selected",
        }
    if prior_selected_backend == "rules" and prior_requested_backend in {"auto", "codex"}:
        return {
            "category": category,
            "requested_backend": prior_requested_backend,
            "selected_backend": prior_selected_backend,
            "mode": "codex_targeting_failed_early",
        }
    return None


def _session_backend_api_preference(config: RunConfig, prior_backend_assistance: dict | None) -> dict | None:
    if config.backend != "auto" or not config.effective_model:
        return None
    signal = _prior_codex_failure_signal(prior_backend_assistance)
    if signal is None:
        return None
    fallback_reason = prior_backend_assistance.get("fallback_reason") or "previous codex fallback"
    if signal["mode"] == "codex_targeting_failed_early":
        selection_reason = (
            "Auto mode reused backend memory from the resumed session and preferred the configured API backend "
            "because the last codex-targeting attempt degraded before a usable local codex path was established "
            f"({signal['category']}: {fallback_reason})."
        )
    else:
        selection_reason = (
            "Auto mode reused backend memory from the resumed session and preferred the configured API backend "
            f"because the last codex-assisted attempt degraded with {signal['category']}: {fallback_reason}"
        )
    return {
        "category": signal["category"],
        "fallback_reason": fallback_reason,
        "selection_reason": selection_reason,
        "prior_selected_backend": signal["selected_backend"],
    }


def build_llm_backend(
    config: RunConfig,
    *,
    prior_backend_assistance: dict | None = None,
    request_profile_hint: dict | None = None,
) -> tuple[LLMBackend | None, dict]:
    requested_backend = config.backend
    effective_backend = requested_backend

    status = {
        "requested_backend": requested_backend,
        "selected_backend": effective_backend,
        "configured": False,
        "backend_name": None,
        "requested_model": config.effective_model,
        "provider": config.provider,
        "model_name": config.model_name,
        "fallback": False,
        "fallback_reason": None,
        "fallback_category": None,
        "fallback_detail_category": None,
        "resolved_base_url": None,
        "backend_executable": None,
        "selection_reason": None,
        "codex_preflight_attempted": False,
        "codex_preflight_timeout_seconds": None,
        "codex_preflight_status": None,
        "codex_preflight_category": None,
        "codex_preflight_detail_category": None,
        "codex_preflight_reason": None,
        "codex_preflight_skipped": False,
        "codex_preflight_skip_reason": None,
        "codex_preflight_soft_failed": False,
        "codex_preflight_soft_failure_reason": None,
        "session_backend_memory_considered": False,
        "session_backend_memory_used": False,
        "session_backend_memory_reason": None,
        "session_backend_prior_category": None,
        "session_backend_prior_selected_backend": None,
    }

    if requested_backend == "auto":
        session_api_preference = _session_backend_api_preference(config, prior_backend_assistance)
        if session_api_preference is not None:
            api_status = {
                **status,
                "selected_backend": "api",
                "selection_reason": session_api_preference["selection_reason"],
                "session_backend_memory_considered": True,
                "session_backend_memory_used": True,
                "session_backend_memory_reason": session_api_preference["selection_reason"],
                "session_backend_prior_category": session_api_preference["category"],
                "session_backend_prior_selected_backend": session_api_preference["prior_selected_backend"],
            }
            backend, api_status = _build_api_backend(config, api_status)
            if backend is not None:
                return backend, api_status
            status["session_backend_memory_considered"] = True
            status["session_backend_prior_category"] = session_api_preference["category"]
            status["session_backend_prior_selected_backend"] = session_api_preference["prior_selected_backend"]
            status["session_backend_memory_reason"] = (
                session_api_preference["selection_reason"]
                + " The configured API backend was not usable, so normal auto backend selection continued."
            )
        executable = _discover_codex_executable()
        if executable is not None:
            backend, backend_status = _build_codex_backend(config, status, executable=executable)
            assert backend_status is status
            skip_preflight, skip_reason = _should_skip_auto_codex_preflight(
                config=config,
                request_profile_hint=request_profile_hint,
            )
            if skip_preflight:
                status["selected_backend"] = "codex"
                status["codex_preflight_status"] = "skipped"
                status["codex_preflight_skipped"] = True
                status["codex_preflight_skip_reason"] = skip_reason
                status["selection_reason"] = (
                    "Auto mode skipped codex preflight for a rough normalization-only request because no configured API "
                    "backend was available; the real codex call will decide whether fallback is necessary."
                )
                return backend, status
            preflight_timeout = min(config.llm_timeout, AUTO_CODEX_PREFLIGHT_TIMEOUT_SECONDS)
            backend, status, preflight_error = _run_codex_preflight(
                backend=backend,
                status=status,
                timeout_seconds=preflight_timeout,
            )
            if preflight_error is not None:
                if preflight_error.category == "timeout" and not config.effective_model:
                    return _soft_continue_codex_after_timeout(
                        config=config,
                        status=status,
                        reason=str(preflight_error),
                        executable=executable,
                        selection_reason=(
                            "Auto mode kept the local codex backend after a short preflight timeout because no configured API backend was available; "
                            "the real codex call will decide whether fallback is still necessary."
                        ),
                    )
                if config.effective_model:
                    status["selection_reason"] = (
                        "Auto mode skipped local codex after preflight failed and switched to the configured API backend."
                    )
                    api_status = {
                        **status,
                        "selected_backend": "api",
                        "fallback": False,
                        "fallback_reason": None,
                        "fallback_category": None,
                        "fallback_detail_category": None,
                    }
                    backend, api_status = _build_api_backend(config, api_status)
                    if backend is None:
                        api_status["selected_backend"] = "rules"
                        api_status["selection_reason"] = (
                            "Auto mode skipped local codex after preflight failed, but the API backend was not actually usable, so the run fell back to rules."
                        )
                    return backend, api_status
                status["selected_backend"] = "rules"
                status["fallback"] = True
                status["fallback_category"] = preflight_error.category
                status["fallback_detail_category"] = preflight_error.detail_category
                status["fallback_reason"] = (
                    f"Auto backend skipped local codex after preflight failed ({preflight_error}) and no configured API backend was available."
                )
                status["selection_reason"] = "Auto mode fell back to rules after codex preflight failed and no API backend was configured."
                return None, status
            if backend is not None:
                status["selected_backend"] = "codex"
                status["selection_reason"] = "Auto mode selected local codex after a successful short preflight."
                return backend, status
        if config.effective_model:
            status["selected_backend"] = "api"
            status["selection_reason"] = "Auto mode selected the configured API backend because no usable local codex backend was available."
            backend, api_status = _build_api_backend(config, status)
            if backend is None:
                api_status["selected_backend"] = "rules"
                api_status["selection_reason"] = (
                    "Auto mode could not use local codex, and the configured API backend was not actually usable, so the run fell back to rules."
                )
            return backend, api_status
        status["selected_backend"] = "rules"
        status["fallback"] = True
        status["fallback_category"] = "configuration_missing"
        status["fallback_reason"] = (
            "Auto backend could not find a usable local codex backend or a configured API model/key, so the run will use the rule-based path."
        )
        status["selection_reason"] = "Auto mode fell back to rules because neither a usable local codex backend nor a configured API backend was available."
        return None, status

    if effective_backend == "api":
        status["selection_reason"] = "Explicit API backend requested."
        return _build_api_backend(config, status)

    if effective_backend == "codex":
        status["selection_reason"] = "Explicit codex backend requested."
        backend, status = _build_codex_backend(config, status)
        skip_preflight, skip_reason = _should_skip_explicit_codex_preflight(request_profile_hint)
        if skip_preflight:
            status["selected_backend"] = "codex"
            status["codex_preflight_status"] = "skipped"
            status["codex_preflight_skipped"] = True
            status["codex_preflight_skip_reason"] = skip_reason
            status["selection_reason"] = (
                "Explicit codex backend skipped preflight for a rough normalization-only request; "
                "the real codex call will decide whether fallback is necessary."
            )
            return backend, status
        preflight_timeout = min(config.llm_timeout, EXPLICIT_CODEX_PREFLIGHT_TIMEOUT_SECONDS)
        backend, status, preflight_error = _run_codex_preflight(
            backend=backend,
            status=status,
            timeout_seconds=preflight_timeout,
        )
        if preflight_error is not None:
            if preflight_error.category == "timeout":
                return _soft_continue_codex_after_timeout(
                    config=config,
                    status=status,
                    reason=str(preflight_error),
                    executable=str(status.get("backend_executable") or "codex"),
                    selection_reason=(
                        "Explicit codex backend kept running after a short preflight timeout; "
                        "the full codex call will decide whether fallback is still necessary."
                    ),
                )
            status["selected_backend"] = "rules"
            status["fallback"] = True
            status["fallback_category"] = preflight_error.category
            status["fallback_detail_category"] = preflight_error.detail_category
            status["fallback_reason"] = (
                f"Explicit codex backend failed preflight ({preflight_error}), so the run will use the rule-based path."
            )
            status["selection_reason"] = "Explicit codex backend failed short preflight and fell back to rules."
            return None, status
        return backend, status

    status["fallback"] = True
    status["fallback_category"] = "configuration_invalid"
    status["fallback_reason"] = f"Unknown backend {config.backend!r}; using rule-based fallback."
    return None, status
