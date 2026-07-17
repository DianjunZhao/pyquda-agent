#!/usr/bin/env python3
"""Run non-mocked backend validation for the real CLI path. Requires Python >= 3.10."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pyquda_agent.config import resolve_api_model
from pyquda_agent.python_version import ensure_supported_python


DEFAULT_PYQUDA_REPO = Path.home() / "PyQUDA"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "backend_execution.json"
DEFAULT_API_MODEL = resolve_api_model(None)

CASES = {
    "rough_pion": {
        "request": "write a simple PyQUDA script for pi meson two-point",
        "expected_status": "needs_input",
        "expected_target": "pion_two_point_correlator",
        "expect_formula_proposals": True,
    },
    "ambiguous_meson": {
        "request": "I want a meson correlator script but I am not sure about the exact operator",
        "expected_status": "needs_input",
        "expected_target": "meson_two_point_correlator_unspecified",
        "expect_formula_proposals": True,
    },
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate real backend execution or explicit fallback reporting. "
            "Requires Python >= 3.10; if bare python3 is older on your machine, rerun with an explicit >=3.10 interpreter path."
        )
    )
    parser.add_argument("--pyquda-repo", type=Path, default=DEFAULT_PYQUDA_REPO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--api-model",
        default=DEFAULT_API_MODEL,
        help="Model passed to --backend api. Defaults to PYQUDA_AGENT_API_MODEL/DEEPSEEK_MODEL/OPENAI_MODEL when set.",
    )
    parser.add_argument("--llm-timeout", type=float, default=30.0)
    parser.add_argument(
        "--case-timeout",
        type=float,
        default=90.0,
        help="Outer subprocess timeout in seconds for each validation case.",
    )
    parser.add_argument(
        "--include-raw-payloads",
        action="store_true",
        help="Keep raw stdout/stderr and parsed payloads in the written report for debugging.",
    )
    return parser.parse_args(argv)


def _artifact_paths(script_path: Path) -> tuple[Path, Path, Path]:
    return (
        script_path.with_suffix(".physics.json"),
        script_path.with_suffix(".task.json"),
        script_path.with_suffix(".plan.json"),
    )


def _run_case(
    *,
    backend: str,
    case_name: str,
    request: str,
    pyquda_repo: Path,
    output_root: Path,
    api_model: str | None,
    llm_timeout: float,
    case_timeout: float,
) -> dict:
    script_path = output_root / f"{case_name}_{backend}.py"
    cmd = [
        sys.executable,
        "-m",
        "pyquda_agent.cli",
        "run",
        request,
        "--backend",
        backend,
        "--llm-timeout",
        str(llm_timeout),
        "--dry-run",
        "--no-interactive",
        "--output",
        str(script_path),
        "--pyquda-repo",
        str(pyquda_repo),
    ]
    if backend == "api" and api_model:
        cmd.extend(["--model", api_model])
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not existing_pythonpath else f"src:{existing_pythonpath}"
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            timeout=case_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_text = exc.output if isinstance(exc.output, str) else ""
        stderr_text = exc.stderr if isinstance(exc.stderr, str) else ""
        payload = None
        if stdout_text.strip():
            try:
                payload = json.loads(stdout_text)
            except json.JSONDecodeError:
                payload = None
        return {
            "case": case_name,
            "request": request,
            "returncode": None,
            "stdout": stdout_text.strip(),
            "stderr": stderr_text.strip(),
            "parsed": payload,
            "status": "validator_timeout",
            "target_id": None,
            "formula_count": 0,
            "artifacts_exist": False,
            "llm_assistance": {
                "attempted": True,
                "used": False,
                "fallback": False,
                "requested_backend": backend,
                "selected_backend": backend,
                "selection_reason": (
                    f"Validator case timed out after {case_timeout:g} seconds before a coherent CLI result was captured."
                ),
            },
            "backend_diagnostic": {
                "status": "validator_timeout",
                "category": "timeout",
                "detail_category": "validator_case_timeout",
                "message": (
                    f"validate_backend_execution.py timed out after {case_timeout:g} seconds while waiting for the CLI subprocess."
                ),
                "failure_origin": "local_validator",
                "recovery_mode": "increase_validator_timeout_or_run_case_directly",
                "retryable_now": True,
                "recommended_fix": "Increase `--case-timeout`, or run the target CLI case directly to inspect the slower backend path.",
                "next_step": "Retry the validator with a larger `--case-timeout`, or execute the backend-specific CLI command directly.",
            },
            "runtime_diagnostic": {
                "status": "blocked_by_validator",
                "category": "validator_timeout",
            },
            "product_status": "validator_timeout",
            "generation_result": {"phase": "validator_timeout"},
            "execution_result": {"phase": "blocked_by_validator"},
            "delivery_status": {
                "generation": {"phase": "validator_timeout"},
                "execution": {"phase": "blocked_by_validator"},
            },
            "action_queue": [
                {
                    "kind": "backend_fix",
                    "priority": "primary",
                    "title": "Increase validator timeout or run the backend case directly",
                    "command": (
                        f"PYTHONPATH=src python3 scripts/validate_backend_execution.py --pyquda-repo {pyquda_repo} "
                        f"--case-timeout {max(case_timeout * 2.0, case_timeout + 10.0):g}"
                    ),
                    "guidance": (
                        "This timeout came from the outer validator subprocess budget, not from a coherent product-level backend fallback. "
                        "Increase the validator case timeout or run the specific CLI case directly."
                    ),
                    "action_state": "ready",
                    "actionable": True,
                    "actionability_reason": None,
                }
            ],
            "case_timeout_seconds": case_timeout,
        }
    payload = None
    if completed.stdout.strip():
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            payload = None
    physics_artifact, task_artifact, plan_artifact = _artifact_paths(script_path)
    llm_assistance = (payload or {}).get("llm_assistance") if isinstance(payload, dict) else None
    target_id = None
    formula_count = 0
    if isinstance(payload, dict):
        physics = payload.get("physics") or {}
        target_id = ((physics.get("confirmed_interpretation") or {}).get("target_id")) or (
            (physics.get("inferred_interpretation") or {}).get("target_id")
        )
        formula_count = len(physics.get("formula_proposals") or [])
    backend_diagnostic = None
    runtime_diagnostic = None
    product_status = None
    generation_result = None
    execution_result = None
    delivery_status = None
    action_queue = None
    if isinstance(payload, dict):
        summary = payload.get("result_summary") or {}
        backend_diagnostic = payload.get("backend_diagnostic") or summary.get("backend_diagnostic")
        runtime_diagnostic = payload.get("runtime_diagnostic") or summary.get("runtime_diagnostic")
        product_status = payload.get("product_status") or summary.get("product_status")
        generation_result = payload.get("generation_result") or summary.get("generation_result")
        execution_result = payload.get("execution_result") or summary.get("execution_result")
        delivery_status = payload.get("delivery_status") or summary.get("delivery_status")
        action_queue = payload.get("action_queue") or summary.get("action_queue")
    return {
        "case": case_name,
        "request": request,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "parsed": payload,
        "status": payload.get("status") if isinstance(payload, dict) else None,
        "target_id": target_id,
        "formula_count": formula_count,
        "artifacts_exist": physics_artifact.exists() and task_artifact.exists() and plan_artifact.exists(),
        "llm_assistance": llm_assistance,
        "backend_diagnostic": backend_diagnostic,
        "runtime_diagnostic": runtime_diagnostic,
        "product_status": product_status,
        "generation_result": generation_result,
        "execution_result": execution_result,
        "delivery_status": delivery_status,
        "action_queue": action_queue,
        "case_timeout_seconds": case_timeout,
    }


def _backend_mode(llm_assistance: dict | None) -> str:
    if not isinstance(llm_assistance, dict):
        return "missing"
    if llm_assistance.get("used"):
        return "used"
    if llm_assistance.get("fallback"):
        return "fallback"
    if llm_assistance.get("attempted"):
        return "attempted_without_result"
    return "rules_only"


def _backend_path_summary(result: dict) -> dict:
    llm_assistance = result.get("llm_assistance") or {}
    backend_diagnostic = result.get("backend_diagnostic") or {}
    return {
        "requested_backend": llm_assistance.get("requested_backend"),
        "selected_backend": llm_assistance.get("selected_backend"),
        "backend_mode": _backend_mode(llm_assistance),
        "attempted": bool(llm_assistance.get("attempted")),
        "used": bool(llm_assistance.get("used")),
        "fallback": bool(llm_assistance.get("fallback")),
        "fallback_category": llm_assistance.get("fallback_category"),
        "fallback_reason": llm_assistance.get("fallback_reason"),
        "selection_reason": llm_assistance.get("selection_reason"),
        "configured_backend": llm_assistance.get("configured_backend"),
        "backend_diagnostic_status": backend_diagnostic.get("status"),
        "backend_diagnostic_category": backend_diagnostic.get("category"),
        "backend_failure_origin": backend_diagnostic.get("failure_origin"),
        "backend_recovery_mode": backend_diagnostic.get("recovery_mode"),
        "backend_retryable_now": backend_diagnostic.get("retryable_now"),
        "codex_preflight_attempted": bool(llm_assistance.get("codex_preflight_attempted")),
        "codex_preflight_status": llm_assistance.get("codex_preflight_status"),
        "codex_preflight_category": llm_assistance.get("codex_preflight_category"),
        "codex_preflight_reason": llm_assistance.get("codex_preflight_reason"),
        "codex_preflight_skipped": bool(llm_assistance.get("codex_preflight_skipped")),
        "codex_preflight_skip_reason": llm_assistance.get("codex_preflight_skip_reason"),
        "codex_preflight_soft_failed": bool(llm_assistance.get("codex_preflight_soft_failed")),
        "codex_preflight_soft_failure_reason": llm_assistance.get("codex_preflight_soft_failure_reason"),
        "session_backend_memory_considered": bool(llm_assistance.get("session_backend_memory_considered")),
        "session_backend_memory_used": bool(llm_assistance.get("session_backend_memory_used")),
        "session_backend_memory_reason": llm_assistance.get("session_backend_memory_reason"),
        "session_backend_prior_category": llm_assistance.get("session_backend_prior_category"),
        "intent_strategy": llm_assistance.get("intent_strategy"),
        "intent_prompt_profile": llm_assistance.get("intent_prompt_profile"),
        "intent_primary_timeout_seconds": llm_assistance.get("intent_primary_timeout_seconds"),
        "timeout_recovery_attempted": bool(llm_assistance.get("timeout_recovery_attempted")),
        "timeout_recovery_skipped": bool(llm_assistance.get("timeout_recovery_skipped")),
        "timeout_recovery_skip_reason": llm_assistance.get("timeout_recovery_skip_reason"),
        "timeout_recovery_used": bool(llm_assistance.get("timeout_recovery_used")),
        "timeout_recovery_failed": bool(llm_assistance.get("timeout_recovery_failed")),
        "timeout_recovery_trigger_category": llm_assistance.get("timeout_recovery_trigger_category"),
        "timeout_recovery_timeout_seconds": llm_assistance.get("timeout_recovery_timeout_seconds"),
        "timeout_recovery_failure_category": llm_assistance.get("timeout_recovery_failure_category"),
    }


def _compact_case_summary(result: dict) -> dict:
    runtime_diagnostic = result.get("runtime_diagnostic") or {}
    backend_diagnostic = result.get("backend_diagnostic") or {}
    backend_path = result.get("backend_path") or {}
    return {
        "case": result.get("case"),
        "status": result.get("status"),
        "product_status": result.get("product_status"),
        "target_id": result.get("target_id"),
        "formula_count": result.get("formula_count"),
        "artifacts_exist": result.get("artifacts_exist"),
        "coherent": result.get("coherent"),
        "backend_path": result.get("backend_path"),
        "generation_phase": ((result.get("generation_result") or {}).get("phase")),
        "execution_phase": ((result.get("execution_result") or {}).get("phase")),
        "backend_status": backend_diagnostic.get("status"),
        "backend_category": backend_diagnostic.get("category"),
        "backend_failure_origin": backend_diagnostic.get("failure_origin"),
        "backend_recovery_mode": backend_diagnostic.get("recovery_mode"),
        "backend_retryable_now": backend_diagnostic.get("retryable_now"),
        "codex_preflight_attempted": backend_path.get("codex_preflight_attempted"),
        "codex_preflight_status": backend_path.get("codex_preflight_status"),
        "codex_preflight_category": backend_path.get("codex_preflight_category"),
        "codex_preflight_reason": backend_path.get("codex_preflight_reason"),
        "codex_preflight_skipped": backend_path.get("codex_preflight_skipped"),
        "codex_preflight_skip_reason": backend_path.get("codex_preflight_skip_reason"),
        "codex_preflight_soft_failed": backend_path.get("codex_preflight_soft_failed"),
        "codex_preflight_soft_failure_reason": backend_path.get("codex_preflight_soft_failure_reason"),
        "session_backend_memory_considered": backend_path.get("session_backend_memory_considered"),
        "session_backend_memory_used": backend_path.get("session_backend_memory_used"),
        "session_backend_memory_reason": backend_path.get("session_backend_memory_reason"),
        "session_backend_prior_category": backend_path.get("session_backend_prior_category"),
        "intent_strategy": backend_path.get("intent_strategy"),
        "intent_prompt_profile": backend_path.get("intent_prompt_profile"),
        "intent_primary_timeout_seconds": backend_path.get("intent_primary_timeout_seconds"),
        "timeout_recovery_attempted": backend_path.get("timeout_recovery_attempted"),
        "timeout_recovery_skipped": backend_path.get("timeout_recovery_skipped"),
        "timeout_recovery_skip_reason": backend_path.get("timeout_recovery_skip_reason"),
        "timeout_recovery_used": backend_path.get("timeout_recovery_used"),
        "timeout_recovery_failed": backend_path.get("timeout_recovery_failed"),
        "timeout_recovery_trigger_category": backend_path.get("timeout_recovery_trigger_category"),
        "timeout_recovery_timeout_seconds": backend_path.get("timeout_recovery_timeout_seconds"),
        "timeout_recovery_failure_category": backend_path.get("timeout_recovery_failure_category"),
        "runtime_category": runtime_diagnostic.get("category"),
        "runtime_status": runtime_diagnostic.get("status"),
        "backend_repair": _backend_repair_summary(result),
    }


def _find_action(result: dict, kind: str) -> dict | None:
    for item in result.get("action_queue") or []:
        if isinstance(item, dict) and item.get("kind") == kind:
            return item
    return None


def _backend_repair_summary(result: dict) -> dict | None:
    backend_diagnostic = result.get("backend_diagnostic") or {}
    if backend_diagnostic.get("status") != "fallback":
        return None
    backend_fix = _find_action(result, "backend_fix") or {}
    verification_command = backend_fix.get("command")
    verification_label = backend_fix.get("title")
    if (
        backend_diagnostic.get("category") == "local_environment_error"
        and backend_diagnostic.get("detail_category") == "codex_app_client_init_failed"
    ):
        verification_command = "codex exec 'Reply with exactly: OK'"
        verification_label = "Verify bare codex exec in a normal local shell"
    return {
        "reason": backend_diagnostic.get("message"),
        "category": backend_diagnostic.get("category"),
        "detail_category": backend_diagnostic.get("detail_category"),
        "failure_origin": backend_diagnostic.get("failure_origin"),
        "recovery_mode": backend_diagnostic.get("recovery_mode"),
        "recommended_fix": backend_diagnostic.get("recommended_fix"),
        "next_step": backend_diagnostic.get("next_step"),
        "repair_action_title": backend_fix.get("title"),
        "repair_action_command": backend_fix.get("command"),
        "repair_action_state": backend_fix.get("action_state"),
        "repair_actionable": backend_fix.get("actionable"),
        "repair_actionability_reason": backend_fix.get("actionability_reason"),
        "verification_label": verification_label,
        "verification_command": verification_command,
    }


def _diagnostic_fields_present(result: dict) -> bool:
    llm_assistance = result.get("llm_assistance")
    backend_diagnostic = result.get("backend_diagnostic")
    if not isinstance(llm_assistance, dict):
        return False
    if not llm_assistance.get("requested_backend"):
        return False
    if not llm_assistance.get("selected_backend"):
        return False
    if not llm_assistance.get("selection_reason"):
        return False
    if not isinstance(backend_diagnostic, dict):
        return False
    if not backend_diagnostic.get("status"):
        return False
    if llm_assistance.get("codex_preflight_attempted") and not llm_assistance.get("codex_preflight_status"):
        return False
    if llm_assistance.get("codex_preflight_skipped") and not llm_assistance.get("codex_preflight_skip_reason"):
        return False
    if llm_assistance.get("codex_preflight_soft_failed") and not llm_assistance.get("codex_preflight_soft_failure_reason"):
        return False
    if llm_assistance.get("session_backend_memory_considered") and not llm_assistance.get("session_backend_memory_reason"):
        return False
    if llm_assistance.get("timeout_recovery_attempted") and llm_assistance.get("timeout_recovery_timeout_seconds") in (None, ""):
        return False
    if llm_assistance.get("timeout_recovery_skipped") and not llm_assistance.get("timeout_recovery_skip_reason"):
        return False
    if llm_assistance.get("timeout_recovery_failed") and not llm_assistance.get("timeout_recovery_failure_category"):
        return False
    if llm_assistance.get("used"):
        return True
    if llm_assistance.get("fallback"):
        return (
            bool(llm_assistance.get("fallback_reason"))
            and bool(llm_assistance.get("fallback_category"))
            and bool(backend_diagnostic.get("category"))
            and backend_diagnostic.get("failure_origin") is not None
            and bool(backend_diagnostic.get("recovery_mode"))
            and isinstance(backend_diagnostic.get("retryable_now"), bool)
        )
    return True


def _origin_counts(backends: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for backend in backends:
        for case in backend.get("cases", []):
            origin = ((case.get("backend_diagnostic") or {}).get("failure_origin")) or "unknown"
            counts[origin] = counts.get(origin, 0) + 1
    return counts


def _recovery_mode_counts(backends: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for backend in backends:
        for case in backend.get("cases", []):
            mode = ((case.get("backend_diagnostic") or {}).get("recovery_mode")) or "unknown"
            counts[mode] = counts.get(mode, 0) + 1
    return counts


def _llm_coherent(llm_assistance: dict | None) -> bool:
    if not isinstance(llm_assistance, dict):
        return False
    if llm_assistance.get("used"):
        return bool(llm_assistance.get("attempted"))
    if llm_assistance.get("fallback"):
        return bool(llm_assistance.get("fallback_reason")) and bool(llm_assistance.get("fallback_category"))
    return bool(llm_assistance.get("selected_backend")) and bool(llm_assistance.get("requested_backend"))


def _case_coherent(result: dict, expected: dict) -> bool:
    if result.get("status") == "validator_timeout":
        return False
    return (
        result.get("returncode") == 0
        and result.get("status") == expected["expected_status"]
        and result.get("target_id") == expected["expected_target"]
        and result.get("artifacts_exist")
        and _llm_coherent(result.get("llm_assistance"))
        and _diagnostic_fields_present(result)
        and result.get("product_status") == "needs_input"
        and ((result.get("generation_result") or {}).get("phase")) == "blocked_on_input"
        and ((result.get("execution_result") or {}).get("phase")) == "blocked_by_generation"
        and (((result.get("delivery_status") or {}).get("generation") or {}).get("phase")) == "blocked_on_input"
        and (((result.get("delivery_status") or {}).get("execution") or {}).get("phase")) == "blocked_by_generation"
        and (
            not expected["expect_formula_proposals"]
            or (result.get("formula_count") or 0) > 0
        )
    )


def _availability_state(cases: list[dict]) -> str:
    if not cases:
        return "missing"
    if not all(case.get("coherent") for case in cases):
        return "incoherent"
    modes = {_backend_mode(case.get("llm_assistance")) for case in cases}
    if modes == {"used"}:
        return "usable"
    if modes <= {"fallback", "rules_only"}:
        return "fallback_only"
    if "used" in modes:
        return "mixed"
    return "diagnostic_only"


def _backend_repair_contract(cases: list[dict]) -> dict | None:
    degraded_cases = [
        case
        for case in cases
        if (case.get("backend_diagnostic") or {}).get("status") in {"fallback", "validator_timeout"}
    ]
    if not degraded_cases:
        return None
    first_case = degraded_cases[0]
    if (first_case.get("backend_diagnostic") or {}).get("status") == "validator_timeout":
        backend_diagnostic = first_case.get("backend_diagnostic") or {}
        backend_fix = _find_action(first_case, "backend_fix") or {}
        return {
            "reason": backend_diagnostic.get("message"),
            "category": backend_diagnostic.get("category"),
            "detail_category": backend_diagnostic.get("detail_category"),
            "failure_origin": backend_diagnostic.get("failure_origin"),
            "recovery_mode": backend_diagnostic.get("recovery_mode"),
            "recommended_fix": backend_diagnostic.get("recommended_fix"),
            "next_step": backend_diagnostic.get("next_step"),
            "repair_action_title": backend_fix.get("title"),
            "repair_action_command": backend_fix.get("command"),
            "repair_action_state": backend_fix.get("action_state"),
            "repair_actionable": backend_fix.get("actionable"),
            "repair_actionability_reason": backend_fix.get("actionability_reason"),
            "verification_label": "Retry validate_backend_execution.py with a larger case timeout",
            "verification_command": backend_fix.get("command"),
            "case_count": len(degraded_cases),
            "case_names": [case.get("case") for case in degraded_cases],
        }
    repair = _backend_repair_summary(first_case)
    if repair is None:
        return None
    repair["case_count"] = len(degraded_cases)
    repair["case_names"] = [case.get("case") for case in degraded_cases]
    return repair


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="scripts/validate_backend_execution.py")
    args = parse_args(argv)
    pyquda_repo = args.pyquda_repo.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    output_root = output_path.parent.parent / "outputs" / "backend_execution" if output_path.parent.name == "data" else output_path.parent / "outputs"
    output_root.mkdir(parents=True, exist_ok=True)

    backends: list[dict] = []
    for backend in ("auto", "api", "codex"):
        cases: list[dict] = []
        for case_name, spec in CASES.items():
            case_result = _run_case(
                backend=backend,
                case_name=case_name,
                request=spec["request"],
                pyquda_repo=pyquda_repo,
                output_root=output_root,
                api_model=args.api_model,
                llm_timeout=args.llm_timeout,
                case_timeout=args.case_timeout,
            )
            case_result["coherent"] = _case_coherent(case_result, spec)
            case_result["backend_path"] = _backend_path_summary(case_result)
            case_result["case_summary"] = _compact_case_summary(case_result)
            if not args.include_raw_payloads:
                case_result.pop("stdout", None)
                case_result.pop("stderr", None)
                case_result.pop("parsed", None)
            cases.append(case_result)
        backends.append(
            {
                "backend": backend,
                "configured_model": args.api_model if backend in {"auto", "api"} else None,
                "cases": cases,
                "case_summaries": [case["case_summary"] for case in cases],
                "coherent": all(case["coherent"] for case in cases),
                "availability_state": _availability_state(cases),
                "used_case_count": sum(1 for case in cases if _backend_mode(case.get("llm_assistance")) == "used"),
                "fallback_case_count": sum(1 for case in cases if _backend_mode(case.get("llm_assistance")) == "fallback"),
                "repair_contract": _backend_repair_contract(cases),
            }
        )

    payload = {
        "pyquda_repo": str(pyquda_repo),
        "api_model": args.api_model,
        "llm_timeout": args.llm_timeout,
        "case_timeout": args.case_timeout,
        "backends": backends,
        "all_coherent": all(item["coherent"] for item in backends),
        "backend_summary": {
            "states": {item["backend"]: item["availability_state"] for item in backends},
            "usable_backends": [item["backend"] for item in backends if item["availability_state"] in {"usable", "mixed"}],
            "fallback_only_backends": [item["backend"] for item in backends if item["availability_state"] == "fallback_only"],
            "incoherent_backends": [item["backend"] for item in backends if item["availability_state"] == "incoherent"],
            "failure_origin_counts": _origin_counts(backends),
            "recovery_mode_counts": _recovery_mode_counts(backends),
        },
        "note": (
            "A backend is considered coherent only when the real CLI path either uses it successfully or records an explicit fallback "
            "with machine-readable requested/selected backend, selection reason, fallback reason/category fields, and coherent product-facing "
            "generation/execution summary phases for the rough-request clarification path. "
            "The compact report also preserves backend failure origin and recovery semantics so product clients can separate local configuration issues from credentials, network, upstream-service, or backend-response problems, "
            "and it records a repair contract with unavailable reason, recommended fix, repair action, and verification command when fallback occurs. "
            "This report does not claim live online lookup support."
        ),
        "payload_policy": {
            "raw_payloads_included": args.include_raw_payloads,
            "default_behavior": "compact_case_summaries_only",
            "raw_fields": ["stdout", "stderr", "parsed"],
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote backend execution report to {output_path}")
    return 0 if payload["all_coherent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
