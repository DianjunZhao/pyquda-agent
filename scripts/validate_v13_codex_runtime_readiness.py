#!/usr/bin/env python3
"""Validate v13 codex usability and local runtime-proof readiness boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_BACKEND_EXECUTION = REPO_ROOT / "data" / "backend_execution.json"
DEFAULT_RUNTIME_CHECK = REPO_ROOT / "data" / "pyquda_runtime_check.json"
DEFAULT_RUNTIME_CANDIDATES = REPO_ROOT / "data" / "runtime_candidates.json"
DEFAULT_GOAL_AUDIT = REPO_ROOT / "data" / "goal_audit.json"
DEFAULT_README = REPO_ROOT / "README.md"
DEFAULT_RUNTIME_BOOTSTRAP_DOC = REPO_ROOT / "docs" / "PYQUDA_RUNTIME_BOOTSTRAP.md"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "v13_codex_runtime_readiness.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate v13 codex usability and runtime readiness boundaries.")
    parser.add_argument("--backend-execution", type=Path, default=DEFAULT_BACKEND_EXECUTION)
    parser.add_argument("--runtime-check", type=Path, default=DEFAULT_RUNTIME_CHECK)
    parser.add_argument("--runtime-candidates", type=Path, default=DEFAULT_RUNTIME_CANDIDATES)
    parser.add_argument("--goal-audit", type=Path, default=DEFAULT_GOAL_AUDIT)
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    parser.add_argument("--runtime-bootstrap-doc", type=Path, default=DEFAULT_RUNTIME_BOOTSTRAP_DOC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _load_json(path: Path) -> dict:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _load_text(path: Path) -> str:
    return path.expanduser().resolve().read_text(encoding="utf-8")


def _codex_backend_state(report: dict) -> dict:
    states = dict((report.get("backend_summary") or {}).get("states") or {})
    state = states.get("codex")
    passed = state in {"usable", "mixed", "fallback_only"}
    return {
        "case_id": "codex_backend_state",
        "passed": passed,
        "observed": {
            "codex_state": state,
            "usable_backends": (report.get("backend_summary") or {}).get("usable_backends"),
            "fallback_only_backends": (report.get("backend_summary") or {}).get("fallback_only_backends"),
        },
        "failure": None if passed else "backend_execution.json does not expose a stable codex backend state.",
    }


def _codex_backend_repair_contract(report: dict) -> dict:
    codex_entry = next((item for item in report.get("backends", []) if item.get("backend") == "codex"), {})
    repair = codex_entry.get("repair_contract") or {}
    availability_state = codex_entry.get("availability_state")
    if availability_state == "usable":
        return {
            "case_id": "codex_backend_repair_contract",
            "passed": True,
            "observed": {
                "availability_state": availability_state,
                "state": "not_needed",
                "reason": "Codex is currently usable in the real CLI path, so no fallback repair contract is required.",
            },
            "failure": None,
        }
    passed = bool(repair.get("verification_command")) and bool(repair.get("category"))
    return {
        "case_id": "codex_backend_repair_contract",
        "passed": passed,
        "observed": {
            "availability_state": availability_state,
            "category": repair.get("category"),
            "detail_category": repair.get("detail_category"),
            "repair_action_state": repair.get("repair_action_state"),
            "verification_command": repair.get("verification_command"),
            "recommended_fix": repair.get("recommended_fix"),
        },
        "failure": None if passed else "Codex fallback state is missing a stable repair contract or verification command.",
    }


def _runtime_remaining_blocker_contract(runtime_check: dict, runtime_candidates: dict) -> dict:
    primary_blocker = runtime_check.get("primary_blocker")
    if primary_blocker is None:
        blockers = list(runtime_check.get("evidence_levels", {}).get("blockers") or [])
        if blockers:
            first = blockers[0]
            primary_blocker = {
                "category": first.get("category"),
                "module": first.get("module"),
                "error_type": first.get("error_type"),
                "error": first.get("error"),
            }
    shortest_remaining_steps = runtime_check.get("shortest_remaining_steps")
    if not shortest_remaining_steps:
        shortest_remaining_steps = list(runtime_check.get("next_actions") or [])
    passed = (
        runtime_check.get("status") in {"ready", "environment_missing"}
        and primary_blocker is not None
        and bool(shortest_remaining_steps)
        and isinstance((runtime_candidates.get("summary") or {}).get("best_candidate_status"), str)
    )
    return {
        "case_id": "runtime_remaining_blocker_contract",
        "passed": passed,
        "observed": {
            "status": runtime_check.get("status"),
            "runtime_level": runtime_check.get("runtime_level"),
            "primary_blocker": primary_blocker,
            "shortest_remaining_steps": shortest_remaining_steps,
            "best_candidate_status": (runtime_candidates.get("summary") or {}).get("best_candidate_status"),
            "best_candidate_python": (runtime_candidates.get("summary") or {}).get("best_candidate_python"),
            "blocker_categories": runtime_check.get("blocker_categories"),
        },
        "failure": None if passed else "Runtime readiness reports do not expose a stable primary blocker plus shortest remaining steps.",
    }


def _docs_and_audit_consistent(backend_execution: dict, runtime_check: dict, goal_audit: dict, readme_text: str, bootstrap_text: str) -> dict:
    backend_states = dict((backend_execution.get("backend_summary") or {}).get("states") or {})
    codex_state = backend_states.get("codex")
    audit_state = (goal_audit.get("backend_availability") or {}).get("codex")
    runtime_proved = runtime_check.get("runtime_level") == "runtime_proved" or runtime_check.get("status") == "ready"
    passed = (
        codex_state == audit_state
        and "codex" in readme_text.lower()
        and "runtime" in bootstrap_text.lower()
        and (runtime_proved or "runtime_proved" in bootstrap_text or "runtime_proved" in readme_text)
    )
    return {
        "case_id": "docs_and_audit_consistent_with_reports",
        "passed": passed,
        "observed": {
            "backend_execution_codex_state": codex_state,
            "goal_audit_codex_state": audit_state,
            "runtime_proved": runtime_proved,
            "readme_mentions_codex": "codex" in readme_text.lower(),
            "bootstrap_mentions_runtime": "runtime" in bootstrap_text.lower(),
        },
        "failure": None if passed else "README/bootstrap/audit no longer align with the reported codex/runtime boundary.",
    }


def _answers(cases: list[dict], backend_execution: dict, runtime_check: dict) -> dict:
    case_map = {case["case_id"]: case for case in cases}
    backend_states = dict((backend_execution.get("backend_summary") or {}).get("states") or {})
    codex_state = backend_states.get("codex")
    runtime_proved = runtime_check.get("runtime_level") == "runtime_proved" or runtime_check.get("status") == "ready"
    return {
        "codex_backend_usable": {
            "answer": codex_state in {"usable", "mixed"},
            "evidence_cases": ["codex_backend_state", "codex_backend_repair_contract"],
        },
        "codex_backend_state": {
            "answer": codex_state,
            "evidence_cases": ["codex_backend_state"],
        },
        "local_runtime_proved": {
            "answer": runtime_proved,
            "evidence_cases": ["runtime_remaining_blocker_contract"],
        },
        "runtime_remaining_blockers": {
            "answer": list(runtime_check.get("blocker_categories") or []),
            "evidence_cases": ["runtime_remaining_blocker_contract"],
        },
        "docs_and_audit_consistent": {
            "answer": bool((case_map.get("docs_and_audit_consistent_with_reports") or {}).get("passed")),
            "evidence_cases": ["docs_and_audit_consistent_with_reports"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    backend_execution = _load_json(args.backend_execution)
    runtime_check = _load_json(args.runtime_check)
    runtime_candidates = _load_json(args.runtime_candidates)
    goal_audit = _load_json(args.goal_audit)
    readme_text = _load_text(args.readme)
    bootstrap_text = _load_text(args.runtime_bootstrap_doc)

    cases = [
        _codex_backend_state(backend_execution),
        _codex_backend_repair_contract(backend_execution),
        _runtime_remaining_blocker_contract(runtime_check, runtime_candidates),
        _docs_and_audit_consistent(backend_execution, runtime_check, goal_audit, readme_text, bootstrap_text),
    ]
    payload = {
        "suite": "v13_codex_runtime_readiness",
        "all_passed": all(case["passed"] for case in cases),
        "cases": cases,
        "answers": _answers(cases, backend_execution, runtime_check),
        "summary": {
            "contract": "codex_runtime_readiness_v13",
            "case_count": len(cases),
            "coverage": [
                "codex backend usable or explicitly fallback_only",
                "runtime proved or exact remaining blockers",
                "backend repair contract",
                "runtime repair contract",
                "docs and audit consistency",
            ],
        },
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote v13 codex/runtime readiness report to {output}")
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
