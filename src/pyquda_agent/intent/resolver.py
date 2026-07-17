"""Resolve physics-target artifacts with optional LLM assistance."""

from __future__ import annotations

import json
import re
from contextlib import contextmanager

from pyquda_agent.backends.base import BackendInvocationError
from pyquda_agent.backends.base import LLMBackend

from .interpreter import interpret_request
from .prompts import build_intent_recovery_system_prompt
from .prompts import build_intent_normalization_recovery_system_prompt
from .prompts import build_intent_normalization_system_prompt
from .prompts import build_intent_normalization_user_prompt
from .prompts import build_intent_timeout_recovery_user_prompt
from .prompts import build_intent_timeout_recovery_normalization_user_prompt
from .prompts import build_intent_system_prompt
from .prompts import build_intent_user_prompt
from .prompts import should_use_concise_intent_prompt
from .prompts import should_use_normalization_only_intent_prompt
from .schema import PhysicsTargetArtifact

INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS = 12.0
INTENT_CODEX_NORMALIZATION_PRIMARY_TIMEOUT_SECONDS = 8.0
INTENT_TIMEOUT_RECOVERY_TIMEOUT_SECONDS = 10.0
INTENT_STRATEGY_NORMALIZATION_ONLY = "normalization_only"
INTENT_STRATEGY_FULL_INTERPRETATION = "full_interpretation"


def _default_knowledge_boundary() -> dict:
    return {
        "local_curated_citations": {
            "implemented": True,
            "used": False,
            "note": "Curated local JSON citations are available and may be attached to the physics artifact or implementation plan.",
        },
        "model_inference": {
            "used": False,
            "note": "Model inference may be used for normalization or formula/operator explanation when an LLM backend is configured.",
        },
        "true_online_lookup": {
            "implemented": False,
            "used": False,
            "note": "Legacy boundary label retained for compatibility. The active opt-in capability is recorded under knowledge_boundary.live_online_lookup.",
        },
        "live_online_lookup": {
            "implemented": True,
            "enabled": False,
            "used": False,
            "status": "disabled",
            "note": "Live online lookup is opt-in and only used when local PyQUDA evidence is insufficient for the physics-side target definition.",
        },
    }


def _extract_json_object(text: str) -> dict:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("LLM response did not contain a JSON object.") from None
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("LLM response JSON must be an object.")
    return payload


def _normalize_formula_proposals(proposals: object) -> list[dict]:
    if not isinstance(proposals, list):
        return []
    normalized: list[dict] = []
    for item in proposals:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "proposal_id": item.get("proposal_id", "llm_formula_proposal"),
                "target_id": item.get("target_id"),
                "label": item.get("label", "LLM-assisted formula proposal"),
                "operator": item.get("operator", "Underspecified"),
                "correlator": item.get("correlator", "Underspecified"),
                "convention": item.get("convention", ""),
                "provenance": "model_inference",
                "citations": [],
                "local_references": [],
            }
        )
    return normalized


def _normalize_candidate_targets(targets: object) -> list[dict]:
    if not isinstance(targets, list):
        return []
    normalized: list[dict] = []
    for item in targets:
        if not isinstance(item, dict):
            continue
        target_id = item.get("target_id")
        label = item.get("label")
        if not isinstance(target_id, str) or not isinstance(label, str):
            continue
        normalized.append(
            {
                "target_id": target_id,
                "label": label,
                "summary": item.get("summary", ""),
                "confidence": item.get("confidence", "low"),
                "status": item.get("status", "candidate"),
                "task_type_hint": item.get("task_type_hint"),
            }
        )
    return normalized


def _merge_llm_output(physics: PhysicsTargetArtifact, payload: dict) -> None:
    normalized_request = payload.get("normalized_request")
    if isinstance(normalized_request, str) and normalized_request.strip():
        physics.normalized_request = normalized_request.strip()

    llm_candidates = _normalize_candidate_targets(payload.get("candidate_targets"))
    llm_proposals = _normalize_formula_proposals(payload.get("formula_proposals"))
    physics_status = payload.get("physics_status")

    if llm_candidates and physics.confirmed_interpretation is None:
        physics.candidate_targets = llm_candidates
        physics.inferred_interpretation = llm_candidates[0]
        physics.task_type_hint = llm_candidates[0].get("task_type_hint") or physics.task_type_hint
        physics.parser_guesses["target_id"] = llm_candidates[0].get("target_id")
        physics.inferred_fields["target_id"] = llm_candidates[0].get("target_id")
        if physics_status in {"needs_confirmation", "unknown"}:
            physics.status = "needs_confirmation"

    if llm_proposals and (physics.confirmed_interpretation is None or not physics.formula_proposals):
        physics.formula_proposals = llm_proposals

    if llm_proposals:
        physics.knowledge_boundary["model_inference"]["used"] = True


