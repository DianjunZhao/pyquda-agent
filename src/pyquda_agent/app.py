"""Application orchestration for the `pyquda-agent run` command."""

from __future__ import annotations

import json
from pathlib import Path
import shlex

from pyquda_agent.backends.factory import build_llm_backend
from pyquda_agent.config import DEFAULT_API_KEY_FILE
from pyquda_agent.config import DEFAULT_INDEX_PATH
from pyquda_agent.config import RunConfig
from pyquda_agent.generator.emitter import emit_script
from pyquda_agent.generator.plan import build_implementation_plan
from pyquda_agent.generator.templates import render_complete_script
from pyquda_agent.generator.validate import validate_generated_script
from pyquda_agent.intent.clarifier import apply_physics_answer
from pyquda_agent.intent.clarifier import build_physics_questions
from pyquda_agent.intent.interpreter import APE_SMEAR_TARGET_ID
from pyquda_agent.intent.interpreter import BARYON_UNSPECIFIED_TARGET_ID
from pyquda_agent.intent.interpreter import HADRON_UNSPECIFIED_TARGET_ID
from pyquda_agent.intent.interpreter import HYP_SMEAR_TARGET_ID
from pyquda_agent.intent.interpreter import MESON_SPEC_TARGET_ID
from pyquda_agent.intent.interpreter import MESON_UNSPECIFIED_TARGET_ID
from pyquda_agent.intent.interpreter import NEUTRON_TARGET_ID
from pyquda_agent.intent.interpreter import PION_PCAC_TARGET_ID
from pyquda_agent.intent.interpreter import PION_DISPERSION_TARGET_ID
from pyquda_agent.intent.interpreter import PION_TARGET_ID
from pyquda_agent.intent.interpreter import PROTON_TARGET_ID
from pyquda_agent.intent.interpreter import QUARK_PROPAGATOR_TARGET_ID
from pyquda_agent.intent.interpreter import RHO_TARGET_ID
from pyquda_agent.intent.interpreter import STOUT_SMEAR_TARGET_ID
from pyquda_agent.intent.interpreter import WILSON_FLOW_TARGET_ID
from pyquda_agent.intent.interpreter import interpret_request
from pyquda_agent.intent.prompts import should_use_normalization_only_intent_prompt
from pyquda_agent.intent.resolver import resolve_physics_target
from pyquda_agent.intent.schema import PhysicsTargetArtifact
from pyquda_agent.knowledge.external import maybe_lookup_external_knowledge
from pyquda_agent.models import GenerationResult
from pyquda_agent.retrieval.context_builder import build_context_bundle
from pyquda_agent.sessions.state import SessionState
from pyquda_agent.sessions.state import load_session
from pyquda_agent.sessions.state import merge_session_into_current
from pyquda_agent.sessions.state import save_session
from pyquda_agent.tasks.clarifier import apply_answer
from pyquda_agent.tasks.clarifier import build_questions
from pyquda_agent.tasks.clarifier import determine_missing_fields
from pyquda_agent.tasks.clarifier import QUESTION_PROMPTS
from pyquda_agent.tasks.clarification_groups import build_group_metadata
from pyquda_agent.tasks.clarification_groups import expand_grouped_set_assignment
from pyquda_agent.tasks.clarification_groups import FIELD_TO_GROUP
from pyquda_agent.tasks.parser import parse_task_description
from pyquda_agent.tasks.pion_2pt import finalize_task
from pyquda_agent.tasks.schema import Pion2ptTaskDraft
from pyquda_agent.workflows.matcher import WorkflowMatchResult
from pyquda_agent.workflows.matcher import apply_workflow_match
from pyquda_agent.workflows.matcher import APE_SMEAR_WORKFLOW_ID
from pyquda_agent.workflows.matcher import HYP_SMEAR_WORKFLOW_ID
from pyquda_agent.workflows.matcher import match_supported_workflow
from pyquda_agent.workflows.matcher import MESON_SPEC_PROPAGATOR_WORKFLOW_ID
from pyquda_agent.workflows.matcher import MESON_SPEC_WORKFLOW_ID
from pyquda_agent.workflows.matcher import PION_2PT_PROPAGATOR_WORKFLOW_ID
from pyquda_agent.workflows.matcher import PION_2PT_WORKFLOW_ID
from pyquda_agent.workflows.matcher import PION_PCAC_PROPAGATOR_WORKFLOW_ID
from pyquda_agent.workflows.matcher import PION_PCAC_WORKFLOW_ID
from pyquda_agent.workflows.matcher import PION_DISPERSION_WORKFLOW_ID
from pyquda_agent.workflows.matcher import PROTON_2PT_PROPAGATOR_WORKFLOW_ID
from pyquda_agent.workflows.matcher import PROTON_2PT_WORKFLOW_ID
from pyquda_agent.workflows.matcher import QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID
from pyquda_agent.workflows.matcher import QUARK_PROPAGATOR_WORKFLOW_ID
from pyquda_agent.workflows.matcher import RHO_VECTOR_PROPAGATOR_WORKFLOW_ID
from pyquda_agent.workflows.matcher import RHO_VECTOR_WORKFLOW_ID
from pyquda_agent.workflows.matcher import STOUT_SMEAR_WORKFLOW_ID
from pyquda_agent.workflows.matcher import WILSON_FLOW_WORKFLOW_ID
from scripts.probe_generated_workflow import build_probe as build_generated_probe


RESULT_SUMMARY_SCHEMA_FAMILY = "pyquda_agent.result_summary"
RESULT_SUMMARY_SCHEMA_VERSION = "2026-07-v1"


def _default_script_basename_for_target(physics: PhysicsTargetArtifact, draft: Pion2ptTaskDraft) -> str:
    workflow = draft.chosen_workflow_target or draft.workflow_id
    task_type = draft.task_type or physics.task_type_hint
    target_id = _resolved_target_id(physics)
    if draft.start_from == "propagator" and task_type == "pion_2pt":
        return "pion_2pt_from_propagator.py"
    if draft.start_from == "propagator" and task_type == "pion_pcac":
        return "pion_pcac_from_propagator.py"
    if draft.start_from == "propagator" and task_type == "meson_spec":
        return "meson_spec_from_propagator.py"
    if draft.start_from == "propagator" and task_type == "proton_2pt":
        return "proton_2pt_from_propagator.py"
    if draft.start_from == "propagator" and task_type == "rho_vector":
        return "rho_vector_from_propagator.py"
    if workflow == PION_PCAC_PROPAGATOR_WORKFLOW_ID:
        return "pion_pcac_from_propagator.py"
    if workflow == PION_PCAC_WORKFLOW_ID or target_id == PION_PCAC_TARGET_ID or task_type == "pion_pcac":
        return "pion_pcac.py"
    if workflow == "pion_dispersion_chroma_point_momentum_npy_v1" or target_id == PION_DISPERSION_TARGET_ID or task_type == "pion_dispersion":
        return "pion_dispersion.py"
    if workflow == MESON_SPEC_WORKFLOW_ID or target_id == MESON_SPEC_TARGET_ID or task_type == "meson_spec":
        return "meson_spec.py"
    if workflow == MESON_SPEC_PROPAGATOR_WORKFLOW_ID:
        return "meson_spec_from_propagator.py"
    if workflow == PROTON_2PT_PROPAGATOR_WORKFLOW_ID:
        return "proton_2pt_from_propagator.py"
    if workflow == RHO_VECTOR_PROPAGATOR_WORKFLOW_ID:
        return "rho_vector_from_propagator.py"
    if workflow == "proton_2pt_chroma_wall_local_zero_momentum_npy_v1" or target_id == PROTON_TARGET_ID or task_type == "proton_2pt":
        return "proton_2pt.py"
    if workflow == RHO_VECTOR_WORKFLOW_ID or target_id == RHO_TARGET_ID or task_type == "rho_vector":
        return "rho_vector.py"
    if target_id == NEUTRON_TARGET_ID:
        return "neutron_2pt.py"
    if workflow == QUARK_PROPAGATOR_WORKFLOW_ID or target_id == QUARK_PROPAGATOR_TARGET_ID or task_type == "quark_propagator":
        return "quark_propagator.py"
    if target_id == APE_SMEAR_TARGET_ID:
        return "ape_smear.py"
    if workflow == HYP_SMEAR_WORKFLOW_ID or target_id == HYP_SMEAR_TARGET_ID or task_type == "hyp_smear":
        return "hyp_smear.py"
    if workflow == STOUT_SMEAR_WORKFLOW_ID or target_id == STOUT_SMEAR_TARGET_ID or task_type == "stout_smear":
        return "stout_smear.py"
    if workflow == WILSON_FLOW_WORKFLOW_ID or target_id == WILSON_FLOW_TARGET_ID or task_type == "wilson_flow":
        return "wilson_flow.py"
    if workflow == "pion_2pt_existing_propagator_local_zero_momentum_npy_v1":
        return "pion_2pt_from_propagator.py"
    return "pion_2pt.py"


def _default_output_path(config: RunConfig, physics: PhysicsTargetArtifact, draft: Pion2ptTaskDraft) -> Path:
    if config.output_explicit:
        return config.output.expanduser().resolve()
    configured_output = config.output.expanduser().resolve()
    output_dir, _relative_root = _relative_output_root(configured_output)
    return (output_dir / _default_script_basename_for_target(physics, draft)).resolve()


def _relative_output_root(config_output: Path) -> tuple[Path, Path]:
    output_path = config_output.expanduser().resolve()
    output_dir = output_path.parent
    relative_root = output_dir.parent if output_dir.name == "outputs" else output_dir
    return output_dir, relative_root


def _resolve_runtime_output_path(raw_path: str, *, output_dir: Path, relative_root: Path) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path.resolve()
    if path.parent == Path("."):
        return (output_dir / path.name).resolve()
    return (relative_root / path).resolve()


def _normalize_output_paths(config: RunConfig, physics: PhysicsTargetArtifact, draft: Pion2ptTaskDraft) -> None:
    config_output = _default_output_path(config, physics, draft)
    output_dir, relative_root = _relative_output_root(config_output)
    if not draft.script_output_path:
        draft.script_output_path = str(config_output)
        draft.field_sources["script_output_path"] = "default"
        draft.fixed_fields["script_output_path"] = str(config_output)
    else:
        draft.script_output_path = str(
            _resolve_runtime_output_path(
                draft.script_output_path,
                output_dir=output_dir,
                relative_root=relative_root,
            )
        )
        draft.field_sources.setdefault("script_output_path", "parsed")
    if not draft.correlator_output_path:
        default_suffix = ".h5" if (draft.task_type == "quark_propagator" or _resolved_target_id(physics) == QUARK_PROPAGATOR_TARGET_ID) else ".npy"
        default_format = "hdf5" if default_suffix == ".h5" else "npy"
        draft.correlator_output_path = str(config_output.with_suffix(default_suffix))
        draft.correlator_output_format = default_format
        draft.field_sources["correlator_output_path"] = "default"
        draft.field_sources["correlator_output_format"] = "default"
        draft.fixed_fields["correlator_output_path"] = draft.correlator_output_path
        draft.fixed_fields["correlator_output_format"] = default_format
    else:
        draft.correlator_output_path = str(
            _resolve_runtime_output_path(
                draft.correlator_output_path,
                output_dir=output_dir,
                relative_root=relative_root,
            )
        )
        draft.field_sources.setdefault("correlator_output_path", "parsed")


def _load_or_parse_state(
    config: RunConfig,
    physics: PhysicsTargetArtifact | None,
    saved_state: SessionState | None = None,
) -> tuple[Pion2ptTaskDraft, PhysicsTargetArtifact, list[dict], dict | None, SessionState | None]:
    if config.resume_session:
        state = saved_state or load_session(config.resume_session)
        draft = parse_task_description(config.task_description)
        assert physics is not None
        draft, physics = merge_session_into_current(
            current_draft=draft,
            current_physics=physics,
            saved_state=state,
        )
        _normalize_output_paths(config, physics, draft)
        return draft, physics, list(state.asked_questions), state.workflow_match, state
    draft = parse_task_description(config.task_description)
    assert physics is not None
    _normalize_output_paths(config, physics, draft)
    if draft.gauge_path:
        draft.gauge_path = str(Path(draft.gauge_path).expanduser().resolve())
    if draft.resource_path and draft.resource_path.startswith("~"):
        draft.resource_path = str(Path(draft.resource_path).expanduser())
    return draft, physics, [], None, None


def _resume_pending_fields(saved_state: SessionState | None) -> list[str]:
    if saved_state is None:
        return []
    return [field_name for field_name in (saved_state.minimal_missing_fields or []) if field_name]


def _ask_physics_questions(config: RunConfig, physics: PhysicsTargetArtifact, asked_questions: list[dict]) -> None:
    for question in build_physics_questions(physics, config.max_questions):
        if not config.interactive:
            break
        answer = input(f"{question.prompt}\n> ")
        apply_physics_answer(physics, question.field_name, answer)
        asked_questions.append(
            {
                "field_name": question.field_name,
                "answer": answer,
                "category": question.category,
                "scope": question.scope,
            }
        )


def _ask_task_questions(
    config: RunConfig,
    draft: Pion2ptTaskDraft,
    asked_questions: list[dict],
    resume_pending_fields: list[str] | None = None,
) -> None:
    for question in build_questions(draft, config.max_questions, preferred_fields=resume_pending_fields):
        if not config.interactive:
            break
        answer = input(f"{question.prompt}\n> ")
        apply_answer(draft, question.field_name, answer)
        asked_questions.append(
            {
                "field_name": question.field_name,
                "answer": answer,
                "category": question.category,
                "scope": question.scope,
            }
        )


def _apply_physics_field_hints_to_draft(
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
) -> None:
    for field_source, assignments in (
        ("physics_clarified", physics.clarified_fields),
        ("physics_inferred", physics.inferred_fields),
        ("physics_confirmed", physics.user_confirmed_fields),
    ):
        for field_name, value in assignments.items():
            if field_name == "target_id" or not hasattr(draft, field_name):
                continue
            current_value = getattr(draft, field_name)
            if current_value not in (None, [], {}):
                continue
            setattr(draft, field_name, value)
            draft.field_sources.setdefault(field_name, field_source)


def _apply_cli_set_fields(
    config: RunConfig,
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    asked_questions: list[dict],
) -> None:
    for item in config.set_fields or []:
        if "=" not in item:
            raise ValueError(f"--set expects field=value, got {item!r}")
        field_name, raw_value = item.split("=", 1)
        field_name = field_name.strip()
        raw_value = raw_value.strip()
        if not field_name:
            raise ValueError(f"--set expects a non-empty field name, got {item!r}")
        if field_name == "confirmed_target_id":
            apply_physics_answer(physics, field_name, raw_value)
            asked_questions.append(
                {
                    "field_name": field_name,
                    "answer": raw_value,
                    "category": "physics",
                    "scope": "physics",
                    "source": "cli_set",
                }
            )
            continue
        group_assignments = expand_grouped_set_assignment(field_name, raw_value)
        if group_assignments is not None:
            for grouped_field_name, grouped_value in group_assignments:
                apply_answer(draft, grouped_field_name, grouped_value)
                asked_questions.append(
                    {
                        "field_name": grouped_field_name,
                        "answer": grouped_value,
                        "category": "task",
                        "scope": "task",
                        "source": "cli_set_group",
                        "group_id": field_name,
                    }
                )
            continue
        apply_answer(draft, field_name, raw_value)
        asked_questions.append(
            {
                "field_name": field_name,
                "answer": raw_value,
                "category": "task",
                "scope": "task",
                "source": "cli_set",
            }
        )


def _apply_cli_reply_answers(
    config: RunConfig,
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    asked_questions: list[dict],
    resume_pending_fields: list[str] | None = None,
) -> None:
    pending_replies = list(config.reply_answers or [])
    while pending_replies:
        physics_questions = build_physics_questions(physics, max_questions=max(len(pending_replies), 1))
        if physics_questions:
            question = physics_questions[0]
            answer = pending_replies.pop(0)
            trace_len_before = len(physics.clarification_trace)
            confirmed_before = physics.confirmed_interpretation
            example_answer = _example_set_value(
                question.field_name,
                physics=physics,
                draft=draft,
                script_output_path=draft.script_output_path,
            )
            apply_physics_answer(physics, question.field_name, answer)
            _apply_physics_field_hints_to_draft(physics, draft)
            if physics.confirmed_interpretation is None and len(physics.clarification_trace) == trace_len_before and confirmed_before is None:
                raise _reply_resolution_error(question, answer, example_answer=example_answer)
            asked_questions.append(
                {
                    "field_name": question.field_name,
                    "answer": answer,
                    "category": question.category,
                    "scope": question.scope,
                    "source": "cli_reply",
                }
            )
            continue
        workflow_match = match_supported_workflow(physics, draft)
        if workflow_match.matched:
            apply_workflow_match(draft, physics, workflow_match)
        task_questions = (
            build_questions(
                draft,
                max_questions=max(len(pending_replies), 1),
                preferred_fields=resume_pending_fields,
            )
            if physics.confirmed_interpretation is not None and workflow_match.matched
            else []
        )
        if task_questions:
            question = task_questions[0]
            answer = pending_replies.pop(0)
            example_answer = _example_set_value(
                question.field_name,
                physics=physics,
                draft=draft,
                script_output_path=draft.script_output_path,
            )
            apply_answer(draft, question.field_name, answer)
            if question.field_name in determine_missing_fields(draft):
                raise _reply_resolution_error(question, answer, example_answer=example_answer)
            asked_questions.append(
                {
                    "field_name": question.field_name,
                    "answer": answer,
                    "category": question.category,
                    "scope": question.scope,
                    "source": "cli_reply",
                }
            )
            continue
        raise ValueError("--reply was provided but there are no pending clarification questions to answer.")


def _maybe_save_session(
    config: RunConfig,
    draft: Pion2ptTaskDraft,
    physics: PhysicsTargetArtifact,
    asked_questions: list[dict],
    workflow_match: WorkflowMatchResult | None,
    context_bundle: dict | None,
    implementation_plan: dict | None,
) -> None:
    session_path = _effective_session_path(config, draft.script_output_path)
    if not session_path:
        return
    if physics.confirmed_interpretation is None:
        session_pending_fields = ["confirmed_target_id"]
    elif workflow_match is not None and workflow_match.matched:
        session_pending_fields = [
            question.field_name
            for question in build_questions(draft, config.max_questions)
        ]
    else:
        session_pending_fields = list(draft.missing_fields)
    save_session(
        session_path,
        SessionState(
            task_description=config.task_description,
            draft=draft,
            asked_questions=asked_questions,
            physics_target=physics,
            backend_assistance=physics.llm_assistance,
            confirmed_fields={
                **physics.user_confirmed_fields,
                **draft.user_confirmed_fields,
                **draft.clarified_fields,
            },
            rejected_options=dict(physics.unsupported_fields),
            minimal_missing_fields=session_pending_fields,
            workflow_match=workflow_match.to_dict() if workflow_match is not None else None,
            context_bundle=context_bundle,
            implementation_plan=implementation_plan,
        ),
    )


def _artifact_paths(script_output_path: str) -> tuple[Path, Path, Path]:
    script_path = Path(script_output_path)
    stem = script_path.stem
    artifact_dir = script_path.parent
    return (
        artifact_dir / f"{stem}.task.json",
        artifact_dir / f"{stem}.physics.json",
        artifact_dir / f"{stem}.plan.json",
    )


def _default_session_path(script_output_path: str) -> Path:
    return Path(script_output_path).with_suffix(".session.json")


def _effective_session_path(config: RunConfig, script_output_path: str | None = None) -> Path | None:
    if config.save_session is not None:
        return config.save_session
    if config.resume_session is not None:
        return config.resume_session
    if script_output_path:
        return _default_session_path(script_output_path)
    return None


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _probe_artifact_path(script_output_path: str) -> Path:
    return Path(script_output_path).with_suffix(".probe.json")


def _backend_request_profile_hint(config: RunConfig) -> dict | None:
    physics_preview = interpret_request(config.task_description)
    draft_preview = parse_task_description(config.task_description)
    if (
        physics_preview.status == "confirmed"
        and physics_preview.confirmed_interpretation is not None
        and draft_preview.task_type is not None
        and draft_preview.start_from in {"gauge", "propagator"}
        and bool(draft_preview.lattice_size)
        and bool(draft_preview.grid_size)
        and bool(draft_preview.script_output_path)
        and bool(draft_preview.correlator_output_path)
        and (
            bool(draft_preview.gauge_path)
            or bool(draft_preview.propagator_paths)
        )
    ):
        return {
            "backend_policy": "skip",
            "backend_skip_reason": (
                "Skipped backend-assisted interpretation because the request already contains a confirmed physics target "
                "and enough runnable task fields for grounded PyQUDA generation."
            ),
        }
    if not should_use_normalization_only_intent_prompt(physics_preview, backend_name="codex"):
        return None
    hint = {
        "intent_strategy_hint": "normalization_only",
    }
    if config.backend == "codex":
        hint.update(
            {
                "codex_preflight_policy": "skip",
                "codex_preflight_skip_reason": (
                    "Skipped explicit codex preflight because the request is a rough normalization-only path and the real codex call is the first meaningful backend signal."
                ),
            }
        )
    if config.backend == "auto":
        hint.update(
            {
                "auto_codex_preflight_policy": "skip",
                "auto_codex_preflight_skip_reason": (
                    "Skipped auto-mode codex preflight because the request is a rough normalization-only path and, when no configured API backend is available, the real codex call is the first meaningful backend signal."
                ),
            }
        )
    if len(hint) > 1:
        return hint
    return None


def _resolved_target_id(physics: PhysicsTargetArtifact) -> str | None:
    confirmed = physics.confirmed_interpretation or {}
    inferred = physics.inferred_interpretation or {}
    return confirmed.get("target_id") or inferred.get("target_id")


def _workflow_reply_value(task_type: str | None) -> str | None:
    return {
        "pion_2pt": "pion",
        "pion_pcac": "pion pcac",
        "pion_dispersion": "pion dispersion",
        "meson_spec": "meson spectrum",
        "proton_2pt": "proton",
        "rho_vector": "rho",
        "quark_propagator": "quark propagator",
        "ape_smear": "ape smear",
        "hyp_smear": "hyp smear",
        "stout_smear": "stout smear",
        "wilson_flow": "wilson flow",
    }.get(task_type or "")


def _target_task_type_hint(target_id: str | None) -> str | None:
    return {
        PION_TARGET_ID: "pion_2pt",
        PION_PCAC_TARGET_ID: "pion_pcac",
        PION_DISPERSION_TARGET_ID: "pion_dispersion",
        MESON_SPEC_TARGET_ID: "meson_spec",
        RHO_TARGET_ID: "rho_vector",
        PROTON_TARGET_ID: "proton_2pt",
        QUARK_PROPAGATOR_TARGET_ID: "quark_propagator",
        STOUT_SMEAR_TARGET_ID: "stout_smear",
        APE_SMEAR_TARGET_ID: "ape_smear",
        HYP_SMEAR_TARGET_ID: "hyp_smear",
        WILSON_FLOW_TARGET_ID: "wilson_flow",
    }.get(target_id or "")


def _physics_target_alias(target_id: str | None) -> str | None:
    return {
        PION_TARGET_ID: "pion",
        PION_PCAC_TARGET_ID: "pion pcac",
        PION_DISPERSION_TARGET_ID: "pion dispersion",
        MESON_SPEC_TARGET_ID: "meson spectrum",
        MESON_UNSPECIFIED_TARGET_ID: "meson",
        RHO_TARGET_ID: "rho",
        PROTON_TARGET_ID: "proton",
        NEUTRON_TARGET_ID: "neutron",
        BARYON_UNSPECIFIED_TARGET_ID: "baryon",
        HADRON_UNSPECIFIED_TARGET_ID: "hadron",
        QUARK_PROPAGATOR_TARGET_ID: "quark propagator",
        STOUT_SMEAR_TARGET_ID: "stout smear",
        APE_SMEAR_TARGET_ID: "ape smear",
        HYP_SMEAR_TARGET_ID: "hyp smear",
        WILSON_FLOW_TARGET_ID: "wilson flow",
    }.get(target_id or "")


