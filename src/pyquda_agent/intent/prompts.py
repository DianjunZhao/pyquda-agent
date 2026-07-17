"""Prompts for optional LLM-assisted intent interpretation."""

from __future__ import annotations

import json

from pyquda_agent.intent.interpreter import BARYON_UNSPECIFIED_TARGET_ID
from pyquda_agent.intent.interpreter import MESON_UNSPECIFIED_TARGET_ID
from pyquda_agent.intent.schema import PhysicsTargetArtifact


def build_intent_system_prompt(*, concise: bool = False) -> str:
    if concise:
        return (
            "Interpret a PyQUDA request. Return strict JSON only. "
            "Prefer the smallest sufficient answer. "
            "Do not invent APIs or user confirmation."
        )
    return (
        "You help interpret lattice-QCD / PyQUDA user requests. "
        "Return strict JSON only. Do not invent PyQUDA APIs. "
        "Do not claim the user has confirmed a physics target unless the request is explicit. "
        "If the request is ambiguous, keep the status at needs_confirmation and explain candidate operators/formulas."
    )


def build_intent_normalization_system_prompt() -> str:
    return (
        "Normalize a rough PyQUDA physics request into a short precise label. "
        "Return strict JSON only. "
        "Do not invent APIs, formulas, or user confirmation."
    )


def build_intent_recovery_system_prompt(*, concise: bool = False) -> str:
    if concise:
        return (
            "Retry a timed-out PyQUDA request interpretation. "
            "Return the smallest sufficient strict JSON answer. "
            "Do not invent APIs or user confirmation."
        )
    return (
        "You are retrying a timed-out physics-target interpretation for a PyQUDA request. "
        "Return strict JSON only. Prefer the smallest sufficient answer. "
        "Do not invent PyQUDA APIs or claim user confirmation unless it is explicit in the request."
    )


def build_intent_normalization_recovery_system_prompt() -> str:
    return (
        "Retry a timed-out PyQUDA request normalization. "
        "Return the smallest sufficient strict JSON answer. "
        "Do not invent APIs, formulas, or user confirmation."
    )


def _compact_formula_proposals(rule_based: PhysicsTargetArtifact) -> list[dict]:
    proposals: list[dict] = []
    for item in rule_based.formula_proposals:
        if not isinstance(item, dict):
            continue
        proposals.append(
            {
                "proposal_id": item.get("proposal_id"),
                "target_id": item.get("target_id"),
                "label": item.get("label"),
                "operator": item.get("operator"),
                "correlator": item.get("correlator"),
                "convention": item.get("convention"),
                "provenance": item.get("provenance"),
            }
        )
    return proposals


def _compact_rule_based_view(rule_based: PhysicsTargetArtifact) -> dict:
    include_formula_detail = _needs_formula_detail(rule_based)
    return {
        "status": rule_based.status,
        "normalized_request": rule_based.normalized_request,
        "task_type_hint": rule_based.task_type_hint,
        "candidate_targets": rule_based.candidate_targets,
        "inferred_interpretation": rule_based.inferred_interpretation,
        "confirmed_interpretation": rule_based.confirmed_interpretation,
        "formula_proposal_count": len(rule_based.formula_proposals),
        "formula_proposals": _compact_formula_proposals(rule_based) if include_formula_detail else [],
        "inferred_fields": rule_based.inferred_fields,
        "user_confirmed_fields": rule_based.user_confirmed_fields,
        "parser_guesses": rule_based.parser_guesses,
        "local_reference_count": len(rule_based.local_references),
        "external_citation_count": len(rule_based.external_citations),
        "has_curated_local_citations": bool(rule_based.external_citations),
        "unsupported_reasons": rule_based.unsupported_reasons,
    }


def _concise_rule_based_view(rule_based: PhysicsTargetArtifact) -> dict:
    return {
        "status": rule_based.status,
        "task_type_hint": rule_based.task_type_hint,
        "candidate_targets": rule_based.candidate_targets,
        "inferred_interpretation": rule_based.inferred_interpretation,
        "confirmed_interpretation": rule_based.confirmed_interpretation,
        "local_reference_count": len(rule_based.local_references),
        "external_citation_count": len(rule_based.external_citations),
        "has_curated_local_citations": bool(rule_based.external_citations),
    }


def _compact_recovery_view(rule_based: PhysicsTargetArtifact) -> dict:
    compact = _compact_rule_based_view(rule_based)
    return {
        "status": compact["status"],
        "task_type_hint": compact["task_type_hint"],
        "candidate_targets": compact["candidate_targets"],
        "inferred_interpretation": compact["inferred_interpretation"],
        "confirmed_interpretation": compact["confirmed_interpretation"],
        "formula_proposals": compact["formula_proposals"],
        "unsupported_reasons": compact["unsupported_reasons"],
    }