@contextmanager
def _temporary_backend_timeout(backend: LLMBackend, timeout_seconds: float | None):
    if timeout_seconds is None or not hasattr(backend, "timeout_seconds"):
        yield
        return
    original = getattr(backend, "timeout_seconds")
    try:
        setattr(backend, "timeout_seconds", timeout_seconds)
        yield
    finally:
        setattr(backend, "timeout_seconds", original)


def _recovery_timeout_seconds(backend: LLMBackend) -> float | None:
    current = getattr(backend, "timeout_seconds", None)
    if not isinstance(current, (int, float)):
        return None
    return min(float(current), INTENT_TIMEOUT_RECOVERY_TIMEOUT_SECONDS)


def _primary_intent_timeout_seconds(backend: LLMBackend, *, strategy: str) -> float | None:
    backend_name = getattr(backend, "name", None)
    if backend_name != "codex":
        return None
    current = getattr(backend, "timeout_seconds", None)
    if not isinstance(current, (int, float)):
        return None
    ceiling = (
        INTENT_CODEX_NORMALIZATION_PRIMARY_TIMEOUT_SECONDS
        if strategy == INTENT_STRATEGY_NORMALIZATION_ONLY
        else INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS
    )
    return min(float(current), ceiling)


def _intent_strategy(physics: PhysicsTargetArtifact, *, backend_name: str | None) -> str:
    if should_use_normalization_only_intent_prompt(physics, backend_name=backend_name):
        return INTENT_STRATEGY_NORMALIZATION_ONLY
    return INTENT_STRATEGY_FULL_INTERPRETATION


def _intent_stage_list(strategy: str) -> list[str]:
    if strategy == INTENT_STRATEGY_NORMALIZATION_ONLY:
        return ["rough_request_normalization"]
    return [
        "rough_request_normalization",
        "physics_target_interpretation",
        "formula_operator_explanation",
    ]


def _should_attempt_timeout_recovery(
    *,
    backend_name: str | None,
    strategy: str,
) -> tuple[bool, str | None]:
    if backend_name == "codex" and strategy == INTENT_STRATEGY_NORMALIZATION_ONLY:
        return (
            False,
            "Skipped timeout recovery because the codex normalization-only intent path had already used the smallest low-value rough-request prompt.",
        )
    return True, None


def _generate_intent_response(
    *,
    backend: LLMBackend,
    user_request: str,
    physics: PhysicsTargetArtifact,
    strategy: str,
    concise_prompt: bool,
) -> str:
    if strategy == INTENT_STRATEGY_NORMALIZATION_ONLY:
        return backend.generate_text(
            system_prompt=build_intent_normalization_system_prompt(),
            user_prompt=build_intent_normalization_user_prompt(user_request, physics),
        )
    return backend.generate_text(
        system_prompt=build_intent_system_prompt(concise=concise_prompt),
        user_prompt=build_intent_user_prompt(user_request, physics, concise=concise_prompt),
    )


def _generate_timeout_recovery_response(
    *,
    backend: LLMBackend,
    user_request: str,
    physics: PhysicsTargetArtifact,
    strategy: str,
    concise_prompt: bool,
) -> str:
    if strategy == INTENT_STRATEGY_NORMALIZATION_ONLY:
        return backend.generate_text(
            system_prompt=build_intent_normalization_recovery_system_prompt(),
            user_prompt=build_intent_timeout_recovery_normalization_user_prompt(user_request, physics),
        )
    return backend.generate_text(
        system_prompt=build_intent_recovery_system_prompt(concise=concise_prompt),
        user_prompt=build_intent_timeout_recovery_user_prompt(user_request, physics, concise=concise_prompt),
    )


