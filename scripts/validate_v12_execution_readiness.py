#!/usr/bin/env python3
"""Validate v12 backend/runtime execution-readiness behavior and write a JSON report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pyquda_agent.python_version import ensure_supported_python
from scripts.check_pyquda_runtime import build_report as build_runtime_report
from scripts.probe_generated_workflow import build_probe


DEFAULT_BACKEND_EXECUTION = REPO_ROOT / "data" / "backend_execution.json"
DEFAULT_SUPPORTED_WORKFLOWS = REPO_ROOT / "data" / "supported_workflows_validation.json"
DEFAULT_V11_TASK_SUITE = REPO_ROOT / "data" / "v11_task_suite.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "v12_execution_readiness.json"
DEFAULT_PYQUDA_REPO = Path.home() / "PyQUDA"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate v12 backend/runtime execution-readiness behavior and write a JSON summary. "
            "This validator audits repair contracts, handoff readiness, runtime dependency blockers, and probe-failure semantics."
        )
    )
    parser.add_argument("--backend-execution", type=Path, default=DEFAULT_BACKEND_EXECUTION)
    parser.add_argument("--supported-workflows", type=Path, default=DEFAULT_SUPPORTED_WORKFLOWS)
    parser.add_argument("--v11-task-suite", type=Path, default=DEFAULT_V11_TASK_SUITE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pyquda-repo", type=Path, default=DEFAULT_PYQUDA_REPO)
    return parser.parse_args(argv)


def _load_json(path: Path) -> dict:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _case_backend_degraded_but_continueable(report: dict) -> dict:
    observed = []
    passed = False
    states = dict((report.get("backend_summary") or {}).get("states") or {})
    for backend in report.get("backends", []):
        repair = backend.get("repair_contract") or {}
        if backend.get("availability_state") == "fallback_only" and repair:
            observed.append(
                {
                    "backend": backend.get("backend"),
                    "repair_action_state": repair.get("repair_action_state"),
                    "repair_actionable": repair.get("repair_actionable"),
                    "verification_command": repair.get("verification_command"),
                }
            )
            if repair.get("repair_action_state") in {"blocked", "conditional", "ready"}:
                passed = True
    if not observed and states and all(state == "usable" for state in states.values()):
        return {
            "case_id": "backend_degraded_but_continueable",
            "passed": True,
            "observed": {
                "state": "not_needed",
                "reason": "All tracked backends are currently usable, so no degraded-backend repair contract is required.",
                "states": states,
            },
            "failure": None,
        }
    return {
        "case_id": "backend_degraded_but_continueable",
        "passed": passed,
        "observed": observed,
        "failure": None if passed else "No fallback backend exposed a stable repair contract.",
    }


def _case_backend_usable(report: dict) -> dict:
    backend_summary = report.get("backend_summary") or {}
    states = dict(backend_summary.get("states") or {})
    usable_backends = list(backend_summary.get("usable_backends") or [])
    if not usable_backends and states:
        usable_backends = [backend for backend, state in states.items() if state == "usable"]
    passed = bool(usable_backends)
    return {
        "case_id": "backend_usable",
        "passed": passed,
        "observed": {
            "states": states,
            "usable_backends": usable_backends,
            "fallback_only_backends": backend_summary.get("fallback_only_backends"),
        },
        "failure": None if passed else "No backend is currently marked usable.",
    }


def _case_backend_repair_path(report: dict) -> dict:
    observed = []
    passed = False
    states = dict((report.get("backend_summary") or {}).get("states") or {})
    for backend in report.get("backends", []):
        repair = backend.get("repair_contract") or {}
        if not repair:
            continue
        observed.append(
            {
                "backend": backend.get("backend"),
                "reason_category": repair.get("category"),
                "repair_action_command": repair.get("repair_action_command"),
                "verification_command": repair.get("verification_command"),
            }
        )
        if repair.get("verification_command"):
            passed = True
    if not observed and states and all(state == "usable" for state in states.values()):
        return {
            "case_id": "backend_repair_path",
            "passed": True,
            "observed": {
                "state": "not_needed",
                "reason": "All tracked backends are currently usable, so no backend repair-path contract is required.",
                "states": states,
            },
            "failure": None,
        }
    return {
        "case_id": "backend_repair_path",
        "passed": passed,
        "observed": observed,
        "failure": None if passed else "No backend fallback exposed a verification command.",
    }


def _case_runtime_blocked_but_handoff_ready(report: dict) -> dict:
    summary = report.get("summary") or {}
    passed = (
        summary.get("report_status") == "coherent_but_runtime_blocked"
        and int(summary.get("hpc_handoff_coherent_count") or 0) > 0
        and int((summary.get("direct_execution_status_counts") or {}).get("runtime_missing") or 0) > 0
    )
    return {
        "case_id": "runtime_blocked_but_handoff_ready",
        "passed": passed,
        "observed": {
            "report_status": summary.get("report_status"),
            "hpc_handoff_coherent_count": summary.get("hpc_handoff_coherent_count"),
            "direct_execution_status_counts": summary.get("direct_execution_status_counts"),
        },
        "failure": None if passed else "Supported-workflow validation no longer shows coherent handoff under runtime-blocked conditions.",
    }


def _case_runtime_blocked_due_to_missing_dependencies(pyquda_repo: Path) -> dict:
    report = build_runtime_report(pyquda_repo, use_repo_pythonpath=False)
    blockers = report.get("evidence_levels", {}).get("blockers") or []
    passed = "module_missing" in (report.get("blocker_categories") or []) and bool(blockers)
    return {
        "case_id": "runtime_blocked_due_to_missing_dependencies",
        "passed": passed,
        "observed": {
            "status": report.get("status"),
            "blocker_categories": report.get("blocker_categories"),
            "missing_modules": report.get("missing_modules"),
            "next_actions": report.get("next_actions"),
        },
        "failure": None if passed else "Runtime dependency report did not surface module-missing blockers.",
    }


def _case_runtime_blocked_due_to_probe_harness_failure() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "probe_target.py"
        script_path.write_text("print('ok')\n", encoding="utf-8")
        with patch("scripts.probe_generated_workflow.subprocess.run", side_effect=OSError("mock harness failure")):
            artifact = build_probe(script_path, timeout=5.0)
    passed = artifact.get("status") == "probe_driver_failed"
    return {
        "case_id": "runtime_blocked_due_to_probe_harness_failure",
        "passed": passed,
        "observed": {
            "status": artifact.get("status"),
            "runtime_level": artifact.get("runtime_level"),
            "blocker_scope": artifact.get("blocker_scope"),
            "next_action": artifact.get("next_action"),
        },
        "failure": None if passed else "Probe harness failure did not map to probe_driver_failed.",
    }


def _case_input_output_cluster_classification() -> dict:
    samples = {
        "input_visibility_blocked": "Traceback\nFileNotFoundError: Gauge configuration not found: /missing/gauge.lime",
        "output_writability_blocked": "PermissionError: Correlator output path /tmp/out.npy requires a writable parent directory on the submission filesystem",
        "cluster_assumption_mismatch": "ValueError: LATTICE_SIZE[0]=24 must be divisible by GRID_SIZE[0]=5",
    }
    observed = {}
    passed = True
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "probe_target.py"
        script_path.write_text("print('ok')\n", encoding="utf-8")
        for expected_status, stderr in samples.items():
            class Completed:
                def __init__(self, stderr_text: str) -> None:
                    self.returncode = 1
                    self.stdout = ""
                    self.stderr = stderr_text

            with patch("scripts.probe_generated_workflow.subprocess.run", return_value=Completed(stderr)):
                artifact = build_probe(script_path, timeout=5.0)
            observed[expected_status] = {
                "status": artifact.get("status"),
                "blocker_scope": artifact.get("blocker_scope"),
                "next_action": artifact.get("next_action"),
            }
            if artifact.get("status") != expected_status:
                passed = False
    return {
        "case_id": "runtime_blocked_subclassification",
        "passed": passed,
        "observed": observed,
        "failure": None if passed else "Probe blocking subclasses did not map to expected statuses.",
    }


def _case_real_tasks_need_less_manual_fallback(report: dict) -> dict:
    case_rows = report.get("cases") or []
    target_categories = {"ambiguous_meson", "explicit_supported"}
    selected = [case for case in case_rows if case.get("category") in target_categories]
    observed = {}
    passed = bool(selected)
    for case in selected:
        observed[case.get("case_id")] = {
            "category": case.get("category"),
            "passed": case.get("passed"),
            "product_status": ((case.get("observed") or {}).get("product_status")),
            "clarification_mode": ((case.get("observed") or {}).get("clarification_mode")),
            "primary_action_kind": ((case.get("observed") or {}).get("primary_action_kind")),
        }
        if not case.get("passed"):
            passed = False
            continue
        product_status = (case.get("observed") or {}).get("product_status")
        primary_action_kind = (case.get("observed") or {}).get("primary_action_kind")
        if product_status == "unsupported":
            passed = False
        if primary_action_kind == "backend_fix":
            passed = False
    return {
        "case_id": "real_tasks_need_less_manual_fallback",
        "passed": passed,
        "observed": observed,
        "failure": None if passed else "High-value rough task cases still degrade into unsupported or backend-fix-first responses.",
    }


def _build_question_answers(cases: list[dict]) -> dict:
    case_map = {case["case_id"]: case for case in cases}
    backend_usable = bool((case_map.get("backend_usable") or {}).get("passed"))
    runtime_evidence_stronger_than_v11 = all(
        bool((case_map.get(case_id) or {}).get("passed"))
        for case_id in (
            "runtime_blocked_but_handoff_ready",
            "runtime_blocked_due_to_missing_dependencies",
            "runtime_blocked_due_to_probe_harness_failure",
            "runtime_blocked_subclassification",
        )
    )
    real_tasks_less_manual_fallback = bool((case_map.get("real_tasks_need_less_manual_fallback") or {}).get("passed"))
    return {
        "backend_truly_usable": {
            "answer": backend_usable,
            "evidence_cases": ["backend_usable"],
        },
        "runtime_evidence_stronger_than_v11": {
            "answer": runtime_evidence_stronger_than_v11,
            "evidence_cases": [
                "runtime_blocked_but_handoff_ready",
                "runtime_blocked_due_to_missing_dependencies",
                "runtime_blocked_due_to_probe_harness_failure",
                "runtime_blocked_subclassification",
            ],
        },
        "real_tasks_less_reliant_on_manual_fallback": {
            "answer": real_tasks_less_manual_fallback,
            "evidence_cases": ["real_tasks_need_less_manual_fallback"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="scripts/validate_v12_execution_readiness.py")
    args = parse_args(argv)
    backend_report = _load_json(args.backend_execution)
    workflow_report = _load_json(args.supported_workflows)
    v11_task_suite = _load_json(args.v11_task_suite)
    pyquda_repo = args.pyquda_repo.expanduser().resolve()

    cases = [
        _case_backend_usable(backend_report),
        _case_backend_degraded_but_continueable(backend_report),
        _case_backend_repair_path(backend_report),
        _case_runtime_blocked_but_handoff_ready(workflow_report),
        _case_runtime_blocked_due_to_missing_dependencies(pyquda_repo),
        _case_runtime_blocked_due_to_probe_harness_failure(),
        _case_input_output_cluster_classification(),
        _case_real_tasks_need_less_manual_fallback(v11_task_suite),
    ]
    passed = [case for case in cases if case["passed"]]
    answers = _build_question_answers(cases)

    payload = {
        "suite": "v12_execution_readiness",
        "all_passed": len(passed) == len(cases),
        "cases": cases,
        "answers": answers,
        "summary": {
            "case_count": len(cases),
            "passed_case_count": len(passed),
            "coverage": [
                "backend truly usable",
                "backend degraded but continueable",
                "backend repair path",
                "runtime blocked but handoff ready",
                "runtime blocked due to missing dependencies",
                "runtime blocked due to probe harness failure",
                "runtime blocked due to input visibility / output writability / cluster assumptions",
                "real tasks less reliant on manual fallback",
            ],
            "contract": "execution_readiness_v12",
        },
        "note": (
            "This validator does not claim runtime_proved on the current machine. "
            "It checks whether backend usability, backend repair contracts, runtime-blocker classifications, and rough-task first-response quality remain explicit enough for HPC handoff and retry planning."
        ),
    }
    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote v12 execution-readiness report to {output_path}")
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
