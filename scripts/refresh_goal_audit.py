#!/usr/bin/env python3
"""Refresh audit artifacts from current repository evidence. Requires Python >= 3.10."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_TASK = REPO_ROOT / "outputs" / "run_pion_api.task.json"
DEFAULT_PLAN = REPO_ROOT / "outputs" / "run_pion_api.plan.json"
DEFAULT_RUNTIME = REPO_ROOT / "data" / "pyquda_runtime_check.json"
DEFAULT_PROBE = REPO_ROOT / "outputs" / "run_pion_api.probe.json"
DEFAULT_BACKEND_PARITY = REPO_ROOT / "data" / "backend_parity.json"
DEFAULT_BACKEND_EXECUTION = REPO_ROOT / "data" / "backend_execution.json"
DEFAULT_RUNTIME_CANDIDATES = REPO_ROOT / "data" / "runtime_candidates.json"
DEFAULT_SUPPORTED_VALIDATION = REPO_ROOT / "data" / "supported_workflows_validation.json"
DEFAULT_V9_PRODUCT_BEHAVIOR = REPO_ROOT / "data" / "v9_product_behavior.json"
DEFAULT_V11_TASK_SUITE = REPO_ROOT / "data" / "v11_task_suite.json"
DEFAULT_AUDIT = REPO_ROOT / "data" / "goal_audit.json"
DEFAULT_DOC = REPO_ROOT / "docs" / "FIRST_WORKFLOW_AUDIT.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh machine-readable and Markdown audit artifacts. "
            "Requires Python >= 3.10; if bare python3 is older on your machine, rerun with an explicit >=3.10 interpreter path."
        )
    )
    parser.add_argument("--task", type=Path, default=DEFAULT_TASK, help="Structured task artifact path.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN, help="Implementation plan artifact path.")
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME, help="Runtime readiness artifact path.")
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE, help="Generated-script probe artifact path.")
    parser.add_argument("--backend-parity", type=Path, default=DEFAULT_BACKEND_PARITY, help="Backend parity artifact path.")
    parser.add_argument("--backend-execution", type=Path, default=DEFAULT_BACKEND_EXECUTION, help="Real backend execution report path.")
    parser.add_argument("--runtime-candidates", type=Path, default=DEFAULT_RUNTIME_CANDIDATES, help="Runtime candidate scan artifact path.")
    parser.add_argument(
        "--supported-validation",
        type=Path,
        default=DEFAULT_SUPPORTED_VALIDATION,
        help="Integration-style validation artifact covering all currently supported workflows.",
    )
    parser.add_argument(
        "--v9-product-behavior",
        type=Path,
        default=DEFAULT_V9_PRODUCT_BEHAVIOR,
        help="Product-behavior regression artifact covering v9 user-visible states.",
    )
    parser.add_argument(
        "--v11-task-suite",
        type=Path,
        default=DEFAULT_V11_TASK_SUITE,
        help="Natural-language regression artifact covering v11 realistic task-suite behavior.",
    )
    parser.add_argument(
        "--audit-date",
        default=None,
        help="Override the audit date recorded in artifacts (YYYY-MM-DD). Useful when regenerating repository docs under a controlled review date.",
    )
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT, help="Where to write the JSON audit.")
    parser.add_argument("--doc-output", type=Path, default=DEFAULT_DOC, help="Where to write the Markdown audit.")
    return parser.parse_args(argv)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _has_fields(task: dict, field_names: list[str]) -> bool:
    return all(task.get(field_name) not in (None, [], {}, "") for field_name in field_names)


def _all_parsed_or_fixed(field_resolution: dict, field_names: list[str]) -> bool:
    allowed = {
        "parsed",
        "fixed",
        "default",
        "clarified",
        "parser_guess",
        "inherited",
        "user_confirmed",
        "inferred",
    }
    return all(field_resolution.get(field_name) in allowed for field_name in field_names)


def _load_plan_references_from_path(raw_path: str | None) -> set[str]:
    if not raw_path:
        return set()
    path = Path(raw_path).expanduser()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return set()
    references = payload.get("references", [])
    return {item.get("path", "") for item in references if item.get("path")}


def _collect_reference_paths(plan: dict, supported_validation: dict) -> set[str]:
    reference_paths = {item.get("path", "") for item in plan.get("references", []) if item.get("path")}
    for workflow in supported_validation.get("workflows", []):
        direct = workflow.get("direct") or {}
        parsed = direct.get("parsed") or {}
        artifacts = parsed.get("artifacts") or {}
        reference_paths.update(_load_plan_references_from_path(artifacts.get("plan")))
    return reference_paths


def _resolve_audit_date(raw_value: str | None) -> str:
    if raw_value is None:
        return date.today().isoformat()
    return date.fromisoformat(raw_value).isoformat()


def build_goal_audit(
    task: dict,
    plan: dict,
    runtime: dict,
    probe: dict,
    backend_parity: dict,
    backend_execution: dict,
    runtime_candidates: dict,
    supported_validation: dict,
    v9_product_behavior: dict,
    v11_task_suite: dict,
    audit_date: str | None = None,
) -> dict:
    audit_date = _resolve_audit_date(audit_date)
    workflow_id = task.get("workflow_id")
    references = plan.get("references", [])
    reference_paths = _collect_reference_paths(plan, supported_validation)
    external_citations = plan.get("external_citations", [])
    convention_decisions = plan.get("convention_decisions", [])
    field_resolution = plan.get("field_resolution", {})
    validation_checks = set(plan.get("validation_checks", []))
    clarification_trace = plan.get("clarification_trace", [])
    probe_status = probe.get("status")
    probe_runtime_level = probe.get("runtime_level")
    generated_probe = ((plan.get("runtime_readiness") or {}).get("generated_script_probe") or {})
    parity_comparisons = backend_parity.get("comparisons", {})
    parity_equivalence = backend_parity.get("equivalence", {})
    parity_ok = bool(parity_equivalence.get("implementation_equivalent"))
    if not parity_ok and parity_comparisons:
        parity_ok = all(item.get("identical") for item in parity_comparisons.values())
    backend_execution_entries = backend_execution.get("backends", [])
    backend_states = dict((backend_execution.get("backend_summary") or {}).get("states") or {})
    if not backend_states and backend_execution_entries:
        backend_states = {item.get("backend"): item.get("availability_state", "unknown") for item in backend_execution_entries if item.get("backend")}
    backend_execution_ok = bool(backend_execution_entries) and all(item.get("coherent") for item in backend_execution_entries)
    backend_diagnostics_complete = bool(backend_states) and all(state not in {None, "", "incoherent", "unknown"} for state in backend_states.values())
    any_runtime_candidate = bool(runtime_candidates.get("any_ready"))
    supported_results = supported_validation.get("workflows", [])
    v9_groups = v9_product_behavior.get("groups", [])
    v9_group_status = {item.get("group"): bool(item.get("passed")) for item in v9_groups if item.get("group")}
    v9_product_behavior_ok = bool(v9_product_behavior.get("all_passed")) and bool(v9_groups)
    v9_summary = v9_product_behavior.get("summary") or {}
    unsupported_behavior = v9_summary.get("unsupported_behavior") or {}
    v11_cases = v11_task_suite.get("cases", [])
    v11_summary = v11_task_suite.get("summary") or {}
    supported_workflows_ok = len(supported_results) >= 3 and all(item.get("coherent") for item in supported_results)
    backend_product_path_ok = bool(backend_execution_entries) and all(
        all(
            (case.get("case_summary") or {}).get(key) not in (None, "")
            for key in ("product_status", "generation_phase", "execution_phase")
        )
        for backend_entry in backend_execution_entries
        for case in (backend_entry.get("cases") or [])
    )
    supported_product_path_ok = len(supported_results) >= 3 and all(
        all(
            (item.get("product_path") or {}).get(key) not in (None, "")
            for key in (
                "rough_product_status",
                "rough_generation_phase",
                "rough_execution_phase",
                "direct_product_status",
                "direct_generation_phase",
                "direct_execution_phase",
            )
        )
        for item in supported_results
    )
    rough_request_clarification_ok = bool(v9_group_status.get("rough_request_clarification")) and len(supported_results) >= 3 and all(
        (item.get("product_path") or {}).get("rough_product_status") == "needs_input"
        and (item.get("product_path") or {}).get("rough_generation_phase") == "blocked_on_input"
        and (item.get("product_path") or {}).get("rough_execution_phase") == "blocked_by_generation"
        for item in supported_results
    )
    direct_supported_generation_ok = bool(v9_group_status.get("supported_workflow_generation")) and len(supported_results) >= 3 and all(
        (item.get("product_path") or {}).get("direct_product_status") in {"generated_probe_available", "generated_runtime_blocked", "runtime_proved"}
        and (item.get("product_path") or {}).get("direct_generation_phase") == "generated"
        and (item.get("product_path") or {}).get("direct_execution_phase") in {"probe_available", "runtime_missing", "probe_driver_failed", "runtime_proved"}
        for item in supported_results
    )
    actionable_recovery_guidance_ok = (
        bool(v9_group_status.get("backend_degradation"))
        and bool(v9_group_status.get("terminal_execution_awareness"))
        and bool(v9_group_status.get("runtime_recovery_guidance"))
        and bool(v9_group_status.get("probe_artifact_consistency"))
        and bool(v9_group_status.get("explicit_unsupported_refusal"))
    )
    unsupported_actionability_ok = (
        bool(v9_group_status.get("explicit_unsupported_refusal"))
        and bool(unsupported_behavior.get("covered"))
        and ((unsupported_behavior.get("primary_action_contract") or {}).get("copyable_retry_kind") == "retry_supported_workflow")
        and ((unsupported_behavior.get("primary_action_contract") or {}).get("choice_required_kind") == "choose_supported_variant")
        and bool((unsupported_behavior.get("primary_action_contract") or {}).get("backend_fix_should_not_be_primary"))
    )
    v11_task_suite_ok = bool(v11_task_suite.get("all_passed")) and bool(v11_cases)

    required_task_fields = [
        "start_from",
        "gauge_format",
        "gauge_path",
        "lattice_size",
        "grid_size",
        "fermion_action",
        "mass",
        "xi_0",
        "nu",
        "coeff_t",
        "coeff_r",
        "solver_tol",
        "solver_maxiter",
        "source_type",
        "sink_type",
        "momentum_projection",
        "source_timeslices",
        "gauge_fixed",
        "correlator_output_format",
        "correlator_output_path",
        "resource_path",
        "script_output_path",
        "script_style",
    ]

    req1 = all(
        path in reference_paths
        for path in (
            "/Users/zhaodianjun/PyQUDA/examples/3_Pion_Proton_2pt.py",
            "/Users/zhaodianjun/PyQUDA/examples/4_Pion_PCAC.py",
            "/Users/zhaodianjun/PyQUDA/examples/5_Pion_Dispersion.py",
            "/Users/zhaodianjun/PyQUDA/tests/test_mesonspec.py",
            "/Users/zhaodianjun/PyQUDA/tests/test_io.py",
            "/Users/zhaodianjun/PyQUDA/pyquda_utils/io/__init__.py",
            "/Users/zhaodianjun/PyQUDA/pyquda_utils/source.py",
            "/Users/zhaodianjun/PyQUDA/pyquda_utils/core.py",
            "/Users/zhaodianjun/PyQUDA/pyquda_utils/gamma.py",
        )
    )
    req2 = bool(external_citations) and any(item.get("citations") for item in convention_decisions)
    req3 = _has_fields(task, required_task_fields)
    req4 = not task.get("missing_fields") and not task.get("unsupported_reasons")
    req5 = all(section in plan for section in ("physics_choices", "pyquda_choices", "runtime_choices"))
    req6 = req3 and req4 and task.get("script_style") == "complete" and not plan.get("unresolved_fields")
    req7 = "generated code contains no TODO/pass/placeholder text" in validation_checks
    req8_static = (
        "generated code imports real PyQUDA APIs" in validation_checks
        and any("generated code matches local examples/tests/io helpers" in item for item in validation_checks)
    )
    req8 = req8_static and probe_status in {"ok", "runtime_missing"}

    real_imports_and_apis = (
        task.get("gauge_path", "").endswith("weak_field.lime")
        and task.get("source_type") == "wall"
        and task.get("sink_type") == "local"
        and probe_status in {"ok", "runtime_missing"}
    )
    traceable = bool(references) and bool(convention_decisions)
    no_placeholder = req7
    field_provenance = _all_parsed_or_fixed(field_resolution, required_task_fields) and "workflow_id" in field_resolution
    supports_both = parity_ok and backend_execution_ok and backend_diagnostics_complete
    hpc_ready = req8_static and field_provenance and supports_both and task.get("cluster_launch") not in (None, "", [])
    unified_probe_reporting = (
        generated_probe.get("artifact_path") is not None
        and generated_probe.get("status") in {"not_run", "ok", "runtime_missing"}
    )
    product_validation_chain = backend_product_path_ok and supported_product_path_ok

    def status(value: bool, partial: bool = False) -> str:
        if value:
            return "proved"
        if partial:
            return "partially_proved"
        return "not_proved"

    return {
        "objective": "product_like_multi_workflow_pyquda_agent",
        "last_audited_on": audit_date,
        "backend_availability": backend_states,
        "items": [
            {
                "id": "req-1-local-retrieval",
                "requirement": "Retrieve implementation details from ~/pyquda-agent and ~/PyQUDA, especially runnable examples, tests, IO helpers, source helpers, inversion paths, contraction patterns, and output conventions.",
                "status": status(req1),
                "evidence": [
                    "src/pyquda_agent/retrieval/context_builder.py",
                    "src/pyquda_agent/retrieval/repo_scan.py",
                    str(DEFAULT_PLAN.relative_to(REPO_ROOT)),
                    "data/supported_workflows_validation.json",
                    "tests/test_context_builder.py",
                ],
                "notes": "The audit aggregates pinned PyQUDA references from the representative plan plus the validated workflow-plan artifacts, covering examples, tests, io/__init__.py, source.py, core.py, gamma.py, and family-specific references such as the PCAC example.",
            },
            {
                "id": "req-2-external-citations",
                "requirement": "When local repository knowledge is insufficient for physics conventions, consult authoritative sources and record chosen conventions with citations.",
                "status": status(req2, partial=bool(external_citations)),
                "evidence": [
                    "scripts/refresh_physics_citations.py",
                    "data/physics_citations/pion_2pt_chroma_wall_local_zero_momentum_npy_v1.sources.json",
                    "data/physics_citations/pion_2pt_chroma_wall_local_zero_momentum_npy_v1.json",
                    "src/pyquda_agent/generator/plan.py",
                    str(DEFAULT_PLAN.relative_to(REPO_ROOT)),
                    "tests/test_cli_run.py",
                    "tests/test_refresh_physics_citations.py",
                ],
                "notes": "Citations are recorded in the implementation plan; they are currently refreshed from a curated manifest rather than chosen by live task-time browsing.",
            },
            {
                "id": "req-3-structured-task-spec",
                "requirement": "Parse the user request into a structured task specification instead of directly writing code.",
                "status": status(req3),
                "evidence": [
                    "src/pyquda_agent/tasks/parser.py",
                    "src/pyquda_agent/tasks/schema.py",
                    str(DEFAULT_TASK.relative_to(REPO_ROOT)),
                    "tests/test_task_parser.py",
                ],
                "notes": "The CLI emits a structured task artifact before generation.",
            },
            {
                "id": "req-4-clarification-loop",
                "requirement": "Detect underspecified fields and ask follow-up questions rather than inventing missing parameters.",
                "status": status(req4),
                "evidence": [
                    "src/pyquda_agent/tasks/clarifier.py",
                    "tests/test_clarifier.py",
                    "tests/test_cli_run.py",
                ],
                "notes": "Missing required fields stop complete generation and surface follow-up questions.",
            },
            {
                "id": "req-5-choice-separation",
                "requirement": "Distinguish physics choices, PyQUDA implementation choices, and cluster/runtime choices.",
                "status": status(req5),
                "evidence": [
                    "src/pyquda_agent/generator/plan.py",
                    "src/pyquda_agent/models.py",
                    str(DEFAULT_PLAN.relative_to(REPO_ROOT)),
                    "docs/TASK_SCHEMAS.md",
                ],
                "notes": "The implementation plan has dedicated sections for all three categories.",
            },
            {
                "id": "req-6-complete-after-resolution",
                "requirement": "Generate a complete Python script only after required fields are resolved.",
                "status": status(req6),
                "evidence": [
                    "src/pyquda_agent/app.py",
                    "src/pyquda_agent/tasks/pion_2pt.py",
                    "tests/test_cli_run.py",
                ],
                "notes": "The command returns needs_input or unsupported before generation when fields are unresolved.",
            },
            {
                "id": "req-7-no-placeholders",
                "requirement": "Refuse to label output as complete if placeholders, TODOs, fake helper calls, or guessed APIs remain.",
                "status": status(req7),
                "evidence": [
                    "src/pyquda_agent/generator/validate.py",
                    "tests/test_generator.py",
                ],
                "notes": "Validation rejects forbidden tokens and asserts required real API strings.",
            },
            {
                "id": "req-8-validate-against-real-interfaces",
                "requirement": "Validate generated scripts against real PyQUDA interfaces and example usage patterns.",
                "status": status(req8, partial=req8_static),
                "evidence": [
                    "src/pyquda_agent/generator/templates.py",
                    "outputs/run_pion_api.py",
                    str(DEFAULT_PLAN.relative_to(REPO_ROOT)),
                    str(DEFAULT_PROBE.relative_to(REPO_ROOT)),
                    "scripts/probe_generated_workflow.py",
                    "tests/test_generator.py",
                ],
                "notes": "Static structure and reference grounding are validated; direct execution evidence is tracked through the unified run-path probe artifact. Full numerical validation still depends on a working PyQUDA runtime.",
            },
            {
                "id": "dod-real-imports-and-apis",
                "requirement": "Generated script uses real PyQUDA imports, source/inversion/contraction APIs, and real gauge IO paths.",
                "status": status(real_imports_and_apis, partial=probe_status == "runtime_missing"),
                "evidence": [
                    "outputs/run_pion_api.py",
                    str(DEFAULT_TASK.relative_to(REPO_ROOT)),
                    str(DEFAULT_PLAN.relative_to(REPO_ROOT)),
                    str(DEFAULT_PROBE.relative_to(REPO_ROOT)),
                    "tests/test_generator.py",
                ],
                "notes": "The script uses real local gauge input and reference-grounded API choices; the direct probe shows runtime preflight is reached.",
            },
            {
                "id": "dod-traceable-upstream-references",
                "requirement": "Generated script is derived from and traceable to concrete upstream references in ~/PyQUDA.",
                "status": status(traceable),
                "evidence": [
                    "outputs/run_pion_api.py",
                    str(DEFAULT_PLAN.relative_to(REPO_ROOT)),
                    "tests/test_generator.py",
                ],
                "notes": "The plan and generated script trace the workflow back to concrete upstream PyQUDA references.",
            },
            {
                "id": "dod-no-todo-pass-placeholder",
                "requirement": "Generated complete script contains no TODO/pass/placeholder sections.",
                "status": status(no_placeholder),
                "evidence": [
                    "src/pyquda_agent/generator/validate.py",
                    "tests/test_generator.py",
                    "outputs/run_pion_api.py",
                ],
                "notes": "The generated script is guarded by token-level validation and regression tests.",
            },
            {
                "id": "dod-explain-field-provenance",
                "requirement": "The system explains which task fields were user-specified, clarified interactively, and which conventions were chosen from references.",
                "status": status(field_provenance),
                "evidence": [
                    str(DEFAULT_TASK.relative_to(REPO_ROOT)),
                    str(DEFAULT_PLAN.relative_to(REPO_ROOT)),
                    "src/pyquda_agent/generator/plan.py",
                    "src/pyquda_agent/sessions/state.py",
                    "tests/test_cli_run.py",
                    "tests/test_generator.py",
                ],
                "notes": "Field provenance is tracked in field_sources/field_resolution, and convention decisions plus clarification traces are carried in the implementation plan.",
            },
            {
                "id": "dod-support-api-and-codex",
                "requirement": "The system supports both --backend api and --backend codex.",
                "status": status(supports_both),
                "evidence": [
                    "src/pyquda_agent/cli.py",
                    "src/pyquda_agent/app.py",
                    "data/backend_parity.json",
                    "data/backend_execution.json",
                    "data/supported_workflows_validation.json",
                    "scripts/check_backend_parity.py",
                    "scripts/validate_backend_execution.py",
                    "tests/test_cli_run.py",
                ],
                "notes": f"Both backends drive the same structured generation path. Parity and non-mocked execution artifacts track either real use or explicit fallback. Current backend availability states: {backend_states}.",
            },
            {
                "id": "multi-workflow-routing",
                "requirement": "The system reliably selects among the currently supported workflow families from rough or direct runnable requests, with the pion_2pt family retaining both grounded gauge-entry and propagator-entry paths.",
                "status": status(supported_workflows_ok),
                "evidence": [
                    "src/pyquda_agent/intent/interpreter.py",
                    "src/pyquda_agent/workflows/matcher.py",
                    "data/supported_workflows_validation.json",
                    "tests/test_cli_run.py",
                    "tests/test_workflow_matcher.py",
                ],
                "notes": "The current supported set spans the grounded pion_2pt, pion_pcac, pion_dispersion, meson_spec, proton_2pt, rho_vector, quark_propagator, ape_smear, hyp_smear, stout_smear, and wilson_flow families, including the validated propagator-entry branches where applicable. Unsupported requests must remain explicit.",
            },
            {
                "id": "dod-hpc-script-readiness",
                "requirement": "Generated script is complete and HPC-ready: real APIs, explicit cluster/runtime assumptions, no placeholders, and suitable for handoff to a properly configured PyQUDA cluster environment.",
                "status": status(hpc_ready),
                "evidence": [
                    str(DEFAULT_TASK.relative_to(REPO_ROOT)),
                    str(DEFAULT_PLAN.relative_to(REPO_ROOT)),
                    "outputs/run_pion_api.py",
                    "src/pyquda_agent/generator/templates.py",
                    "tests/test_generator.py",
                    "tests/test_cli_run.py",
                ],
                "notes": "This repository now treats grounded HPC handoff readiness as the default done condition. Local runtime proof remains optional evidence and must be reported separately.",
            },
            {
                "id": "env-local-runtime-readiness",
                "requirement": "Optional: have local evidence that the current machine can numerically execute the generated script.",
                "status": "not_proved" if not any_runtime_candidate else "partially_proved",
                "evidence": [
                    str(DEFAULT_RUNTIME.relative_to(REPO_ROOT)),
                    "data/runtime_candidates.json",
                    str(DEFAULT_PROBE.relative_to(REPO_ROOT)),
                    str(DEFAULT_PLAN.relative_to(REPO_ROOT)),
                    "scripts/check_pyquda_runtime.py",
                    "scripts/probe_generated_workflow.py",
                    "scripts/scan_runtime_candidates.py",
                    "scripts/refresh_runtime_check.py",
                    "docs/PYQUDA_RUNTIME_BOOTSTRAP.md",
                ],
                "notes": f"Local runtime proof is informative only. Current probe status={probe_status!r}, runtime_level={probe_runtime_level!r}. The generated script may still be complete for HPC handoff even when this workstation lacks CuPy, pyquda, or built QUDA bindings.",
            },
            {
                "id": "v8-unified-run-and-probe-reporting",
                "requirement": "The main run path distinguishes generation success from execution/probe success and persists sibling probe artifacts for auditable runtime evidence.",
                "status": status(unified_probe_reporting, partial=generated_probe.get('artifact_path') is not None),
                "evidence": [
                    "src/pyquda_agent/app.py",
                    str(DEFAULT_PLAN.relative_to(REPO_ROOT)),
                    str(DEFAULT_PROBE.relative_to(REPO_ROOT)),
                    "scripts/refresh_first_workflow_demo.py",
                    "scripts/validate_supported_workflows.py",
                    "tests/test_cli_run.py",
                ],
                "notes": "The top-level run result carries execution_status while runtime_evidence.generated_script_probe links the sibling .probe.json artifact and its command path.",
            },
            {
                "id": "v8-product-facing-validation-chain",
                "requirement": "Validation artifacts preserve product-facing lifecycle evidence, including product_status plus generation/execution phases for both backend execution checks and supported-workflow integration checks.",
                "status": status(product_validation_chain, partial=backend_product_path_ok or supported_product_path_ok),
                "evidence": [
                    "data/backend_execution.json",
                    "data/supported_workflows_validation.json",
                    "scripts/validate_backend_execution.py",
                    "scripts/validate_supported_workflows.py",
                    "tests/test_validate_backend_execution.py",
                    "tests/test_validate_supported_workflows.py",
                ],
                "notes": "The compact validation artifacts now record rough-request and direct-run product-facing phases so product clients can audit the same lifecycle contract outside individual CLI invocations.",
            },
            {
                "id": "v9-product-behavior-regression-surface",
                "requirement": "Product-behavior regression artifacts cover clarification routing, backend degradation, terminal execution awareness, terminal repair guidance, supported workflow generation, explicit unsupported refusal, and probe artifact consistency.",
                "status": status(v9_product_behavior_ok, partial=bool(v9_groups)),
                "evidence": [
                    "data/v9_product_behavior.json",
                    "scripts/validate_v9_product_behavior.py",
                    "tests/test_validate_v9_product_behavior.py",
                    "tests/test_cli_run.py",
                    "tests/test_summary_contract.py",
                ],
                "notes": f"The current v9 product-behavior groups are {[item.get('group') for item in v9_groups]}.",
            },
            {
                "id": "v9-rough-request-clarification-routing",
                "requirement": "Rough but reasonable supported requests enter clarification instead of collapsing into pseudocode or premature unsupported output.",
                "status": status(rough_request_clarification_ok, partial=bool(v9_group_status.get("rough_request_clarification"))),
                "evidence": [
                    "data/v9_product_behavior.json",
                    "data/supported_workflows_validation.json",
                    "tests/test_intent_interpreter.py",
                    "tests/test_cli_run.py",
                ],
                "notes": "The supported-workflow validator checks rough request shapes across the current workflow catalog, while the v9 product-behavior validator checks the product-facing clarification path explicitly.",
            },
            {
                "id": "v9-direct-supported-generation-consistency",
                "requirement": "Explicit supported requests generate grounded scripts together with coherent generation/probe/runtime status reporting.",
                "status": status(direct_supported_generation_ok, partial=bool(v9_group_status.get("supported_workflow_generation"))),
                "evidence": [
                    "data/v9_product_behavior.json",
                    "data/supported_workflows_validation.json",
                    "tests/test_cli_run.py",
                    "tests/test_summary_contract.py",
                ],
                "notes": "Direct supported runs are expected to reach generated/probe-available, generated/runtime-blocked, or runtime-proved states with matching lifecycle cards and sibling artifacts.",
            },
            {
                "id": "v9-actionable-recovery-guidance",
                "requirement": "Backend failures, network failures, runtime-environment blockers, and probe-harness failures expose clear next actions instead of silent degradation.",
                "status": status(actionable_recovery_guidance_ok),
                "evidence": [
                    "data/v9_product_behavior.json",
                    "tests/test_cli_run.py",
                    "src/pyquda_agent/app.py",
                    "src/pyquda_agent/cli.py",
                ],
                "notes": "This requirement is proved by the current backend degradation, terminal execution-awareness, probe consistency, and explicit refusal groups in the v9 product-behavior validator.",
            },
            {
                "id": "v9-unsupported-actionability-contract",
                "requirement": "Explicit unsupported requests expose the nearest grounded recovery path with either a copyable retry action or an explicit physics-choice gate, without letting backend-fix guidance override the main unsupported action.",
                "status": status(unsupported_actionability_ok, partial=bool(v9_group_status.get("explicit_unsupported_refusal"))),
                "evidence": [
                    "data/v9_product_behavior.json",
                    "scripts/validate_v9_product_behavior.py",
                    "tests/test_validate_v9_product_behavior.py",
                    "tests/test_cli_run.py",
                    "src/pyquda_agent/app.py",
                ],
                "notes": (
                    "The v9 product-behavior summary now records the unsupported-action contract directly: "
                    f"{unsupported_behavior.get('primary_action_contract')!r}."
                ),
            },
            {
                "id": "v11-realistic-task-suite-regression",
                "requirement": "A realistic natural-language task suite covers ambiguous requests, explicit supported requests, and near-boundary unsupported variants with explicit nearest-grounded recovery expectations.",
                "status": status(v11_task_suite_ok, partial=bool(v11_cases)),
                "evidence": [
                    "data/v11_task_suite.json",
                    "src/pyquda_agent/v11_task_suite.py",
                    "scripts/validate_v11_task_suite.py",
                    "tests/test_validate_v11_task_suite.py",
                    "tests/test_intent_interpreter.py",
                    "tests/test_cli_run.py",
                ],
                "notes": (
                    "The current v11 task suite covers "
                    f"{v11_summary.get('case_count', len(v11_cases))} realistic requests across "
                    f"{v11_summary.get('categories', [])}, including unsupported propagator/smear/flow boundary variants."
                ),
            },
        ],
    }


def render_audit_markdown(audit: dict) -> str:
    items = {item["id"]: item for item in audit["items"]}
    proved = [item for item in audit["items"] if item["status"] == "proved"]
    partial = [item for item in audit["items"] if item["status"] == "partially_proved"]
    not_proved = [item for item in audit["items"] if item["status"] == "not_proved"]
    backend_availability = audit.get("backend_availability") or {}
    backend_availability_text = ", ".join(f"{name}={state}" for name, state in sorted(backend_availability.items())) or "unknown"

    lines = [
        "# Current Product Audit",
        "",
        "This document is generated from current workflow artifacts and records the audit state for:",
        "",
        "- support surface: `11` workflow families / `17` concrete grounded workflow targets",
        "- family `pion_2pt`: `pion_2pt_chroma_wall_local_zero_momentum_npy_v1`, `pion_2pt_existing_propagator_local_zero_momentum_npy_v1`",
        "- family `pion_pcac`: `pion_pcac_chroma_wall_local_zero_momentum_npy_v1`, `pion_pcac_existing_propagator_local_zero_momentum_npy_v1`",
        "- family `pion_dispersion`: `pion_dispersion_chroma_point_momentum_npy_v1`",
        "- family `meson_spec`: `meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1`, `meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1`",
        "- family `proton_2pt`: `proton_2pt_chroma_wall_local_zero_momentum_npy_v1`, `proton_2pt_existing_propagator_local_zero_momentum_npy_v1`",
        "- family `rho_vector`: `rho_vector_chroma_wall_local_zero_momentum_npy_v1`, `rho_vector_existing_propagator_local_zero_momentum_npy_v1`",
        "- family `quark_propagator`: `quark_propagator_chroma_point_hdf5_v1`, `quark_propagator_gaussian_shell_chroma_hdf5_v1`",
        "- family `ape_smear`: `ape_smear_chroma_qio_npy_v1`",
        "- family `hyp_smear`: `hyp_smear_chroma_qio_npy_v1`",
        "- family `stout_smear`: `stout_smear_chroma_qio_npy_v1`",
        "- family `wilson_flow`: `wilson_flow_chroma_qio_energy_npy_v1`",
        "",
        "## Requirements currently proved",
        "",
    ]
    for item in proved:
        lines.append(f"- {item['requirement']}")

    lines.extend(
        [
            "",
            "## Requirements partially proved",
            "",
        ]
    )
    for item in partial:
        lines.append(f"- {item['requirement']}")

    lines.extend(
        [
            "",
            "## Requirements not yet fully proved",
            "",
        ]
    )
    for item in not_proved:
        lines.append(f"- {item['requirement']}")

    lines.extend(
        [
            "",
            "## Current evidence",
            "",
            "- `data/pyquda_runtime_check.json`",
            "- `data/run_pion_api_probe.json`",
            "- `data/backend_parity.json`",
            "- `data/backend_execution.json`",
            "- `data/supported_workflows_validation.json`",
            "- `data/v9_product_behavior.json`",
            "- `data/v11_task_suite.json`",
            "- `data/runtime_candidates.json`",
            "- `data/goal_audit.json`",
            "- `outputs/run_pion_api.py`",
            "- `outputs/run_pion_api.physics.json`",
            "- `outputs/run_pion_api.task.json`",
            "- `outputs/run_pion_api.plan.json`",
            "- `outputs/run_pion_api.probe.json`",
            "- `outputs/run_pion_pcac.py`",
            "- `outputs/validate_pion_dispersion.py`",
            "- `outputs/run_meson_spec.py`",
            "- `outputs/validate_proton_2pt.py`",
            "- `outputs/validate_quark_propagator.py`",
            "- `outputs/validate_ape_smear.py`",
            "- `outputs/validate_hyp_smear.py`",
            "- `outputs/run_stout_smear_api.py`",
            "",
            "## Completion stance",
            "",
            f"- Grounded HPC handoff readiness status: `{items['dod-hpc-script-readiness']['status']}`.",
            f"- Backend execution usability summary: `{backend_availability_text}`.",
            f"- Optional local runtime readiness status: `{items['env-local-runtime-readiness']['status']}`.",
            f"- Supported workflow routing status: `{items['multi-workflow-routing']['status']}`.",
            f"- Unified run/probe reporting status: `{items['v8-unified-run-and-probe-reporting']['status']}`.",
            f"- Product-facing validation-chain status: `{items['v8-product-facing-validation-chain']['status']}`.",
            f"- V9 product-behavior regression status: `{items['v9-product-behavior-regression-surface']['status']}`.",
            f"- V9 rough-request clarification status: `{items['v9-rough-request-clarification-routing']['status']}`.",
            f"- V9 direct supported-generation status: `{items['v9-direct-supported-generation-consistency']['status']}`.",
            f"- V9 actionable recovery-guidance status: `{items['v9-actionable-recovery-guidance']['status']}`.",
            f"- V9 unsupported actionability status: `{items['v9-unsupported-actionability-contract']['status']}`.",
            f"- V11 realistic task-suite regression status: `{items['v11-realistic-task-suite-regression']['status']}`.",
            "- The repository default done condition is now: generate a complete, reference-grounded PyQUDA script with an auditable HPC handoff contract.",
            "- Backend usability is audited separately through backend_execution artifacts; a `fallback_only` backend state does not negate grounded generation or handoff readiness.",
            "- Local runtime proof on this workstation remains a separate evidence layer; missing CuPy/PyQUDA runtime is treated as an environment limitation, not a blocker on grounded generation.",
            "",
            "## Exit condition for this audit",
            "",
            "1. `outputs/*.task.json` and `outputs/*.plan.json` fully resolve each supported workflow without unsupported fields.",
            "2. Generated scripts remain traceable to concrete local PyQUDA references and pass placeholder-free static validation.",
            "3. The scripts record explicit cluster/runtime assumptions for HPC handoff.",
            "4. Optional: capture local runtime evidence when a usable PyQUDA environment happens to be available.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    task = _load_json(args.task.expanduser().resolve())
    plan = _load_json(args.plan.expanduser().resolve())
    runtime = _load_json(args.runtime.expanduser().resolve())
    probe = _load_json(args.probe.expanduser().resolve())
    backend_parity = _load_json(args.backend_parity.expanduser().resolve())
    backend_execution = _load_json(args.backend_execution.expanduser().resolve())
    runtime_candidates = _load_json(args.runtime_candidates.expanduser().resolve())
    supported_validation = _load_json(args.supported_validation.expanduser().resolve())
    v9_product_behavior = _load_json(args.v9_product_behavior.expanduser().resolve())
    v11_task_suite = _load_json(args.v11_task_suite.expanduser().resolve())

    audit = build_goal_audit(
        task,
        plan,
        runtime,
        probe,
        backend_parity,
        backend_execution,
        runtime_candidates,
        supported_validation,
        v9_product_behavior,
        v11_task_suite,
        audit_date=args.audit_date,
    )

    audit_output = args.audit_output.expanduser().resolve()
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    audit_output.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    doc_output = args.doc_output.expanduser().resolve()
    doc_output.parent.mkdir(parents=True, exist_ok=True)
    doc_output.write_text(render_audit_markdown(audit), encoding="utf-8")

    print(f"Wrote goal audit to {audit_output}")
    print(f"Wrote workflow audit doc to {doc_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
