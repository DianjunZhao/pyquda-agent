#!/usr/bin/env python3
"""Run the v11 natural-language task-suite regression and write a JSON summary."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
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

from pyquda_agent.cli import main as cli_main
from pyquda_agent.python_version import ensure_supported_python
from pyquda_agent.v11_task_suite import V11_TASK_SUITE


DEFAULT_OUTPUT = REPO_ROOT / "data" / "v11_task_suite.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the v11 natural-language task-suite regression and write a JSON summary. "
            "Requires Python >= 3.10; if bare python3 is older on your machine, rerun with an explicit >=3.10 interpreter path. "
            "This validator checks current summary-contract behavior; it does not prove backend usability or a local PyQUDA runtime."
        )
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _prepare_repo_fixture(root: Path) -> tuple[Path, Path, Path]:
    pyquda = root / "PyQUDA"
    output = root / "outputs" / "task_suite.py"
    index_path = root / "data" / "pyquda_index.json"

    (root / "data").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (pyquda / "examples").mkdir(parents=True)
    (pyquda / "tests").mkdir(parents=True)
    (pyquda / "pyquda_utils").mkdir(parents=True)
    (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

    fixture_files = {
        root / "docs" / "RUNNABLE_PION_2PT_SPEC.md": "pion helper",
        root / "docs" / "RUNNABLE_QUARK_PROPAGATOR_SPEC.md": "quark helper",
        root / "docs" / "RUNNABLE_MESON_SPEC_SPEC.md": "meson spec helper",
        root / "docs" / "TASK_SCHEMAS.md": "task schema",
        root / "docs" / "RUN_WORKFLOW.md": "workflow",
        pyquda / "examples" / "2_Quark_Propagator.py": "quark example",
        pyquda / "examples" / "3_Pion_Proton_2pt.py": "pion example",
        pyquda / "examples" / "5_Pion_Dispersion.py": "dispersion",
        pyquda / "tests" / "test_mesonspec.py": "mesonspec",
        pyquda / "tests" / "test_io.py": "io test",
        pyquda / "pyquda_utils" / "source.py": "wall source",
        pyquda / "pyquda_utils" / "core.py": "invert core",
        pyquda / "pyquda_utils" / "gamma.py": "gamma",
        pyquda / "pyquda_utils" / "phase.py": "phase",
        pyquda / "pyquda_utils" / "io" / "__init__.py": "readQIOGauge",
    }
    for path, content in fixture_files.items():
        path.write_text(content, encoding="utf-8")

    index_path.write_text(
        json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 3}}),
        encoding="utf-8",
    )
    return pyquda, output, index_path


def _run_case(case: dict, *, pyquda_repo: Path, output_path: Path, index_path: Path) -> dict:
    stdout = io.StringIO()
    argv = [
        "run",
        case["request"],
        "--summary-only",
        "--dry-run",
        "--no-interactive",
        "--pyquda-repo",
        str(pyquda_repo),
        "--output",
        str(output_path),
    ]
    with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
        with patch(
            "pyquda_agent.app.build_llm_backend",
            return_value=(
                None,
                {
                    "requested_backend": "codex",
                    "configured": False,
                    "backend_name": None,
                    "fallback": True,
                    "fallback_reason": "validator fallback",
                },
            ),
        ):
            with redirect_stdout(stdout):
                exit_code = cli_main(argv)
    payload = json.loads(stdout.getvalue())
    return {"exit_code": exit_code, "summary": payload}


def _matches_prefix(actual: list[str], expected: list[str]) -> bool:
    if not expected:
        return True
    return actual[: len(expected)] == expected


def _validate_case(case: dict, result: dict) -> dict:
    payload = result["summary"]
    failures: list[str] = []
    if result["exit_code"] != 0:
        failures.append(f"cli_exit={result['exit_code']}")
    if payload.get("product_status") != case["expected_product_status"]:
        failures.append(f"product_status={payload.get('product_status')!r}")
    if payload.get("physics_target") != case["expected_physics_target"]:
        failures.append(f"physics_target={payload.get('physics_target')!r}")
    if payload.get("workflow_target") != case.get("expected_workflow_target"):
        failures.append(f"workflow_target={payload.get('workflow_target')!r}")
    clarification_mode = (payload.get("clarification_status") or {}).get("mode")
    if clarification_mode != case["expected_clarification_mode"]:
        failures.append(f"clarification_mode={clarification_mode!r}")
    primary_action_kind = (payload.get("primary_action") or {}).get("kind") if payload.get("primary_action") else None
    if primary_action_kind != case["expected_primary_action_kind"]:
        failures.append(f"primary_action_kind={primary_action_kind!r}")
    nearest_fix_kind = primary_action_kind if payload.get("product_status") == "unsupported" else None
    if nearest_fix_kind != case["expected_nearest_fix_kind"]:
        failures.append(f"nearest_fix_kind={nearest_fix_kind!r}")
    if bool(payload.get("physics_formula_preview")) != case["expected_formula_preview"]:
        failures.append("physics_formula_preview_presence")
    if bool(payload.get("physics_workflow_preview")) != case["expected_workflow_preview"]:
        failures.append("physics_workflow_preview_presence")
    expected_scope = case.get("expected_unsupported_scope")
    if expected_scope is not None:
        actual_scope = ((payload.get("unsupported_guidance") or {}).get("primary_scope"))
        if actual_scope != expected_scope:
            failures.append(f"unsupported_scope={actual_scope!r}")
    expected_shortest_fix = case.get("expected_shortest_fix_target")
    if expected_shortest_fix is not None:
        actual_shortest_fix = ((payload.get("unsupported_guidance") or {}).get("shortest_fix") or {}).get("workflow_target")
        if actual_shortest_fix != expected_shortest_fix:
            failures.append(f"shortest_fix={actual_shortest_fix!r}")
    expected_candidates = case.get("expected_candidate_prefix") or []
    if expected_candidates:
        actual_candidates = [item.get("target_id") for item in payload.get("physics_candidate_preview") or []]
        if not _matches_prefix(actual_candidates, expected_candidates):
            failures.append(f"candidate_prefix={actual_candidates!r}")
    expected_formula = case.get("expected_formula_prefix") or []
    if expected_formula:
        actual_formula = [item.get("proposal_id") for item in payload.get("physics_formula_preview") or []]
        if not _matches_prefix(actual_formula, expected_formula):
            failures.append(f"formula_prefix={actual_formula!r}")
    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "request": case["request"],
        "passed": not failures,
        "failures": failures,
        "observed": {
            "product_status": payload.get("product_status"),
            "physics_target": payload.get("physics_target"),
            "workflow_target": payload.get("workflow_target"),
            "clarification_mode": clarification_mode,
            "primary_action_kind": primary_action_kind,
            "unsupported_scope": ((payload.get("unsupported_guidance") or {}).get("primary_scope")),
            "shortest_fix_target": ((payload.get("unsupported_guidance") or {}).get("shortest_fix") or {}).get("workflow_target"),
            "physics_candidate_preview": [item.get("target_id") for item in payload.get("physics_candidate_preview") or []],
            "physics_formula_preview": [item.get("proposal_id") for item in payload.get("physics_formula_preview") or []],
        },
    }


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="scripts/validate_v11_task_suite.py")
    args = parse_args(argv)
    output_path = args.output.expanduser().resolve()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        pyquda_repo, script_output, index_path = _prepare_repo_fixture(root)
        case_results = [
            _validate_case(case, _run_case(case, pyquda_repo=pyquda_repo, output_path=script_output, index_path=index_path))
            for case in V11_TASK_SUITE
        ]

    passed = [item for item in case_results if item["passed"]]
    payload = {
        "suite": "v11_task_suite",
        "cases": case_results,
        "all_passed": len(passed) == len(case_results),
        "summary": {
            "case_count": len(case_results),
            "passed_case_count": len(passed),
            "categories": sorted({item["category"] for item in case_results}),
            "coverage": [
                "ambiguous meson",
                "explicit pion / pion_pcac / meson_spec / rho / proton",
                "propagator / gaussian-shell propagator",
                "smear / flow",
                "unsupported propagator / smear / flow boundary variants",
                "unsupported neutron",
                "unsupported non-grounded meson-like variants",
            ],
            "contract": "summary_only_dry_run",
        },
        "note": (
            "This suite records current natural-language routing behavior against the summary contract. "
            "It validates interpretation, clarification mode, workflow selection, and nearest grounded recovery signals, "
            "but it does not prove a local PyQUDA runtime."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote v11 task-suite report to {output_path}")
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