def _attempt_timeout_recovery(
    *,
    backend: LLMBackend,
    user_request: str,
    physics: PhysicsTargetArtifact,
    llm_assistance: dict,
    original_error: BackendInvocationError,
    strategy: str,
    concise_prompt: bool,
) -> dict | None:
    llm_assistance["timeout_recovery_attempted"] = True
    llm_assistance["timeout_recovery_trigger_category"] = original_error.category
    llm_assistance["timeout_recovery_trigger_reason"] = str(original_error)
    llm_assistance["timeout_recovery_timeout_seconds"] = _recovery_timeout_seconds(backend)
    llm_assistance["stages_attempted"].append("timeout_recovery_interpretation")
    try:
        with _temporary_backend_timeout(backend, llm_assistance["timeout_recovery_timeout_seconds"]):
            response_text = _generate_timeout_recovery_response(
                backend=backend,
                user_request=user_request,
                physics=physics,
                strategy=strategy,
                concise_prompt=concise_prompt,
            )
        payload = _extract_json_object(response_text)
    except BackendInvocationError as exc:
        llm_assistance["timeout_recovery_used"] = False
        llm_assistance["timeout_recovery_failed"] = True
        llm_assistance["timeout_recovery_failure_category"] = exc.category
        llm_assistance["timeout_recovery_failure_detail_category"] = exc.detail_category
        llm_assistance["timeout_recovery_failure_reason"] = str(exc)
        raise
    except Exception as exc:
        llm_assistance["timeout_recovery_used"] = False
        llm_assistance["timeout_recovery_failed"] = True
        llm_assistance["timeout_recovery_failure_category"] = "unexpected_error"
        llm_assistance["timeout_recovery_failure_reason"] = f"LLM timeout recovery failed: {exc}"
        raise
    llm_assistance["timeout_recovery_used"] = True
    llm_assistance["timeout_recovery_failed"] = False
    llm_assistance["stages_completed"].append("timeout_recovery_interpretation")
    notes = llm_assistance.setdefault("notes", [])
    notes.append("llm timeout recovery path used")
    return payload


