#!/usr/bin/env python3
"""Run product-behavior regression checks for v9. Requires Python >= 3.10."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pyquda_agent.python_version import ensure_supported_python


DEFAULT_OUTPUT = REPO_ROOT / "data" / "v9_product_behavior.json"

TEST_GROUPS = {
    "rough_request_clarification": [
        "tests.test_intent_interpreter.IntentInterpreterTests.test_ambiguous_meson_request_generates_physics_question",
        "tests.test_intent_interpreter.IntentInterpreterTests.test_generic_pyquda_request_generates_capability_chooser_prompt",
        "tests.test_intent_interpreter.IntentInterpreterTests.test_axial_meson_request_prefers_meson_spec_confirmation",
        "tests.test_cli_run.CliRunTests.test_rough_pion_request_needs_input_instead_of_unsupported",
        "tests.test_cli_run.CliRunTests.test_generic_pyquda_request_enters_capability_chooser_instead_of_meson_only_prompt",
        "tests.test_cli_run.CliRunTests.test_axial_meson_request_prefers_meson_spec_clarification",
        "tests.test_cli_run.CliRunTests.test_cli_run_terminal_mode_surfaces_physics_candidates_for_ambiguous_meson_request",
    ],
    "backend_degradation": [
        "tests.test_cli_run.CliRunTests.test_cli_run_summary_reports_codex_timeout_guidance",
        "tests.test_cli_run.CliRunTests.test_cli_run_summary_reports_api_network_guidance",
        "tests.test_cli_run.CliRunTests.test_cli_run_summary_reports_codex_local_environment_guidance",
    ],
    "terminal_execution_awareness": [
        "tests.test_cli_run.CliRunTests.test_cli_run_can_print_terminal_message_via_result_format",
        "tests.test_cli_run.CliRunTests.test_cli_run_terminal_mode_surfaces_runtime_execution_closure",
        "tests.test_cli_run.CliRunTests.test_cli_run_terminal_mode_surfaces_runtime_proved_without_repair_noise",
        "tests.test_cli_run.CliRunTests.test_cli_run_terminal_mode_surfaces_backend_fix_for_timeout",
        "tests.test_cli_run.CliRunTests.test_cli_run_terminal_mode_surfaces_conditional_backend_fix_for_local_codex_failure",
    ],
    "supported_workflow_generation": [
        "tests.test_cli_run.CliRunTests.test_cli_run_can_report_runtime_proved_after_probe",
        "tests.test_cli_run.CliRunTests.test_cli_run_complete_generation_supports_quark_propagator_workflow",
        "tests.test_summary_contract.SummaryContractTests.test_contract_generated_probe_available",
        "tests.test_summary_contract.SummaryContractTests.test_contract_generated_runtime_blocked_environment",
        "tests.test_summary_contract.SummaryContractTests.test_contract_runtime_proved",
    ],
    "hpc_handoff_quality": [
        "tests.test_summary_contract.SummaryContractTests.test_contract_generated_probe_available",
        "tests.test_summary_contract.SummaryContractTests.test_contract_propagator_entry_handoff_exposes_input_manifest_and_immutability",
        "tests.test_summary_contract.SummaryContractTests.test_contract_rho_propagator_entry_handoff_exposes_input_manifest_and_immutability",
        "tests.test_cli_run.CliRunTests.test_cli_run_complete_generation_supports_quark_propagator_workflow",
    ],
    "runtime_recovery_guidance": [
        "tests.test_cli_run.CliRunTests.test_cli_run_can_optionally_probe_after_generation",
        "tests.test_cli_run.CliRunTests.test_cli_run_records_probe_driver_failure_without_losing_generated_script",
    ],
    "explicit_unsupported_refusal": [
        "tests.test_cli_run.CliRunTests.test_cli_run_explicit_unsupported_request_does_not_suggest_backend_fix_as_primary_action",
        "tests.test_cli_run.CliRunTests.test_cli_run_quark_unsupported_request_reports_shortest_fix_against_quark_family",
        "tests.test_cli_run.CliRunTests.test_cli_run_explicit_rho_request_reports_nearest_grounded_meson_fix",
        "tests.test_cli_run.CliRunTests.test_cli_run_explicit_neutron_request_reports_nearest_grounded_baryon_fix",
    ],
    "probe_artifact_consistency": [
        "tests.test_cli_run.CliRunTests.test_cli_run_can_optionally_probe_after_generation",
        "tests.test_cli_run.CliRunTests.test_cli_run_records_probe_driver_failure_without_losing_generated_script",
    ],
}


UNSUPPORTED_BEHAVIOR_SUMMARY = {
    "covered": True,
    "primary_action_contract": {
        "copyable_retry_kind": "retry_supported_workflow",
        "choice_required_kind": "choose_supported_variant",
        "backend_fix_should_not_be_primary": True,
    },
    "covered_tests": {
        "choice_required_path": [
            "tests.test_cli_run.CliRunTests.test_cli_run_explicit_unsupported_request_does_not_suggest_backend_fix_as_primary_action",
        ],
        "copyable_retry_paths": [
            "tests.test_cli_run.CliRunTests.test_cli_run_quark_unsupported_request_reports_shortest_fix_against_quark_family",
            "tests.test_cli_run.CliRunTests.test_cli_run_explicit_rho_request_reports_nearest_grounded_meson_fix",
            "tests.test_cli_run.CliRunTests.test_cli_run_explicit_neutron_request_reports_nearest_grounded_baryon_fix",
        ],
    },
    "note": (
        "Unsupported user paths are expected to surface a nearest grounded recovery action. "
        "Some paths are copyable immediately via `retry_supported_workflow`, while others intentionally stop at "
        "`choose_supported_variant` until one physics-side choice is confirmed."
    ),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run v9 product-behavior regression groups and write a JSON summary. "
            "Requires Python >= 3.10; if bare python3 is older on your machine, rerun with an explicit >=3.10 interpreter path."
        )
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _run_group(group_name: str, test_ids: list[str]) -> dict:
    cmd = [sys.executable, "-B", "-m", "unittest", *test_ids]
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "group": group_name,
        "command": cmd,
        "tests": list(test_ids),
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="scripts/validate_v9_product_behavior.py")
    args = parse_args(argv)
    output_path = args.output.expanduser().resolve()

    groups = [_run_group(name, test_ids) for name, test_ids in TEST_GROUPS.items()]
    payload = {
        "suite": "v9_product_behavior",
        "groups": groups,
        "all_passed": all(item["passed"] for item in groups),
        "summary": {
            "group_count": len(groups),
            "passed_group_count": sum(1 for item in groups if item["passed"]),
            "unsupported_behavior": UNSUPPORTED_BEHAVIOR_SUMMARY,
        },
        "note": (
            "This validator is a product-behavior regression entry point. It focuses on clarification routing, "
            "backend degradation guidance, terminal execution-state rendering, terminal repair guidance, runtime recovery guidance, "
            "explicit unsupported refusal, supported workflow generation states, HPC handoff quality, and probe-artifact consistency. "
            "It is intentionally unit/integration-style and does not by itself prove a real local PyQUDA runtime."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote v9 product-behavior report to {output_path}")
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
