"""Application orchestration for the `pyquda-agent run` command."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from pyquda_agent.config import DEFAULT_INDEX_PATH
from pyquda_agent.config import RunConfig
from pyquda_agent.generator.emitter import emit_script
from pyquda_agent.generator.plan import build_implementation_plan
from pyquda_agent.generator.templates import render_pion_2pt_script
from pyquda_agent.generator.validate import validate_generated_script
from pyquda_agent.models import GenerationResult
from pyquda_agent.retrieval.context_builder import build_context_bundle
from pyquda_agent.sessions.state import SessionState
from pyquda_agent.sessions.state import load_session
from pyquda_agent.sessions.state import save_session
from pyquda_agent.tasks.clarifier import apply_answer
from pyquda_agent.tasks.clarifier import build_questions
from pyquda_agent.tasks.clarifier import determine_missing_fields
from pyquda_agent.tasks.parser import parse_task_description
from pyquda_agent.tasks.pion_2pt import finalize_task
from pyquda_agent.tasks.schema import Pion2ptTaskDraft


def _load_or_parse_draft(config: RunConfig) -> tuple[Pion2ptTaskDraft, list[dict]]:
    if config.resume_session:
        state = load_session(config.resume_session)
        if not state.draft.script_output_path:
            state.draft.script_output_path = str(config.output)
        return state.draft, list(state.asked_questions)
    draft = parse_task_description(config.task_description)
    output_base = config.output.parent
    if not draft.script_output_path:
        draft.script_output_path = str(config.output)
        draft.field_sources["script_output_path"] = "default"
    else:
        script_path = Path(draft.script_output_path).expanduser()
        if not script_path.is_absolute():
            script_path = output_base / script_path.name if script_path.parent == Path(".") else output_base.parent / script_path
        draft.script_output_path = str(script_path.resolve())
        draft.field_sources.setdefault("script_output_path", "parsed")
    if not draft.correlator_output_path:
        draft.correlator_output_path = str(config.output.with_suffix(".npy"))
        draft.correlator_output_format = "npy"
        draft.field_sources["correlator_output_path"] = "default"
        draft.field_sources["correlator_output_format"] = "default"
    else:
        correlator_path = Path(draft.correlator_output_path).expanduser()
        if not correlator_path.is_absolute():
            correlator_path = output_base / correlator_path.name if correlator_path.parent == Path(".") else output_base.parent / correlator_path
        draft.correlator_output_path = str(correlator_path.resolve())
        draft.field_sources.setdefault("correlator_output_path", "parsed")
    if draft.gauge_path:
        draft.gauge_path = str(Path(draft.gauge_path).expanduser().resolve())
    if draft.resource_path and draft.resource_path.startswith("~"):
        draft.resource_path = str(Path(draft.resource_path).expanduser())
    if not draft.workflow_id and draft.task_type == "pion_2pt":
        draft.workflow_id = "pion_2pt_chroma_wall_local_zero_momentum_npy_v1"
        draft.field_sources["workflow_id"] = "fixed"
    return draft, []


def _ask_questions(config: RunConfig, draft: Pion2ptTaskDraft, asked_questions: list[dict]) -> None:
    for question in build_questions(draft, config.max_questions):
        if not config.interactive:
            break
        answer = input(f"{question.prompt}\n> ")
        apply_answer(draft, question.field_name, answer)
        asked_questions.append({"field_name": question.field_name, "answer": answer})


def _maybe_save_session(
    config: RunConfig,
    draft: Pion2ptTaskDraft,
    asked_questions: list[dict],
    context_bundle: dict | None,
    implementation_plan: dict | None,
) -> None:
    if not config.save_session:
        return
    save_session(
        config.save_session,
        SessionState(
            task_description=config.task_description,
            draft=draft,
            asked_questions=asked_questions,
            context_bundle=context_bundle,
            implementation_plan=implementation_plan,
        ),
    )


def _artifact_paths(script_output_path: str) -> tuple[Path, Path]:
    script_path = Path(script_output_path)
    stem = script_path.stem
    artifact_dir = script_path.parent
    return artifact_dir / f"{stem}.task.json", artifact_dir / f"{stem}.plan.json"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(config: RunConfig) -> dict:
    draft, asked_questions = _load_or_parse_draft(config)
    missing = determine_missing_fields(draft)
    if missing and config.interactive:
        _ask_questions(config, draft, asked_questions)
        missing = determine_missing_fields(draft)

    context_bundle = build_context_bundle(
        task_description=config.task_description,
        task_type=draft.task_type or "pion_2pt",
        workspace_root=config.workspace_root,
        pyquda_repo=config.pyquda_repo,
        index_path=DEFAULT_INDEX_PATH,
    )
    implementation_plan = build_implementation_plan(draft, context_bundle, asked_questions, config.pyquda_repo)
    _maybe_save_session(
        config,
        draft,
        asked_questions,
        context_bundle.to_dict(),
        implementation_plan.to_dict(),
    )

    task_artifact = None
    plan_artifact = None
    if draft.script_output_path:
        task_artifact, plan_artifact = _artifact_paths(draft.script_output_path)
        _write_json(task_artifact, draft.to_dict())
        _write_json(plan_artifact, implementation_plan.to_dict())

    result = {
        "status": "ok",
        "backend": config.backend,
        "model": config.model,
        "pipeline": [
            "structured_task_spec",
            "clarification_loop",
            "reference_grounded_implementation_plan",
            "complete_script",
            "minimal_validation",
        ],
        "task": draft.to_dict(),
        "missing_fields": missing,
        "questions": [asdict(question) for question in build_questions(draft, config.max_questions)],
        "context": context_bundle.to_dict(),
        "implementation_plan": implementation_plan.to_dict(),
        "task_artifact": str(task_artifact) if task_artifact else None,
        "plan_artifact": str(plan_artifact) if plan_artifact else None,
    }
    if draft.unsupported_reasons:
        result["status"] = "unsupported"
        result["refusal_reason"] = (
            "Request falls outside the fixed runnable v1 workflow. Review the structured task spec and implementation plan artifacts."
        )
        return result
    if missing:
        result["status"] = "needs_input"
        result["next_action"] = "Resolve missing fields in the structured task spec before complete generation."
        return result
    if config.dry_run:
        result["status"] = "dry_run"
        return result

    task = finalize_task(draft)
    code = render_pion_2pt_script(task, implementation_plan)
    warnings: list[str] = []
    validate_generated_script(code)
    emit_script(Path(task.script_output_path), code)
    generation_result = GenerationResult(
        output_path=task.script_output_path,
        script_style=task.script_style,
        used_backend=config.backend,
        warnings=warnings,
    )
    result["generation"] = generation_result.to_dict()
    if config.print_context:
        result["context_text"] = context_bundle.to_dict()
    return result