def _needs_formula_detail(rule_based: PhysicsTargetArtifact) -> bool:
    inferred_target_id = (rule_based.inferred_interpretation or {}).get("target_id")
    if inferred_target_id in {MESON_UNSPECIFIED_TARGET_ID, BARYON_UNSPECIFIED_TARGET_ID}:
        return True
    if len(rule_based.candidate_targets) > 1:
        return True
    return bool(rule_based.unsupported_reasons)


def _requested_output_keys(rule_based: PhysicsTargetArtifact) -> str:
    if _needs_formula_detail(rule_based):
        return (
            "{\n"
            '  "normalized_request": string,\n'
            '  "physics_status": "confirmed" | "needs_confirmation" | "unknown",\n'
            '  "candidate_targets": [\n'
            "    {\n"
            '      "target_id": string,\n'
            '      "label": string,\n'
            '      "summary": string,\n'
            '      "confidence": "high" | "medium" | "low",\n'
            '      "status": "confirmed" | "inferred" | "candidate" | "needs_confirmation",\n'
            '      "task_type_hint": string | null\n'
            "    }\n"
            "  ],\n"
            '  "formula_proposals": [\n'
            "    {\n"
            '      "proposal_id": string,\n'
            '      "target_id": string,\n'
            '      "label": string,\n'
            '      "operator": string,\n'
            '      "correlator": string,\n'
            '      "convention": string,\n'
            '      "provenance": "model_inference"\n'
            "    }\n"
            "  ],\n"
            '  "notes": [string]\n'
            "}"
        )
    return (
        "{\n"
        '  "normalized_request": string,\n'
        '  "physics_status": "confirmed" | "needs_confirmation" | "unknown",\n'
        '  "candidate_targets": [\n'
        "    {\n"
        '      "target_id": string,\n'
        '      "label": string,\n'
        '      "summary": string,\n'
        '      "confidence": "high" | "medium" | "low",\n'
        '      "status": "confirmed" | "inferred" | "candidate" | "needs_confirmation",\n'
        '      "task_type_hint": string | null\n'
        "    }\n"
        "  ],\n"
        '  "notes": [string]\n'
        "}"
    )


def _requested_output_keys_concise() -> str:
    return (
        '{'
        '"normalized_request": string, '
        '"physics_status": "confirmed" | "needs_confirmation" | "unknown", '
        '"candidate_targets": [{"target_id": string, "label": string, "summary": string, "confidence": "high" | "medium" | "low", "status": "confirmed" | "inferred" | "candidate" | "needs_confirmation", "task_type_hint": string | null}], '
        '"notes": [string]'
        '}'
    )


def _requested_normalization_output_keys() -> str:
    return '{"normalized_request": string, "notes": [string]}'


def build_intent_user_prompt(user_request: str, rule_based: PhysicsTargetArtifact, *, concise: bool = False) -> str:
    compact_view = json.dumps(
        _concise_rule_based_view(rule_based) if concise else _compact_rule_based_view(rule_based),
        indent=2,
        ensure_ascii=False,
    )
    formula_guidance = (
        "Because the request is ambiguous, include candidate formula/operator explanations in `formula_proposals`."
        if _needs_formula_detail(rule_based)
        else "Do not spend tokens restating formula/operator detail unless it is strictly needed; leave `formula_proposals` omitted or empty."
    )
    if concise:
        return (
            "Interpret this rough PyQUDA request.\n\n"
            f"Request:\n{user_request}\n\n"
            "Compact hint:\n"
            f"{compact_view}\n\n"
            "Return JSON with exactly these keys:\n"
            f"{_requested_output_keys_concise()}\n\n"
            "If the request is rough, keep the target inferred or needs_confirmation."
        )
    return (
        "Interpret the following rough user request for a PyQUDA script workflow.\n\n"
        f"User request:\n{user_request}\n\n"
        "Current rule-based interpretation snapshot (compact JSON; full curated citations and reference lists are intentionally omitted to keep the backend prompt small):\n"
        f"{compact_view}\n\n"
        "Return JSON with the following keys:\n"
        f"{_requested_output_keys(rule_based)}\n\n"
        f"{formula_guidance}\n"
        "Current supported targets include a zero-momentum pion two-point workflow, a narrow pion-dispersion workflow, "
        "a fixed meson-spectroscopy workflow, and a zero-momentum proton two-point workflow. "
        "If the request is clearly about one of them, you may normalize the wording, "
        "but if the wording is rough you must still leave the physics target as inferred or needs_confirmation rather than claiming user confirmation."
    )


