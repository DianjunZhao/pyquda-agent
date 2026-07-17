"""Command-line interface for pyquda-agent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from pyquda_agent.app import run_command
from pyquda_agent.config import DEFAULT_API_KEY_FILE
from pyquda_agent.config import DEFAULT_OUTPUT_PATH
from pyquda_agent.config import DEFAULT_PYQUDA_REPO
from pyquda_agent.config import RunConfig
from pyquda_agent.python_version import ensure_supported_python


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyquda-agent", description="PyQUDA analysis and script-generation helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Parse a PyQUDA task and generate a script or template.")
    run_parser.add_argument("task_description", help="Natural-language task description.")
    run_parser.add_argument(
        "--backend",
        default="auto",
        choices=("auto", "api", "codex"),
        help="LLM backend selection. 'auto' prefers codex, then configured API, then rule-based fallback.",
    )
    run_parser.add_argument("--model", default=None, help="API model as provider/model_id for --backend api.")
    run_parser.add_argument("--api-key-file", type=Path, default=DEFAULT_API_KEY_FILE)
    run_parser.add_argument("--base-url", default=None)
    run_parser.add_argument("--pyquda-repo", type=Path, default=DEFAULT_PYQUDA_REPO)
    run_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    run_parser.add_argument("--interactive", action=argparse.BooleanOptionalAction, default=True)
    run_parser.add_argument("--max-questions", type=int, default=7)
    run_parser.add_argument("--save-session", type=Path, default=None)
    run_parser.add_argument("--resume-session", type=Path, default=None)
    run_parser.add_argument("--print-context", action="store_true")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--verbose", action="store_true")
    run_parser.add_argument(
        "--set",
        dest="set_fields",
        action="append",
        default=[],
        help="Apply a clarification answer directly as field=value. Repeat for multiple fields, for example --set mass=0.09253 --set source_timeslices=0.",
    )
    run_parser.add_argument(
        "--reply",
        dest="reply_answers",
        action="append",
        default=[],
        help="Reply to pending clarification questions in order without naming fields. Repeat for multiple answers, for example --reply pion --reply gauge --reply 0.",
    )
    run_parser.add_argument(
        "--result-format",
        choices=("full", "summary", "terminal"),
        default="full",
        help="CLI output format. 'full' prints the complete JSON payload; 'summary' prints only result_summary; 'terminal' prints the distilled terminal_message.",
    )
    run_parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Shortcut for --result-format summary.",
    )
    run_parser.add_argument("--enable-external-lookup", action="store_true")
    run_parser.add_argument(
        "--llm-timeout",
        type=float,
        default=30.0,
        help="Timeout in seconds for an optional LLM backend call before explicit fallback.",
    )
    run_parser.add_argument("--runtime-probe", action="store_true", help="After generation, run a minimal probe against the generated script.")
    run_parser.add_argument("--probe-timeout", type=float, default=30.0, help="Timeout in seconds for the optional runtime probe.")
    run_parser.add_argument(
        "--probe-use-repo-pythonpath",
        action="store_true",
        help="For the optional runtime probe, prepend --pyquda-repo to PYTHONPATH before execution.",
    )
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if args.command != "run":
        raise ValueError(f"Unsupported command {args.command!r}.")
    if args.backend == "codex" and args.model:
        print("warning: --model is ignored for backend='codex'.", file=sys.stderr)


def _terminal_blocking_reason(summary: dict) -> str | None:
    return summary.get("blocking_reason")


def _terminal_blocking_category(summary: dict) -> str | None:
    detail = summary.get("blocking_reason_detail") or {}
    category = detail.get("category")
    if isinstance(category, str) and category:
        return category
    return None


def _terminal_first_artifact(summary: dict) -> tuple[str, str] | None:
    hint = summary.get("inspection_hint") or {}
    label = hint.get("label")
    path = hint.get("path")
    if label and path:
        return label, path
    return None


def _render_execution_closure(summary: dict) -> list[str]:
    closure = summary.get("execution_closure") or {}
    state = closure.get("state")
    if not state:
        return []
    parts = [f"Execution: {state}"]
    next_artifact = closure.get("next_artifact")
    next_command_kind = closure.get("next_command_kind")
    if next_artifact:
        parts.append(f"inspect={next_artifact}")
    if next_command_kind:
        parts.append(f"next={next_command_kind}")
    lines = [" | ".join(parts)]
    headline = closure.get("headline")
    if headline:
        lines.append(f"Execution detail: {headline}")
    blocking_detail = summary.get("blocking_reason_detail") or {}
    runtime_category = closure.get("runtime_category")
    if state not in {"runtime_environment_missing", "probe_harness_failed", "runtime_proved"}:
        runtime_category = None
    if runtime_category:
        lines.append(f"Runtime class: {runtime_category}")
    backend_category = closure.get("backend_category")
    if not backend_category and blocking_detail.get("source") == "backend":
        backend_category = blocking_detail.get("category")
    if backend_category:
        lines.append(f"Backend class: {backend_category}")
    return lines


def _render_execution_checkpoint(summary: dict) -> list[str]:
    checkpoint = summary.get("execution_checkpoint") or {}
    state = checkpoint.get("state")
    if not state:
        return []
    parts = [f"Checkpoint: {state}"]
    runtime_level = checkpoint.get("runtime_level")
    probe_state = checkpoint.get("runtime_probe_status")
    if runtime_level:
        parts.append(f"runtime={runtime_level}")
    if probe_state:
        parts.append(f"probe={probe_state}")
    if checkpoint.get("hpc_handoff_ready"):
        parts.append("handoff=ready")
    lines = [" | ".join(parts)]
    headline = checkpoint.get("headline")
    if headline:
        lines.append(f"Checkpoint detail: {headline}")
    return lines


def _render_physics_snapshot(result: dict, summary: dict) -> list[str]:
    physics = result.get("physics") or {}
    confirmed = ((physics.get("confirmed_interpretation") or {}).get("target_id"))
    inferred = ((physics.get("inferred_interpretation") or {}).get("target_id")) or summary.get("physics_target")
    candidates = physics.get("candidate_targets") or []
    lines: list[str] = []
    if confirmed:
        lines.append(f"Physics: confirmed={confirmed}")
    elif inferred:
        lines.append(f"Physics: inferred={inferred}")
    formatted_candidates: list[str] = []
    max_candidates = 4
    for item in candidates[:max_candidates]:
        target_id = item.get("target_id")
        label = item.get("label")
        if isinstance(target_id, str) and isinstance(label, str):
            formatted_candidates.append(f"{target_id} ({label})")
    if formatted_candidates and not confirmed:
        suffix = ""
        if len(candidates) > max_candidates:
            suffix = f" ... (+{len(candidates) - max_candidates} more)"
        lines.append(f"Candidates: {'; '.join(formatted_candidates)}{suffix}")
    return lines


def _truncate_terminal_text(value: str | None, *, limit: int = 120) -> str | None:
    if not isinstance(value, str):
        return None
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _render_formula_snapshot(summary: dict) -> list[str]:
    preview = summary.get("physics_formula_preview") or []
    if not preview:
        return []
    lines = ["Formula candidates:"]
    for item in preview[:2]:
        label = _truncate_terminal_text(item.get("label"), limit=72) or "unnamed formula"
        target_id = _truncate_terminal_text(item.get("target_id"), limit=56) or "unknown_target"
        operator = _truncate_terminal_text(item.get("operator"), limit=92) or "not provided"
        convention = _truncate_terminal_text(item.get("convention"), limit=110)
        provenance = _truncate_terminal_text(item.get("provenance"), limit=48)
        line = f"  {label} [{target_id}] | operator={operator}"
        if provenance:
            line += f" | provenance={provenance}"
        lines.append(line)
        if convention:
            lines.append(f"  Assumption: {convention}")
    if summary.get("physics_formula_preview_truncated"):
        lines.append("  ... more formula/operator candidates are available in the physics artifact.")
    return lines


def _render_workflow_hint_snapshot(summary: dict) -> list[str]:
    preview = summary.get("physics_workflow_preview") or []
    if not preview:
        return []
    lines = ["Workflow hints:"]
    for item in preview[:2]:
        target_id = _truncate_terminal_text(item.get("target_id"), limit=56) or "unknown_target"
        availability = _truncate_terminal_text(item.get("availability"), limit=24) or "unknown"
        workflows = [str(workflow) for workflow in item.get("grounded_workflow_targets") or [] if workflow]
        shown = workflows[:2]
        workflow_text = ", ".join(shown) if shown else "none"
        remaining = len(workflows) - len(shown)
        if remaining > 0:
            workflow_text += f" ... (+{remaining} more)"
        lines.append(f"  {target_id} | availability={availability} | workflows={workflow_text}")
    if summary.get("physics_workflow_preview_truncated"):
        lines.append("  ... more candidate-to-workflow mappings are available in the physics artifact.")
    return lines


def _render_clarification_snapshot(summary: dict) -> list[str]:
    clarification = summary.get("clarification_status") or {}
    if not clarification.get("active"):
        return []
    fields = clarification.get("preview_fields") or clarification.get("question_batch_fields") or []
    fields = [field for field in fields[:3] if isinstance(field, str) and field]
    mode = clarification.get("mode") or "unknown"
    line = f"Clarification: {mode}"
    if fields:
        line += f" | missing={', '.join(fields)}"
    lines = [line]
    preview = summary.get("pending_question_preview") or []
    if preview:
        first = preview[0] or {}
        prompt = first.get("prompt")
        answer_example = first.get("answer_example")
        if prompt:
            lines.append(f"Next prompt: {prompt}")
        if answer_example:
            lines.append(f"Example answer: {answer_example}")
    return lines


def _render_workflow_snapshot(summary: dict) -> list[str]:
    workflow_target = summary.get("workflow_target")
    if not workflow_target:
        return []
    return [f"Workflow: {workflow_target}"]


def _render_hpc_handoff_snapshot(summary: dict) -> list[str]:
    handoff = summary.get("hpc_handoff") or {}
    if not handoff:
        return []
    input_directories = [str(item) for item in handoff.get("input_directories") or [] if item]
    output_directories = [str(item) for item in handoff.get("output_directories") or [] if item]
    start_from = handoff.get("start_from")
    writer = handoff.get("output_writer_policy")
    if not any([input_directories, output_directories, start_from, writer]):
        return []
    header_parts = ["Handoff:"]
    if start_from:
        header_parts.append(f"start_from={start_from}")
    if input_directories:
        header_parts.append(f"input_dirs={len(input_directories)}")
    if output_directories:
        header_parts.append(f"output_dirs={len(output_directories)}")
    if writer:
        header_parts.append(f"writer={writer}")
    lines = [" | ".join(header_parts)]
    input_policy = _truncate_terminal_text(handoff.get("input_directory_policy"), limit=96)
    output_policy = _truncate_terminal_text(handoff.get("output_directory_policy"), limit=96)
    if input_policy:
        lines.append(f"Input policy: {input_policy}")
    if output_policy:
        lines.append(f"Output policy: {output_policy}")
    if input_directories:
        shown = ", ".join(input_directories[:2])
        if len(input_directories) > 2:
            shown += f" ... (+{len(input_directories) - 2} more)"
        lines.append(f"Input dirs: {shown}")
    if output_directories:
        shown = ", ".join(output_directories[:2])
        if len(output_directories) > 2:
            shown += f" ... (+{len(output_directories) - 2} more)"
        lines.append(f"Output dirs: {shown}")
    return lines


def _render_unsupported_snapshot(summary: dict) -> list[str]:
    guidance = summary.get("unsupported_guidance") or {}
    if not guidance:
        return []
    nearest = guidance.get("nearest_workflow_card") or {}
    if not nearest:
        return []
    workflow_target = _truncate_terminal_text(nearest.get("workflow_target"), limit=72) or "unknown_workflow"
    primary_scope = _truncate_terminal_text(nearest.get("primary_scope"), limit=24) or "unknown"
    required_change_count = nearest.get("required_change_count")
    repair_hint = guidance.get("repair_hint") or {}
    repair_mode = _truncate_terminal_text(repair_hint.get("mode"), limit=24) or "unknown"

    lines = [
        "Nearest grounded:"
        + f" workflow={workflow_target}"
        + f" | scope={primary_scope}"
        + (f" | changes={required_change_count}" if required_change_count is not None else "")
        + f" | repair={repair_mode}"
    ]
    summary_text = _truncate_terminal_text(nearest.get("summary"), limit=200)
    if summary_text:
        lines.append(f"Nearest detail: {summary_text}")
    gap_summary = ((guidance.get("shortest_fix_gap_summary") or {}).get("sentence"))
    gap_summary = _truncate_terminal_text(gap_summary, limit=200)
    if gap_summary:
        lines.append(f"Fix by scope: {gap_summary}")
    repair_summary = _truncate_terminal_text(repair_hint.get("summary"), limit=200)
    if repair_summary:
        lines.append(f"Repair hint: {repair_summary}")
    return lines


def _render_runtime_snapshot(summary: dict) -> list[str]:
    runtime_level = summary.get("runtime_level")
    execution = summary.get("execution_result") or {}
    evidence_level = execution.get("evidence_level")
    if not runtime_level and not evidence_level:
        return []
    parts = []
    if runtime_level:
        parts.append(f"level={runtime_level}")
    if evidence_level and evidence_level != runtime_level:
        parts.append(f"evidence={evidence_level}")
    elif evidence_level and not runtime_level:
        parts.append(f"evidence={evidence_level}")
    return [f"Runtime evidence: {' | '.join(parts)}"]


def _render_actionability_snapshot(summary: dict) -> list[str]:
    primary_action = summary.get("primary_action") or {}
    kind = primary_action.get("kind")
    command = primary_action.get("command")
    if not kind and not command:
        return []
    action_state = primary_action.get("action_state")
    if not action_state:
        action_state = "ready" if primary_action.get("actionable") else "blocked"
    parts = [f"Actionability: {action_state}"]
    if kind:
        parts.append(f"kind={kind}")
    if primary_action.get("actionable"):
        parts.append("copyable=yes")
    elif command:
        parts.append("copyable=not_now")
    else:
        parts.append("copyable=no")
    return [" | ".join(parts)]


def _render_continuation_snapshot(summary: dict) -> list[str]:
    overview = summary.get("run_overview") or {}
    blocking_kind = overview.get("blocking_kind")
    can_continue_now = overview.get("can_continue_now")
    primary_kind = overview.get("primary_action_kind")
    if blocking_kind in {None, "none"} and primary_kind is None and can_continue_now in {None, False}:
        return []
    if blocking_kind is None and can_continue_now is None and primary_kind is None:
        return []
    parts = [f"Continuation: now={'yes' if can_continue_now else 'no'}"]
    if blocking_kind:
        parts.append(f"gate={blocking_kind}")
    if primary_kind:
        parts.append(f"action={primary_kind}")
    return [" | ".join(parts)]


def _infer_backend_retry_category(summary: dict) -> str | None:
    backend = summary.get("backend_diagnostic") or {}
    category = backend.get("category")
    if isinstance(category, str) and category:
        return category

    blocking_detail = summary.get("blocking_reason_detail") or {}
    category = blocking_detail.get("backend_category")
    if isinstance(category, str) and category and category != "fallback":
        return category

    if backend.get("status") != "fallback":
        return None

    message_parts = [
        backend.get("message"),
        backend.get("next_step"),
        backend.get("recommended_fix"),
        blocking_detail.get("message"),
    ]
    message = " ".join(str(part) for part in message_parts if part).lower()
    if "credential" in message or "api key" in message or "auth" in message:
        return "credentials_missing"
    if "timeout" in message:
        return "timeout"
    if "network" in message or "connect" in message:
        return "network_error"
    if "endpoint" in message or "base-url" in message:
        return "endpoint_not_found"
    if "local `codex`" in message or "codex cli" in message or "executable" in message:
        return "local_executable_missing"
    if "model" in message or "configure" in message or "backend" in message:
        return "configuration_missing"

    requested_backend = backend.get("requested_backend")
    selected_backend = backend.get("selected_backend")
    if requested_backend in {"api", "codex", "auto"} or selected_backend in {"api", "codex"}:
        return "configuration_missing"
    return None


def _render_retryability_snapshot(summary: dict) -> list[str]:
    overview = summary.get("run_overview") or {}
    if overview.get("blocking_kind") in {None, "none"}:
        return []
    lines: list[str] = []
    backend = summary.get("backend_diagnostic") or {}
    if backend.get("status") == "fallback":
        retryable = backend.get("retryable_now")
        category = _infer_backend_retry_category(summary)
        parts = [f"Backend retry: {'yes' if retryable else 'no'}"]
        if category:
            parts.append(f"category={category}")
        lines.append(" | ".join(parts))
    runtime = summary.get("runtime_diagnostic") or {}
    if runtime.get("status") in {"probe_available", "runtime_missing", "probe_driver_failed", "runtime_blocked", "probe_pending"}:
        retryable = bool(runtime.get("retry_command"))
        category = runtime.get("category")
        parts = [f"Runtime retry: {'yes' if retryable else 'no'}"]
        if category:
            parts.append(f"category={category}")
        lines.append(" | ".join(parts))
    return lines


def _render_backend_fix_snapshot(summary: dict) -> list[str]:
    backend = summary.get("backend_diagnostic") or {}
    if backend.get("status") != "fallback":
        return []
    if not backend.get("category"):
        return []

    action_queue = summary.get("action_queue") or []
    backend_fix = next((item for item in action_queue if item.get("kind") == "backend_fix"), None)
    if not isinstance(backend_fix, dict):
        return []

    command = backend_fix.get("command")
    action_state = backend_fix.get("action_state")
    if not action_state:
        action_state = "ready" if backend_fix.get("actionable") else "blocked"
    copyable = "yes" if backend_fix.get("actionable") else ("not_now" if command else "no")
    title = backend_fix.get("title") or "Fix backend assistance and retry"

    lines = [f"Backend fix: {action_state} | title={title} | copyable={copyable}"]
    detail = backend_fix.get("guidance")
    if detail:
        lines.append(f"Backend fix detail: {detail}")
    blocker = backend_fix.get("actionability_reason")
    if blocker and blocker != detail:
        lines.append(f"Backend fix blocker: {blocker}")
    if command:
        lines.append(f"Backend fix command: {command}")
    return lines


def _render_runtime_fix_snapshot(summary: dict) -> list[str]:
    runtime = summary.get("runtime_diagnostic") or {}
    if runtime.get("category") not in {"environment_missing", "probe_driver_failed", "runtime_blocked"}:
        return []

    action_queue = summary.get("action_queue") or []
    runtime_fix = next((item for item in action_queue if item.get("kind") == "runtime_fix"), None)
    if not isinstance(runtime_fix, dict):
        return []

    command = runtime_fix.get("command")
    action_state = runtime_fix.get("action_state")
    if not action_state:
        action_state = "ready" if runtime_fix.get("actionable") else "blocked"
    copyable = "yes" if runtime_fix.get("actionable") else ("not_now" if command else "no")
    title = runtime_fix.get("title") or "Repair the runtime blockers before retrying the probe"

    lines = [f"Runtime fix: {action_state} | title={title} | copyable={copyable}"]
    detail = runtime_fix.get("guidance") or runtime.get("recommended_fix") or runtime.get("next_step")
    if detail:
        lines.append(f"Runtime fix detail: {detail}")
    blocker = runtime_fix.get("actionability_reason")
    if blocker and blocker != detail:
        lines.append(f"Runtime fix blocker: {blocker}")
    if command:
        lines.append(f"Runtime fix command: {command}")
    return lines


def _render_terminal_output(result: dict) -> str:
    summary = result.get("result_summary") or {}
    message = summary.get("terminal_message") or result.get("terminal_message") or {}
    capability = summary.get("capability_summary") or {}
    lifecycle = summary.get("workflow_lifecycle") or {}
    artifacts = summary.get("artifacts") or {}
    generation_result = summary.get("generation_result") or {}
    execution_result = summary.get("execution_result") or {}
    headline = message.get("headline") or "Run completed."
    detail = message.get("detail")
    command = message.get("recommended_command")
    alternatives = [item for item in (message.get("alternative_commands") or []) if item.get("command")]
    lines = [f"Outcome: {headline}"]
    if detail:
        lines.append(f"Detail: {detail}")
    blocking_reason = _terminal_blocking_reason(summary)
    if blocking_reason:
        lines.append(f"Reason: {blocking_reason}")
    blocking_category = _terminal_blocking_category(summary)
    if blocking_category:
        lines.append(f"Category: {blocking_category}")
    status_lines: list[str] = []
    backend_state = ((capability.get("backend") or {}).get("state"))
    generation_state = ((capability.get("generation") or {}).get("state"))
    runtime_state = ((capability.get("runtime") or {}).get("state"))
    external_lookup_status = summary.get("external_lookup_status")
    if backend_state:
        status_lines.append(f"Backend: {backend_state}")
    if generation_state:
        status_lines.append(f"Generation: {generation_state}")
    if runtime_state:
        status_lines.append(f"Runtime: {runtime_state}")
    if external_lookup_status:
        status_lines.append(f"External lookup: {external_lookup_status}")
    if status_lines:
        lines.append("Status:")
        for item in status_lines:
            lines.append(f"  {item}")
    execution_lines = _render_execution_closure(summary)
    if execution_lines:
        lines.extend(execution_lines)
    checkpoint_lines = _render_execution_checkpoint(summary)
    if checkpoint_lines:
        lines.extend(checkpoint_lines)
    physics_lines = _render_physics_snapshot(result, summary)
    if physics_lines:
        lines.extend(physics_lines)
    formula_lines = _render_formula_snapshot(summary)
    if formula_lines:
        lines.extend(formula_lines)
    workflow_hint_lines = _render_workflow_hint_snapshot(summary)
    if workflow_hint_lines:
        lines.extend(workflow_hint_lines)
    clarification_lines = _render_clarification_snapshot(summary)
    if clarification_lines:
        lines.extend(clarification_lines)
    workflow_lines = _render_workflow_snapshot(summary)
    if workflow_lines:
        lines.extend(workflow_lines)
    handoff_lines = _render_hpc_handoff_snapshot(summary)
    if handoff_lines:
        lines.extend(handoff_lines)
    unsupported_lines = _render_unsupported_snapshot(summary)
    if unsupported_lines:
        lines.extend(unsupported_lines)
    runtime_lines = _render_runtime_snapshot(summary)
    if runtime_lines:
        lines.extend(runtime_lines)
    actionability_lines = _render_actionability_snapshot(summary)
    if actionability_lines:
        lines.extend(actionability_lines)
    continuation_lines = _render_continuation_snapshot(summary)
    if continuation_lines:
        lines.extend(continuation_lines)
    retryability_lines = _render_retryability_snapshot(summary)
    if retryability_lines:
        lines.extend(retryability_lines)
    backend_fix_lines = _render_backend_fix_snapshot(summary)
    if backend_fix_lines:
        lines.extend(backend_fix_lines)
    runtime_fix_lines = _render_runtime_fix_snapshot(summary)
    if runtime_fix_lines:
        lines.extend(runtime_fix_lines)
    lifecycle_stage = lifecycle.get("stage")
    lifecycle_blocking = lifecycle.get("blocking_kind")
    lifecycle_next = ((lifecycle.get("next") or {}).get("action_kind"))
    if lifecycle_stage:
        lifecycle_line = f"Lifecycle: {lifecycle_stage}"
        if lifecycle_blocking and lifecycle_blocking != "none":
            lifecycle_line += f" | gate={lifecycle_blocking}"
        if lifecycle_next:
            lifecycle_line += f" | next={lifecycle_next}"
        lines.append(lifecycle_line)
    generation_phase = generation_result.get("phase")
    execution_phase = execution_result.get("phase")
    if generation_phase or execution_phase:
        lines.append("Results:")
        if generation_phase:
            lines.append(f"  Generation result: {generation_phase}")
        if execution_phase:
            lines.append(f"  Execution result: {execution_phase}")
    artifact_lines: list[str] = []
    for label, key in (
        ("Session", "session"),
        ("Physics", "physics"),
        ("Task", "task"),
        ("Plan", "plan"),
        ("Script", "script"),
        ("Probe", "probe"),
    ):
        value = artifacts.get(key)
        if value:
            artifact_lines.append(f"{label}: {value}")
    if artifact_lines:
        lines.append("Artifacts:")
        for item in artifact_lines[:6]:
            lines.append(f"  {item}")
    first_artifact = _terminal_first_artifact(summary)
    if first_artifact:
        label, value = first_artifact
        lines.append(f"Inspect first: {label}: {value}")
    if command:
        lines.append("Command:")
        lines.append(f"  {command}")
    if alternatives:
        lines.append("Options:")
        for item in alternatives[:3]:
            label = item.get("label") or "Alternative"
            lines.append(f"- {label}")
            lines.append(f"  {item['command']}")
    return "\n".join(lines)


def _render_output_payload(args: argparse.Namespace, result: dict) -> dict | str:
    if args.command == "run" and (args.summary_only or args.result_format == "summary"):
        return result.get("result_summary") or {}
    if args.command == "run" and args.result_format == "terminal":
        return _render_terminal_output(result)
    return result


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="pyquda-agent CLI")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _validate_args(args)
        result = run_command(
            RunConfig(
                task_description=args.task_description,
                backend=args.backend,
                model=args.model,
                api_key_file=args.api_key_file,
                base_url=args.base_url,
                pyquda_repo=args.pyquda_repo.expanduser().resolve(),
                output=args.output.expanduser().resolve(),
                output_explicit=("--output" in (argv or sys.argv[1:])),
                interactive=args.interactive,
                max_questions=args.max_questions,
                save_session=args.save_session.expanduser().resolve() if args.save_session else None,
                resume_session=args.resume_session.expanduser().resolve() if args.resume_session else None,
                print_context=args.print_context,
                dry_run=args.dry_run,
                verbose=args.verbose,
                result_format=("summary" if args.summary_only else args.result_format),
                set_fields=list(args.set_fields or []),
                reply_answers=list(args.reply_answers or []),
                enable_external_lookup=args.enable_external_lookup,
                llm_timeout=args.llm_timeout,
                runtime_probe=args.runtime_probe,
                probe_timeout=args.probe_timeout,
                probe_use_repo_pythonpath=args.probe_use_repo_pythonpath,
            )
        )
    except ValueError as exc:
        parser.error(str(exc))
    rendered = _render_output_payload(args, result)
    if isinstance(rendered, str):
        print(rendered)
    else:
        print(json.dumps(rendered, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