def _supported_workflow_catalog() -> list[dict]:
    return [
        {
            "workflow_target": PION_2PT_WORKFLOW_ID,
            "task_type": "pion_2pt",
            "label": "Pion two-point from gauge",
            "summary": "Gauge -> Clover -> wall source -> local sink -> zero momentum -> npy correlator.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "source_type", "accepted_values": ["wall"]},
                {"field_name": "sink_type", "accepted_values": ["local"]},
                {"field_name": "momentum_projection", "accepted_values": ["zero"]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=gauge.",
                "Keep source_type=wall and sink_type=local.",
                "Keep momentum_projection=zero with momenta=[[0,0,0]].",
                "Write the correlator as npy.",
            ],
        },
        {
            "workflow_target": PION_2PT_PROPAGATOR_WORKFLOW_ID,
            "task_type": "pion_2pt",
            "label": "Pion two-point from existing propagators",
            "summary": "Existing propagator files -> local contraction -> zero momentum -> npy correlator.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["propagator"]},
                {"field_name": "has_existing_propagators", "accepted_values": [True]},
                {"field_name": "source_type", "accepted_values": ["wall", "point"]},
                {"field_name": "sink_type", "accepted_values": ["local"]},
                {"field_name": "momentum_projection", "accepted_values": ["zero"]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=propagator and provide propagator_paths.",
                "Keep source_type=wall or point.",
                "Keep sink_type=local and momentum_projection=zero.",
                "Write the correlator as npy.",
            ],
        },
        {
            "workflow_target": PION_PCAC_WORKFLOW_ID,
            "task_type": "pion_pcac",
            "label": "Pion PCAC ratio from gauge",
            "summary": "Gauge -> stout-smear + getDirac -> wall source -> pion/pionA4 zero-momentum contractions -> PCAC ratio -> npy correlator bundle.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "source_type", "accepted_values": ["wall"]},
                {"field_name": "sink_type", "accepted_values": ["local"]},
                {"field_name": "momentum_projection", "accepted_values": ["zero"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=gauge.",
                "Keep source_type=wall, sink_type=local, and momentum_projection=zero.",
                "Do not request gauge fixing in this family.",
                "Write the correlator bundle as npy.",
            ],
        },
        {
            "workflow_target": PION_PCAC_PROPAGATOR_WORKFLOW_ID,
            "task_type": "pion_pcac",
            "label": "Pion PCAC ratio from existing propagators",
            "summary": "Existing wall-source propagator files -> zero-momentum pion/pionA4 contractions -> PCAC ratio -> npy correlator bundle.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["propagator"]},
                {"field_name": "has_existing_propagators", "accepted_values": [True]},
                {"field_name": "source_type", "accepted_values": ["wall"]},
                {"field_name": "sink_type", "accepted_values": ["local"]},
                {"field_name": "momentum_projection", "accepted_values": ["zero"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=propagator and provide propagator_paths plus source_timeslices.",
                "Keep source_type=wall, sink_type=local, and momentum_projection=zero.",
                "Keep gauge_fixed=false to stay aligned with the grounded local PCAC wall-source path.",
                "Write the correlator bundle as npy.",
            ],
        },
        {
            "workflow_target": PION_DISPERSION_WORKFLOW_ID,
            "task_type": "pion_dispersion",
            "label": "Pion dispersion from gauge",
            "summary": "Gauge -> Clover -> point source -> grounded 9-momentum family or subset -> npy correlator.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "source_type", "accepted_values": ["point"]},
                {"field_name": "sink_type", "accepted_values": ["local"]},
                {"field_name": "momentum_projection", "accepted_values": ["explicit"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=gauge.",
                "Keep source_type=point and sink_type=local.",
                "Use momentum_projection=explicit with a subset of the grounded 9-momentum family.",
                "Do not request gauge fixing in this family.",
            ],
        },
        {
            "workflow_target": MESON_SPEC_WORKFLOW_ID,
            "task_type": "meson_spec",
            "label": "Meson spectroscopy from gauge",
            "summary": "Gauge -> Clover -> wall source -> fixed gamma5/gamma4gamma5 insertion family -> grounded |p|^2<=9 momentum family -> npy correlator tensor.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "source_type", "accepted_values": ["wall"]},
                {"field_name": "sink_type", "accepted_values": ["local"]},
                {"field_name": "momentum_projection", "accepted_values": ["explicit"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=gauge.",
                "Keep source_type=wall and sink_type=local.",
                "Use momentum_projection=explicit with momenta inside the grounded |p|^2<=9 family.",
                "Do not request gauge fixing in this family.",
            ],
        },
        {
            "workflow_target": MESON_SPEC_PROPAGATOR_WORKFLOW_ID,
            "task_type": "meson_spec",
            "label": "Meson spectroscopy from existing propagators",
            "summary": "Existing wall-source propagator files -> fixed gamma5/gamma4gamma5 insertion family -> grounded |p|^2<=9 momentum family -> npy correlator tensor.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["propagator"]},
                {"field_name": "has_existing_propagators", "accepted_values": [True]},
                {"field_name": "source_type", "accepted_values": ["wall"]},
                {"field_name": "sink_type", "accepted_values": ["local"]},
                {"field_name": "momentum_projection", "accepted_values": ["explicit"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=propagator and provide propagator_paths plus source_timeslices.",
                "Keep source_type=wall and sink_type=local.",
                "Use momentum_projection=explicit with momenta inside the grounded |p|^2<=9 family.",
                "Keep gauge_fixed=false to stay aligned with the grounded local mesonspec path.",
            ],
        },
        {
            "workflow_target": RHO_VECTOR_WORKFLOW_ID,
            "task_type": "rho_vector",
            "label": "Rho/vector meson two-point from gauge",
            "summary": "Gauge -> Clover -> wall source -> local sink -> fixed spatial gamma_i family -> zero momentum -> npy correlator tensor.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "source_type", "accepted_values": ["wall"]},
                {"field_name": "sink_type", "accepted_values": ["local"]},
                {"field_name": "momentum_projection", "accepted_values": ["zero"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=gauge.",
                "Keep source_type=wall and sink_type=local.",
                "Keep the fixed gamma_i family ['gamma1_gamma1','gamma2_gamma2','gamma3_gamma3'].",
                "Keep momentum_projection=zero with momenta=[[0,0,0]].",
            ],
        },
        {
            "workflow_target": RHO_VECTOR_PROPAGATOR_WORKFLOW_ID,
            "task_type": "rho_vector",
            "label": "Rho/vector meson two-point from existing propagators",
            "summary": "Existing wall-source propagator files -> fixed spatial gamma_i family -> zero momentum -> npy correlator tensor.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["propagator"]},
                {"field_name": "has_existing_propagators", "accepted_values": [True]},
                {"field_name": "source_type", "accepted_values": ["wall"]},
                {"field_name": "sink_type", "accepted_values": ["local"]},
                {"field_name": "momentum_projection", "accepted_values": ["zero"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=propagator and provide propagator_paths plus source_timeslices.",
                "Keep source_type=wall and sink_type=local.",
                "Keep the fixed gamma_i family ['gamma1_gamma1','gamma2_gamma2','gamma3_gamma3'].",
                "Keep momentum_projection=zero with momenta=[[0,0,0]] and gauge_fixed=false.",
            ],
        },
        {
            "workflow_target": PROTON_2PT_WORKFLOW_ID,
            "task_type": "proton_2pt",
            "label": "Proton two-point from gauge",
            "summary": "Gauge -> Clover -> stout-smear + multigrid -> wall source -> local sink -> zero momentum -> npy correlator.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "source_type", "accepted_values": ["wall"]},
                {"field_name": "sink_type", "accepted_values": ["local"]},
                {"field_name": "momentum_projection", "accepted_values": ["zero"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=gauge.",
                "Keep source_type=wall, sink_type=local, and momentum_projection=zero.",
                "Do not request gauge fixing in this family.",
                "Write the correlator as npy.",
            ],
        },
        {
            "workflow_target": PROTON_2PT_PROPAGATOR_WORKFLOW_ID,
            "task_type": "proton_2pt",
            "label": "Proton two-point from existing propagators",
            "summary": "Existing wall-source propagator files -> parity-projected zero-momentum proton contraction -> npy correlator.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["propagator"]},
                {"field_name": "has_existing_propagators", "accepted_values": [True]},
                {"field_name": "source_type", "accepted_values": ["wall"]},
                {"field_name": "sink_type", "accepted_values": ["local"]},
                {"field_name": "momentum_projection", "accepted_values": ["zero"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=propagator and provide propagator_paths.",
                "Keep source_type=wall, sink_type=local, and momentum_projection=zero.",
                "Keep gauge_fixed=false to stay aligned with the grounded local proton wall-source path.",
                "Write the correlator as npy.",
            ],
        },
        {
            "workflow_target": QUARK_PROPAGATOR_WORKFLOW_ID,
            "task_type": "quark_propagator",
            "label": "Quark propagator from gauge",
            "summary": "Gauge -> stout-smear + getDirac -> point source at [0,0,0,t_src] -> HDF5 propagator.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "source_type", "accepted_values": ["point"]},
                {"field_name": "sink_type", "accepted_values": ["propagator"]},
                {"field_name": "momentum_projection", "accepted_values": ["none"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["hdf5"]},
            ],
            "adjustments": [
                "Use start_from=gauge.",
                "Keep source_type=point at the fixed spatial origin [0,0,0].",
                "Keep sink_type=propagator and momentum_projection=none.",
                "Do not request gauge fixing in this family.",
                "Write the propagator as HDF5.",
            ],
        },
        {
            "workflow_target": QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID,
            "task_type": "quark_propagator",
            "label": "Gaussian-shell quark propagator from gauge",
            "summary": "Gauge -> point-source seed propagator -> gaussianSmear(2.0, 5) -> getClover/invertPropagator -> HDF5 propagator.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "source_type", "accepted_values": ["point"]},
                {"field_name": "sink_type", "accepted_values": ["propagator"]},
                {"field_name": "momentum_projection", "accepted_values": ["none"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["hdf5"]},
                {"field_name": "source_smearing_kind", "accepted_values": ["gaussian_shell"]},
            ],
            "adjustments": [
                "Use start_from=gauge.",
                "Keep source_type=point at the fixed spatial origin [0,0,0].",
                "Keep sink_type=propagator and momentum_projection=none.",
                "Use the fixed Gaussian shell-source branch with rho=2.0 and n_steps=5.",
                "Do not request gauge fixing in this family.",
                "Write the propagator as HDF5.",
            ],
        },
        {
            "workflow_target": APE_SMEAR_WORKFLOW_ID,
            "task_type": "ape_smear",
            "label": "APE-smeared gauge from gauge",
            "summary": "Gauge -> gauge.copy() -> apeSmearChroma(1, 2.5, 4) -> npy smeared-gauge artifact.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "gauge_format", "accepted_values": ["chroma_qio"]},
                {"field_name": "source_type", "accepted_values": ["none"]},
                {"field_name": "sink_type", "accepted_values": ["gauge"]},
                {"field_name": "momentum_projection", "accepted_values": ["none"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=gauge and provide a Chroma/QIO gauge path.",
                "Do not request propagator input, source/sink variants, or momentum projection in this family.",
                "Keep the narrow local APE path: apeSmearChroma(1, 2.5, 4).",
                "Write the smeared gauge as npy.",
            ],
        },
        {
            "workflow_target": HYP_SMEAR_WORKFLOW_ID,
            "task_type": "hyp_smear",
            "label": "HYP-smeared gauge from gauge",
            "summary": "Gauge -> gauge.copy() -> hypSmear(1, 0.75, 0.6, 0.3, 4) -> npy smeared-gauge artifact.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "gauge_format", "accepted_values": ["chroma_qio"]},
                {"field_name": "source_type", "accepted_values": ["none"]},
                {"field_name": "sink_type", "accepted_values": ["gauge"]},
                {"field_name": "momentum_projection", "accepted_values": ["none"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=gauge and provide a Chroma/QIO gauge path.",
                "Do not request propagator input, source/sink variants, or momentum projection in this family.",
                "Keep the narrow local HYP path: hypSmear(1, 0.75, 0.6, 0.3, 4).",
                "Write the smeared gauge as npy.",
            ],
        },
        {
            "workflow_target": STOUT_SMEAR_WORKFLOW_ID,
            "task_type": "stout_smear",
            "label": "Stout-smeared gauge from gauge",
            "summary": "Gauge -> gauge.copy() -> stoutSmear(1, 0.241, 3) -> npy smeared-gauge artifact.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "gauge_format", "accepted_values": ["chroma_qio"]},
                {"field_name": "source_type", "accepted_values": ["none"]},
                {"field_name": "sink_type", "accepted_values": ["gauge"]},
                {"field_name": "momentum_projection", "accepted_values": ["none"]},
                {"field_name": "gauge_fixed", "accepted_values": [False]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=gauge and provide a Chroma/QIO gauge path.",
                "Do not request propagator input, source/sink variants, or momentum projection in this family.",
                "Keep the narrow local stout path: stoutSmear(1, 0.241, 3).",
                "Write the smeared gauge as npy.",
            ],
        },
        {
            "workflow_target": WILSON_FLOW_WORKFLOW_ID,
            "task_type": "wilson_flow",
            "label": "Wilson flow energy history from gauge",
            "summary": "Gauge -> gauge.copy() -> wilsonFlowChroma(flow_steps, flow_epsilon) -> npy energy-history artifact.",
            "retry_fields": [
                {"field_name": "start_from", "accepted_values": ["gauge"]},
                {"field_name": "has_existing_propagators", "accepted_values": [False]},
                {"field_name": "gauge_format", "accepted_values": ["chroma_qio"]},
                {"field_name": "correlator_output_format", "accepted_values": ["npy"]},
            ],
            "adjustments": [
                "Use start_from=gauge and provide a Chroma/QIO gauge path.",
                "Set flow_steps and flow_epsilon explicitly.",
                "Do not request propagator input, source/sink variants, or momentum projection in this family.",
                "Write the energy history as npy.",
            ],
        },
    ]


def _nearby_supported_workflows_for_target_id(target_id: str | None, draft: Pion2ptTaskDraft) -> list[dict]:
    catalog = _supported_workflow_catalog()
    by_workflow = {item["workflow_target"]: item for item in catalog}
    if target_id == PION_TARGET_ID:
        workflows = [PION_2PT_WORKFLOW_ID, PION_2PT_PROPAGATOR_WORKFLOW_ID]
        if draft.start_from == "propagator" or draft.has_existing_propagators:
            workflows = [PION_2PT_PROPAGATOR_WORKFLOW_ID, PION_2PT_WORKFLOW_ID]
        return [by_workflow[item] for item in workflows if item in by_workflow]
    if target_id == PION_PCAC_TARGET_ID:
        workflows = [PION_PCAC_WORKFLOW_ID, PION_PCAC_PROPAGATOR_WORKFLOW_ID]
        if draft.start_from == "propagator" or draft.has_existing_propagators:
            workflows = [PION_PCAC_PROPAGATOR_WORKFLOW_ID, PION_PCAC_WORKFLOW_ID]
        return [by_workflow[item] for item in workflows if item in by_workflow]
    if target_id == PION_DISPERSION_TARGET_ID:
        return [by_workflow[PION_DISPERSION_WORKFLOW_ID]] if PION_DISPERSION_WORKFLOW_ID in by_workflow else []
    if target_id == MESON_SPEC_TARGET_ID:
        return [by_workflow[MESON_SPEC_WORKFLOW_ID]] if MESON_SPEC_WORKFLOW_ID in by_workflow else []
    if target_id == RHO_TARGET_ID:
        workflows = [RHO_VECTOR_WORKFLOW_ID, RHO_VECTOR_PROPAGATOR_WORKFLOW_ID, MESON_SPEC_WORKFLOW_ID, PION_2PT_WORKFLOW_ID, PION_DISPERSION_WORKFLOW_ID]
        if draft.start_from == "propagator" or draft.has_existing_propagators:
            workflows = [RHO_VECTOR_PROPAGATOR_WORKFLOW_ID, RHO_VECTOR_WORKFLOW_ID, MESON_SPEC_WORKFLOW_ID, PION_2PT_WORKFLOW_ID, PION_DISPERSION_WORKFLOW_ID]
        return [by_workflow[item] for item in workflows if item in by_workflow]
    if target_id == PROTON_TARGET_ID:
        workflows = [PROTON_2PT_WORKFLOW_ID, PROTON_2PT_PROPAGATOR_WORKFLOW_ID]
        if draft.start_from == "propagator" or draft.has_existing_propagators:
            workflows = [PROTON_2PT_PROPAGATOR_WORKFLOW_ID, PROTON_2PT_WORKFLOW_ID]
        return [by_workflow[item] for item in workflows if item in by_workflow]
    if target_id == NEUTRON_TARGET_ID:
        workflows = [PROTON_2PT_WORKFLOW_ID, PROTON_2PT_PROPAGATOR_WORKFLOW_ID]
        if draft.start_from == "propagator" or draft.has_existing_propagators:
            workflows = [PROTON_2PT_PROPAGATOR_WORKFLOW_ID, PROTON_2PT_WORKFLOW_ID]
        return [by_workflow[item] for item in workflows if item in by_workflow]
    if target_id == QUARK_PROPAGATOR_TARGET_ID:
        workflows = [QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID]
        if draft.source_smearing_kind == "gaussian_shell":
            workflows = [QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID, QUARK_PROPAGATOR_WORKFLOW_ID]
        return [by_workflow[item] for item in workflows if item in by_workflow]
    if target_id == APE_SMEAR_TARGET_ID:
        return [by_workflow[APE_SMEAR_WORKFLOW_ID]] if APE_SMEAR_WORKFLOW_ID in by_workflow else []
    if target_id == HYP_SMEAR_TARGET_ID:
        return [by_workflow[HYP_SMEAR_WORKFLOW_ID]] if HYP_SMEAR_WORKFLOW_ID in by_workflow else []
    if target_id == STOUT_SMEAR_TARGET_ID:
        return [by_workflow[STOUT_SMEAR_WORKFLOW_ID]] if STOUT_SMEAR_WORKFLOW_ID in by_workflow else []
    if target_id == WILSON_FLOW_TARGET_ID:
        return [by_workflow[WILSON_FLOW_WORKFLOW_ID]] if WILSON_FLOW_WORKFLOW_ID in by_workflow else []
    if target_id == BARYON_UNSPECIFIED_TARGET_ID:
        return [by_workflow[PROTON_2PT_WORKFLOW_ID]] if PROTON_2PT_WORKFLOW_ID in by_workflow else []
    if target_id == HADRON_UNSPECIFIED_TARGET_ID:
        return [
            by_workflow[item]
            for item in (
                PION_2PT_WORKFLOW_ID,
                PION_DISPERSION_WORKFLOW_ID,
                MESON_SPEC_WORKFLOW_ID,
                RHO_VECTOR_WORKFLOW_ID,
                PROTON_2PT_WORKFLOW_ID,
            )
            if item in by_workflow
        ]
    if target_id == MESON_UNSPECIFIED_TARGET_ID:
        return [
            by_workflow[item]
            for item in (
                PION_2PT_WORKFLOW_ID,
                PION_2PT_PROPAGATOR_WORKFLOW_ID,
                PION_PCAC_WORKFLOW_ID,
                PION_PCAC_PROPAGATOR_WORKFLOW_ID,
                PION_DISPERSION_WORKFLOW_ID,
                MESON_SPEC_WORKFLOW_ID,
            )
            if item in by_workflow
        ]
    return catalog


def _nearby_supported_workflows(physics: PhysicsTargetArtifact, draft: Pion2ptTaskDraft) -> list[dict]:
    return _nearby_supported_workflows_for_target_id(_resolved_target_id(physics), draft)


def _format_retry_value(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        if all(not isinstance(item, list) for item in value):
            return " ".join(str(item) for item in value)
        return " ".join("[" + ",".join(str(part) for part in item) + "]" for item in value if isinstance(item, list))
    return str(value)


def _unsupported_scope_for_field(field_name: str | None) -> str:
    if field_name in {
        "confirmed_target_id",
        "task_type",
        "source_type",
        "sink_type",
        "gamma_insertions",
        "momentum_projection",
        "momenta",
        "source_timeslices",
        "gauge_fixed",
    }:
        return "physics"
    if field_name in {
        "start_from",
        "has_existing_propagators",
        "gauge_format",
        "propagator_format",
        "fermion_action",
        "mass",
        "xi_0",
        "nu",
        "coeff_t",
        "coeff_r",
        "solver_tol",
        "solver_maxiter",
        "multigrid_blocks",
        "stout_smear_steps",
        "stout_smear_rho",
        "stout_smear_ndim",
        "flow_steps",
        "flow_epsilon",
        "workflow_id",
        "script_style",
    }:
        return "implementation"
    if field_name in {
        "gauge_path",
        "propagator_paths",
        "lattice_size",
        "grid_size",
        "correlator_output_path",
        "resource_path",
        "cluster_launch",
        "script_output_path",
    }:
        return "runtime"
    return "unknown"


def _scope_title(scope: str) -> str:
    return {
        "physics": "Physics",
        "implementation": "Implementation",
        "runtime": "Runtime",
    }.get(scope, "Unknown")


def _build_retry_command(
    *,
    config: RunConfig,
    session_path: Path | None,
    script_output_path: str | None,
    assignments: list[tuple[str, object]],
) -> str | None:
    effective_session_path = session_path or _effective_session_path(config, script_output_path)
    if effective_session_path is None or not assignments:
        return None
    output_path = _effective_output_path(config, script_output_path)
    assignment_tokens: list[str] = []
    for field_name, value in assignments:
        if field_name == "confirmed_target_id":
            assignment_tokens.append(_reply_argument_token(str(value)))
        else:
            assignment_tokens.append(_set_assignment_token(field_name, _format_retry_value(value)))
    command_parts = [
        "PYTHONPATH=src python3 -m pyquda_agent.cli run",
        json.dumps(config.task_description),
        f"--resume-session {str(effective_session_path)!r}",
        *assignment_tokens,
        *_continuation_flag_parts(config),
        f"--output {str(output_path)!r}",
        f"--pyquda-repo {str(config.pyquda_repo)!r}",
    ]
    return " ".join(command_parts)


def _unsupported_retry_suggestions(
    *,
    config: RunConfig,
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    nearby_workflows: list[dict],
    session_path: Path | None,
    script_output_path: str | None,
) -> list[dict]:
    suggestions: list[dict] = []
    resolved_target_id = _resolved_target_id(physics)
    resolved_task_type = _target_task_type_hint(resolved_target_id)
    confirmed_target = physics.confirmed_interpretation is not None
    for workflow in nearby_workflows:
        specs = workflow.get("retry_fields") or []
        conflicting_fields: list[dict] = []
        deterministic_assignments: list[tuple[str, object]] = []
        variant_fields: list[dict] = []
        workflow_task_type = workflow.get("task_type")
        needs_target_switch = confirmed_target and (
            resolved_target_id in {NEUTRON_TARGET_ID} or (
                resolved_task_type is not None
                and workflow_task_type is not None
                and workflow_task_type != resolved_task_type
            )
        )
        if needs_target_switch:
            reply_value = _workflow_reply_value(workflow.get("task_type"))
            if reply_value:
                conflicting_fields.append(
                    {
                        "field_name": "confirmed_target_id",
                        "current_value": resolved_target_id,
                        "accepted_values": [reply_value],
                        "scope": "physics",
                    }
                )
                deterministic_assignments.append(("confirmed_target_id", reply_value))
        for spec in specs:
            field_name = spec.get("field_name")
            accepted_values = list(spec.get("accepted_values") or [])
            if not field_name or not accepted_values:
                continue
            actual = getattr(draft, field_name, None)
            if actual in (None, [], {}):
                if len(accepted_values) == 1:
                    deterministic_assignments.append((field_name, accepted_values[0]))
                else:
                    variant_fields.append(
                        {
                            "field_name": field_name,
                            "current_value": actual,
                            "accepted_values": accepted_values,
                            "required": True,
                            "source": "missing",
                        }
                    )
                continue
            if actual in accepted_values:
                continue
            conflicting_fields.append(
                {
                    "field_name": field_name,
                    "current_value": actual,
                    "accepted_values": accepted_values,
                    "scope": _unsupported_scope_for_field(field_name),
                }
            )
            if len(accepted_values) == 1:
                deterministic_assignments.append((field_name, accepted_values[0]))
            else:
                variant_fields.append(
                        {
                            "field_name": field_name,
                            "current_value": actual,
                            "accepted_values": accepted_values,
                            "required": False,
                            "source": "conflict",
                            "scope": _unsupported_scope_for_field(field_name),
                        }
                    )

        conflicting_field_names = {item["field_name"] for item in conflicting_fields if item.get("field_name")}
        variant_field_names = {item["field_name"] for item in variant_fields if item.get("field_name")}
        workflow_fixed_assignments = [
            {"field_name": field_name, "value": value}
            for field_name, value in deterministic_assignments
            if field_name not in conflicting_field_names and field_name not in variant_field_names
        ]
        user_change_count = len(conflicting_field_names | variant_field_names)

        retry_command = None
        variant_retry_commands: list[dict] = []
        if not variant_fields:
            retry_command = _build_retry_command(
                config=config,
                session_path=session_path,
                script_output_path=script_output_path,
                assignments=deterministic_assignments,
            )
        elif len(variant_fields) == 1:
            variant = variant_fields[0]
            for value in variant["accepted_values"]:
                command = _build_retry_command(
                    config=config,
                    session_path=session_path,
                    script_output_path=script_output_path,
                    assignments=[*deterministic_assignments, (variant["field_name"], value)],
                )
                if command is not None:
                    variant_retry_commands.append(
                        {
                            "field_name": variant["field_name"],
                            "accepted_value": value,
                            "scope": variant.get("scope"),
                            "command": command,
                        }
                    )

        scope_changes = {
            "physics": [],
            "implementation": [],
            "runtime": [],
        }
        for field_name, value in deterministic_assignments:
            if field_name and field_name in conflicting_field_names:
                rendered = f"{field_name}={_format_retry_value(value)}"
                scope = _unsupported_scope_for_field(field_name)
                if scope in scope_changes and rendered not in scope_changes[scope]:
                    scope_changes[scope].append(rendered)
        for variant in variant_fields:
            field_name = variant.get("field_name")
            accepted_values = list(variant.get("accepted_values") or [])
            if not field_name or not accepted_values:
                continue
            rendered_values = ", ".join(_format_retry_value(value) for value in accepted_values)
            rendered = f"{field_name} in {{{rendered_values}}}"
            scope = _unsupported_scope_for_field(field_name)
            if scope in scope_changes and rendered not in scope_changes[scope]:
                scope_changes[scope].append(rendered)
        scope_breakdown = {
            scope: {
                "title": _scope_title(scope),
                "changes": list(changes),
            }
            for scope, changes in scope_changes.items()
            if changes
        }
        primary_scope = next((scope for scope in ("physics", "implementation", "runtime") if scope_changes[scope]), "unknown")
        if not conflicting_field_names and not variant_fields:
            summary = f"Nearest grounded path already aligns with {workflow['workflow_target']}; only missing values need to be supplied."
        elif user_change_count == 1:
            change = next(
                (
                    item
                    for scope in ("physics", "implementation", "runtime")
                    for item in scope_changes[scope]
                ),
                None,
            )
            if change:
                summary = f"Change {change} to align with {workflow['workflow_target']}."
            else:
                summary = f"Make one user-side change to align with {workflow['workflow_target']}."
        else:
            rendered_changes = [
                item
                for scope in ("physics", "implementation", "runtime")
                for item in scope_changes[scope]
            ]
            if rendered_changes:
                summary = (
                    f"Change {user_change_count} user-specified fields to align with {workflow['workflow_target']}: "
                    + ", ".join(rendered_changes)
                    + "."
                )
            else:
                summary = f"Change {user_change_count} user-specified fields to align with {workflow['workflow_target']}."

        repair_mode = "manual_review"
        if retry_command:
            repair_mode = "copyable_now"
        elif variant_retry_commands:
            repair_mode = "choice_required"

        suggestions.append(
            {
                "workflow_target": workflow["workflow_target"],
                "label": workflow["label"],
                "conflicting_fields": conflicting_fields,
                "deterministic_assignments": [
                    {"field_name": field_name, "value": value} for field_name, value in deterministic_assignments
                ],
                "workflow_fixed_assignments": workflow_fixed_assignments,
                "variant_fields": variant_fields,
                "required_change_count": user_change_count,
                "retry_command": retry_command,
                "variant_retry_commands": variant_retry_commands,
                "primary_scope": primary_scope,
                "scope_breakdown": scope_breakdown,
                "summary": summary,
                "repair_mode": repair_mode,
            }
        )
    return suggestions


def _shortest_fix_summary(retry_suggestions: list[dict]) -> dict | None:
    if not retry_suggestions:
        return None

    ranked = sorted(
        (item for item in retry_suggestions if isinstance(item, dict)),
        key=lambda item: (
            1
            if any(
                field.get("field_name") == "confirmed_target_id"
                for field in (
                    list(item.get("conflicting_fields") or [])
                    + list(item.get("variant_fields") or [])
                )
                if isinstance(field, dict)
            )
            else 0,
            int(item.get("required_change_count") or 0),
            0 if item.get("retry_command") else 1,
            len(item.get("variant_retry_commands") or []),
            str(item.get("workflow_target") or ""),
        ),
    )
    chosen = ranked[0]
    workflow_target = chosen.get("workflow_target")
    label = chosen.get("label")
    deterministic_assignments = list(chosen.get("deterministic_assignments") or [])
    workflow_fixed_assignments = list(chosen.get("workflow_fixed_assignments") or [])
    variant_fields = list(chosen.get("variant_fields") or [])
    required_change_count = int(chosen.get("required_change_count") or 0)
    conflicting_field_names = {item.get("field_name") for item in chosen.get("conflicting_fields") or [] if item.get("field_name")}

    change_lines: list[str] = []
    scope_changes = {
        "physics": [],
        "implementation": [],
        "runtime": [],
    }
    for item in deterministic_assignments:
        field_name = item.get("field_name")
        value = item.get("value")
        if field_name and field_name in conflicting_field_names:
            rendered = f"{field_name}={_format_retry_value(value)}"
            change_lines.append(rendered)
            scope = _unsupported_scope_for_field(field_name)
            if scope in scope_changes:
                scope_changes[scope].append(rendered)
    for item in variant_fields:
        field_name = item.get("field_name")
        accepted_values = item.get("accepted_values") or []
        if field_name and accepted_values:
            rendered = ", ".join(_format_retry_value(value) for value in accepted_values)
            line = f"{field_name} in {{{rendered}}}"
            change_lines.append(line)
            scope = _unsupported_scope_for_field(field_name)
            if scope in scope_changes:
                scope_changes[scope].append(line)

    if not change_lines:
        summary = "No grounded correction path could be summarized automatically."
    elif required_change_count == 1:
        summary = f"Nearest grounded path: {workflow_target}. Change {change_lines[0]}."
    else:
        summary = (
            f"Nearest grounded path: {workflow_target}. Change {required_change_count} fields: "
            + ", ".join(change_lines)
            + "."
        )
    if workflow_fixed_assignments:
        autofill_lines = ", ".join(
            f"{item['field_name']}={_format_retry_value(item['value'])}"
            for item in workflow_fixed_assignments
            if item.get("field_name")
        )
        if autofill_lines:
            summary += f" The retry command also pins workflow-fixed fields automatically: {autofill_lines}."

    primary_scope = next((scope for scope in ("physics", "implementation", "runtime") if scope_changes[scope]), "unknown")
    if primary_scope != "unknown":
        summary += f" Primary mismatch category: {primary_scope}."

    scope_breakdown = {
        scope: {
            "title": _scope_title(scope),
            "changes": list(changes),
        }
        for scope, changes in scope_changes.items()
        if changes
    }

    return {
        "workflow_target": workflow_target,
        "label": label,
        "required_change_count": required_change_count,
        "changes": change_lines,
        "primary_scope": primary_scope,
        "scope_breakdown": scope_breakdown,
        "summary": summary,
        "workflow_fixed_assignments": workflow_fixed_assignments,
        "retry_command": chosen.get("retry_command"),
        "variant_retry_commands": chosen.get("variant_retry_commands") or [],
    }


def _scope_breakdown_summary(scope_breakdown: dict | None) -> dict | None:
    if not isinstance(scope_breakdown, dict) or not scope_breakdown:
        return None
    ordered_items: list[dict] = []
    sentence_parts: list[str] = []
    for scope in ("physics", "implementation", "runtime"):
        item = scope_breakdown.get(scope)
        if not isinstance(item, dict):
            continue
        changes = [str(change) for change in item.get("changes") or [] if change]
        if not changes:
            continue
        title = str(item.get("title") or _scope_title(scope))
        ordered_items.append(
            {
                "scope": scope,
                "title": title,
                "changes": changes,
                "summary": f"{title}: {', '.join(changes)}",
            }
        )
        sentence_parts.append(f"{title}: {', '.join(changes)}")
    if not ordered_items:
        return None
    return {
        "items": ordered_items,
        "sentence": "Missing conditions by scope: " + "; ".join(sentence_parts) + ".",
    }


def _unsupported_repair_hint(shortest_fix: dict | None) -> dict | None:
    if not isinstance(shortest_fix, dict) or not shortest_fix:
        return None
    retry_command = shortest_fix.get("retry_command")
    variant_retry_commands = list(shortest_fix.get("variant_retry_commands") or [])
    workflow_target = shortest_fix.get("workflow_target")
    if isinstance(retry_command, str) and retry_command:
        return {
            "mode": "copyable_now",
            "summary": (
                f"Fastest grounded retry: use the copyable command for {workflow_target} as-is."
                if workflow_target
                else "Fastest grounded retry: use the copyable command as-is."
            ),
            "copyable_now": True,
            "choice_required": False,
        }
    if variant_retry_commands:
        field_name = next((item.get("field_name") for item in variant_retry_commands if item.get("field_name")), None)
        accepted_values: list[str] = []
        for item in variant_retry_commands:
            value = item.get("accepted_value")
            rendered = _format_retry_value(value)
            if rendered not in accepted_values:
                accepted_values.append(rendered)
        choice_summary = ", ".join(accepted_values)
        if field_name and accepted_values:
            summary = f"Fastest grounded retry needs one explicit choice first: choose {field_name} from {{{choice_summary}}}."
        else:
            summary = "Fastest grounded retry needs one explicit choice first before a copyable command can be selected."
        return {
            "mode": "choice_required",
            "summary": summary,
            "copyable_now": False,
            "choice_required": True,
            "choice_field": field_name,
            "choice_values": accepted_values,
        }
    return {
        "mode": "manual_review",
        "summary": "No direct retry command could be synthesized automatically; review the nearby grounded workflows and align the conflicting fields manually.",
        "copyable_now": False,
        "choice_required": False,
    }


def _clarification_gap_summary(*, missing: list[str], questions: list[dict]) -> dict | None:
    if not missing or missing == ["confirmed_target_id"]:
        return None
    scoped_fields: dict[str, list[str]] = {
        "physics": [],
        "implementation": [],
        "runtime": [],
    }
    question_scope_map: dict[str, str] = {}
    for item in questions:
        field_name = item.get("field_name")
        if not field_name:
            continue
        raw_scope = str(item.get("scope") or "")
        if raw_scope in scoped_fields:
            question_scope_map[str(field_name)] = raw_scope
            continue
        raw_category = str(item.get("category") or "")
        if raw_category in scoped_fields:
            question_scope_map[str(field_name)] = raw_category

    fields, batch_fields = _clarification_display_fields(missing=missing, questions=questions)
    for field_name in fields:
        scope = question_scope_map.get(field_name) or _unsupported_scope_for_field(field_name)
        if scope in scoped_fields and field_name not in scoped_fields[scope]:
            scoped_fields[scope].append(field_name)
    ordered_items: list[dict] = []
    sentence_parts: list[str] = []
    for scope in ("physics", "implementation", "runtime"):
        fields_for_scope = scoped_fields[scope]
        if not fields_for_scope:
            continue
        title = _scope_title(scope)
        summary = f"{title}: {', '.join(fields_for_scope)}"
        ordered_items.append(
            {
                "scope": scope,
                "title": title,
                "fields": fields_for_scope,
                "summary": summary,
            }
        )
        sentence_parts.append(summary)
    if not ordered_items:
        return None
    sentence = "Current missing conditions by scope: " + "; ".join(sentence_parts) + "."
    if batch_fields and len(batch_fields) < len(missing):
        sentence += " Additional fields remain after this batch."
    return {
        "items": ordered_items,
        "sentence": sentence,
        "batch_fields": batch_fields,
        "missing_fields_total": len(missing),
        "batch_truncated": bool(batch_fields and len(batch_fields) < len(missing)),
    }


def _clarification_display_fields(*, missing: list[str], questions: list[dict]) -> tuple[list[str], list[str]]:
    batch_fields = [str(item.get("field_name")) for item in questions if item.get("field_name")]
    fields = list(batch_fields) or list(missing)
    if batch_fields:
        for field_name in list(batch_fields):
            definition = FIELD_TO_GROUP.get(field_name)
            if definition is None:
                continue
            for grouped_field in definition.fields:
                if grouped_field in missing and grouped_field not in fields:
                    fields.append(grouped_field)
    return fields, batch_fields


def _build_clarification_batch_card(
    *,
    result: dict,
    missing: list[str],
    questions: list[dict],
    clarification_status: dict,
    clarification_gap_summary: dict | None,
) -> dict | None:
    if result.get("status") != "needs_input":
        return None
    if clarification_status.get("mode") != "task_fields":
        return None
    display_fields, batch_fields = _clarification_display_fields(missing=missing, questions=questions)
    if not batch_fields:
        return None
    remaining_fields = [field_name for field_name in missing if field_name not in display_fields]
    field_groups = clarification_status.get("field_groups") or []
    return {
        "mode": "task_fields",
        "current_batch_fields": batch_fields,
        "current_batch_display_fields": display_fields,
        "current_batch_count": len(batch_fields),
        "current_batch_display_count": len(display_fields),
        "remaining_after_batch_count": len(remaining_fields),
        "remaining_after_batch_preview": remaining_fields[:5],
        "recommended_answer_mode": clarification_status.get("recommended_answer_mode"),
        "grouped_set_available": any(item.get("set_example") for item in field_groups),
        "field_group_ids": [item.get("group_id") for item in field_groups if item.get("group_id")],
        "gap_summary": clarification_gap_summary,
        "next_milestone": "further_clarification" if remaining_fields else "complete_generation",
    }


def _build_unsupported_guidance(
    *,
    config: RunConfig,
    result: dict,
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    workflow_match: WorkflowMatchResult,
    session_path: Path | None,
) -> dict | None:
    if result.get("status") != "unsupported":
        return None
    reasons: list[str] = []
    reasons.extend(workflow_match.unsupported_reasons or [])
    reasons.extend(draft.unsupported_reasons or [])
    nearby = _nearby_supported_workflows(physics, draft)
    retry_suggestions = _unsupported_retry_suggestions(
        config=config,
        physics=physics,
        draft=draft,
        nearby_workflows=nearby,
        session_path=session_path,
        script_output_path=draft.script_output_path,
    )
    retry_by_workflow = {
        item.get("workflow_target"): item
        for item in retry_suggestions
        if isinstance(item, dict) and item.get("workflow_target")
    }
    shortest_fix = _shortest_fix_summary(retry_suggestions)
    repair_hint = _unsupported_repair_hint(shortest_fix)
    primary_scope = (shortest_fix or {}).get("primary_scope")
    scope_breakdown_summary = _scope_breakdown_summary((shortest_fix or {}).get("scope_breakdown"))
    if primary_scope == "physics":
        next_step = "Choose one nearby grounded workflow family, confirm the physics-side choices first, then retry the run."
    elif primary_scope == "implementation":
        next_step = "Choose one nearby grounded workflow family, align the implementation-side fields with the grounded PyQUDA path, then retry the run."
    elif primary_scope == "runtime":
        next_step = "Choose one nearby grounded workflow family, fill in the runtime/input-path fields, then retry the run."
    else:
        next_step = "Choose one nearby grounded workflow family, align the conflicting fields, and retry the run."
    if scope_breakdown_summary is not None:
        next_step = f"{next_step} {scope_breakdown_summary['sentence']}"
    if repair_hint is not None:
        next_step = f"{next_step} {repair_hint['summary']}"
    if shortest_fix and shortest_fix.get("workflow_target"):
        nearest_label = shortest_fix.get("label") or shortest_fix["workflow_target"]
        next_step = f"Closest grounded workflow: {nearest_label}. {next_step}"
    return {
        "primary_reason": reasons[0] if reasons else result.get("refusal_reason"),
        "reason_count": len(reasons),
        "all_reasons": reasons,
        "primary_scope": primary_scope,
        "repair_readiness": (repair_hint or {}).get("mode"),
        "repair_hint": repair_hint,
        "nearby_workflow_targets": [item["workflow_target"] for item in nearby],
        "nearby_workflow_guidance": [
            {
                "workflow_target": item["workflow_target"],
                "label": item["label"],
                "summary": item["summary"],
                "adjustments": item.get("adjustments") or [],
                "repair_mode": (retry_by_workflow.get(item["workflow_target"]) or {}).get("repair_mode"),
                "primary_scope": (retry_by_workflow.get(item["workflow_target"]) or {}).get("primary_scope"),
                "conflict_breakdown": (retry_by_workflow.get(item["workflow_target"]) or {}).get("scope_breakdown") or {},
            }
            for item in nearby
        ],
        "retry_suggestions": retry_suggestions,
        "shortest_fix": shortest_fix,
        "shortest_fix_gap_summary": scope_breakdown_summary,
        "nearest_workflow_card": {
            "workflow_target": (shortest_fix or {}).get("workflow_target"),
            "label": (shortest_fix or {}).get("label"),
            "required_change_count": (shortest_fix or {}).get("required_change_count"),
            "primary_scope": primary_scope,
            "summary": (shortest_fix or {}).get("summary"),
            "gap_summary": scope_breakdown_summary,
            "repair_hint": repair_hint,
        }
        if shortest_fix
        else None,
        "next_step": next_step,
    }


def _build_physics_candidate_preview(physics: PhysicsTargetArtifact, *, max_items: int = 4) -> tuple[list[dict], bool]:
    preview: list[dict] = []
    for item in physics.candidate_targets[:max_items]:
        if not isinstance(item, dict):
            continue
        preview.append(
            {
                "target_id": item.get("target_id"),
                "label": item.get("label"),
                "summary": item.get("summary"),
                "confidence": item.get("confidence"),
                "status": item.get("status"),
                "task_type_hint": item.get("task_type_hint"),
            }
        )
    return preview, len(physics.candidate_targets) > max_items


def _build_physics_formula_preview(physics: PhysicsTargetArtifact, *, max_items: int = 4) -> tuple[list[dict], bool]:
    if physics.confirmed_interpretation is not None:
        return [], False
    if len(physics.candidate_targets) <= 1 and len(physics.formula_proposals) <= 1:
        return [], False

    preview: list[dict] = []
    for item in physics.formula_proposals[:max_items]:
        if not isinstance(item, dict):
            continue
        preview.append(
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
    return preview, len(physics.formula_proposals) > max_items


def _build_physics_workflow_preview(
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    *,
    max_items: int = 4,
) -> tuple[list[dict], bool]:
    preview: list[dict] = []
    for item in physics.candidate_targets[:max_items]:
        if not isinstance(item, dict):
            continue
        target_id = item.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            continue
        workflows = _nearby_supported_workflows_for_target_id(target_id, draft)
        preview.append(
            {
                "target_id": target_id,
                "label": item.get("label"),
                "status": item.get("status"),
                "task_type_hint": item.get("task_type_hint"),
                "availability": "grounded" if workflows else "unsupported",
                "grounded_workflow_targets": [workflow.get("workflow_target") for workflow in workflows if workflow.get("workflow_target")],
                "grounded_workflow_labels": [workflow.get("label") for workflow in workflows if workflow.get("label")],
                "grounded_workflow_count": len(workflows),
            }
        )
    return preview, len(physics.candidate_targets) > max_items


def _build_result_summary(
    *,
    config: RunConfig,
    result: dict,
    draft: Pion2ptTaskDraft,
    physics: PhysicsTargetArtifact,
    workflow_match: WorkflowMatchResult,
    missing: list[str],
    questions: list[dict],
    task_artifact: Path | None,
    physics_artifact: Path | None,
    plan_artifact: Path | None,
    session_path: Path | None,
) -> dict:
    runtime_evidence = result.get("runtime_evidence") or {}
    generated_script_probe = runtime_evidence.get("generated_script_probe") or {}
    llm_assistance = physics.llm_assistance or {}
    backend_diagnostic = _build_backend_diagnostic(
        config=config,
        physics=physics,
        result_status=result.get("status"),
        execution_status=result.get("execution_status"),
    )
    selected_backend = llm_assistance.get("selected_backend") or config.backend
    script_path = str(config.output.expanduser().resolve())
    probe_artifact = str(_probe_artifact_path(script_path))
    context_bundle = result.get("context") or {}
    index_provenance = context_bundle.get("index_provenance")
    pending_fields_preview = [item.get("field_name") for item in questions[:5]]
    pending_prompts_preview = [item.get("prompt") for item in questions[:3]]
    pending_categories_preview = [item.get("category") for item in questions[:5]]
    missing_fields_preview = pending_fields_preview or missing[:5]
    pending_question_preview = _pending_question_preview(
        physics=physics,
        draft=draft,
        missing_fields=missing,
        questions=questions,
        script_output_path=draft.script_output_path,
    )
    pending_set_examples = _pending_set_examples(
        physics=physics,
        draft=draft,
        missing_fields=missing,
        questions=questions,
        script_output_path=draft.script_output_path,
    )
    pending_reply_examples = _pending_reply_examples(
        physics=physics,
        draft=draft,
        missing_fields=missing,
        questions=questions,
        script_output_path=draft.script_output_path,
    )
    clarification_status = _build_clarification_status(
        result=result,
        questions=questions,
        missing=missing,
        pending_question_preview=pending_question_preview,
        reply_hint=result.get("reply_hint"),
        set_hint=result.get("set_hint"),
        physics=physics,
        draft=draft,
        script_output_path=draft.script_output_path,
    )
    result["clarification_status"] = clarification_status
    group_set_hint = _group_set_command_hint(
        config=config,
        session_path=session_path,
        script_output_path=draft.script_output_path,
        physics=physics,
        draft=draft,
        missing_fields=missing,
        questions=questions,
        clarification_status=clarification_status,
    )
    result["group_set_hint"] = group_set_hint
    workflow_outcome = _build_workflow_outcome(
        config=config,
        result=result,
        draft=draft,
        physics=physics,
        workflow_match=workflow_match,
        missing=missing,
        questions=questions,
    )
    clarification_batch_card = _build_clarification_batch_card(
        result=result,
        missing=missing,
        questions=questions,
        clarification_status=clarification_status,
        clarification_gap_summary=workflow_outcome.get("clarification_gap_summary"),
    )
    result["clarification_batch_card"] = clarification_batch_card
    workflow_outcome["clarification_batch_card"] = clarification_batch_card
    runtime_diagnostic = _build_runtime_diagnostic(
        result=result,
        workflow_outcome=workflow_outcome,
    )
    physics_candidate_preview, physics_candidate_preview_truncated = _build_physics_candidate_preview(physics)
    physics_formula_preview, physics_formula_preview_truncated = _build_physics_formula_preview(physics)
    physics_workflow_preview, physics_workflow_preview_truncated = _build_physics_workflow_preview(physics, draft)
    result["runtime_diagnostic"] = runtime_diagnostic
    supported_workflows = _supported_workflow_catalog()
    nearby_supported_workflows = _nearby_supported_workflows(physics, draft)
    unsupported_guidance = _build_unsupported_guidance(
        config=config,
        result=result,
        physics=physics,
        draft=draft,
        workflow_match=workflow_match,
        session_path=session_path,
    )
    result["unsupported_guidance"] = unsupported_guidance
    action_queue = _build_action_queue(
        config=config,
        result=result,
        workflow_outcome=workflow_outcome,
        backend_diagnostic=backend_diagnostic,
    )
    primary_action = _primary_action(action_queue)
    workflow_outcome = _synchronize_workflow_outcome_actions(workflow_outcome, primary_action)
    run_overview = _build_run_overview(
        result=result,
        workflow_outcome=workflow_outcome,
        backend_diagnostic=backend_diagnostic,
        runtime_diagnostic=runtime_diagnostic,
        primary_action=primary_action,
    )
    workflow_outcome["action_queue"] = action_queue
    workflow_outcome["primary_action"] = primary_action
    delivery_status = _build_delivery_status(
        result=result,
        workflow_outcome=workflow_outcome,
        primary_action=primary_action,
    )
    product_status = _build_product_status(
        result=result,
        workflow_outcome=workflow_outcome,
    )
    capability_summary = _build_capability_summary(
        result=result,
        workflow_outcome=workflow_outcome,
        delivery_status=delivery_status,
        backend_diagnostic=backend_diagnostic,
        primary_action=primary_action,
    )
    terminal_message = _build_terminal_message(
        result=result,
        workflow_outcome=workflow_outcome,
        delivery_status=delivery_status,
        runtime_diagnostic=runtime_diagnostic,
        primary_action=primary_action,
        action_queue=action_queue,
        unsupported_guidance=unsupported_guidance,
    )
    artifacts = {
        "physics": str(physics_artifact) if physics_artifact else None,
        "task": str(task_artifact) if task_artifact else None,
        "plan": str(plan_artifact) if plan_artifact else None,
        "session": str(session_path) if session_path else result.get("session_artifact"),
        "probe": generated_script_probe.get("artifact_path") or probe_artifact,
        "script": result.get("generation", {}).get("output_path") if isinstance(result.get("generation"), dict) else None,
    }
    if not artifacts["script"] and result.get("status") == "ok":
        artifacts["script"] = script_path
    blocking_reason = _build_blocking_reason(
        run_overview=run_overview,
        delivery_status=delivery_status,
        backend_diagnostic=backend_diagnostic,
        runtime_diagnostic=runtime_diagnostic,
    )
    blocking_reason_detail = _build_blocking_reason_detail(
        run_overview=run_overview,
        delivery_status=delivery_status,
        backend_diagnostic=backend_diagnostic,
        runtime_diagnostic=runtime_diagnostic,
        blocking_reason=blocking_reason,
    )
    inspection_hint = _build_inspection_hint(
        run_overview=run_overview,
        artifacts=artifacts,
    )
    frontend_profile = _build_frontend_profile(
        product_status=product_status,
        run_overview=run_overview,
        capability_summary=capability_summary,
        blocking_reason=blocking_reason,
        blocking_reason_detail=blocking_reason_detail,
        inspection_hint=inspection_hint,
        primary_action=primary_action,
    )
    generation_result = _build_generation_result(delivery_status=delivery_status, workflow_outcome=workflow_outcome)
    execution_result = _build_execution_result(
        delivery_status=delivery_status,
        workflow_outcome=workflow_outcome,
        runtime_diagnostic=runtime_diagnostic,
        probe_hint=result.get("probe_hint"),
        probe_artifact=artifacts.get("probe"),
    )
    execution_closure = _build_execution_closure(
        product_status=product_status,
        workflow_outcome=workflow_outcome,
        delivery_status=delivery_status,
        runtime_diagnostic=runtime_diagnostic or {},
        backend_diagnostic=backend_diagnostic,
        primary_action=primary_action,
        artifacts=artifacts,
    )
    execution_checkpoint = _build_execution_checkpoint(
        product_status=product_status,
        workflow_outcome=workflow_outcome,
        delivery_status=delivery_status,
        execution_closure=execution_closure,
        runtime_diagnostic=runtime_diagnostic or {},
        primary_action=primary_action,
        artifacts=artifacts,
    )
    backend_path = _build_backend_path(
        backend_diagnostic=backend_diagnostic,
        action_queue=action_queue,
        product_status=product_status,
    )
    hpc_handoff = _build_hpc_handoff_summary(
        result=result,
        draft=draft,
        workflow_outcome=workflow_outcome,
        artifacts=artifacts,
    )
    workflow_lifecycle = _build_workflow_lifecycle(
        product_status=product_status,
        run_overview=run_overview,
        generation_result=generation_result,
        execution_result=execution_result,
        primary_action=primary_action,
        artifacts=artifacts,
    )
    external_lookup = physics.external_lookup or {}
    summary = {
        "schema_family": RESULT_SUMMARY_SCHEMA_FAMILY,
        "schema_version": RESULT_SUMMARY_SCHEMA_VERSION,
        "status": result.get("status"),
        "product_status": product_status,
        "physics_target": _resolved_target_id(physics),
        "physics_candidate_preview": physics_candidate_preview,
        "physics_candidate_preview_truncated": physics_candidate_preview_truncated,
        "physics_formula_preview": physics_formula_preview,
        "physics_formula_preview_truncated": physics_formula_preview_truncated,
        "physics_workflow_preview": physics_workflow_preview,
        "physics_workflow_preview_truncated": physics_workflow_preview_truncated,
        "workflow_target": (workflow_match.to_dict() if hasattr(workflow_match, "to_dict") else {}).get("workflow_target"),
        "requested_backend": config.backend,
        "selected_backend": selected_backend,
        "backend_selection_reason": llm_assistance.get("selection_reason"),
        "index_provenance": index_provenance,
        "llm_attempted": bool(llm_assistance.get("attempted")),
        "llm_used": bool(llm_assistance.get("used")),
        "llm_fallback": bool(llm_assistance.get("fallback")),
        "llm_fallback_category": llm_assistance.get("fallback_category"),
        "llm_fallback_detail_category": llm_assistance.get("fallback_detail_category"),
        "llm_fallback_reason": llm_assistance.get("fallback_reason"),
        "llm_codex_preflight_attempted": bool(llm_assistance.get("codex_preflight_attempted")),
        "llm_codex_preflight_status": llm_assistance.get("codex_preflight_status"),
        "llm_codex_preflight_category": llm_assistance.get("codex_preflight_category"),
        "llm_codex_preflight_detail_category": llm_assistance.get("codex_preflight_detail_category"),
        "llm_codex_preflight_reason": llm_assistance.get("codex_preflight_reason"),
        "llm_codex_preflight_skipped": bool(llm_assistance.get("codex_preflight_skipped")),
        "llm_codex_preflight_skip_reason": llm_assistance.get("codex_preflight_skip_reason"),
        "llm_codex_preflight_soft_failed": bool(llm_assistance.get("codex_preflight_soft_failed")),
        "llm_codex_preflight_soft_failure_reason": llm_assistance.get("codex_preflight_soft_failure_reason"),
        "llm_session_backend_memory_considered": bool(llm_assistance.get("session_backend_memory_considered")),
        "llm_session_backend_memory_used": bool(llm_assistance.get("session_backend_memory_used")),
        "llm_session_backend_memory_reason": llm_assistance.get("session_backend_memory_reason"),
        "llm_session_backend_prior_category": llm_assistance.get("session_backend_prior_category"),
        "llm_intent_strategy": llm_assistance.get("intent_strategy"),
        "llm_intent_prompt_profile": llm_assistance.get("intent_prompt_profile"),
        "llm_intent_primary_timeout_seconds": llm_assistance.get("intent_primary_timeout_seconds"),
        "llm_timeout_recovery_attempted": bool(llm_assistance.get("timeout_recovery_attempted")),
        "llm_timeout_recovery_skipped": bool(llm_assistance.get("timeout_recovery_skipped")),
        "llm_timeout_recovery_skip_reason": llm_assistance.get("timeout_recovery_skip_reason"),
        "llm_timeout_recovery_used": bool(llm_assistance.get("timeout_recovery_used")),
        "llm_timeout_recovery_failed": bool(llm_assistance.get("timeout_recovery_failed")),
        "llm_timeout_recovery_trigger_category": llm_assistance.get("timeout_recovery_trigger_category"),
        "llm_timeout_recovery_timeout_seconds": llm_assistance.get("timeout_recovery_timeout_seconds"),
        "llm_timeout_recovery_failure_category": llm_assistance.get("timeout_recovery_failure_category"),
        "llm_timeout_recovery_failure_detail_category": llm_assistance.get("timeout_recovery_failure_detail_category"),
        "backend_diagnostic": backend_diagnostic,
        "runtime_diagnostic": runtime_diagnostic,
        "external_lookup_status": external_lookup.get("status"),
        "external_lookup_attempted": bool(external_lookup.get("attempted")),
        "external_lookup_used": bool(external_lookup.get("used")),
        "external_lookup_enabled": bool(external_lookup.get("enabled")),
        "external_lookup_reason": external_lookup.get("reason"),
        "execution_status": result.get("execution_status"),
        "runtime_level": runtime_evidence.get("runtime_level"),
        "next_action": result.get("next_action"),
        "refusal_reason": result.get("refusal_reason"),
        "supported_workflows": supported_workflows,
        "nearby_supported_workflows": nearby_supported_workflows,
        "unsupported_guidance": unsupported_guidance,
        "missing_fields_count": len(missing),
        "missing_fields_preview": missing_fields_preview,
        "pending_question_count": len(questions),
        "pending_question_fields": pending_fields_preview,
        "pending_question_prompts": pending_prompts_preview,
        "pending_question_categories": pending_categories_preview,
        "pending_question_preview": pending_question_preview,
        "clarification_status": clarification_status,
        "clarification_gap_summary": workflow_outcome.get("clarification_gap_summary"),
        "clarification_batch_card": clarification_batch_card,
        "pending_set_examples": pending_set_examples,
        "pending_group_set_examples": [item.get("set_example") for item in clarification_status.get("field_groups", []) if item.get("set_example")],
        "pending_reply_examples": pending_reply_examples,
        "artifacts": artifacts,
        "blocking_reason": blocking_reason,
        "blocking_reason_detail": blocking_reason_detail,
        "inspection_hint": inspection_hint,
        "resume_hint": result.get("resume_hint"),
        "reply_hint": result.get("reply_hint"),
        "set_hint": result.get("set_hint"),
        "group_set_hint": group_set_hint,
        "probe_hint": result.get("probe_hint"),
        "workflow_outcome": workflow_outcome,
        "delivery_status": delivery_status,
        "generation_result": generation_result,
        "execution_result": execution_result,
        "execution_closure": execution_closure,
        "execution_checkpoint": execution_checkpoint,
        "workflow_lifecycle": workflow_lifecycle,
        "capability_summary": capability_summary,
        "frontend_profile": frontend_profile,
        "terminal_message": terminal_message,
        "action_queue": action_queue,
        "primary_action": primary_action,
        "run_overview": run_overview,
        "backend_path": backend_path,
        "hpc_handoff": hpc_handoff,
        "review_order": [
            "physics",
            "task",
            "plan",
            "session",
            "script",
            "probe",
        ],
    }
    return summary


def _build_workflow_outcome(
    *,
    config: RunConfig,
    result: dict,
    draft: Pion2ptTaskDraft,
    physics: PhysicsTargetArtifact,
    workflow_match: WorkflowMatchResult,
    missing: list[str],
    questions: list[dict],
) -> dict:
    runtime_evidence = result.get("runtime_evidence") or {}
    evidence_levels = runtime_evidence.get("evidence_levels") or {}
    generated_script_probe = runtime_evidence.get("generated_script_probe") or {}
    backend_diagnostic = _build_backend_diagnostic(
        config=config,
        physics=physics,
        result_status=result.get("status"),
        execution_status=result.get("execution_status"),
    )
    generation = result.get("generation") if isinstance(result.get("generation"), dict) else {}
    generated_script_path = generation.get("output_path") or runtime_evidence.get("generated_script_path")
    status = result.get("status")
    generation_succeeded = status == "ok"
    execution_status = result.get("execution_status")
    probe_policy = runtime_evidence.get("probe_policy") or {}
    execution_attempted = bool(probe_policy.get("current_run_attempted"))
    if not execution_attempted and config.runtime_probe and generation_succeeded:
        execution_attempted = bool(generated_script_probe.get("result")) or generated_script_probe.get("status") not in {
            None,
            "requested",
            "not_run",
        }
    execution_succeeded = None
    if execution_attempted and execution_status is not None:
        execution_succeeded = execution_status == "runtime_proved"

    unsupported_reasons: list[str] = []
    unsupported_reasons.extend(workflow_match.unsupported_reasons or [])
    unsupported_reasons.extend(draft.unsupported_reasons or [])

    blockers: list[str] = []
    phase = "planning"
    generation_status = "pending"
    probe_status = "not_applicable"
    next_step = result.get("next_action")
    recommended_command = None
    clarification_gap_summary = None

    if status == "needs_input":
        phase = "clarification"
        generation_status = "blocked_on_input"
        probe_status = "pending_generation" if config.runtime_probe else "not_applicable"
        blockers = (
            ["physics target confirmation required"]
            if physics.confirmed_interpretation is None
            else [item.get("field_name") for item in questions[:5] if item.get("field_name")] or list(missing[:5])
        )
        recommended_command = result.get("reply_hint") or result.get("set_hint") or result.get("resume_hint")
        if physics.confirmed_interpretation is not None:
            clarification_gap_summary = _clarification_gap_summary(missing=missing, questions=questions)
            if clarification_gap_summary is not None:
                next_step = f"{next_step} {clarification_gap_summary['sentence']}"
    elif status == "unsupported":
        phase = "unsupported"
        generation_status = "unsupported"
        probe_status = "not_applicable"
        blockers = unsupported_reasons or ([result.get("refusal_reason")] if result.get("refusal_reason") else [])
        next_step = result.get("refusal_reason")
        recommended_command = result.get("reply_hint") or result.get("set_hint")
    elif status == "dry_run":
        phase = "ready_to_generate"
        generation_status = "dry_run"
        probe_status = "pending_generation" if config.runtime_probe else "not_applicable"
        next_step = "Re-run without --dry-run to emit the grounded script."
        recommended_command = _remove_cli_flag(result.get("resume_hint"), "--dry-run")
    elif status == "ok":
        phase = "generated_and_probed" if config.runtime_probe else "generated"
        generation_status = "generated"
        if config.runtime_probe:
            probe_status = generated_script_probe.get("status") or "requested"
            blockers = list(
                (generated_script_probe.get("result") or {}).get("evidence_levels", {}).get("blockers")
                or evidence_levels.get("blockers")
                or []
            )
            if execution_succeeded is True:
                next_step = "Runtime probe succeeded. Review artifacts or hand off the generated workflow."
            elif execution_succeeded is False:
                if execution_status == "probe_driver_failed" or probe_status == "probe_driver_failed":
                    next_step = _runtime_probe_driver_recommended_fix(
                        artifact_path=generated_script_probe.get("artifact_path")
                    )
                elif execution_status == "runtime_missing" or probe_status == "runtime_missing":
                    next_step = _runtime_environment_recommended_fix(blockers)
                else:
                    next_step = "Inspect the probe blockers and retry after fixing the runtime environment."
                recommended_command = result.get("probe_hint")
            else:
                next_step = "Inspect the probe artifact to determine the current runtime blocker."
                recommended_command = result.get("probe_hint")
        else:
            probe_status = "not_requested"
            blockers = list(evidence_levels.get("blockers") or [])
            next_step = "Run the probe command to collect runtime evidence for the generated script."
            recommended_command = result.get("probe_hint")
    runtime_level = runtime_evidence.get("runtime_level")
    evidence_level = evidence_levels.get("current_level") or runtime_level
    if status != "ok":
        runtime_level = "structurally_grounded"
        evidence_level = "structurally_grounded"
    return {
        "phase": phase,
        "generation_status": generation_status,
        "generation_succeeded": generation_succeeded,
        "execution_attempted": execution_attempted,
        "execution_succeeded": execution_succeeded,
        "execution_status": execution_status,
        "runtime_probe_requested": bool(config.runtime_probe),
        "runtime_probe_status": probe_status,
        "runtime_level": runtime_level,
        "evidence_level": evidence_level,
        "generated_script_path": generated_script_path,
        "generated_script_exists": bool(runtime_evidence.get("generated_script_exists")),
        "blockers": blockers,
        "backend_diagnostic": backend_diagnostic,
        "clarification_gap_summary": clarification_gap_summary,
        "next_step": next_step,
        "recommended_command": recommended_command,
    }


def _backend_result_context_label(*, result_status: str | None, execution_status: str | None, runtime_probe_requested: bool) -> str:
    if result_status == "needs_input":
        return "current rule-based clarification result"
    if result_status == "dry_run":
        return "current grounded dry-run plan"
    if result_status == "unsupported":
        return "current grounded unsupported assessment"
    if result_status == "ok":
        if runtime_probe_requested and execution_status:
            return "current generated script and runtime probe result"
        if runtime_probe_requested:
            return "current generated script and pending runtime probe state"
        return "current generated script result"
    return "current run result"


def _build_backend_diagnostic(
    *,
    config: RunConfig,
    physics: PhysicsTargetArtifact,
    result_status: str | None,
    execution_status: str | None,
) -> dict | None:
    llm_assistance = physics.llm_assistance or {}
    requested_backend = llm_assistance.get("requested_backend") or config.backend
    selected_backend = llm_assistance.get("selected_backend") or config.backend
    fallback = bool(llm_assistance.get("fallback"))
    used = bool(llm_assistance.get("used"))
    attempted = bool(llm_assistance.get("attempted"))
    category = llm_assistance.get("fallback_category")
    reason = llm_assistance.get("fallback_reason")
    detail_category = (
        llm_assistance.get("fallback_detail_category")
        or llm_assistance.get("codex_preflight_detail_category")
        or llm_assistance.get("timeout_recovery_failure_detail_category")
    )
    codex_preflight_soft_failed = bool(llm_assistance.get("codex_preflight_soft_failed"))
    codex_preflight_soft_failure_reason = llm_assistance.get("codex_preflight_soft_failure_reason")
    codex_preflight_skipped = bool(llm_assistance.get("codex_preflight_skipped"))
    codex_preflight_skip_reason = llm_assistance.get("codex_preflight_skip_reason")
    session_backend_memory_considered = bool(llm_assistance.get("session_backend_memory_considered"))
    session_backend_memory_used = bool(llm_assistance.get("session_backend_memory_used"))
    session_backend_memory_reason = llm_assistance.get("session_backend_memory_reason")
    session_backend_prior_category = llm_assistance.get("session_backend_prior_category")
    session_backend_prior_selected_backend = llm_assistance.get("session_backend_prior_selected_backend")
    intent_strategy = llm_assistance.get("intent_strategy")
    intent_prompt_profile = llm_assistance.get("intent_prompt_profile")
    intent_primary_timeout_seconds = llm_assistance.get("intent_primary_timeout_seconds")
    intent_timeout_capped = bool(llm_assistance.get("intent_timeout_capped"))
    timeout_recovery_attempted = bool(llm_assistance.get("timeout_recovery_attempted"))
    timeout_recovery_skipped = bool(llm_assistance.get("timeout_recovery_skipped"))
    timeout_recovery_skip_reason = llm_assistance.get("timeout_recovery_skip_reason")
    timeout_recovery_used = bool(llm_assistance.get("timeout_recovery_used"))
    if not attempted and not fallback and not used:
        return None

    if not isinstance(detail_category, str) or not detail_category:
        detail_category = _infer_backend_detail_category(
            category=category,
            reason=reason,
            requested_backend=requested_backend,
            selected_backend=selected_backend,
        )

    status = "used" if used else ("fallback" if fallback else "rules_only")
    message = "LLM assistance was used successfully."
    next_step = "Continue with the generated clarification or script result."
    recommended_fix = None
    result_context = _backend_result_context_label(
        result_status=result_status,
        execution_status=execution_status,
        runtime_probe_requested=bool(config.runtime_probe),
    )

    if status == "rules_only":
        message = "The run continued without LLM assistance."
        next_step = f"If you want LLM-assisted interpretation, configure a backend and retry; otherwise continue with the {result_context}."
    elif fallback:
        message = reason or "LLM assistance fell back to the rule-based path."
        next_step = f"The run already continued with the rule-based path. Continue with the {result_context}, or adjust backend configuration and retry."
        if category == "configuration_missing":
            if requested_backend == "api":
                recommended_fix = "Re-run with `--backend api --model openai/gpt-5-mini`, or set `PYQUDA_AGENT_API_MODEL` / `OPENAI_MODEL`."
                next_step = f"Configure an API model if you want backend-assisted interpretation; otherwise continue with the {result_context}."
            elif requested_backend == "auto":
                recommended_fix = "Install a local `codex` executable or configure `--backend api --model <provider/model>`."
                next_step = f"Auto mode could not find a usable LLM backend. Configure one, or continue with the {result_context}."
            else:
                recommended_fix = "Check backend configuration and retry."
        elif category == "credentials_missing":
            recommended_fix = "Add an API key to `api.key`, or set `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` for the chosen provider."
            next_step = f"Configure credentials if you want backend-assisted interpretation; otherwise continue with the {result_context}."
        elif category == "local_executable_missing":
            recommended_fix = "Install the local `codex` CLI, or switch to `--backend api --model <provider/model>`."
            next_step = f"Codex assistance is unavailable locally. Install it or switch backend if you want LLM help; otherwise continue with the {result_context}."
        elif category == "local_environment_error":
            if detail_category == "codex_app_client_init_failed":
                recommended_fix = (
                    "Run `codex exec 'Reply with exactly: OK'` in a normal local shell outside the current sandboxed runner. If that still fails, inspect the local codex app-client setup or switch to `--backend api --model <provider/model>`."
                )
                next_step = (
                    f"The local codex CLI started but failed during app-client initialization, so the run used the rule-based path. "
                    f"If the environment reported 'Operation not permitted', verify `codex exec 'Reply with exactly: OK'` from a normal local shell outside the current sandbox before retrying. "
                    f"Otherwise continue with the {result_context}, or inspect the local codex runtime and retry."
                )
            elif detail_category == "local_permission_error":
                recommended_fix = (
                    "Fix local codex executable permissions or environment restrictions, or switch to `--backend api --model <provider/model>`."
                )
                next_step = (
                    f"Local codex execution was blocked by a local permission/runtime problem, so the run used the rule-based path. "
                    f"Continue with the {result_context}, or repair local execution permissions before retrying."
                )
            else:
                recommended_fix = "Inspect the local codex environment, or switch to `--backend api --model <provider/model>`."
                next_step = f"Local codex initialization failed, so the run used the rule-based path. Continue with the {result_context}, or fix the local backend environment and retry."
        elif category == "authentication_error":
            if selected_backend == "codex":
                recommended_fix = "Run `codex login` and retry."
            else:
                recommended_fix = "Check the configured API key and provider account access, then retry."
            next_step = f"Authentication failed, so the run used the rule-based path. Fix auth only if you still want backend assistance; otherwise continue with the {result_context}."
        elif category == "network_error":
            if detail_category == "dns_resolution_failure":
                recommended_fix = "Fix DNS/network access for the backend host, or switch to a locally reachable backend."
                next_step = (
                    f"The backend host could not be resolved from the current environment, so the run used the rule-based path. "
                    f"Continue with the {result_context}, or retry after restoring DNS/network access."
                )
            elif detail_category == "connection_refused":
                recommended_fix = "Check the configured provider/base URL or network path, or switch to another backend."
                next_step = (
                    f"The backend connection was refused from the current environment, so the run used the rule-based path. "
                    f"Continue with the {result_context}, or retry after checking connectivity and endpoint reachability."
                )
            else:
                recommended_fix = "Retry with working network access, or switch to a locally available backend."
                next_step = f"Network access failed, so the run used the rule-based path. Continue with the {result_context}, or retry later with connectivity."
        elif category == "timeout":
            if selected_backend == "codex" and intent_primary_timeout_seconds and intent_timeout_capped:
                recommended_fix = (
                    "Switch to `--backend api --model <provider/model>`, or keep the current rule-based result if it is sufficient."
                )
                if timeout_recovery_skipped and timeout_recovery_skip_reason:
                    next_step = (
                        f"The backend did not answer in time. This codex intent path is already capped at {intent_primary_timeout_seconds:g} seconds, "
                        f"and timeout recovery was skipped because the first request was already the smallest normalization-only prompt. "
                        f"Switching backend is more likely to help than only increasing `--llm-timeout`. Continue with the {result_context}, or retry with another backend."
                    )
                else:
                    next_step = (
                        f"The backend did not answer in time. This codex intent path is already capped at {intent_primary_timeout_seconds:g} seconds before recovery/fallback, "
                        f"so switching backend is more likely to help than only increasing `--llm-timeout`. Continue with the {result_context}, or retry with another backend."
                    )
            elif selected_backend == "codex" and intent_primary_timeout_seconds:
                recommended_fix = (
                    "Increase `--llm-timeout`, or switch to `--backend api --model <provider/model>` if codex remains slow in this environment."
                )
                next_step = (
                    f"The backend did not answer within {intent_primary_timeout_seconds:g} seconds on the current codex path. "
                    f"Continue with the {result_context}, or retry with a larger `--llm-timeout`. "
                    f"If repeated retries still time out, switch backend."
                )
            else:
                recommended_fix = f"Increase `--llm-timeout`, or keep the {result_context} if it is sufficient."
                next_step = f"The backend did not answer in time. Continue with the {result_context}, or retry with a larger timeout."
        elif category == "rate_limited":
            recommended_fix = "Retry later, or switch to another backend."
            next_step = f"The backend was rate limited. Continue with the {result_context}, or retry later."
        elif category == "upstream_service_error":
            recommended_fix = "Retry later, or switch to another backend."
            next_step = f"The upstream backend service was unavailable. Continue with the {result_context}, or retry later."
        elif category == "endpoint_not_found":
            recommended_fix = "Check `--base-url`, provider selection, or model/provider compatibility, then retry."
            if detail_category == "chat_completions_endpoint_not_found":
                next_step = (
                    f"The configured chat-completions endpoint was not found. Fix the backend base URL or provider/model selection if you still want LLM help; "
                    f"otherwise continue with the {result_context}."
                )
            else:
                next_step = f"The backend endpoint was not found. Fix the backend endpoint configuration if you still want LLM help; otherwise continue with the {result_context}."
        elif category == "request_error":
            recommended_fix = "Inspect the provider/model request configuration, then retry."
            next_step = f"The backend rejected the request format or parameters. Fix the request configuration if you still want backend assistance; otherwise continue with the {result_context}."
        elif category == "response_parse_error":
            recommended_fix = "Retry the backend call, or switch backend if the provider returned an incompatible payload."
            if detail_category == "chat_completions_schema_mismatch":
                next_step = (
                    f"The backend returned a chat-completions payload the agent could not parse. Continue with the {result_context}, "
                    f"or retry after checking provider compatibility."
                )
            else:
                next_step = f"The backend returned a response the agent could not parse. Continue with the {result_context}, or retry with another backend."
        elif category == "empty_response":
            recommended_fix = "Retry the backend call, or switch backend if empty responses persist."
            if detail_category == "empty_message_content":
                next_step = (
                    f"The backend returned an empty message content field. Continue with the {result_context}, or retry with another backend if this keeps happening."
                )
            else:
                next_step = f"The backend returned an empty response. Continue with the {result_context}, or retry with another backend."
        elif category == "configuration_invalid":
            recommended_fix = "Fix the backend/model configuration and retry."
        elif category == "unexpected_error":
            recommended_fix = "Inspect `llm_fallback_reason`, then retry with `--backend auto` or a known-good backend."
        elif category == "backend_process_error":
            recommended_fix = "Inspect `llm_fallback_reason` and local backend logs, then retry or switch backend."
    elif used and codex_preflight_soft_failed:
        message = (
            "LLM assistance was used successfully after continuing past a short codex preflight timeout."
        )
        next_step = (
            f"Continue with the {result_context}. If codex latency becomes a problem, retry with a larger `--llm-timeout`."
        )
        recommended_fix = "Increase `--llm-timeout` if short codex preflight timeouts keep occurring."
    elif used and codex_preflight_skipped:
        message = "LLM assistance was used successfully after skipping explicit codex preflight for a rough normalization-only request."
        next_step = (
            f"Continue with the {result_context}. This path skipped the extra preflight round-trip and used the real codex call as the first backend signal."
        )
        recommended_fix = None
    elif used and session_backend_memory_used:
        if session_backend_prior_selected_backend == "rules":
            message = (
                "LLM assistance was used successfully after auto mode reused backend memory from the resumed session "
                "and skipped a previously failed codex-targeting attempt."
            )
        else:
            message = "LLM assistance was used successfully after auto mode reused backend memory from the resumed session."
        next_step = (
            f"Continue with the {result_context}. Auto mode skipped a previously degraded backend path for this resumed session."
        )
        recommended_fix = None
    elif used and timeout_recovery_used:
        message = "LLM assistance was used successfully after a timeout-triggered recovery retry."
        if selected_backend == "codex" and intent_primary_timeout_seconds:
            next_step = (
                f"Continue with the {result_context}. If this codex intent path keeps timing out on the first attempt, switching backend may help more than only increasing `--llm-timeout`."
            )
            recommended_fix = "If first-attempt codex intent timeouts keep forcing recovery retries, consider switching to `--backend api --model <provider/model>`."
        else:
            next_step = (
                f"Continue with the {result_context}. If this backend keeps timing out on the first attempt, retry with a larger `--llm-timeout`."
            )
            recommended_fix = "Increase `--llm-timeout` if first-attempt backend timeouts keep forcing recovery retries."

    failure_origin, recovery_mode, retryable_now = _classify_backend_failure(
        status=status,
        category=category,
    )

    return {
        "status": status,
        "requested_backend": requested_backend,
        "selected_backend": selected_backend,
        "attempted": attempted,
        "used": used,
        "fallback": fallback,
        "category": category,
        "detail_category": detail_category,
        "message": message,
        "next_step": next_step,
        "recommended_fix": recommended_fix,
        "codex_preflight_skipped": codex_preflight_skipped,
        "codex_preflight_skip_reason": codex_preflight_skip_reason,
        "codex_preflight_soft_failed": codex_preflight_soft_failed,
        "codex_preflight_soft_failure_reason": codex_preflight_soft_failure_reason,
        "session_backend_memory_considered": session_backend_memory_considered,
        "session_backend_memory_used": session_backend_memory_used,
        "session_backend_memory_reason": session_backend_memory_reason,
        "session_backend_prior_category": session_backend_prior_category,
        "session_backend_prior_selected_backend": session_backend_prior_selected_backend,
        "intent_strategy": intent_strategy,
        "intent_prompt_profile": intent_prompt_profile,
        "intent_primary_timeout_seconds": intent_primary_timeout_seconds,
        "intent_timeout_capped": intent_timeout_capped,
        "timeout_recovery_attempted": timeout_recovery_attempted,
        "timeout_recovery_skipped": timeout_recovery_skipped,
        "timeout_recovery_skip_reason": timeout_recovery_skip_reason,
        "timeout_recovery_used": timeout_recovery_used,
        "timeout_recovery_timeout_seconds": llm_assistance.get("timeout_recovery_timeout_seconds"),
        "failure_origin": failure_origin,
        "recovery_mode": recovery_mode,
        "retryable_now": retryable_now,
    }


def _infer_backend_detail_category(
    *,
    category: str | None,
    reason: str | None,
    requested_backend: str | None,
    selected_backend: str | None,
) -> str | None:
    lowered = (reason or "").lower()
    if category == "local_environment_error":
        if "app-client initialization" in lowered or "app-server client" in lowered:
            return "codex_app_client_init_failed"
        if "permission denied" in lowered or "operation not permitted" in lowered:
            return "local_permission_error"
    if category == "network_error":
        if any(token in lowered for token in ("dns", "name resolution", "lookup address", "temporary dns failure")):
            return "dns_resolution_failure"
        if "connection refused" in lowered:
            return "connection_refused"
    if category == "endpoint_not_found":
        if selected_backend == "api" or requested_backend == "api":
            return "chat_completions_endpoint_not_found"
    if category == "response_parse_error":
        return "chat_completions_schema_mismatch"
    if category == "empty_response":
        return "empty_message_content"
    return None


def _classify_backend_failure(*, status: str, category: str | None) -> tuple[str | None, str, bool]:
    if status == "used":
        return None, "continue", True
    if status == "rules_only":
        return "not_configured", "configure_backend", False

    mapping: dict[str | None, tuple[str, str, bool]] = {
        "configuration_missing": ("local_configuration", "configure_backend", True),
        "configuration_invalid": ("local_configuration", "configure_backend", True),
        "credentials_missing": ("credentials", "configure_credentials", False),
        "authentication_error": ("credentials", "authenticate", False),
        "local_executable_missing": ("local_backend", "install_or_switch_backend", False),
        "local_environment_error": ("local_backend", "repair_or_switch_backend", False),
        "backend_process_error": ("local_backend", "repair_or_switch_backend", False),
        "network_error": ("network", "retry_or_switch_backend", True),
        "timeout": ("network", "retry_or_switch_backend", True),
        "rate_limited": ("upstream_service", "retry_later_or_switch_backend", False),
        "upstream_service_error": ("upstream_service", "retry_later_or_switch_backend", False),
        "endpoint_not_found": ("request_configuration", "fix_endpoint_or_backend_config", True),
        "request_error": ("request_configuration", "fix_request_or_backend_config", True),
        "response_parse_error": ("backend_response", "retry_or_switch_backend", True),
        "empty_response": ("backend_response", "retry_or_switch_backend", True),
        "unexpected_error": ("unknown", "inspect_and_retry", False),
        None: ("unknown", "inspect_and_retry", False),
    }
    return mapping.get(category, ("unknown", "inspect_and_retry", False))


def _append_action(actions: list[dict], action: dict | None) -> None:
    if action is None:
        return
    action_state = action.get("action_state")
    if action_state is None:
        action_state = "ready" if action.get("command") else "blocked"
        action = {**action, "action_state": action_state}
    if "actionable" not in action:
        action = {**action, "actionable": action_state == "ready"}
    kind = action.get("kind")
    command = action.get("command")
    guidance = action.get("guidance")
    for existing in actions:
        if existing.get("kind") == kind and existing.get("command") == command and existing.get("guidance") == guidance:
            return
    actions.append(action)


def _primary_action(action_queue: list[dict]) -> dict | None:
    return action_queue[0] if action_queue else None


def _synchronize_workflow_outcome_actions(workflow_outcome: dict, primary_action: dict | None) -> dict:
    if not isinstance(workflow_outcome, dict):
        return workflow_outcome
    command = (primary_action or {}).get("command")
    if not command:
        return workflow_outcome
    return {
        **workflow_outcome,
        "recommended_command": command,
    }


def _build_capability_summary(
    *,
    result: dict,
    workflow_outcome: dict,
    delivery_status: dict,
    backend_diagnostic: dict | None,
    primary_action: dict | None,
) -> dict:
    status = result.get("status")
    runtime_probe_status = workflow_outcome.get("runtime_probe_status")
    execution_status = workflow_outcome.get("execution_status")
    backend_status = "rules_only"
    backend_ready = False
    backend_detail = None
    if isinstance(backend_diagnostic, dict):
        backend_status = backend_diagnostic.get("status") or backend_status
        backend_ready = backend_status == "used"
        backend_detail = (
            backend_diagnostic.get("recommended_fix")
            or backend_diagnostic.get("next_step")
            or backend_diagnostic.get("message")
        )

    generation_state = "in_progress"
    generation_ready = False
    if status == "needs_input":
        generation_state = "blocked_on_clarification"
    elif status == "unsupported":
        generation_state = "unsupported"
    elif status == "dry_run":
        generation_state = "ready_to_generate"
        generation_ready = True
    elif status == "ok":
        generation_state = "generated"
        generation_ready = True

    runtime_state = "not_applicable"
    runtime_ready = False
    runtime_proved = False
    if status == "ok":
        if execution_status == "runtime_proved" or runtime_probe_status == "runtime_proved":
            runtime_state = "runtime_proved"
            runtime_ready = True
            runtime_proved = True
        elif runtime_probe_status == "not_requested":
            runtime_state = "probe_available"
            runtime_ready = True
        elif _runtime_probe_is_blocked(runtime_probe_status):
            runtime_state = "runtime_blocked"
        elif runtime_probe_status in {"requested", "ok"}:
            runtime_state = "probe_in_progress"
            runtime_ready = True
        else:
            runtime_state = str(runtime_probe_status or "pending")
    elif status == "dry_run":
        runtime_state = "blocked_by_generation"
    elif status == "needs_input":
        runtime_state = "blocked_by_clarification"
    elif status == "unsupported":
        runtime_state = "unsupported"

    return {
        "backend": {
            "state": backend_status,
            "ready": backend_ready,
            "requested_backend": (backend_diagnostic or {}).get("requested_backend"),
            "selected_backend": (backend_diagnostic or {}).get("selected_backend"),
            "category": (backend_diagnostic or {}).get("category"),
            "detail": backend_detail,
        },
        "generation": {
            "state": generation_state,
            "ready": generation_ready,
            "succeeded": bool(workflow_outcome.get("generation_succeeded")),
            "phase": delivery_status.get("generation", {}).get("phase"),
            "detail": delivery_status.get("generation", {}).get("headline") or workflow_outcome.get("next_step"),
        },
        "runtime": {
            "state": runtime_state,
            "ready": runtime_ready,
            "proved": runtime_proved,
            "attempted": bool(workflow_outcome.get("execution_attempted")),
            "level": workflow_outcome.get("runtime_level"),
            "evidence_level": workflow_outcome.get("evidence_level"),
            "detail": delivery_status.get("execution", {}).get("headline") or workflow_outcome.get("next_step"),
            "blockers": list(workflow_outcome.get("blockers") or []),
        },
        "next_step": {
            "kind": (primary_action or {}).get("kind"),
            "actionable": bool((primary_action or {}).get("actionable")),
            "command": (primary_action or {}).get("command"),
        },
    }


def _build_terminal_message(
    *,
    result: dict,
    workflow_outcome: dict,
    delivery_status: dict,
    runtime_diagnostic: dict | None,
    primary_action: dict | None,
    action_queue: list[dict],
    unsupported_guidance: dict | None,
) -> dict:
    status = result.get("status")
    command = (primary_action or {}).get("command")
    alternative_commands = _terminal_alternative_commands(
        action_queue=action_queue,
        primary_action=primary_action,
    )
    if status == "needs_input":
        return {
            "headline": "More input is required before code generation.",
            "detail": workflow_outcome.get("next_step"),
            "recommended_command": command,
            "alternative_commands": alternative_commands,
        }
    if status == "unsupported":
        guidance = unsupported_guidance or {}
        nearby = guidance.get("nearby_workflow_targets") or []
        detail = guidance.get("primary_reason") or result.get("refusal_reason")
        shortest_fix = guidance.get("shortest_fix") or {}
        gap_summary = guidance.get("shortest_fix_gap_summary") or {}
        repair_hint = guidance.get("repair_hint") or {}
        if nearby:
            detail = f"{detail} Nearby grounded workflows: {', '.join(nearby)}."
        shortest_fix_summary = shortest_fix.get("summary")
        if shortest_fix_summary:
            detail = f"{detail} {shortest_fix_summary}"
        gap_sentence = gap_summary.get("sentence")
        if gap_sentence:
            detail = f"{detail} {gap_sentence}"
        repair_sentence = repair_hint.get("summary")
        if repair_sentence:
            detail = f"{detail} {repair_sentence}"
        alternative_commands = []
        for retry in guidance.get("retry_suggestions") or []:
            retry_command = retry.get("retry_command")
            if retry_command:
                alternative_commands.append(
                    {
                        "label": f"Retry toward {retry.get('workflow_target')}",
                        "command": retry_command,
                    }
                )
            for variant in retry.get("variant_retry_commands") or []:
                alternative_commands.append(
                    {
                        "label": f"Retry {retry.get('workflow_target')} with {variant.get('field_name')}={variant.get('accepted_value')}",
                        "command": variant.get("command"),
                    }
                )
        return {
            "headline": "The confirmed request is outside the current grounded workflow scope.",
            "detail": detail,
            "recommended_command": command or (alternative_commands[0]["command"] if alternative_commands else None),
            "alternative_commands": alternative_commands,
        }
    if status == "dry_run":
        return {
            "headline": "The grounded plan is ready; re-run without --dry-run to emit the script.",
            "detail": workflow_outcome.get("next_step"),
            "recommended_command": command,
            "alternative_commands": alternative_commands,
        }
    if status == "ok":
        execution_phase = delivery_status.get("execution", {}).get("phase")
        if execution_phase == "probe_available":
            return {
                "headline": "The script was generated successfully.",
                "detail": "Runtime proof has not been attempted yet; run the probe when you want execution evidence.",
                "recommended_command": command,
                "alternative_commands": alternative_commands,
            }
        if execution_phase == "runtime_proved":
            return {
                "headline": "The script was generated and runtime proof succeeded.",
                "detail": workflow_outcome.get("next_step"),
                "recommended_command": command,
                "alternative_commands": alternative_commands,
            }
        if execution_phase == "probe_driver_failed":
            return {
                "headline": "The script was generated, but the probe harness failed.",
                "detail": (runtime_diagnostic or {}).get("next_step") or workflow_outcome.get("next_step"),
                "recommended_command": command,
                "alternative_commands": alternative_commands,
            }
        if execution_phase == "runtime_missing":
            return {
                "headline": "The script was generated, but the runtime environment is incomplete.",
                "detail": (runtime_diagnostic or {}).get("next_step") or workflow_outcome.get("next_step"),
                "recommended_command": command,
                "alternative_commands": alternative_commands,
            }
        if execution_phase not in {"not_applicable", "blocked_by_generation"}:
            return {
                "headline": "The script was generated, but runtime proof is still blocked.",
                "detail": workflow_outcome.get("next_step"),
                "recommended_command": command,
                "alternative_commands": alternative_commands,
            }
        return {
            "headline": "The script was generated successfully.",
            "detail": workflow_outcome.get("next_step"),
            "recommended_command": command,
            "alternative_commands": alternative_commands,
        }
    return {
        "headline": "Run in progress.",
        "detail": workflow_outcome.get("next_step") or result.get("next_action"),
        "recommended_command": command,
        "alternative_commands": alternative_commands,
    }


def _terminal_alternative_commands(*, action_queue: list[dict], primary_action: dict | None) -> list[dict]:
    primary_command = (primary_action or {}).get("command")
    alternatives: list[dict] = []
    for item in action_queue or []:
        command = item.get("command")
        if not command or command == primary_command:
            continue
        if not item.get("actionable", True):
            continue
        alternatives.append(
            {
                "label": item.get("title") or item.get("kind") or "Alternative",
                "command": command,
            }
        )
    return alternatives[:3]


def _runtime_probe_is_blocked(status: str | None) -> bool:
    return status not in {
        None,
        "not_requested",
        "not_applicable",
        "requested",
        "ok",
        "runtime_proved",
        "pending_generation",
    }


def _extract_missing_runtime_dependency(blocker: str) -> str | None:
    marker = "Missing runtime dependency '"
    if marker not in blocker:
        return None
    suffix = blocker.split(marker, 1)[1]
    if "'" not in suffix:
        return None
    return suffix.split("'", 1)[0]


def _runtime_environment_recommended_fix(blockers: list[str]) -> str:
    for blocker in blockers:
        dependency = _extract_missing_runtime_dependency(blocker)
        if dependency:
            return f"Activate a PyQUDA Python environment that provides `{dependency}`, then rerun the probe command."
        if "Unable to import 'pyquda_utils'" in blocker:
            return (
                "Build/install the local PyQUDA checkout or export `PYTHONPATH=~/PyQUDA`, "
                "then rerun the probe command."
            )
        if "Unable to import 'pyquda'" in blocker:
            return "Activate the Python environment that contains the PyQUDA core bindings, then rerun the probe command."
        if "Gauge configuration not found:" in blocker or "Propagator not found:" in blocker:
            return "Fix the input-path visibility on the target filesystem, then rerun the probe command."
        if "requires a writable parent directory" in blocker or "Unable to locate an existing parent directory for" in blocker:
            return "Choose or create a writable output directory on the target filesystem, then rerun the probe command."
        if "must be divisible by GRID_SIZE" in blocker or "GRID_SIZE must" in blocker or "LATTICE_SIZE must" in blocker:
            return "Fix the lattice/grid launch assumptions so they match the target cluster layout, then rerun the probe command."
        if "Expected sibling review artifacts next to this script" in blocker:
            return "Restore the sibling .physics.json, .task.json, and .plan.json artifacts next to the generated script, then rerun the probe command."
    return "Fix the missing runtime prerequisites, then rerun the probe command."


def _runtime_probe_driver_recommended_fix(*, artifact_path: str | None) -> str:
    if artifact_path:
        return f"Inspect the probe artifact at `{artifact_path}` for the harness-side traceback, then rerun the probe command."
    return "Inspect the probe artifact for the harness-side traceback, then rerun the probe command."


def _runtime_probe_blocked_recommended_fix(*, status: str | None, blockers: list[str], artifact_path: str | None) -> str:
    if status == "input_visibility_blocked":
        return "Fix the input-path visibility on the target filesystem for all ranks, then rerun the probe command."
    if status == "output_writability_blocked":
        return "Choose or create a writable output directory on the target filesystem, then rerun the probe command."
    if status == "cluster_assumption_mismatch":
        return "Align lattice/grid/resource-path assumptions with the target cluster launch configuration, then rerun the probe command."
    if status == "artifact_chain_missing":
        return "Restore the sibling .physics.json, .task.json, and .plan.json artifacts next to the generated script, then rerun the probe command."
    if status == "handoff_contract_mismatch":
        return "Fix the generated-script handoff contract inputs or fixed workflow parameters, then rerun the probe command."
    if status == "probe_timeout":
        return "Increase the probe timeout or reduce startup latency in the target runtime environment, then rerun the probe command."
    if blockers:
        return _runtime_environment_recommended_fix(blockers)
    return _runtime_probe_driver_recommended_fix(artifact_path=artifact_path)


def _build_runtime_diagnostic(*, result: dict, workflow_outcome: dict) -> dict | None:
    status = result.get("status")
    runtime_probe_status = workflow_outcome.get("runtime_probe_status")
    execution_status = workflow_outcome.get("execution_status")
    blockers = list(workflow_outcome.get("blockers") or [])
    runtime_evidence = result.get("runtime_evidence") or {}
    generated_script_probe = runtime_evidence.get("generated_script_probe") or {}
    artifact_path = generated_script_probe.get("artifact_path")
    probe_command = result.get("probe_hint")
    runtime_level = workflow_outcome.get("runtime_level")
    evidence_level = workflow_outcome.get("evidence_level")

    if status != "ok":
        return {
            "status": "not_applicable",
            "category": "generation_incomplete",
            "message": "Runtime proof is only available after script generation succeeds.",
            "next_step": workflow_outcome.get("next_step"),
            "recommended_fix": None,
            "artifact_path": artifact_path,
            "probe_command": probe_command,
            "retry_command": None,
            "runtime_level": runtime_level,
            "evidence_level": evidence_level,
            "blockers": blockers,
        }

    if execution_status == "runtime_proved":
        return {
            "status": "runtime_proved",
            "category": "runtime_proved",
            "message": "Runtime proof succeeded for the generated script.",
            "next_step": workflow_outcome.get("next_step"),
            "recommended_fix": None,
            "artifact_path": artifact_path,
            "probe_command": probe_command,
            "retry_command": None,
            "runtime_level": runtime_level,
            "evidence_level": evidence_level,
            "blockers": blockers,
        }

    if runtime_probe_status == "not_requested":
        return {
            "status": "probe_available",
            "category": "probe_not_requested",
            "message": "Script generation succeeded; runtime proof has not been attempted yet.",
            "next_step": workflow_outcome.get("next_step"),
            "recommended_fix": "Run the probe command when you want runtime evidence for the generated script.",
            "artifact_path": artifact_path,
            "probe_command": probe_command,
            "retry_command": probe_command,
            "runtime_level": runtime_level,
            "evidence_level": evidence_level,
            "blockers": blockers,
        }

    if execution_status == "probe_driver_failed" or runtime_probe_status == "probe_driver_failed":
        recommended_fix = _runtime_probe_driver_recommended_fix(artifact_path=artifact_path)
        return {
            "status": "probe_driver_failed",
            "category": "probe_driver_failed",
            "message": "The generated script exists, but the probe harness failed before it could assess runtime readiness.",
            "next_step": recommended_fix,
            "recommended_fix": recommended_fix,
            "artifact_path": artifact_path,
            "probe_command": probe_command,
            "retry_command": probe_command,
            "runtime_level": runtime_level,
            "evidence_level": evidence_level,
            "blockers": blockers,
        }

    if execution_status == "runtime_missing" or runtime_probe_status == "runtime_missing":
        recommended_fix = _runtime_environment_recommended_fix(blockers)
        return {
            "status": "runtime_missing",
            "category": "environment_missing",
            "message": "The generated script exists, but the current environment is missing runtime dependencies or configuration.",
            "next_step": recommended_fix,
            "recommended_fix": recommended_fix,
            "artifact_path": artifact_path,
            "probe_command": probe_command,
            "retry_command": probe_command,
            "runtime_level": runtime_level,
            "evidence_level": evidence_level,
            "blockers": blockers,
        }

    if _runtime_probe_is_blocked(runtime_probe_status):
        blocked_status = str(runtime_probe_status or execution_status or "runtime_blocked")
        recommended_fix = _runtime_probe_blocked_recommended_fix(
            status=blocked_status,
            blockers=blockers,
            artifact_path=artifact_path,
        )
        category = blocked_status if blocked_status in {
            "input_visibility_blocked",
            "output_writability_blocked",
            "cluster_assumption_mismatch",
            "artifact_chain_missing",
            "handoff_contract_mismatch",
            "probe_timeout",
            "probe_failed",
        } else "runtime_blocked"
        return {
            "status": blocked_status,
            "category": category,
            "message": "Runtime proof was attempted, but the generated script is still blocked on runtime-side issues.",
            "next_step": recommended_fix,
            "recommended_fix": recommended_fix,
            "artifact_path": artifact_path,
            "probe_command": probe_command,
            "retry_command": probe_command,
            "runtime_level": runtime_level,
            "evidence_level": evidence_level,
            "blockers": blockers,
        }

    return {
        "status": str(runtime_probe_status or execution_status or "pending"),
        "category": "probe_pending",
        "message": "Runtime proof is pending for the generated script.",
        "next_step": workflow_outcome.get("next_step"),
        "recommended_fix": None,
        "artifact_path": artifact_path,
        "probe_command": probe_command,
        "retry_command": probe_command,
        "runtime_level": runtime_level,
        "evidence_level": evidence_level,
        "blockers": blockers,
    }


def _build_run_overview(
    *,
    result: dict,
    workflow_outcome: dict,
    backend_diagnostic: dict | None,
    runtime_diagnostic: dict | None,
    primary_action: dict | None,
) -> dict:
    status = result.get("status")
    phase = workflow_outcome.get("phase")
    runtime_probe_status = workflow_outcome.get("runtime_probe_status")
    execution_status = workflow_outcome.get("execution_status")

    headline = "Run in progress."
    detail = workflow_outcome.get("next_step")
    blocking_kind = "none"

    if status == "needs_input":
        headline = "More input is required before code generation."
        blocking_kind = "clarification"
    elif status == "dry_run":
        headline = "The grounded plan is ready, but the script has not been emitted yet."
        blocking_kind = "generation"
    elif status == "unsupported":
        headline = "The confirmed request is outside the currently grounded implementation scope."
        blocking_kind = "unsupported"
    elif status == "ok" and runtime_probe_status == "not_requested":
        headline = "The script was generated successfully."
        blocking_kind = "runtime_probe_optional"
    elif status == "ok" and _runtime_probe_is_blocked(runtime_probe_status):
        headline = "The script was generated, but runtime proof is still blocked."
        blocking_kind = "runtime"
    elif status == "ok" and execution_status == "runtime_proved":
        headline = "The script was generated and runtime proof succeeded."
        blocking_kind = "none"

    backend_state = None
    if isinstance(backend_diagnostic, dict):
        backend_state = backend_diagnostic.get("status")
        if backend_state == "fallback" and blocking_kind in {"clarification", "generation"}:
            blocking_kind = "backend_fallback"
    if status == "ok" and isinstance(runtime_diagnostic, dict):
        if runtime_diagnostic.get("category") == "probe_driver_failed":
            headline = "The script was generated, but the probe harness failed."
            detail = runtime_diagnostic.get("next_step") or detail
            blocking_kind = "probe_driver"
        elif runtime_diagnostic.get("category") == "environment_missing":
            headline = "The script was generated, but the runtime environment is incomplete."
            detail = runtime_diagnostic.get("next_step") or detail
            blocking_kind = "runtime_environment"

    return {
        "status": status,
        "phase": phase,
        "headline": headline,
        "detail": detail,
        "blocking_kind": blocking_kind,
        "backend_state": backend_state,
        "runtime_level": workflow_outcome.get("runtime_level"),
        "can_continue_now": bool((primary_action or {}).get("actionable")),
        "primary_action_kind": (primary_action or {}).get("kind"),
        "primary_action_title": (primary_action or {}).get("title"),
    }


def _build_blocking_reason(
    *,
    run_overview: dict,
    delivery_status: dict,
    backend_diagnostic: dict | None,
    runtime_diagnostic: dict | None,
) -> str | None:
    blocking_kind = run_overview.get("blocking_kind")
    if blocking_kind == "clarification":
        return (delivery_status.get("generation") or {}).get("headline")
    if blocking_kind == "backend_fallback":
        return (
            (backend_diagnostic or {}).get("message")
            or (backend_diagnostic or {}).get("next_step")
            or (delivery_status.get("generation") or {}).get("headline")
        )
    if blocking_kind == "generation":
        return (delivery_status.get("generation") or {}).get("headline")
    if blocking_kind == "unsupported":
        return run_overview.get("headline")
    if blocking_kind == "runtime_probe_optional":
        return (
            (runtime_diagnostic or {}).get("message")
            or (delivery_status.get("execution") or {}).get("headline")
        )
    if blocking_kind in {"runtime_environment", "probe_driver", "runtime"}:
        return (
            (runtime_diagnostic or {}).get("message")
            or (delivery_status.get("execution") or {}).get("headline")
        )
    return None


def _build_blocking_reason_detail(
    *,
    run_overview: dict,
    delivery_status: dict,
    backend_diagnostic: dict | None,
    runtime_diagnostic: dict | None,
    blocking_reason: str | None,
) -> dict | None:
    if not blocking_reason:
        return None
    blocking_kind = run_overview.get("blocking_kind")
    if blocking_kind == "clarification":
        return {
            "category": "needs_clarification",
            "source": "generation",
            "message": blocking_reason,
        }
    if blocking_kind == "backend_fallback":
        backend_category = (backend_diagnostic or {}).get("category") or "fallback"
        category_map = {
            "configuration_missing": "backend_configuration_missing",
            "configuration_invalid": "backend_configuration_invalid",
            "credentials_missing": "backend_credentials_missing",
            "local_executable_missing": "backend_local_executable_missing",
            "local_environment_error": "backend_local_environment_error",
            "authentication_error": "backend_authentication_failed",
            "network_error": "backend_network_error",
            "timeout": "backend_timeout",
            "rate_limited": "backend_rate_limited",
            "upstream_service_error": "backend_service_unavailable",
            "endpoint_not_found": "backend_endpoint_not_found",
            "request_error": "backend_request_error",
            "response_parse_error": "backend_response_parse_error",
            "empty_response": "backend_empty_response",
            "unexpected_error": "backend_unexpected_error",
            "backend_process_error": "backend_process_error",
        }
        return {
            "category": category_map.get(backend_category, "backend_fallback"),
            "source": "backend",
            "message": blocking_reason,
            "backend_category": backend_category,
            "backend_detail_category": (backend_diagnostic or {}).get("detail_category"),
        }
    if blocking_kind == "generation":
        return {
            "category": "generation_not_emitted",
            "source": "generation",
            "message": blocking_reason,
        }
    if blocking_kind == "unsupported":
        return {
            "category": "unsupported_request",
            "source": "workflow_match",
            "message": blocking_reason,
        }
    if blocking_kind == "runtime_probe_optional":
        return {
            "category": "runtime_probe_not_run",
            "source": "runtime",
            "message": blocking_reason,
            "runtime_category": (runtime_diagnostic or {}).get("category"),
        }
    if blocking_kind == "runtime_environment":
        return {
            "category": "runtime_dependencies_missing",
            "source": "runtime",
            "message": blocking_reason,
            "runtime_category": (runtime_diagnostic or {}).get("category"),
        }
    if blocking_kind == "probe_driver":
        return {
            "category": "runtime_probe_harness_failed",
            "source": "runtime",
            "message": blocking_reason,
            "runtime_category": (runtime_diagnostic or {}).get("category"),
        }
    if blocking_kind == "runtime":
        return {
            "category": "runtime_blocked",
            "source": "runtime",
            "message": blocking_reason,
            "runtime_category": (runtime_diagnostic or {}).get("category"),
        }
    return {
        "category": "informational",
        "source": "summary",
        "message": blocking_reason,
    }


def _build_inspection_hint(*, run_overview: dict, artifacts: dict) -> dict | None:
    blocking_kind = run_overview.get("blocking_kind")
    preferred_orders = [
        ("Probe", "probe", {"none"}),
        ("Probe", "probe", {"runtime_environment", "probe_driver", "runtime", "runtime_probe_optional"}),
        ("Task", "task", {"clarification", "backend_fallback"}),
        ("Plan", "plan", {"generation"}),
        ("Physics", "physics", {"unsupported"}),
    ]
    for label, key, applicable_kinds in preferred_orders:
        value = artifacts.get(key)
        if value and blocking_kind in applicable_kinds:
            return {"label": label, "artifact_key": key, "path": value}
    for label, key in (
        ("Task", "task"),
        ("Physics", "physics"),
        ("Plan", "plan"),
        ("Script", "script"),
        ("Session", "session"),
        ("Probe", "probe"),
    ):
        value = artifacts.get(key)
        if value:
            return {"label": label, "artifact_key": key, "path": value}
    return None


def _build_frontend_profile(
    *,
    product_status: str,
    run_overview: dict,
    capability_summary: dict,
    blocking_reason: str | None,
    blocking_reason_detail: dict | None,
    inspection_hint: dict | None,
    primary_action: dict | None,
) -> dict:
    return {
        "summary_schema": RESULT_SUMMARY_SCHEMA_VERSION,
        "status_card": {
            "product_status": product_status,
            "headline": run_overview.get("headline"),
            "detail": run_overview.get("detail"),
            "blocking_kind": run_overview.get("blocking_kind"),
            "blocking_reason": blocking_reason,
            "blocking_reason_category": (blocking_reason_detail or {}).get("category"),
        },
        "capabilities": {
            "backend_state": ((capability_summary.get("backend") or {}).get("state")),
            "generation_state": ((capability_summary.get("generation") or {}).get("state")),
            "runtime_state": ((capability_summary.get("runtime") or {}).get("state")),
            "runtime_proved": bool((capability_summary.get("runtime") or {}).get("proved")),
        },
        "next": {
            "action_kind": (primary_action or {}).get("kind"),
            "action_title": (primary_action or {}).get("title"),
            "actionable": bool((primary_action or {}).get("actionable")),
            "command": (primary_action or {}).get("command"),
        },
        "inspect": inspection_hint,
    }


def _build_delivery_status(*, result: dict, workflow_outcome: dict, primary_action: dict | None) -> dict:
    status = result.get("status")
    execution_status = workflow_outcome.get("execution_status")
    runtime_probe_status = workflow_outcome.get("runtime_probe_status")
    generation_succeeded = bool(workflow_outcome.get("generation_succeeded"))
    execution_attempted = bool(workflow_outcome.get("execution_attempted"))
    execution_succeeded = workflow_outcome.get("execution_succeeded")

    generation_phase = "not_started"
    generation_headline = "Generation has not started yet."
    if status == "needs_input":
        generation_phase = "blocked_on_input"
        generation_headline = "Generation is blocked on clarification."
    elif status == "unsupported":
        generation_phase = "unsupported"
        generation_headline = "Generation stopped because the confirmed request is unsupported."
    elif status == "dry_run":
        generation_phase = "ready_to_generate"
        generation_headline = "Generation is ready, but the script has not been emitted yet."
    elif status == "ok" and generation_succeeded:
        generation_phase = "generated"
        generation_headline = "The script was generated successfully."

    execution_phase = "not_applicable"
    execution_headline = "Runtime proof does not apply until a script exists."
    if generation_phase == "generated":
        if runtime_probe_status == "not_requested":
            execution_phase = "probe_available"
            execution_headline = "Runtime proof has not been attempted yet; a probe command is available."
        elif execution_attempted and execution_succeeded is True:
            execution_phase = "runtime_proved"
            execution_headline = "Runtime proof succeeded."
        elif execution_attempted:
            execution_phase = str(execution_status or runtime_probe_status or "probe_failed")
            if execution_phase == "probe_driver_failed":
                execution_headline = "The probe harness failed before runtime readiness could be assessed."
            elif execution_phase == "runtime_missing":
                execution_headline = "Runtime proof found that the current environment is missing required runtime pieces."
            else:
                execution_headline = "Runtime proof was attempted but is still blocked."
        else:
            execution_phase = "pending_probe"
            execution_headline = "Runtime proof is pending."
    elif generation_phase in {"blocked_on_input", "ready_to_generate"}:
        execution_phase = "blocked_by_generation"
        execution_headline = "Resolve generation first before runtime proof."
    elif generation_phase == "unsupported":
        execution_phase = "unsupported"
        execution_headline = "Runtime proof is unavailable because generation is unsupported."

    return {
        "generation": {
            "phase": generation_phase,
            "succeeded": generation_succeeded,
            "headline": generation_headline,
            "script_path": workflow_outcome.get("generated_script_path"),
            "script_exists": workflow_outcome.get("generated_script_exists"),
        },
        "execution": {
            "phase": execution_phase,
            "attempted": execution_attempted,
            "succeeded": execution_succeeded,
            "status": execution_status,
            "runtime_probe_status": runtime_probe_status,
            "runtime_level": workflow_outcome.get("runtime_level"),
            "evidence_level": workflow_outcome.get("evidence_level"),
            "headline": execution_headline,
        },
        "next_step": {
            "kind": (primary_action or {}).get("kind"),
            "title": (primary_action or {}).get("title"),
            "command": (primary_action or {}).get("command"),
            "actionable": bool((primary_action or {}).get("actionable")),
        },
    }


def _build_generation_result(*, delivery_status: dict, workflow_outcome: dict) -> dict:
    generation = delivery_status.get("generation") or {}
    phase = generation.get("phase")
    return {
        "phase": phase,
        "headline": generation.get("headline"),
        "ready": phase in {"ready_to_generate", "generated"},
        "emitted": phase == "generated",
        "succeeded": bool(generation.get("succeeded")),
        "script_path": generation.get("script_path"),
        "script_exists": bool(generation.get("script_exists")),
        "workflow_phase": workflow_outcome.get("phase"),
    }


def _build_execution_result(
    *,
    delivery_status: dict,
    workflow_outcome: dict,
    runtime_diagnostic: dict,
    probe_hint: str | None,
    probe_artifact: str | None,
) -> dict:
    execution = delivery_status.get("execution") or {}
    phase = execution.get("phase")
    return {
        "phase": phase,
        "headline": execution.get("headline"),
        "attempted": bool(execution.get("attempted")),
        "succeeded": execution.get("succeeded"),
        "status": execution.get("status"),
        "runtime_probe_status": execution.get("runtime_probe_status"),
        "runtime_level": execution.get("runtime_level"),
        "evidence_level": execution.get("evidence_level"),
        "probe_available": phase == "probe_available",
        "blocked": phase in {"runtime_missing", "probe_driver_failed", "pending_probe"},
        "diagnostic_category": runtime_diagnostic.get("category"),
        "diagnostic_source": runtime_diagnostic.get("source"),
        "probe_command": probe_hint,
        "probe_artifact": probe_artifact,
    }


def _build_execution_closure(
    *,
    product_status: str,
    workflow_outcome: dict,
    delivery_status: dict,
    runtime_diagnostic: dict,
    backend_diagnostic: dict | None,
    primary_action: dict | None,
    artifacts: dict,
) -> dict:
    generation_phase = (delivery_status.get("generation") or {}).get("phase")
    execution_phase = (delivery_status.get("execution") or {}).get("phase")
    runtime_category = runtime_diagnostic.get("category")
    state = product_status
    headline = workflow_outcome.get("headline")
    why = workflow_outcome.get("next_step")
    next_artifact = "plan"
    if artifacts.get("probe"):
        next_artifact = "probe"
    elif artifacts.get("script"):
        next_artifact = "script"

    if product_status == "needs_input":
        state = "needs_clarification"
        headline = "Clarification is still required before grounded code generation."
        next_artifact = "physics" if "physics target confirmation required" in str(workflow_outcome.get("blockers")) else "task"
    elif product_status == "ready_to_generate":
        state = "ready_to_generate"
        headline = "The grounded plan is ready; emit the script next."
        next_artifact = "plan"
    elif product_status == "generated_probe_available":
        state = "generated_not_probed"
        headline = "The grounded script exists; runtime proof has not been attempted yet."
        next_artifact = "script"
    elif execution_phase == "runtime_missing" or runtime_category == "environment_missing":
        state = "runtime_environment_missing"
        headline = "The grounded script exists, but the runtime environment is incomplete."
        next_artifact = "probe"
    elif execution_phase == "probe_driver_failed" or runtime_category == "probe_driver_failed":
        state = "probe_harness_failed"
        headline = "The grounded script exists, but the probe harness failed before runtime assessment."
        next_artifact = "probe"
    elif product_status == "runtime_proved":
        state = "runtime_proved"
        headline = "Grounded script generation and runtime proof both succeeded."
        next_artifact = "probe"
    elif product_status == "unsupported":
        state = "unsupported"
        headline = "The confirmed request is outside the current grounded workflow scope."
        next_artifact = "physics"

    return {
        "state": state,
        "headline": headline,
        "generation_phase": generation_phase,
        "execution_phase": execution_phase,
        "runtime_category": runtime_category,
        "backend_category": (backend_diagnostic or {}).get("category"),
        "why": why,
        "next_artifact": next_artifact,
        "next_command_kind": (primary_action or {}).get("kind"),
        "next_command": (primary_action or {}).get("command"),
        "probe_artifact": artifacts.get("probe"),
        "script_artifact": artifacts.get("script"),
        "actionable": bool((primary_action or {}).get("actionable")),
    }


def _build_execution_checkpoint(
    *,
    product_status: str,
    workflow_outcome: dict,
    delivery_status: dict,
    execution_closure: dict,
    runtime_diagnostic: dict,
    primary_action: dict | None,
    artifacts: dict,
) -> dict:
    generation_phase = (delivery_status.get("generation") or {}).get("phase")
    execution_phase = (delivery_status.get("execution") or {}).get("phase")
    runtime_probe_status = workflow_outcome.get("runtime_probe_status")
    runtime_level = workflow_outcome.get("runtime_level")
    state = execution_closure.get("state") or product_status
    generated_script_exists = bool(artifacts.get("script"))
    handoff_ready = generated_script_exists and state in {
        "generated_not_probed",
        "runtime_environment_missing",
        "probe_harness_failed",
        "runtime_proved",
        "generated_runtime_blocked",
    }
    return {
        "state": state,
        "headline": execution_closure.get("headline") or workflow_outcome.get("next_step"),
        "generation_phase": generation_phase,
        "execution_phase": execution_phase,
        "runtime_probe_status": runtime_probe_status,
        "runtime_level": runtime_level,
        "diagnostic_category": runtime_diagnostic.get("category"),
        "generated_script_exists": generated_script_exists,
        "probe_artifact": artifacts.get("probe"),
        "probe_command": (primary_action or {}).get("kind") in {"run_probe", "retry_probe"} and (primary_action or {}).get("command") or None,
        "hpc_handoff_ready": handoff_ready,
        "next_artifact": execution_closure.get("next_artifact"),
        "next_action_kind": (primary_action or {}).get("kind"),
        "next_action_command": (primary_action or {}).get("command"),
    }


def _build_backend_path(
    *,
    backend_diagnostic: dict | None,
    action_queue: list[dict],
    product_status: str,
) -> dict | None:
    if not isinstance(backend_diagnostic, dict):
        return None
    repair_action = next((item for item in action_queue if item.get("kind") == "backend_fix"), None)
    return {
        "requested_backend": backend_diagnostic.get("requested_backend"),
        "selected_backend": backend_diagnostic.get("selected_backend"),
        "status": backend_diagnostic.get("status"),
        "category": backend_diagnostic.get("category"),
        "detail_category": backend_diagnostic.get("detail_category"),
        "failure_origin": backend_diagnostic.get("failure_origin"),
        "recovery_mode": backend_diagnostic.get("recovery_mode"),
        "retryable_now": backend_diagnostic.get("retryable_now"),
        "current_result_usable": product_status != "unsupported",
        "continue_with_current_result": product_status in {
            "needs_input",
            "ready_to_generate",
            "generated_probe_available",
            "generated_runtime_blocked",
            "runtime_proved",
        },
        "repair_action_kind": (repair_action or {}).get("kind"),
        "repair_action_state": (repair_action or {}).get("action_state"),
        "repair_action_command": (repair_action or {}).get("command"),
        "repair_action_guidance": (repair_action or {}).get("guidance"),
    }


def _build_hpc_handoff_summary(
    *,
    result: dict,
    draft: Pion2ptTaskDraft,
    workflow_outcome: dict,
    artifacts: dict,
) -> dict:
    implementation_plan = result.get("implementation_plan") or {}
    handoff_contract = dict(implementation_plan.get("handoff_contract") or {})
    input_paths = list(handoff_contract.get("input_paths") or [])
    input_manifest = list(handoff_contract.get("input_manifest") or [])
    output_paths = dict(handoff_contract.get("output_paths") or {})
    if artifacts.get("script"):
        output_paths.setdefault("script", artifacts.get("script"))
    if artifacts.get("probe"):
        output_paths.setdefault("probe_artifact", artifacts.get("probe"))
    if draft.correlator_output_path:
        output_paths.setdefault("correlator", draft.correlator_output_path)
    input_directories = sorted(
        {
            str(Path(path).expanduser().resolve().parent)
            for path in input_paths
            if isinstance(path, str) and path
        }
    )
    output_directories = sorted(
        {
            str(Path(path).expanduser().resolve().parent)
            for path in output_paths.values()
            if isinstance(path, str) and path
        }
    )
    start_from = handoff_contract.get("start_from") or draft.start_from
    if start_from == "propagator":
        handoff_boundary = (
            "Stored propagators are the handoff boundary: this workflow only contracts validated input propagators and never regenerates inversions."
        )
        input_directory_policy = "treat_input_directories_as_read_only_handoff_storage"
        output_directory_policy = "prefer_dedicated_writable_results_directory"
    elif start_from == "gauge":
        handoff_boundary = (
            "Gauge input is the handoff boundary: this workflow regenerates the grounded inversion/contraction path from the supplied gauge configuration."
        )
        input_directory_policy = "treat_gauge_input_directories_as_shared_read_only_storage_when_possible"
        output_directory_policy = "write_new_outputs_to_explicit_writable_results_directory"
    else:
        handoff_boundary = "Review the structured task and implementation plan artifacts before cluster submission."
        input_directory_policy = "review_input_directory_visibility_and_mutability"
        output_directory_policy = "review_output_directory_writability_before_submission"
    return {
        "cluster_launch": handoff_contract.get("cluster_launch") or draft.cluster_launch,
        "resource_path": handoff_contract.get("resource_path") or draft.resource_path,
        "start_from": start_from,
        "input_paths": input_paths,
        "input_manifest": input_manifest,
        "input_path_count": len(input_paths),
        "input_directories": input_directories,
        "input_directory_policy": input_directory_policy,
        "input_mutability_policy": handoff_contract.get("input_mutability_policy") or "unspecified",
        "output_paths": output_paths,
        "output_directories": output_directories,
        "output_directory_count": len(output_directories),
        "output_directory_policy": output_directory_policy,
        "output_input_overlap_forbidden": bool(start_from == "propagator"),
        "input_visibility": handoff_contract.get("input_visibility") or "all_ranks",
        "output_writer_policy": handoff_contract.get("output_writer_policy") or "rank0_only",
        "required_modules": list(handoff_contract.get("required_modules") or ["numpy", "cupy", "pyquda_utils", "pyquda"]),
        "preflight_checks": list(handoff_contract.get("preflight_checks") or []),
        "submission_assumption": handoff_contract.get("submission_assumption"),
        "handoff_boundary": handoff_boundary,
        "runtime_level": workflow_outcome.get("runtime_level"),
        "generated_script_exists": bool(artifacts.get("script")),
        "probe_artifact": artifacts.get("probe"),
        "probe_command": result.get("probe_hint"),
    }


def _build_workflow_lifecycle(
    *,
    product_status: str,
    run_overview: dict,
    generation_result: dict,
    execution_result: dict,
    primary_action: dict | None,
    artifacts: dict,
) -> dict:
    return {
        "stage": product_status,
        "headline": run_overview.get("headline"),
        "detail": run_overview.get("detail"),
        "blocking_kind": run_overview.get("blocking_kind"),
        "generation": {
            "phase": generation_result.get("phase"),
            "ready": bool(generation_result.get("ready")),
            "emitted": bool(generation_result.get("emitted")),
            "succeeded": bool(generation_result.get("succeeded")),
            "script_path": generation_result.get("script_path"),
            "script_exists": bool(generation_result.get("script_exists")),
        },
        "runtime": {
            "phase": execution_result.get("phase"),
            "attempted": bool(execution_result.get("attempted")),
            "succeeded": execution_result.get("succeeded"),
            "probe_available": bool(execution_result.get("probe_available")),
            "blocked": bool(execution_result.get("blocked")),
            "runtime_level": execution_result.get("runtime_level"),
            "evidence_level": execution_result.get("evidence_level"),
            "probe_command": execution_result.get("probe_command"),
            "probe_artifact": execution_result.get("probe_artifact"),
        },
        "next": {
            "action_kind": (primary_action or {}).get("kind"),
            "action_title": (primary_action or {}).get("title"),
            "actionable": bool((primary_action or {}).get("actionable")),
            "command": (primary_action or {}).get("command"),
        },
        "artifacts": {
            "physics": artifacts.get("physics"),
            "task": artifacts.get("task"),
            "plan": artifacts.get("plan"),
            "script": artifacts.get("script"),
            "probe": artifacts.get("probe"),
            "session": artifacts.get("session"),
        },
    }


def _build_product_status(*, result: dict, workflow_outcome: dict) -> str:
    status = result.get("status")
    runtime_probe_status = workflow_outcome.get("runtime_probe_status")
    execution_status = workflow_outcome.get("execution_status")

    if status == "needs_input":
        return "needs_input"
    if status == "unsupported":
        return "unsupported"
    if status == "dry_run":
        return "ready_to_generate"
    if status == "ok":
        if execution_status == "runtime_proved":
            return "runtime_proved"
        if _runtime_probe_is_blocked(runtime_probe_status):
            return "generated_runtime_blocked"
        if runtime_probe_status == "not_requested":
            return "generated_probe_available"
        if runtime_probe_status in {"requested", "ok", "runtime_proved"}:
            return "generated_probe_in_progress"
        return "generated"
    return "in_progress"


def _build_clarification_status(
    *,
    result: dict,
    questions: list[dict],
    missing: list[str],
    pending_question_preview: list[dict],
    reply_hint: str | None,
    set_hint: str | None,
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    script_output_path: str | None,
) -> dict:
    status = result.get("status")
    batch_fields = [item.get("field_name") for item in questions if item.get("field_name")]
    preview_fields = [item.get("field_name") for item in pending_question_preview if item.get("field_name")]
    field_groups = build_group_metadata(
        batch_fields=batch_fields,
        example_value_for_field=lambda field_name: _example_set_value(
            field_name,
            physics=physics,
            draft=draft,
            script_output_path=script_output_path,
        ),
        set_assignment_token=_set_assignment_token,
    )
    return {
        "active": status == "needs_input",
        "mode": "physics_confirmation" if missing == ["confirmed_target_id"] else ("task_fields" if status == "needs_input" else "not_applicable"),
        "missing_fields_total": len(missing),
        "question_batch_total": len(batch_fields),
        "question_batch_fields": batch_fields,
        "preview_fields": preview_fields,
        "preview_truncated": len(preview_fields) < len(batch_fields),
        "field_groups": field_groups,
        "recommended_answer_mode": _recommended_answer_mode(
            field_groups=field_groups,
            batch_fields=batch_fields,
            has_reply_hint=bool(reply_hint),
            has_set_hint=bool(set_hint),
        ),
        "has_reply_hint": bool(reply_hint),
        "has_set_hint": bool(set_hint),
    }


def _recommended_answer_mode(
    *,
    field_groups: list[dict],
    batch_fields: list[str],
    has_reply_hint: bool,
    has_set_hint: bool,
) -> str | None:
    if has_set_hint:
        for group in field_groups:
            if group.get("recommended_input_mode") != "set":
                continue
            return "set"
    if has_reply_hint:
        return "reply"
    if has_set_hint:
        return "set"
    return None


def _clarification_batch_summary(result: dict) -> str | None:
    clarification_status = result.get("clarification_status") or {}
    fields = clarification_status.get("question_batch_fields") or []
    if not fields:
        return None
    return ", ".join(fields)


def _clarification_group_label(result: dict) -> str | None:
    clarification_status = result.get("clarification_status") or {}
    field_groups = clarification_status.get("field_groups") or []
    if not field_groups:
        return None
    first_group = field_groups[0]
    label = first_group.get("label")
    if not label:
        return None
    if first_group.get("complete_in_batch"):
        return label
    return f"partial {label}"


def _group_set_command_hint(
    *,
    config: RunConfig,
    session_path: Path | None,
    script_output_path: str | None,
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    missing_fields: list[str],
    questions: list[dict] | None,
    clarification_status: dict,
) -> str | None:
    field_groups = clarification_status.get("field_groups") or []
    grouped_candidates = [item for item in field_groups if item.get("set_example")]
    if not grouped_candidates:
        return None
    effective_session_path = session_path or _effective_session_path(config, script_output_path)
    if effective_session_path is None:
        return None
    output_path = _effective_output_path(config, script_output_path)
    parts: list[str] = []
    consumed_fields: set[str] = set()
    for group in grouped_candidates:
        parts.append(group["set_example"])
        consumed_fields.update(group.get("fields") or [])
    for field_name in _hint_set_fields(missing_fields, questions):
        if field_name in consumed_fields:
            continue
        example_value = _example_set_value(
            field_name,
            physics=physics,
            draft=draft,
            script_output_path=script_output_path,
        )
        parts.append(_set_assignment_token(field_name, example_value))
    command_parts = [
        "PYTHONPATH=src python3 -m pyquda_agent.cli run",
        json.dumps(config.task_description),
        f"--resume-session {str(effective_session_path)!r}",
        *parts,
        *_continuation_flag_parts(config),
        f"--output {str(output_path)!r}",
        f"--pyquda-repo {str(config.pyquda_repo)!r}",
    ]
    return " ".join(command_parts)


def _rewrite_cli_flag(command: str | None, flag: str, value: str) -> str | None:
    if not command:
        return None
    tokens = shlex.split(command)
    for idx, token in enumerate(tokens[:-1]):
        if token == flag:
            tokens[idx + 1] = value
            return shlex.join(tokens)
    tokens.extend([flag, value])
    return shlex.join(tokens)


def _remove_cli_flag(command: str | None, flag: str) -> str | None:
    if not command:
        return None
    tokens = shlex.split(command)
    rewritten: list[str] = []
    for token in tokens:
        if token == flag:
            continue
        rewritten.append(token)
    return shlex.join(rewritten)


def _suggest_api_backend_retry(base_command: str | None, model: str = "openai/gpt-5-mini") -> str | None:
    rewritten = _rewrite_cli_flag(base_command, "--backend", "api")
    return _rewrite_cli_flag(rewritten, "--model", model)


def _suggest_llm_timeout_retry(config: RunConfig, base_command: str | None) -> str | None:
    if not base_command:
        return None
    next_timeout = max(10.0, config.llm_timeout * 2.0)
    return _rewrite_cli_flag(base_command, "--llm-timeout", str(next_timeout))


def _backend_fix_command(config: RunConfig, result: dict, backend_diagnostic: dict | None) -> str | None:
    if not isinstance(backend_diagnostic, dict):
        return None
    category = backend_diagnostic.get("category")
    detail_category = backend_diagnostic.get("detail_category")
    selected_backend = backend_diagnostic.get("selected_backend")
    requested_backend = backend_diagnostic.get("requested_backend")
    intent_primary_timeout_seconds = backend_diagnostic.get("intent_primary_timeout_seconds")
    intent_timeout_capped = bool(backend_diagnostic.get("intent_timeout_capped"))
    resume_hint = result.get("resume_hint")
    if category == "configuration_missing":
        if requested_backend == "api":
            return _suggest_api_backend_retry(resume_hint)
        if requested_backend == "auto":
            return _suggest_api_backend_retry(resume_hint)
    if category == "local_executable_missing":
        return _suggest_api_backend_retry(resume_hint)
    if category == "local_environment_error":
        if detail_category == "codex_app_client_init_failed":
            return "codex exec 'Reply with exactly: OK'"
    if category == "network_error":
        return resume_hint
    if category == "authentication_error" and selected_backend == "codex":
        return "codex login"
    if category == "authentication_error" and requested_backend == "api":
        return resume_hint
    if category == "timeout":
        if selected_backend == "codex" and intent_primary_timeout_seconds and intent_timeout_capped:
            return _suggest_api_backend_retry(resume_hint) or resume_hint
        return _suggest_llm_timeout_retry(config, resume_hint)
    if category == "rate_limited":
        return _suggest_api_backend_retry(resume_hint) or _suggest_llm_timeout_retry(config, resume_hint) or resume_hint
    if category == "upstream_service_error":
        return _suggest_api_backend_retry(resume_hint) or _suggest_llm_timeout_retry(config, resume_hint) or resume_hint
    if category in {"endpoint_not_found", "request_error"}:
        return resume_hint
    if category in {"response_parse_error", "empty_response"}:
        return _suggest_llm_timeout_retry(config, resume_hint) or resume_hint
    if category in {"backend_process_error", "unexpected_error"}:
        return resume_hint
    return None


def _backend_fix_title(backend_diagnostic: dict | None) -> str:
    if not isinstance(backend_diagnostic, dict):
        return "Fix backend assistance and retry if you still want LLM help"
    category = backend_diagnostic.get("category")
    detail_category = backend_diagnostic.get("detail_category")
    selected_backend = backend_diagnostic.get("selected_backend")
    requested_backend = backend_diagnostic.get("requested_backend")
    intent_primary_timeout_seconds = backend_diagnostic.get("intent_primary_timeout_seconds")
    intent_timeout_capped = bool(backend_diagnostic.get("intent_timeout_capped"))
    if category == "configuration_missing":
        if requested_backend == "api":
            return "Add an API model and retry backend assistance"
        if requested_backend == "auto":
            return "Configure an API backup or local codex, then retry backend assistance"
        return "Complete backend configuration and retry"
    if category == "configuration_invalid":
        return "Fix backend configuration and retry"
    if category == "credentials_missing":
        return "Add API credentials before retrying backend assistance"
    if category == "local_executable_missing":
        return "Switch to an API backend or install local codex"
    if category == "local_environment_error":
        if detail_category == "codex_app_client_init_failed":
            return "Verify local codex exec in a normal shell"
        if detail_category == "local_permission_error":
            return "Repair local codex permissions or switch backend"
        return "Repair the local codex environment or switch backend"
    if category == "authentication_error" and selected_backend == "codex":
        return "Run codex login and retry"
    if category == "authentication_error":
        return "Fix backend authentication and retry"
    if category == "network_error":
        if detail_category == "dns_resolution_failure":
            return "Restore DNS/network access before retrying backend assistance"
        if detail_category == "connection_refused":
            return "Check backend endpoint reachability before retrying"
        return "Restore network access before retrying backend assistance"
    if category == "timeout":
        if selected_backend == "codex" and intent_primary_timeout_seconds and intent_timeout_capped:
            return "Switch to an API backend for this request"
        return "Increase backend timeout and retry"
    if category == "rate_limited":
        return "Retry later or switch backend provider"
    if category == "upstream_service_error":
        return "Retry later or switch backend provider"
    if category in {"endpoint_not_found", "request_error"}:
        return "Fix backend endpoint or request settings and retry"
    if category in {"response_parse_error", "empty_response"}:
        return "Retry backend assistance or switch backend"
    if category in {"backend_process_error", "unexpected_error"}:
        return "Inspect the backend failure and retry"
    return "Fix backend assistance and retry if you still want LLM help"


def _backend_fix_state(backend_diagnostic: dict | None) -> tuple[str, str | None]:
    if not isinstance(backend_diagnostic, dict):
        return "blocked", None
    category = backend_diagnostic.get("category")
    detail_category = backend_diagnostic.get("detail_category")
    selected_backend = backend_diagnostic.get("selected_backend")
    requested_backend = backend_diagnostic.get("requested_backend")
    intent_primary_timeout_seconds = backend_diagnostic.get("intent_primary_timeout_seconds")
    intent_timeout_capped = bool(backend_diagnostic.get("intent_timeout_capped"))
    if category == "configuration_missing":
        if requested_backend == "api":
            return "conditional", "Re-run will add a model, but API credentials may still be required."
        if requested_backend == "auto":
            return "conditional", "Re-run may still require API credentials or a local codex installation."
        return "conditional", "Backend configuration still needs to be completed."
    if category == "configuration_invalid":
        return "conditional", "Requires correcting backend/provider configuration before retrying."
    if category == "local_executable_missing":
        return "conditional", "Switching to an API backend may help, but API credentials may still be required."
    if category == "local_environment_error":
        if detail_category == "codex_app_client_init_failed":
            return "conditional", "Requires checking whether bare `codex exec` works in a normal local shell outside the current sandbox before retrying or switching backend."
        if detail_category == "local_permission_error":
            return "conditional", "Requires fixing local codex permissions or environment restrictions before retrying."
        return "conditional", "Retry may require fixing the local codex environment or switching to an API backend."
    if category == "authentication_error" and selected_backend == "codex":
        return "ready", None
    if category == "authentication_error":
        return "conditional", "Requires correcting backend authentication before retrying."
    if category == "timeout":
        if selected_backend == "codex" and intent_primary_timeout_seconds and intent_timeout_capped:
            return "conditional", "This codex intent path already uses a short capped first-attempt timeout; switching backend may help more than increasing --llm-timeout."
        return "ready", None
    if category == "rate_limited":
        return "conditional", "Retry later or switch backend if another provider is available."
    if category == "upstream_service_error":
        return "conditional", "Retry later or switch backend if another provider is available."
    if category in {"endpoint_not_found", "request_error"}:
        return "conditional", "Requires correcting backend endpoint or request configuration before retrying."
    if category in {"response_parse_error", "empty_response"}:
        return "conditional", "Retry may work, but switching backend may be necessary if the provider keeps returning incompatible responses."
    if category == "credentials_missing":
        return "blocked", "Requires API credentials to be configured before retrying."
    if category == "network_error":
        if detail_category == "dns_resolution_failure":
            return "blocked", "Requires restoring DNS resolution or general network connectivity before retrying backend assistance."
        if detail_category == "connection_refused":
            return "blocked", "Requires checking backend endpoint reachability or provider connectivity before retrying."
        return "blocked", "Requires network connectivity before retrying backend assistance."
    if category in {"backend_process_error", "unexpected_error"}:
        return "conditional", "Requires inspecting the backend failure before retrying or switching backend."
    return "blocked", None


def _runtime_fix_title(runtime_diagnostic: dict | None) -> str:
    if not isinstance(runtime_diagnostic, dict):
        return "Repair the runtime blockers before retrying the probe"
    category = runtime_diagnostic.get("category")
    if category == "environment_missing":
        return "Repair the runtime environment before retrying the probe"
    if category == "probe_driver_failed":
        return "Inspect the probe artifact and repair the harness-side failure"
    if category == "input_visibility_blocked":
        return "Fix input visibility before retrying the probe"
    if category == "output_writability_blocked":
        return "Fix output-directory writability before retrying the probe"
    if category == "cluster_assumption_mismatch":
        return "Fix cluster-layout assumptions before retrying the probe"
    if category == "artifact_chain_missing":
        return "Restore sibling review artifacts before retrying the probe"
    if category == "handoff_contract_mismatch":
        return "Fix the handoff contract before retrying the probe"
    if category == "probe_timeout":
        return "Increase probe timeout or reduce startup latency"
    return "Repair the runtime blockers before retrying the probe"


def _runtime_fix_state(runtime_diagnostic: dict | None) -> tuple[str, str | None]:
    if not isinstance(runtime_diagnostic, dict):
        return "blocked", None
    category = runtime_diagnostic.get("category")
    if category == "environment_missing":
        return (
            "conditional",
            "Requires a PyQUDA runtime with the missing dependencies and input visibility before the probe can succeed.",
        )
    if category == "probe_driver_failed":
        return (
            "conditional",
            "Requires inspecting the probe artifact and fixing the harness-side failure before retrying.",
        )
    if category == "input_visibility_blocked":
        return "conditional", "Requires making all input paths visible on the target filesystem before retrying."
    if category == "output_writability_blocked":
        return "conditional", "Requires a writable output directory on the target filesystem before retrying."
    if category == "cluster_assumption_mismatch":
        return "conditional", "Requires aligning lattice/grid/resource-path assumptions with the target launch layout before retrying."
    if category == "artifact_chain_missing":
        return "conditional", "Requires restoring the sibling review artifacts next to the generated script before retrying."
    if category == "handoff_contract_mismatch":
        return "conditional", "Requires correcting generated-script handoff inputs or fixed workflow parameters before retrying."
    if category == "probe_timeout":
        return "conditional", "Requires increasing probe timeout or reducing runtime startup latency before retrying."
    if category == "runtime_blocked":
        return "conditional", "Requires resolving the current runtime blockers before the probe can succeed."
    return "blocked", None


def _build_action_queue(*, config: RunConfig, result: dict, workflow_outcome: dict, backend_diagnostic: dict | None) -> list[dict]:
    actions: list[dict] = []
    status = result.get("status")
    reply_hint = result.get("reply_hint")
    set_hint = result.get("set_hint")
    group_set_hint = result.get("group_set_hint")
    resume_hint = result.get("resume_hint")
    probe_hint = result.get("probe_hint")
    runtime_diagnostic = result.get("runtime_diagnostic") or {}
    clarification_status = result.get("clarification_status") or {}
    unsupported_guidance = result.get("unsupported_guidance") or {}
    batch_summary = _clarification_batch_summary(result)
    group_label = _clarification_group_label(result)
    recommended_answer_mode = clarification_status.get("recommended_answer_mode")

    if status == "needs_input":
        prefer_set = recommended_answer_mode == "set"
        reply_action = (
            {
                "kind": "continue_by_reply",
                "priority": "secondary" if prefer_set else "primary",
                "title": (
                    f"Continue by replying in order for: {batch_summary}"
                    if batch_summary
                    else "Continue by answering the next clarification questions in order"
                )
                + (f" [{group_label}]" if group_label else ""),
                "command": reply_hint,
                "guidance": (
                    workflow_outcome.get("next_step")
                    if recommended_answer_mode == "reply" or not batch_summary
                    else f"{workflow_outcome.get('next_step')} Current batch: {batch_summary}."
                ),
            }
            if reply_hint
            else None
        )
        set_action = (
            {
                "kind": "continue_by_set",
                "priority": "primary" if prefer_set else "secondary",
                "title": (
                    f"Continue by setting fields explicitly for: {batch_summary}"
                    if batch_summary
                    else "Continue by setting the missing fields explicitly"
                )
                + (f" [{group_label}]" if group_label else ""),
                "command": group_set_hint or set_hint,
                "guidance": (
                    "Use explicit field assignments when you do not want to answer by question order."
                    if not batch_summary
                    else (
                        f"Use grouped explicit assignments for the current batch: {batch_summary}."
                        if group_set_hint
                        else f"Use explicit field assignments for the current batch: {batch_summary}."
                    )
                ),
            }
            if (group_set_hint or set_hint)
            else None
        )
        if recommended_answer_mode == "set":
            _append_action(actions, set_action)
            _append_action(actions, reply_action)
        else:
            _append_action(actions, reply_action)
            _append_action(actions, set_action)
    elif status == "unsupported":
        shortest_fix = unsupported_guidance.get("shortest_fix") or {}
        repair_hint = unsupported_guidance.get("repair_hint") or {}
        workflow_label = shortest_fix.get("label") or shortest_fix.get("workflow_target") or "nearest grounded workflow"
        retry_command = shortest_fix.get("retry_command")
        if retry_command:
            _append_action(
                actions,
                {
                    "kind": "retry_supported_workflow",
                    "priority": "primary",
                    "title": f"Retry with nearest grounded workflow: {workflow_label}",
                    "command": retry_command,
                    "guidance": unsupported_guidance.get("next_step") or shortest_fix.get("summary"),
                },
            )
        elif repair_hint.get("mode") == "choice_required":
            choice_field = repair_hint.get("choice_field") or "one field"
            choice_values = list(repair_hint.get("choice_values") or [])
            values_text = " / ".join(str(item) for item in choice_values) if choice_values else "supported values"
            _append_action(
                actions,
                {
                    "kind": "choose_supported_variant",
                    "priority": "primary",
                    "title": f"Choose {choice_field} ({values_text}) before retrying {workflow_label}",
                    "command": None,
                    "action_state": "conditional",
                    "actionable": False,
                    "actionability_reason": repair_hint.get("summary"),
                    "guidance": unsupported_guidance.get("next_step") or shortest_fix.get("summary"),
                },
            )
            for variant in shortest_fix.get("variant_retry_commands") or []:
                _append_action(
                    actions,
                    {
                        "kind": "retry_supported_variant",
                        "priority": "secondary",
                        "title": f"Retry {workflow_label} with {variant.get('field_name')}={variant.get('accepted_value')}",
                        "command": variant.get("command"),
                        "guidance": shortest_fix.get("summary") or unsupported_guidance.get("next_step"),
                    }
                    if variant.get("command")
                    else None,
                )
        else:
            _append_action(
                actions,
                {
                    "kind": "review_supported_workflows",
                    "priority": "primary",
                    "title": f"Review nearby grounded workflows for {workflow_label}",
                    "command": None,
                    "action_state": "conditional",
                    "actionable": False,
                    "actionability_reason": repair_hint.get("summary") or unsupported_guidance.get("next_step"),
                    "guidance": unsupported_guidance.get("next_step") or shortest_fix.get("summary"),
                },
            )
    elif status == "dry_run":
        _append_action(
            actions,
            {
                "kind": "generate_script",
                "priority": "primary",
                "title": "Re-run without --dry-run to emit the grounded script",
                "command": _remove_cli_flag(resume_hint, "--dry-run"),
                "guidance": workflow_outcome.get("next_step"),
            }
            if resume_hint
            else None,
        )
    elif status == "ok":
        if workflow_outcome.get("runtime_probe_status") == "not_requested":
            _append_action(
                actions,
                {
                    "kind": "run_probe",
                    "priority": "primary",
                    "title": "Run the generated-script probe",
                    "command": probe_hint,
                    "guidance": workflow_outcome.get("next_step"),
                }
                if probe_hint
                else None,
            )
        elif workflow_outcome.get("runtime_probe_status") not in {"ok", "runtime_proved"}:
            retry_title = "Retry the generated-script probe after addressing blockers"
            retry_guidance = workflow_outcome.get("next_step")
            if runtime_diagnostic.get("category") == "probe_driver_failed":
                retry_title = "Retry the probe after fixing the harness-side failure"
                retry_guidance = runtime_diagnostic.get("next_step") or retry_guidance
            elif runtime_diagnostic.get("category") == "environment_missing":
                retry_title = "Retry the probe after fixing the runtime environment"
                retry_guidance = runtime_diagnostic.get("next_step") or retry_guidance
            _append_action(
                actions,
                {
                    "kind": "retry_probe",
                    "priority": "primary",
                    "title": retry_title,
                    "command": probe_hint,
                    "guidance": retry_guidance,
                }
                if probe_hint
                else None,
            )
            if runtime_diagnostic.get("category") in {"probe_driver_failed", "environment_missing", "runtime_blocked"}:
                action_state, actionability_reason = _runtime_fix_state(runtime_diagnostic)
                _append_action(
                    actions,
                    {
                        "kind": "runtime_fix",
                        "priority": "secondary",
                        "title": _runtime_fix_title(runtime_diagnostic),
                        "command": None,
                        "action_state": action_state,
                        "actionable": False,
                        "actionability_reason": actionability_reason,
                        "guidance": runtime_diagnostic.get("recommended_fix") or runtime_diagnostic.get("next_step"),
                    },
                )

    runtime_proved = workflow_outcome.get("execution_status") == "runtime_proved" or workflow_outcome.get("runtime_probe_status") == "runtime_proved"
    if (
        status != "unsupported"
        and not runtime_proved
        and isinstance(backend_diagnostic, dict)
        and backend_diagnostic.get("status") == "fallback"
    ):
        backend_fix_command = _backend_fix_command(config, result, backend_diagnostic)
        action_state, actionability_reason = _backend_fix_state(backend_diagnostic)
        _append_action(
            actions,
            {
                "kind": "backend_fix",
                "priority": "secondary",
                "title": _backend_fix_title(backend_diagnostic),
                "command": backend_fix_command,
                "action_state": action_state,
                "actionable": action_state == "ready" and bool(backend_fix_command),
                "actionability_reason": actionability_reason,
                "guidance": backend_diagnostic.get("recommended_fix") or backend_diagnostic.get("next_step"),
            },
        )

    if status not in {"unsupported", "ok"} and not actions and resume_hint:
        _append_action(
            actions,
            {
                "kind": "resume",
                "priority": "secondary",
                "title": "Resume the current run state",
                "command": resume_hint,
                "guidance": workflow_outcome.get("next_step"),
            },
        )
    return actions


def _attach_result_summary(
    *,
    config: RunConfig,
    result: dict,
    draft: Pion2ptTaskDraft,
    physics: PhysicsTargetArtifact,
    workflow_match: WorkflowMatchResult,
    missing: list[str],
    questions: list[dict],
    task_artifact: Path | None,
    physics_artifact: Path | None,
    plan_artifact: Path | None,
    session_path: Path | None,
) -> None:
    result["result_summary"] = _build_result_summary(
        config=config,
        result=result,
        draft=draft,
        physics=physics,
        workflow_match=workflow_match,
        missing=missing,
        questions=questions,
        task_artifact=task_artifact,
        physics_artifact=physics_artifact,
        plan_artifact=plan_artifact,
        session_path=session_path,
    )
    result["product_status"] = result["result_summary"]["product_status"]
    result["clarification_status"] = result["result_summary"]["clarification_status"]
    result["group_set_hint"] = result["result_summary"].get("group_set_hint")
    result["workflow_outcome"] = result["result_summary"]["workflow_outcome"]
    result["delivery_status"] = result["result_summary"]["delivery_status"]
    result["generation_result"] = result["result_summary"]["generation_result"]
    result["execution_result"] = result["result_summary"]["execution_result"]
    result["execution_closure"] = result["result_summary"]["execution_closure"]
    result["execution_checkpoint"] = result["result_summary"]["execution_checkpoint"]
    result["workflow_lifecycle"] = result["result_summary"]["workflow_lifecycle"]
    result["capability_summary"] = result["result_summary"]["capability_summary"]
    result["terminal_message"] = result["result_summary"]["terminal_message"]
    result["action_queue"] = result["result_summary"]["action_queue"]
    result["primary_action"] = result["result_summary"]["primary_action"]
    result["run_overview"] = result["result_summary"]["run_overview"]
    result["backend_diagnostic"] = result["result_summary"]["backend_diagnostic"]
    result["backend_path"] = result["result_summary"]["backend_path"]
    result["hpc_handoff"] = result["result_summary"]["hpc_handoff"]
    result["runtime_diagnostic"] = result["result_summary"]["runtime_diagnostic"]
    result["blocking_reason"] = result["result_summary"]["blocking_reason"]
    result["blocking_reason_detail"] = result["result_summary"]["blocking_reason_detail"]
    result["inspection_hint"] = result["result_summary"]["inspection_hint"]
    result["frontend_profile"] = result["result_summary"]["frontend_profile"]
    result["supported_workflows"] = result["result_summary"]["supported_workflows"]
    result["nearby_supported_workflows"] = result["result_summary"]["nearby_supported_workflows"]
    result["unsupported_guidance"] = result["result_summary"]["unsupported_guidance"]
    result["physics_workflow_preview"] = result["result_summary"]["physics_workflow_preview"]
    result["physics_workflow_preview_truncated"] = result["result_summary"]["physics_workflow_preview_truncated"]


def _candidate_target_preview_ids(physics: PhysicsTargetArtifact, *, max_items: int = 4) -> list[str]:
    candidate_ids: list[str] = []
    for item in physics.candidate_targets:
        if len(candidate_ids) >= max_items:
            break
        target_id = item.get("target_id")
        if isinstance(target_id, str) and target_id and target_id not in candidate_ids:
            candidate_ids.append(target_id)
    return candidate_ids


def _formula_preview_text(physics: PhysicsTargetArtifact, *, max_items: int = 2) -> str | None:
    parts: list[str] = []
    for item in physics.formula_proposals[:max_items]:
        if not isinstance(item, dict):
            continue
        target_id = item.get("target_id")
        label = item.get("label")
        operator = item.get("operator")
        if not isinstance(target_id, str) or not isinstance(label, str):
            continue
        alias = _physics_target_alias(target_id) or target_id
        segment = f"{alias}: {label}"
        if isinstance(operator, str) and operator:
            compact_operator = " ".join(operator.split())
            if len(compact_operator) > 96:
                compact_operator = compact_operator[:93].rstrip() + "..."
            segment += f" (operator={compact_operator})"
        parts.append(segment)
    if not parts:
        return None
    return "; ".join(parts)


def _workflow_preview_text(
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    *,
    max_items: int = 2,
    max_workflows_per_target: int = 2,
) -> str | None:
    preview, _truncated = _build_physics_workflow_preview(physics, draft, max_items=max_items)
    parts: list[str] = []
    for item in preview:
        target_id = item.get("target_id")
        workflows = [str(workflow) for workflow in item.get("grounded_workflow_targets") or [] if workflow]
        if not isinstance(target_id, str) or not workflows:
            continue
        shown = workflows[:max_workflows_per_target]
        segment = f"{target_id} -> {', '.join(shown)}"
        remaining = len(workflows) - len(shown)
        if remaining > 0:
            segment += f" (+{remaining} more)"
        parts.append(segment)
    if not parts:
        return None
    return "; ".join(parts)


def _next_action_with_preview(
    base: str,
    pending_question_preview: list[dict],
    *,
    candidate_targets: list[str] | None = None,
    formula_preview: str | None = None,
    workflow_preview: str | None = None,
) -> str:
    if not pending_question_preview:
        if candidate_targets:
            suffix = f" Candidates: {', '.join(candidate_targets)}."
            if formula_preview:
                suffix += f" Formula hints: {formula_preview}."
            if workflow_preview:
                suffix += f" Workflow hints: {workflow_preview}."
            return f"{base}{suffix}"
        return base
    fields = [item.get("field_name") for item in pending_question_preview if item.get("field_name")]
    suffixes: list[str] = []
    if candidate_targets:
        suffixes.append(f"Candidates: {', '.join(candidate_targets)}.")
    if formula_preview:
        suffixes.append(f"Formula hints: {formula_preview}.")
    if workflow_preview:
        suffixes.append(f"Workflow hints: {workflow_preview}.")
    if fields:
        suffixes.append(f"Current batch: {', '.join(fields)}.")
    if suffixes:
        return f"{base} {' '.join(suffixes)}"
    return base


def _effective_output_path(config: RunConfig, script_output_path: str | None = None) -> Path:
    if script_output_path:
        return Path(script_output_path).expanduser().resolve()
    return config.output.expanduser().resolve()


def _continuation_flag_parts(config: RunConfig) -> list[str]:
    parts = [f"--backend {shlex.quote(config.backend)}"]
    if config.model:
        parts.append(f"--model {shlex.quote(config.model)}")
    if config.base_url:
        parts.append(f"--base-url {shlex.quote(config.base_url)}")
    if config.api_key_file != DEFAULT_API_KEY_FILE:
        parts.append(f"--api-key-file {shlex.quote(str(config.api_key_file))}")
    if not config.interactive:
        parts.append("--no-interactive")
    if config.max_questions != 7:
        parts.append(f"--max-questions {config.max_questions}")
    if config.print_context:
        parts.append("--print-context")
    if config.dry_run:
        parts.append("--dry-run")
    if config.verbose:
        parts.append("--verbose")
    if config.result_format == "summary":
        parts.append("--result-format summary")
    elif config.result_format == "terminal":
        parts.append("--result-format terminal")
    if config.enable_external_lookup:
        parts.append("--enable-external-lookup")
    if config.llm_timeout != 30.0:
        parts.append(f"--llm-timeout {config.llm_timeout}")
    if config.runtime_probe:
        parts.append("--runtime-probe")
    if config.probe_timeout != 30.0:
        parts.append(f"--probe-timeout {config.probe_timeout}")
    if config.probe_use_repo_pythonpath:
        parts.append("--probe-use-repo-pythonpath")
    return parts


def _resume_command_hint(config: RunConfig, session_path: Path, script_output_path: str | None = None) -> str:
    output_path = _effective_output_path(config, script_output_path)
    command_parts = [
        "PYTHONPATH=src python3 -m pyquda_agent.cli run",
        json.dumps(config.task_description),
        f"--resume-session {str(session_path)!r}",
        f"--output {str(output_path)!r}",
        *_continuation_flag_parts(config),
        f"--pyquda-repo {str(config.pyquda_repo)!r}",
    ]
    return " ".join(command_parts)


def _example_set_value(
    field_name: str,
    *,
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    script_output_path: str | None = None,
) -> str:
    workflow = getattr(draft, "chosen_workflow_target", None) or draft.workflow_id
    if field_name == "confirmed_target_id":
        inferred = (physics.inferred_interpretation or {}).get("target_id")
        if inferred == PION_TARGET_ID:
            return "pion"
        if inferred == PION_DISPERSION_TARGET_ID:
            return "pion dispersion"
        if inferred == MESON_SPEC_TARGET_ID:
            return "meson spectrum"
        if inferred == RHO_TARGET_ID:
            return "rho"
        if inferred == PROTON_TARGET_ID:
            return "proton"
        if inferred == NEUTRON_TARGET_ID:
            return "neutron"
        if inferred == QUARK_PROPAGATOR_TARGET_ID:
            if physics.clarified_fields.get("source_smearing_kind") == "gaussian_shell":
                return "gaussian shell propagator"
            return "quark propagator"
        if inferred == STOUT_SMEAR_TARGET_ID:
            return "stout smear"
        if inferred == WILSON_FLOW_TARGET_ID:
            return "wilson flow"
        if inferred == HADRON_UNSPECIFIED_TARGET_ID:
            tail_targets = [item.get("target_id") for item in physics.candidate_targets[1:] if isinstance(item, dict)]
            if MESON_UNSPECIFIED_TARGET_ID in tail_targets and BARYON_UNSPECIFIED_TARGET_ID in tail_targets:
                return "meson"
            for target_id in tail_targets:
                if target_id == PION_TARGET_ID:
                    return "pion"
                if target_id == PION_DISPERSION_TARGET_ID:
                    return "pion dispersion"
                if target_id == MESON_SPEC_TARGET_ID:
                    return "meson spectrum"
                if target_id == RHO_TARGET_ID:
                    return "rho"
                if target_id == PROTON_TARGET_ID:
                    return "proton"
                if target_id == NEUTRON_TARGET_ID:
                    return "neutron"
            return "pion"
        if inferred == BARYON_UNSPECIFIED_TARGET_ID:
            return "proton"
        if inferred == MESON_UNSPECIFIED_TARGET_ID:
            return "pion"
        for candidate in physics.candidate_targets:
            target_id = candidate.get("target_id")
            if target_id == PION_TARGET_ID:
                return "pion"
            if target_id == PION_DISPERSION_TARGET_ID:
                return "pion dispersion"
            if target_id == MESON_SPEC_TARGET_ID:
                return "meson spectrum"
            if target_id == PROTON_TARGET_ID:
                return "proton"
            if target_id == NEUTRON_TARGET_ID:
                return "neutron"
            if target_id == QUARK_PROPAGATOR_TARGET_ID:
                return "quark propagator"
            if target_id == STOUT_SMEAR_TARGET_ID:
                return "stout smear"
        return "pion"
    if field_name == "start_from":
        if workflow == "pion_2pt_existing_propagator_local_zero_momentum_npy_v1":
            return "propagator"
        return "gauge"
    if field_name == "has_existing_propagators":
        return "yes" if workflow == "pion_2pt_existing_propagator_local_zero_momentum_npy_v1" else "no"
    if field_name == "gauge_path":
        return "/path/to/config.lime"
    if field_name == "propagator_format":
        return "npy"
    if field_name == "propagator_paths":
        return "/path/to/propagator.npy"
    if field_name == "lattice_size":
        return "24 24 24 72"
    if field_name == "grid_size":
        return "1 1 1 2"
    if field_name == "fermion_action":
        return "clover"
    if field_name == "mass":
        return "0.09253"
    if field_name == "xi_0":
        return "4.8965"
    if field_name == "nu":
        return "0.86679"
    if field_name == "coeff_t":
        return "0.8549165664"
    if field_name == "coeff_r":
        return "2.32582045"
    if field_name == "solver_tol":
        return "1e-12"
    if field_name == "solver_maxiter":
        return "1000"
    if field_name == "flow_steps":
        return "100"
    if field_name == "flow_epsilon":
        return "1.0"
    if field_name == "source_type":
        if workflow == "pion_dispersion_chroma_point_momentum_npy_v1":
            return "point"
        if workflow in {QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID}:
            return "point"
        if workflow == HYP_SMEAR_WORKFLOW_ID:
            return "none"
        if workflow == STOUT_SMEAR_WORKFLOW_ID:
            return "none"
        if workflow == WILSON_FLOW_WORKFLOW_ID:
            return "none"
        return "wall"
    if field_name == "sink_type":
        if workflow in {QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID}:
            return "propagator"
        if workflow == HYP_SMEAR_WORKFLOW_ID:
            return "gauge"
        if workflow == STOUT_SMEAR_WORKFLOW_ID:
            return "gauge"
        if workflow == WILSON_FLOW_WORKFLOW_ID:
            return "gauge"
        return "local"
    if field_name == "momentum_projection":
        if workflow in {"pion_dispersion_chroma_point_momentum_npy_v1", MESON_SPEC_WORKFLOW_ID}:
            return "explicit"
        if workflow in {QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID}:
            return "none"
        if workflow == HYP_SMEAR_WORKFLOW_ID:
            return "none"
        if workflow == STOUT_SMEAR_WORKFLOW_ID:
            return "none"
        if workflow == WILSON_FLOW_WORKFLOW_ID:
            return "none"
        return "zero"
    if field_name == "momenta":
        return "0 0 0"
    if field_name == "source_timeslices":
        return "0"
    if field_name == "gauge_fixed":
        return "yes"
    if field_name == "correlator_output_format":
        if workflow in {QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID}:
            return "hdf5"
        return "npy"
    if field_name == "correlator_output_path":
        if workflow in {QUARK_PROPAGATOR_WORKFLOW_ID, QUARK_PROPAGATOR_GAUSSIAN_SHELL_WORKFLOW_ID}:
            return "outputs/pt_prop.h5"
        if workflow == APE_SMEAR_WORKFLOW_ID:
            return "outputs/ape_smeared_gauge.npy"
        if workflow == HYP_SMEAR_WORKFLOW_ID:
            return "outputs/hyp_smeared_gauge.npy"
        if workflow == STOUT_SMEAR_WORKFLOW_ID:
            return "outputs/stout_smeared_gauge.npy"
        if workflow == WILSON_FLOW_WORKFLOW_ID:
            return "outputs/wilson_flow_energy.npy"
        return "outputs/pion.npy"
    if field_name == "resource_path":
        return ".cache/quda"
    if field_name == "cluster_launch":
        return "slurm"
    if field_name == "script_output_path":
        if script_output_path:
            return script_output_path
        return f"outputs/{_default_script_basename_for_target(physics, draft)}"
    if field_name == "script_style":
        return "complete"
    return "<value>"


def _set_assignment_token(field_name: str, example_value: str) -> str:
    return f"--set {shlex.quote(f'{field_name}={example_value}')}"


def _reply_argument_token(answer: str) -> str:
    return f"--reply {shlex.quote(answer)}"


def _answer_kind(field_name: str, *, category: str | None = None) -> str:
    if field_name in {"confirmed_target_id", "start_from", "source_type", "sink_type", "momentum_projection", "fermion_action", "propagator_format", "cluster_launch", "script_style"}:
        return "choice"
    if field_name in {"gauge_fixed", "has_existing_propagators"}:
        return "boolean"
    if field_name in {"source_timeslices", "lattice_size", "grid_size", "momenta"}:
        return "integer_list"
    if field_name in {"mass", "xi_0", "nu", "coeff_t", "coeff_r", "solver_tol"}:
        return "number"
    if field_name == "solver_maxiter":
        return "integer"
    if field_name in {"gauge_path", "propagator_paths", "correlator_output_path", "resource_path", "script_output_path"}:
        return "path"
    if category == "implementation":
        return "number"
    return "text"


def _question_details(field_name: str, question_map: dict[str, dict]) -> tuple[str | None, str | None, str | None]:
    question = question_map.get(field_name, {})
    prompt = question.get("prompt")
    category = question.get("category")
    scope = question.get("scope")
    if prompt is None and field_name in QUESTION_PROMPTS:
        prompt, default_category = QUESTION_PROMPTS[field_name]
        category = category or default_category
        scope = scope or "task"
    return prompt, category, scope


def _preview_set_fields(missing_fields: list[str], questions: list[dict] | None = None) -> list[str]:
    preview: list[str] = []
    for item in questions or []:
        if len(preview) >= 3:
            break
        field_name = item.get("field_name")
        if field_name and field_name not in preview:
            preview.append(field_name)
    for field_name in missing_fields:
        if len(preview) >= 3:
            break
        if field_name not in preview:
            preview.append(field_name)
    return preview


def _hint_set_fields(missing_fields: list[str], questions: list[dict] | None = None) -> list[str]:
    hinted: list[str] = []
    for item in questions or []:
        field_name = item.get("field_name")
        if field_name and field_name not in hinted:
            hinted.append(field_name)
    if hinted:
        return hinted
    return _preview_set_fields(missing_fields, questions)


def _pending_question_preview(
    *,
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    missing_fields: list[str],
    questions: list[dict] | None = None,
    script_output_path: str | None = None,
) -> list[dict]:
    preview_items: list[dict] = []
    question_map = {item.get("field_name"): item for item in questions or [] if item.get("field_name")}
    for field_name in _preview_set_fields(missing_fields, questions):
        prompt, category, scope = _question_details(field_name, question_map)
        answer_example = _example_set_value(
            field_name,
            physics=physics,
            draft=draft,
            script_output_path=script_output_path,
        )
        preview_items.append(
            {
                "field_name": field_name,
                "category": category,
                "scope": scope,
                "prompt": prompt,
                "answer_kind": _answer_kind(field_name, category=category),
                "answer_example": answer_example,
                "set_example": _set_assignment_token(field_name, answer_example),
            }
        )
    return preview_items


def _pending_set_examples(
    *,
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    missing_fields: list[str],
    questions: list[dict] | None = None,
    script_output_path: str | None = None,
) -> list[str]:
    return [
        item["set_example"]
        for item in _pending_question_preview(
            physics=physics,
            draft=draft,
            missing_fields=missing_fields,
            questions=questions,
            script_output_path=script_output_path,
        )
    ]


def _pending_reply_examples(
    *,
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    missing_fields: list[str],
    questions: list[dict] | None = None,
    script_output_path: str | None = None,
) -> list[str]:
    return [
        _reply_argument_token(item["answer_example"])
        for item in _pending_question_preview(
            physics=physics,
            draft=draft,
            missing_fields=missing_fields,
            questions=questions,
            script_output_path=script_output_path,
        )
    ]


def _set_command_hint(
    config: RunConfig,
    missing_fields: list[str],
    session_path: Path | None = None,
    script_output_path: str | None = None,
    physics: PhysicsTargetArtifact | None = None,
    draft: Pion2ptTaskDraft | None = None,
    questions: list[dict] | None = None,
) -> str | None:
    if not missing_fields:
        return None
    effective_session_path = session_path or _effective_session_path(config, script_output_path)
    if effective_session_path is None:
        return None
    output_path = _effective_output_path(config, script_output_path)
    parts: list[str] = []
    hinted_fields = _hint_set_fields(missing_fields, questions)
    for field_name in hinted_fields:
        example_value = "<value>"
        if physics is not None and draft is not None:
            example_value = _example_set_value(
                field_name,
                physics=physics,
                draft=draft,
                script_output_path=script_output_path,
            )
        parts.append(_set_assignment_token(field_name, example_value))
    command_parts = [
        "PYTHONPATH=src python3 -m pyquda_agent.cli run",
        json.dumps(config.task_description),
        f"--resume-session {str(effective_session_path)!r}",
        *parts,
        *_continuation_flag_parts(config),
        f"--output {str(output_path)!r}",
        f"--pyquda-repo {str(config.pyquda_repo)!r}",
    ]
    return " ".join(command_parts)


def _reply_command_hint(
    config: RunConfig,
    *,
    physics: PhysicsTargetArtifact,
    draft: Pion2ptTaskDraft,
    missing_fields: list[str],
    questions: list[dict] | None = None,
    session_path: Path | None = None,
    script_output_path: str | None = None,
) -> str | None:
    effective_session_path = session_path or _effective_session_path(config, script_output_path)
    if effective_session_path is None:
        return None
    output_path = _effective_output_path(config, script_output_path)
    parts: list[str] = []
    for field_name in _hint_set_fields(missing_fields, questions):
        answer_example = _example_set_value(
            field_name,
            physics=physics,
            draft=draft,
            script_output_path=script_output_path,
        )
        parts.append(_reply_argument_token(answer_example))
    if not parts:
        return None
    command_parts = [
        "PYTHONPATH=src python3 -m pyquda_agent.cli run",
        json.dumps(config.task_description),
        f"--resume-session {str(effective_session_path)!r}",
        *parts,
        *_continuation_flag_parts(config),
        f"--output {str(output_path)!r}",
        f"--pyquda-repo {str(config.pyquda_repo)!r}",
    ]
    return " ".join(command_parts)


def _reply_resolution_error(question: dict | object, answer: str, *, example_answer: str) -> ValueError:
    prompt = getattr(question, "prompt", None) or (question.get("prompt") if isinstance(question, dict) else None)
    field_name = getattr(question, "field_name", None) or (question.get("field_name") if isinstance(question, dict) else None)
    prompt = prompt or "Please answer the current clarification question."
    field_name = field_name or "unknown"
    return ValueError(
        f"--reply answer {answer!r} did not resolve the current question ({field_name}): "
        f"{prompt} Example reply: {example_answer!r}."
    )


def _probe_command_hint(runtime_evidence: dict | None) -> str | None:
    if runtime_evidence is None or not runtime_evidence.get("generated_script_exists"):
        return None
    generated_script_probe = runtime_evidence.get("generated_script_probe") or {}
    return generated_script_probe.get("command")


def _enrich_runtime_evidence(
    runtime_readiness: dict | None,
    *,
    script_path: str | None,
    task_artifact: Path | None,
    physics_artifact: Path | None,
    plan_artifact: Path | None,
    generated: bool,
    probe_result: dict | None = None,
    probe_requested: bool = False,
    probe_use_repo_pythonpath: bool = False,
) -> dict | None:
    if runtime_readiness is None:
        return None
    report = dict(runtime_readiness)
    evidence_levels = dict(report.get("evidence_levels", {}))
    script = str(Path(script_path).expanduser().resolve()) if script_path else None
    probe_artifact = str(Path(script).with_suffix(".probe.json")) if script else None
    report["generated_script_path"] = script
    report["generated_script_exists"] = generated and bool(script)
    report["artifact_chain"] = {
        "task_artifact": str(task_artifact) if task_artifact else None,
        "physics_artifact": str(physics_artifact) if physics_artifact else None,
        "plan_artifact": str(plan_artifact) if plan_artifact else None,
    }
    report["generated_script_probe"] = {
        "status": "requested" if probe_requested else "not_run",
        "reason": (
            None
            if probe_requested
            else "The run path does not auto-execute generated workflow scripts because they may launch a real PyQUDA inversion workload."
        ),
        "artifact_path": probe_artifact,
        "command": (
            " ".join(
                part
                for part in [
                    "python3 scripts/probe_generated_workflow.py",
                    f"--script {script}" if script else None,
                    f"--output {probe_artifact}" if probe_artifact else None,
                    "--use-repo-pythonpath" if probe_use_repo_pythonpath else None,
                ]
                if part
            )
            if script and probe_artifact
            else None
        ),
    }
    probe_policy = dict(report.get("probe_policy") or {})
    probe_policy.update(
        {
            "auto_run": bool(probe_requested),
            "default_auto_run": False,
            "current_run_requested": bool(probe_requested),
            "current_run_attempted": probe_result is not None,
            "current_run_status": (
                probe_result.get("status")
                if probe_result is not None
                else ("requested" if probe_requested else "not_requested")
            ),
            "reason": (
                "This run explicitly requested a minimal generated-script probe after script emission."
                if probe_requested
                else "Generated-script probes are opt-in because a complete script may start a real PyQUDA inversion workload."
            ),
        }
    )
    report["probe_policy"] = probe_policy
    if probe_result is not None:
        report["generated_script_probe"] = {
            **report["generated_script_probe"],
            "status": probe_result.get("status"),
            "reason": None,
            "result": probe_result,
        }
        report["runtime_level"] = probe_result.get("runtime_level", report.get("runtime_level"))
        evidence_levels["runtime_proved"] = bool((probe_result.get("evidence_levels") or {}).get("runtime_proved"))
        evidence_levels["runtime_ready"] = bool((probe_result.get("evidence_levels") or {}).get("runtime_ready"))
        evidence_levels["current_level"] = report.get("runtime_level")
        if probe_result.get("evidence_levels", {}).get("blockers"):
            evidence_levels["blockers"] = probe_result["evidence_levels"]["blockers"]
    else:
        evidence_levels["runtime_proved"] = False
        evidence_levels["current_level"] = report.get("runtime_level")
    report["evidence_levels"] = evidence_levels
    return report


def _run_optional_probe(config: RunConfig, script_output_path: str) -> dict | None:
    if not config.runtime_probe:
        return None
    try:
        probe_result = build_generated_probe(
            Path(script_output_path),
            config.probe_timeout,
            pyquda_repo=config.pyquda_repo,
            use_repo_pythonpath=config.probe_use_repo_pythonpath,
        )
    except Exception as exc:
        probe_result = {
            "python": None,
            "script": str(Path(script_output_path).expanduser().resolve()),
            "script_exists": Path(script_output_path).expanduser().resolve().exists(),
            "used_repo_pythonpath": config.probe_use_repo_pythonpath,
            "pyquda_repo": str(config.pyquda_repo.expanduser().resolve()),
            "status": "probe_driver_failed",
            "runtime_level": "probe_driver_failed",
            "evidence_levels": {
                "syntax_valid": None,
                "structurally_grounded": None,
                "runtime_ready": False,
                "runtime_proved": False,
                "current_level": "probe_driver_failed",
                "blockers": [f"Runtime probe execution failed before completion: {exc}"],
            },
            "returncode": None,
            "duration_seconds": None,
            "stdout": "",
            "stderr": "",
            "probe_driver_error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }
    _write_json(_probe_artifact_path(script_output_path), probe_result)
    return probe_result


def run_command(config: RunConfig) -> dict:
    saved_state_hint = load_session(config.resume_session) if config.resume_session else None
    backend, backend_status = build_llm_backend(
        config,
        prior_backend_assistance=(saved_state_hint.backend_assistance if saved_state_hint is not None else None),
        request_profile_hint=_backend_request_profile_hint(config),
    )
    physics_seed = resolve_physics_target(
        config.task_description,
        backend=backend,
        backend_status=backend_status,
    )
    physics_seed = maybe_lookup_external_knowledge(
        physics_seed,
        enabled=config.enable_external_lookup,
    )
    draft, physics, asked_questions, _saved_match, saved_state = _load_or_parse_state(
        config,
        physics_seed,
        saved_state=saved_state_hint,
    )
    resume_pending_fields = _resume_pending_fields(saved_state)
    if draft.task_type and "task_type" not in draft.parser_guesses and draft.field_sources.get("task_type") == "parser_guess":
        draft.parser_guesses["task_type"] = draft.task_type
    if physics.inferred_interpretation and "target_id" not in physics.parser_guesses and physics.confirmed_interpretation is None:
        physics.parser_guesses["target_id"] = physics.inferred_interpretation.get("target_id")
    _apply_cli_set_fields(config, physics, draft, asked_questions)
    _apply_cli_reply_answers(config, physics, draft, asked_questions, resume_pending_fields)
    if physics.confirmed_interpretation is None and config.interactive:
        _ask_physics_questions(config, physics, asked_questions)
    _apply_physics_field_hints_to_draft(physics, draft)

    workflow_match = match_supported_workflow(physics, draft)
    if workflow_match.matched:
        apply_workflow_match(draft, physics, workflow_match)

    missing: list[str] = []
    if physics.confirmed_interpretation is not None and workflow_match.matched:
        missing = determine_missing_fields(draft)
        if missing and config.interactive:
            _ask_task_questions(config, draft, asked_questions, resume_pending_fields)
            workflow_match = match_supported_workflow(physics, draft)
            if workflow_match.matched:
                apply_workflow_match(draft, physics, workflow_match)
            missing = determine_missing_fields(draft)

    context_bundle = build_context_bundle(
        task_description=config.task_description,
        task_type=workflow_match.task_type or physics.task_type_hint or draft.task_type or "unknown",
        workspace_root=config.workspace_root,
        pyquda_repo=config.pyquda_repo,
        index_path=DEFAULT_INDEX_PATH,
    )
    implementation_plan = build_implementation_plan(
        draft,
        physics,
        workflow_match,
        context_bundle,
        asked_questions,
        config.pyquda_repo,
    )
    session_path = _effective_session_path(config, draft.script_output_path)
    _maybe_save_session(
        config,
        draft,
        physics,
        asked_questions,
        workflow_match,
        context_bundle.to_dict(),
        implementation_plan.to_dict(),
    )

    task_artifact = None
    physics_artifact = None
    plan_artifact = None
    if draft.script_output_path:
        task_artifact, physics_artifact, plan_artifact = _artifact_paths(draft.script_output_path)
        implementation_plan.runtime_readiness = _enrich_runtime_evidence(
            implementation_plan.runtime_readiness,
            script_path=draft.script_output_path,
            task_artifact=task_artifact,
            physics_artifact=physics_artifact,
            plan_artifact=plan_artifact,
            generated=False,
            probe_requested=config.runtime_probe,
            probe_use_repo_pythonpath=config.probe_use_repo_pythonpath,
        )
        _write_json(task_artifact, draft.to_dict())
        _write_json(physics_artifact, physics.to_dict())
        _write_json(plan_artifact, implementation_plan.to_dict())

    result = {
        "status": "ok",
        "backend": config.backend,
        "model": config.model,
        "pipeline": [
            "physics_interpretation",
            "structured_task_spec",
            "clarification_loop",
            "workflow_matching",
            "reference_grounded_implementation_plan",
            "complete_script",
            "minimal_validation",
        ],
        "physics": physics.to_dict(),
        "llm_assistance": physics.llm_assistance,
        "task": draft.to_dict(),
        "missing_fields": missing,
        "questions": [
            *[question.to_dict() for question in build_physics_questions(physics, config.max_questions)],
            *(
                [
                    question.to_dict()
                    for question in build_questions(
                        draft,
                        config.max_questions,
                        preferred_fields=resume_pending_fields,
                    )
                ]
                if physics.confirmed_interpretation and workflow_match.matched
                else []
            ),
        ],
        "workflow_match": workflow_match.to_dict(),
        "context": context_bundle.to_dict(),
        "implementation_plan": implementation_plan.to_dict(),
        "runtime_evidence": implementation_plan.runtime_readiness,
        "task_artifact": str(task_artifact) if task_artifact else None,
        "physics_artifact": str(physics_artifact) if physics_artifact else None,
        "plan_artifact": str(plan_artifact) if plan_artifact else None,
        "session_artifact": str(session_path) if session_path else None,
    }
    questions = result["questions"]
    if physics.confirmed_interpretation is None:
        confirmation_missing = ["confirmed_target_id"]
        result["missing_fields"] = confirmation_missing
        result["status"] = "needs_input"
        result["next_action"] = _next_action_with_preview(
            "Confirm the physics target before workflow matching and complete generation.",
            _pending_question_preview(
                physics=physics,
                draft=draft,
                missing_fields=confirmation_missing,
                questions=questions,
                script_output_path=draft.script_output_path,
            ),
            candidate_targets=_candidate_target_preview_ids(physics),
            formula_preview=_formula_preview_text(physics),
            workflow_preview=_workflow_preview_text(physics, draft),
        )
        if session_path is not None:
            result["resume_hint"] = _resume_command_hint(config, session_path, draft.script_output_path)
            result["reply_hint"] = _reply_command_hint(
                config,
                physics=physics,
                draft=draft,
                missing_fields=confirmation_missing,
                questions=questions,
                session_path=session_path,
                script_output_path=draft.script_output_path,
            )
            result["set_hint"] = _set_command_hint(
                config,
                confirmation_missing,
                session_path,
                draft.script_output_path,
                physics=physics,
                draft=draft,
                questions=questions,
            )
        _attach_result_summary(
            config=config,
            result=result,
            draft=draft,
            physics=physics,
            workflow_match=workflow_match,
            missing=confirmation_missing,
            questions=questions,
            task_artifact=task_artifact,
            physics_artifact=physics_artifact,
            plan_artifact=plan_artifact,
            session_path=session_path,
        )
        return result
    if workflow_match.unsupported_reasons and not workflow_match.matched:
        result["status"] = "unsupported"
        result["refusal_reason"] = (
            "Confirmed request does not map to the current runnable workflow. Review unsupported_reasons together with nearby_supported_workflows and the physics/task/plan artifacts."
        )
        if session_path is not None:
            result["resume_hint"] = _resume_command_hint(config, session_path, draft.script_output_path)
            result["reply_hint"] = _reply_command_hint(
                config,
                physics=physics,
                draft=draft,
                missing_fields=missing,
                questions=questions,
                session_path=session_path,
                script_output_path=draft.script_output_path,
            )
            result["set_hint"] = _set_command_hint(
                config,
                missing,
                session_path,
                draft.script_output_path,
                physics=physics,
                draft=draft,
                questions=questions,
            )
        _attach_result_summary(
            config=config,
            result=result,
            draft=draft,
            physics=physics,
            workflow_match=workflow_match,
            missing=missing,
            questions=questions,
            task_artifact=task_artifact,
            physics_artifact=physics_artifact,
            plan_artifact=plan_artifact,
            session_path=session_path,
        )
        return result
    if draft.unsupported_reasons:
        result["status"] = "unsupported"
        result["refusal_reason"] = (
            "Request conflicts with the current runnable workflow constraints. Review unsupported_reasons together with nearby_supported_workflows and the structured task/plan artifacts."
        )
        if session_path is not None:
            result["resume_hint"] = _resume_command_hint(config, session_path, draft.script_output_path)
            result["reply_hint"] = _reply_command_hint(
                config,
                physics=physics,
                draft=draft,
                missing_fields=missing,
                questions=questions,
                session_path=session_path,
                script_output_path=draft.script_output_path,
            )
            result["set_hint"] = _set_command_hint(
                config,
                missing,
                session_path,
                draft.script_output_path,
                physics=physics,
                draft=draft,
                questions=questions,
            )
        _attach_result_summary(
            config=config,
            result=result,
            draft=draft,
            physics=physics,
            workflow_match=workflow_match,
            missing=missing,
            questions=questions,
            task_artifact=task_artifact,
            physics_artifact=physics_artifact,
            plan_artifact=plan_artifact,
            session_path=session_path,
        )
        return result
    if missing:
        result["status"] = "needs_input"
        result["next_action"] = _next_action_with_preview(
            "Resolve missing implementation/runtime fields in the structured task spec before complete generation.",
            _pending_question_preview(
                physics=physics,
                draft=draft,
                missing_fields=missing,
                questions=questions,
                script_output_path=draft.script_output_path,
            ),
        )
        if session_path is not None:
            result["resume_hint"] = _resume_command_hint(config, session_path, draft.script_output_path)
            result["reply_hint"] = _reply_command_hint(
                config,
                physics=physics,
                draft=draft,
                missing_fields=missing,
                questions=questions,
                session_path=session_path,
                script_output_path=draft.script_output_path,
            )
            result["set_hint"] = _set_command_hint(
                config,
                missing,
                session_path,
                draft.script_output_path,
                physics=physics,
                draft=draft,
                questions=questions,
            )
        _attach_result_summary(
            config=config,
            result=result,
            draft=draft,
            physics=physics,
            workflow_match=workflow_match,
            missing=missing,
            questions=questions,
            task_artifact=task_artifact,
            physics_artifact=physics_artifact,
            plan_artifact=plan_artifact,
            session_path=session_path,
        )
        return result
    if config.dry_run:
        result["status"] = "dry_run"
        if session_path is not None:
            result["resume_hint"] = _resume_command_hint(config, session_path, draft.script_output_path)
            result["reply_hint"] = _reply_command_hint(
                config,
                physics=physics,
                draft=draft,
                missing_fields=missing,
                questions=questions,
                session_path=session_path,
                script_output_path=draft.script_output_path,
            )
            result["set_hint"] = _set_command_hint(
                config,
                missing,
                session_path,
                draft.script_output_path,
                physics=physics,
                draft=draft,
                questions=questions,
            )
        _attach_result_summary(
            config=config,
            result=result,
            draft=draft,
            physics=physics,
            workflow_match=workflow_match,
            missing=missing,
            questions=questions,
            task_artifact=task_artifact,
            physics_artifact=physics_artifact,
            plan_artifact=plan_artifact,
            session_path=session_path,
        )
        return result

    task = finalize_task(draft)
    code = render_complete_script(task, implementation_plan)
    warnings: list[str] = []
    validate_generated_script(code)
    emit_script(Path(task.script_output_path), code)
    probe_result = _run_optional_probe(config, task.script_output_path)
    implementation_plan.runtime_readiness = _enrich_runtime_evidence(
        implementation_plan.runtime_readiness,
        script_path=task.script_output_path,
        task_artifact=task_artifact,
        physics_artifact=physics_artifact,
        plan_artifact=plan_artifact,
        generated=True,
        probe_result=probe_result,
        probe_requested=config.runtime_probe,
        probe_use_repo_pythonpath=config.probe_use_repo_pythonpath,
    )
    if plan_artifact is not None:
        _write_json(plan_artifact, implementation_plan.to_dict())
    execution_status = "not_requested"
    if config.runtime_probe:
        execution_status = "probe_failed"
        if probe_result is not None:
            if probe_result.get("status") == "ok":
                execution_status = "runtime_proved"
            elif probe_result.get("status") == "runtime_missing":
                execution_status = "runtime_missing"
            else:
                execution_status = str(probe_result.get("status"))
    generation_result = GenerationResult(
        output_path=task.script_output_path,
        script_style=task.script_style,
        used_backend=str((physics.llm_assistance or {}).get("selected_backend") or config.backend),
        execution_status=execution_status,
        warnings=warnings,
    )
    result["generation"] = generation_result.to_dict()
    result["implementation_plan"] = implementation_plan.to_dict()
    result["runtime_evidence"] = implementation_plan.runtime_readiness
    result["execution_status"] = execution_status
    if execution_status == "runtime_proved":
        result["next_action"] = "Runtime probe succeeded. Review artifacts or hand off the generated workflow."
    elif config.runtime_probe:
        probe_blockers = list((probe_result or {}).get("evidence_levels", {}).get("blockers") or [])
        if execution_status == "probe_driver_failed":
            artifact_path = (implementation_plan.runtime_readiness.get("generated_script_probe") or {}).get("artifact_path")
            result["next_action"] = _runtime_probe_driver_recommended_fix(artifact_path=artifact_path)
        elif execution_status == "runtime_missing":
            result["next_action"] = _runtime_environment_recommended_fix(probe_blockers)
        else:
            result["next_action"] = "Inspect the probe blockers and retry after fixing the runtime environment."
    else:
        result["next_action"] = "Run the probe command to collect runtime evidence for the generated script."
    if probe_result is not None:
        result["probe"] = probe_result
    probe_hint = _probe_command_hint(result["runtime_evidence"])
    if probe_hint is not None:
        result["probe_hint"] = probe_hint
    if config.print_context:
        result["context_text"] = context_bundle.to_dict()
    if session_path is not None:
        result["resume_hint"] = _resume_command_hint(config, session_path, task.script_output_path)
        result["reply_hint"] = _reply_command_hint(
            config,
            physics=physics,
            draft=draft,
            missing_fields=missing,
            questions=questions,
            session_path=session_path,
            script_output_path=task.script_output_path,
        )
        result["set_hint"] = _set_command_hint(
            config,
            missing,
            session_path,
            task.script_output_path,
            physics=physics,
            draft=draft,
            questions=questions,
        )
    _attach_result_summary(
        config=config,
        result=result,
        draft=draft,
        physics=physics,
        workflow_match=workflow_match,
        missing=missing,
        questions=questions,
        task_artifact=task_artifact,
        physics_artifact=physics_artifact,
        plan_artifact=plan_artifact,
        session_path=session_path,
    )
    return result