def resolve_physics_target(
    user_request: str,
    *,
    backend: LLMBackend | None,
    backend_status: dict,
) -> PhysicsTargetArtifact:
    physics = interpret_request(user_request)
    physics.normalized_request = user_request.strip()
    physics.knowledge_boundary = _default_knowledge_boundary()
    physics.knowledge_boundary["local_curated_citations"]["used"] = bool(physics.external_citations)

    llm_assistance = {
        "requested_backend": backend_status.get("requested_backend"),
        "selected_backend": backend_status.get("selected_backend"),
        "configured_backend": backend_status.get("backend_name"),
        "configured": backend_status.get("configured", False),
        "resolved_base_url": backend_status.get("resolved_base_url"),
        "provider": backend_status.get("provider"),
        "model_name": backend_status.get("model_name"),
        "backend_executable": backend_status.get("backend_executable"),
        "selection_reason": backend_status.get("selection_reason"),
        "codex_preflight_attempted": backend_status.get("codex_preflight_attempted", False),
        "codex_preflight_timeout_seconds": backend_status.get("codex_preflight_timeout_seconds"),
        "codex_preflight_status": backend_status.get("codex_preflight_status"),
        "codex_preflight_category": backend_status.get("codex_preflight_category"),
        "codex_preflight_detail_category": backend_status.get("codex_preflight_detail_category"),
        "codex_preflight_reason": backend_status.get("codex_preflight_reason"),
        "codex_preflight_skipped": backend_status.get("codex_preflight_skipped", False),
        "codex_preflight_skip_reason": backend_status.get("codex_preflight_skip_reason"),
        "codex_preflight_soft_failed": backend_status.get("codex_preflight_soft_failed", False),
        "codex_preflight_soft_failure_reason": backend_status.get("codex_preflight_soft_failure_reason"),
        "session_backend_memory_considered": backend_status.get("session_backend_memory_considered", False),
        "session_backend_memory_used": backend_status.get("session_backend_memory_used", False),
        "session_backend_memory_reason": backend_status.get("session_backend_memory_reason"),
        "session_backend_prior_category": backend_status.get("session_backend_prior_category"),
        "session_backend_prior_selected_backend": backend_status.get("session_backend_prior_selected_backend"),
        "attempted": False,
        "used": False,
        "fallback": bool(backend_status.get("fallback")),
        "fallback_reason": backend_status.get("fallback_reason"),
        "fallback_category": backend_status.get("fallback_category"),
        "fallback_detail_category": backend_status.get("fallback_detail_category"),
        "stages_attempted": [],
        "stages_completed": [],
        "notes": [],
        "intent_strategy": None,
        "intent_prompt_profile": None,
        "timeout_recovery_attempted": False,
        "timeout_recovery_skipped": False,
        "timeout_recovery_skip_reason": None,
        "timeout_recovery_used": False,
        "timeout_recovery_failed": False,
        "timeout_recovery_trigger_category": None,
        "timeout_recovery_trigger_reason": None,
        "timeout_recovery_failure_category": None,
        "timeout_recovery_failure_detail_category": None,
        "timeout_recovery_failure_reason": None,
        "timeout_recovery_timeout_seconds": None,
        "intent_primary_timeout_seconds": None,
    }

    if backend is None:
        physics.llm_assistance = llm_assistance
        return physics

    llm_assistance["attempted"] = True
    backend_name = backend_status.get("backend_name") or getattr(backend, "name", None)
    concise_prompt = should_use_concise_intent_prompt(physics, backend_name=backend_name)
    strategy = _intent_strategy(physics, backend_name=backend_name)
    llm_assistance["intent_strategy"] = strategy
    llm_assistance["intent_prompt_profile"] = "normalization_only" if strategy == INTENT_STRATEGY_NORMALIZATION_ONLY else ("concise" if concise_prompt else "full")
    llm_assistance["stages_attempted"] = _intent_stage_list(strategy)
    llm_assistance["intent_primary_timeout_seconds"] = _primary_intent_timeout_seconds(backend, strategy=strategy)
    try:
        with _temporary_backend_timeout(backend, llm_assistance["intent_primary_timeout_seconds"]):
            response_text = _generate_intent_response(
                backend=backend,
                user_request=user_request,
                physics=physics,
                strategy=strategy,
                concise_prompt=concise_prompt,
            )
        payload = _extract_json_object(response_text)
    except BackendInvocationError as exc:
        if exc.category == "timeout":
            should_retry, skip_reason = _should_attempt_timeout_recovery(
                backend_name=backend_name,
                strategy=strategy,
            )
            if not should_retry:
                llm_assistance["timeout_recovery_skipped"] = True
                llm_assistance["timeout_recovery_skip_reason"] = skip_reason
                llm_assistance["fallback"] = True
                llm_assistance["fallback_reason"] = (
                    f"Initial LLM attempt timed out ({exc}). {skip_reason}"
                )
                llm_assistance["fallback_category"] = exc.category
                llm_assistance["fallback_detail_category"] = exc.detail_category
                physics.llm_assistance = llm_assistance
                return physics
            try:
                payload = _attempt_timeout_recovery(
                    backend=backend,
                    user_request=user_request,
                    physics=physics,
                    llm_assistance=llm_assistance,
                    original_error=exc,
                    strategy=strategy,
                    concise_prompt=concise_prompt,
                )
            except BackendInvocationError as recovery_exc:
                llm_assistance["fallback"] = True
                llm_assistance["fallback_reason"] = (
                    f"Initial LLM attempt timed out ({exc}); timeout-recovery attempt then failed ({recovery_exc})."
                )
                llm_assistance["fallback_category"] = recovery_exc.category
                llm_assistance["fallback_detail_category"] = recovery_exc.detail_category
                physics.llm_assistance = llm_assistance
                return physics
            except Exception as recovery_exc:
                llm_assistance["fallback"] = True
                llm_assistance["fallback_reason"] = (
                    f"Initial LLM attempt timed out ({exc}); timeout-recovery attempt then failed unexpectedly ({recovery_exc})."
                )
                llm_assistance["fallback_category"] = "unexpected_error"
                physics.llm_assistance = llm_assistance
                return physics
        else:
            llm_assistance["fallback"] = True
            llm_assistance["fallback_reason"] = str(exc)
            llm_assistance["fallback_category"] = exc.category
            llm_assistance["fallback_detail_category"] = exc.detail_category
            physics.llm_assistance = llm_assistance
            return physics
    except Exception as exc:
        llm_assistance["fallback"] = True
        llm_assistance["fallback_reason"] = f"LLM assistance failed: {exc}"
        llm_assistance["fallback_category"] = "unexpected_error"
        physics.llm_assistance = llm_assistance
        return physics

    llm_assistance["used"] = True
    llm_assistance["fallback"] = False
    physics.knowledge_boundary["model_inference"]["used"] = True
    completed = list(llm_assistance["stages_attempted"])
    if llm_assistance.get("timeout_recovery_used"):
        completed = [item for item in completed if item != "timeout_recovery_interpretation"]
        completed.append("timeout_recovery_interpretation")
    llm_assistance["stages_completed"] = completed
    notes = payload.get("notes")
    if isinstance(notes, list):
        llm_assistance["notes"].extend(str(item) for item in notes)
    _merge_llm_output(physics, payload)
    physics.llm_assistance = llm_assistance
    return physics