def build_intent_normalization_user_prompt(user_request: str, rule_based: PhysicsTargetArtifact) -> str:
    inferred = rule_based.inferred_interpretation or {}
    compact_view = json.dumps(
        {
            "status": rule_based.status,
            "candidate_target": {
                "target_id": inferred.get("target_id"),
                "label": inferred.get("label"),
                "task_type_hint": inferred.get("task_type_hint"),
            },
            "normalized_request": rule_based.normalized_request,
        },
        indent=2,
        ensure_ascii=False,
    )
    return (
        "Normalize this rough PyQUDA request into one short precise physics label.\n\n"
        f"Request:\n{user_request}\n\n"
        "Current rule-based target guess:\n"
        f"{compact_view}\n\n"
        "Return JSON with exactly these keys:\n"
        f"{_requested_normalization_output_keys()}\n\n"
        "Keep the existing target guess; only rewrite the request more cleanly."
    )


def build_intent_timeout_recovery_user_prompt(
    user_request: str,
    rule_based: PhysicsTargetArtifact,
    *,
    concise: bool = False,
) -> str:
    recovery_view = json.dumps(
        _concise_rule_based_view(rule_based) if concise else _compact_recovery_view(rule_based),
        indent=2,
        ensure_ascii=False,
    )
    if concise:
        return (
            "The first LLM-assisted interpretation attempt timed out. Retry with the smallest strict JSON answer.\n\n"
            f"Request:\n{user_request}\n\n"
            "Compact hint:\n"
            f"{recovery_view}\n\n"
            "Return JSON with exactly these keys:\n"
            f"{_requested_output_keys_concise()}\n"
        )
    if _needs_formula_detail(rule_based):
        response_shape = (
            "{\n"
            '  "normalized_request": string,\n'
            '  "physics_status": "confirmed" | "needs_confirmation" | "unknown",\n'
            '  "candidate_targets": [{"target_id": string, "label": string, "summary": string, "confidence": "high" | "medium" | "low", "status": "confirmed" | "inferred" | "candidate" | "needs_confirmation", "task_type_hint": string | null}],\n'
            '  "formula_proposals": [{"proposal_id": string, "target_id": string, "label": string, "operator": string, "correlator": string, "convention": string, "provenance": "model_inference"}],\n'
            '  "notes": [string]\n'
            "}"
        )
    else:
        response_shape = (
            "{\n"
            '  "normalized_request": string,\n'
            '  "physics_status": "confirmed" | "needs_confirmation" | "unknown",\n'
            '  "candidate_targets": [{"target_id": string, "label": string, "summary": string, "confidence": "high" | "medium" | "low", "status": "confirmed" | "inferred" | "candidate" | "needs_confirmation", "task_type_hint": string | null}],\n'
            '  "notes": [string]\n'
            "}"
        )
    return (
        "The first LLM-assisted interpretation attempt timed out. "
        "Retry with the smallest sufficient JSON answer.\n\n"
        f"User request:\n{user_request}\n\n"
        "Compact rule-based hint:\n"
        f"{recovery_view}\n\n"
        "Return JSON with exactly these keys:\n"
        f"{response_shape}\n"
    )


def build_intent_timeout_recovery_normalization_user_prompt(
    user_request: str,
    rule_based: PhysicsTargetArtifact,
) -> str:
    inferred = rule_based.inferred_interpretation or {}
    recovery_view = json.dumps(
        {
            "status": rule_based.status,
            "candidate_target": {
                "target_id": inferred.get("target_id"),
                "label": inferred.get("label"),
                "task_type_hint": inferred.get("task_type_hint"),
            },
        },
        indent=2,
        ensure_ascii=False,
    )
    return (
        "The first LLM-assisted normalization attempt timed out. Retry with the smallest strict JSON answer.\n\n"
        f"Request:\n{user_request}\n\n"
        "Current target guess:\n"
        f"{recovery_view}\n\n"
        "Return JSON with exactly these keys:\n"
        f"{_requested_normalization_output_keys()}\n"
    )


def should_use_normalization_only_intent_prompt(rule_based: PhysicsTargetArtifact, *, backend_name: str | None) -> bool:
    if backend_name != "codex":
        return False
    if _needs_formula_detail(rule_based):
        return False
    if rule_based.status != "needs_confirmation":
        return False
    if rule_based.confirmed_interpretation is not None:
        return False
    if len(rule_based.candidate_targets) != 1:
        return False
    inferred = rule_based.inferred_interpretation or {}
    return bool(inferred.get("target_id"))


def should_use_concise_intent_prompt(rule_based: PhysicsTargetArtifact, *, backend_name: str | None) -> bool:
    return backend_name == "codex" and not _needs_formula_detail(rule_based)
