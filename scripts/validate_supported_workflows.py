#!/usr/bin/env python3
"""Run integration-style validation for all currently supported workflow families. Requires Python >= 3.10."""

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
DEFAULT_OUTPUT = REPO_ROOT / "data" / "supported_workflows_validation.json"


WORKFLOWS = {
    "pion_2pt": {
        "rough_request": "please compute the pion two-point correlator",
        "direct_request": (
            "please compute the pion two-point correlator from gauge {gauge} lattice size 4 4 4 8 "
            "grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 "
            "tol=1e-12 maxiter=1000 gauge fixed source timeslice 0 {corr} {script} "
            "resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "pion_two_point_correlator",
        "expected_workflow": "pion_2pt_chroma_wall_local_zero_momentum_npy_v1",
    },
    "pion_2pt_existing_propagator": {
        "rough_request": "please compute the pion two-point correlator from existing propagator",
        "direct_request": (
            "please compute the pion two-point correlator from existing propagator /tmp/pion_prop_0.npy "
            "wall source zero momentum gauge fixed lattice size 4 4 4 8 grid 1 1 1 1 "
            "{corr} {script} resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "pion_two_point_correlator",
        "expected_workflow": "pion_2pt_existing_propagator_local_zero_momentum_npy_v1",
    },
    "pion_pcac": {
        "rough_request": "please compute pion pcac ratio",
        "direct_request": (
            "please compute pion pcac ratio from gauge {gauge} lattice size 4 4 4 8 "
            "grid 1 1 1 1 mass=-0.2770 xi_0=1.0 nu=1.0 coeff_t=1.160920226 coeff_r=1.160920226 "
            "tol=1e-12 maxiter=1000 source timeslice 0 {corr} {script} "
            "resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "pion_pcac_ratio_correlator",
        "expected_workflow": "pion_pcac_chroma_wall_local_zero_momentum_npy_v1",
    },
    "pion_pcac_existing_propagator": {
        "rough_request": "please compute pion pcac ratio from existing propagator",
        "direct_request": (
            "please compute pion pcac ratio from existing propagator /tmp/pcac_prop_0.npy "
            "wall source zero momentum not gauge fixed timeslice 0 lattice size 4 4 4 8 grid 1 1 1 1 "
            "{corr} {script} resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "pion_pcac_ratio_correlator",
        "expected_workflow": "pion_pcac_existing_propagator_local_zero_momentum_npy_v1",
    },
    "pion_dispersion": {
        "rough_request": "please compute pion dispersion",
        "direct_request": (
            "please compute pion dispersion from gauge {gauge} lattice size 4 4 4 8 grid 1 1 1 1 "
            "mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 "
            "tol=1e-12 maxiter=1000 source timeslice 0 {corr} {script} "
            "resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "pion_dispersion_correlator",
        "expected_workflow": "pion_dispersion_chroma_point_momentum_npy_v1",
    },
    "meson_spec": {
        "rough_request": "please compute meson spectroscopy correlators",
        "direct_request": (
            "please compute meson spectroscopy correlators from gauge {gauge} lattice size 4 4 4 8 "
            "grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 "
            "tol=1e-12 maxiter=1000 {corr} {script} resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "meson_spectrum_correlator",
        "expected_workflow": "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1",
    },
    "meson_spec_existing_propagator": {
        "rough_request": "please compute meson spectroscopy correlators from existing propagator",
        "direct_request": (
            "please compute meson spectroscopy correlators from existing propagator /tmp/meson_prop_0.npy "
            "wall source momentum [0,0,0] momentum [1,1,1] not gauge fixed timeslice 0 "
            "lattice size 4 4 4 8 grid 1 1 1 1 {corr} {script} resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "meson_spectrum_correlator",
        "expected_workflow": "meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1",
    },
    "proton_2pt": {
        "rough_request": "please compute the proton two-point correlator",
        "direct_request": (
            "please compute the proton two-point correlator from gauge {gauge} lattice size 4 4 4 8 "
            "grid 1 1 1 1 mass=0.09253 xi_0=1.0 nu=1.0 coeff_t=1.160920226 coeff_r=1.160920226 "
            "tol=1e-12 maxiter=1000 source timeslice 0 {corr} {script} "
            "resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "proton_two_point_correlator",
        "expected_workflow": "proton_2pt_chroma_wall_local_zero_momentum_npy_v1",
    },
    "proton_2pt_existing_propagator": {
        "rough_request": "please compute the proton two-point correlator from existing propagator",
        "direct_request": (
            "please compute the proton two-point correlator from existing propagator /tmp/proton_prop_0.npy "
            "wall source zero momentum not gauge fixed timeslice 0 lattice size 4 4 4 8 grid 1 1 1 1 "
            "{corr} {script} resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "proton_two_point_correlator",
        "expected_workflow": "proton_2pt_existing_propagator_local_zero_momentum_npy_v1",
    },
    "rho_vector": {
        "rough_request": "please compute the rho meson two-point correlator",
        "direct_request": (
            "please compute the rho meson two-point correlator from gauge {gauge} lattice size 4 4 4 8 "
            "grid 1 1 1 1 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 "
            "tol=1e-12 maxiter=1000 source timeslice 0 not gauge fixed {corr} {script} "
            "resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "rho_vector_meson_correlator",
        "expected_workflow": "rho_vector_chroma_wall_local_zero_momentum_npy_v1",
    },
    "rho_vector_existing_propagator": {
        "rough_request": "please compute the rho meson two-point correlator from existing propagator",
        "direct_request": (
            "please compute the rho meson two-point correlator from existing propagator /tmp/rho_prop_0.npy "
            "wall source zero momentum not gauge fixed timeslice 0 lattice size 4 4 4 8 grid 1 1 1 1 "
            "{corr} {script} resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "rho_vector_meson_correlator",
        "expected_workflow": "rho_vector_existing_propagator_local_zero_momentum_npy_v1",
    },
    "quark_propagator": {
        "rough_request": "please generate a quark propagator",
        "direct_request": (
            "please generate a quark propagator from gauge {gauge} lattice size 4 4 4 8 "
            "grid 1 1 1 1 mass=-0.2770 xi_0=1.0 nu=1.0 coeff_t=1.160920226 coeff_r=1.160920226 "
            "tol=1e-12 maxiter=1000 source timeslice 0 point source not gauge fixed {corr} {script} "
            "resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "quark_propagator",
        "expected_workflow": "quark_propagator_chroma_point_hdf5_v1",
    },
    "quark_propagator_gaussian_shell": {
        "rough_request": "please generate a gaussian-shell quark propagator",
        "direct_request": (
            "please generate a gaussian-shell quark propagator from gauge {gauge} lattice size 4 4 4 8 "
            "grid 1 1 1 1 mass=0.3478260869565215 xi_0=2.464 nu=0.95 coeff_t=1.07 coeff_r=0.91 "
            "tol=1e-12 maxiter=1000 source timeslice 0 gaussian shell source not gauge fixed {corr} {script} "
            "resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "quark_propagator",
        "expected_workflow": "quark_propagator_gaussian_shell_chroma_hdf5_v1",
    },
    "ape_smear": {
        "rough_request": "please generate an APE-smeared gauge configuration",
        "direct_request": (
            "please generate an APE-smeared gauge from gauge {gauge} lattice size 4 4 4 8 "
            "grid 1 1 1 1 {corr} {script} resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "ape_smeared_gauge_configuration",
        "expected_workflow": "ape_smear_chroma_qio_npy_v1",
    },
    "hyp_smear": {
        "rough_request": "please generate a HYP-smeared gauge configuration",
        "direct_request": (
            "please generate a HYP-smeared gauge from gauge {gauge} lattice size 4 4 4 8 "
            "grid 1 1 1 1 {corr} {script} resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "hyp_smeared_gauge_configuration",
        "expected_workflow": "hyp_smear_chroma_qio_npy_v1",
    },
    "stout_smear": {
        "rough_request": "please stout-smear this gauge configuration",
        "direct_request": (
            "please generate a stout-smeared gauge from gauge {gauge} lattice size 4 4 4 8 "
            "grid 1 1 1 1 {corr} {script} resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "stout_smeared_gauge_configuration",
        "expected_workflow": "stout_smear_chroma_qio_npy_v1",
    },
    "wilson_flow": {
        "rough_request": "please run wilson flow on this gauge configuration",
        "direct_request": (
            "please run wilson flow from gauge {gauge} lattice size 4 4 4 8 grid 1 1 1 1 "
            "flow_steps=100 flow_epsilon=1.0 not gauge fixed {corr} {script} "
            "resource_path=.cache/quda cluster_launch=local"
        ),
        "expected_target": "wilson_flow_energy_observable",
        "expected_workflow": "wilson_flow_chroma_qio_energy_npy_v1",
    },
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate supported workflow routing and artifact coherence. "
            "Requires Python >= 3.10; if bare python3 is older on your machine, rerun with an explicit >=3.10 interpreter path."
        )
    )
    parser.add_argument("--pyquda-repo", type=Path, default=DEFAULT_PYQUDA_REPO)
    parser.add_argument("--backend", choices=("api", "codex"), default="codex")
    parser.add_argument("--api-model", default=resolve_api_model(None))
    parser.add_argument("--llm-timeout", type=float, default=30.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _artifact_paths(script_path: Path) -> tuple[Path, Path, Path, Path]:
    return (
        script_path.with_suffix(".physics.json"),
        script_path.with_suffix(".task.json"),
        script_path.with_suffix(".plan.json"),
        script_path.with_suffix(".probe.json"),
    )


def _run_request(
    *,
    request: str,
    script_path: Path,
    pyquda_repo: Path,
    backend: str,
    api_model: str | None,
    dry_run: bool,
    summary_only: bool,
    llm_timeout: float,
) -> dict:
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
        "--no-interactive",
        "--runtime-probe",
        "--probe-timeout",
        "5",
        "--output",
        str(script_path),
        "--pyquda-repo",
        str(pyquda_repo),
    ]
    if dry_run:
        cmd.append("--dry-run")
    if summary_only:
        cmd.extend(["--result-format", "summary"])
    if backend == "api" and api_model:
        cmd.extend(["--model", api_model])
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not existing_pythonpath else f"src:{existing_pythonpath}"
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    payload = None
    if completed.stdout.strip():
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            payload = None
    physics_artifact, task_artifact, plan_artifact, probe_artifact = _artifact_paths(script_path)
    artifacts_exist = physics_artifact.exists() and task_artifact.exists() and plan_artifact.exists()
    probe_exists = probe_artifact.exists()
    script_exists = script_path.exists()
    placeholder_free = False
    if script_exists:
        code = script_path.read_text(encoding="utf-8")
        placeholder_free = all(token not in code for token in ("TODO", "pass", "placeholder", "fake_", "mock_"))
    runtime_readiness = None
    execution_status = None
    probe_status = None
    product_status = None
    generation_result = None
    execution_result = None
    delivery_status = None
    if artifacts_exist:
        try:
            plan_payload = json.loads(plan_artifact.read_text(encoding="utf-8"))
            runtime_readiness = plan_payload.get("runtime_readiness")
            probe_status = ((runtime_readiness or {}).get("generated_script_probe") or {}).get("status")
        except json.JSONDecodeError:
            runtime_readiness = None
    if probe_exists:
        try:
            probe_status = json.loads(probe_artifact.read_text(encoding="utf-8")).get("status")
        except json.JSONDecodeError:
            probe_status = probe_status
    llm_assistance = _llm_view(payload)
    backend_diagnostic = _backend_diagnostic_view(payload)
    if isinstance(payload, dict):
        execution_status = payload.get("execution_status")
        product_status = payload.get("product_status")
        generation_result = payload.get("generation_result")
        execution_result = payload.get("execution_result")
        delivery_status = payload.get("delivery_status")
    result = {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "parsed": payload,
        "artifacts_exist": artifacts_exist,
        "probe_exists": probe_exists,
        "script_exists": script_exists,
        "placeholder_free": placeholder_free,
        "llm_assistance": llm_assistance,
        "backend_diagnostic": backend_diagnostic,
        "runtime_readiness": runtime_readiness,
        "execution_status": execution_status,
        "probe_status": probe_status,
        "workflow_outcome": (payload or {}).get("workflow_outcome") if isinstance(payload, dict) else None,
        "product_status": product_status,
        "generation_result": generation_result,
        "execution_result": execution_result,
        "delivery_status": delivery_status,
    }
    return result


def _target_id(payload: dict | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("physics_target"):
        return payload.get("physics_target")
    physics = payload.get("physics") or {}
    confirmed = (physics.get("confirmed_interpretation") or {}).get("target_id")
    inferred = (physics.get("inferred_interpretation") or {}).get("target_id")
    return confirmed or inferred


def _workflow_target(payload: dict | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("workflow_target") or ((payload.get("workflow_match") or {}).get("workflow_target"))


def _llm_view(payload: dict | None) -> dict | None:
    if not isinstance(payload, dict):
        return None
    if isinstance(payload.get("llm_assistance"), dict):
        return payload.get("llm_assistance")
    if any(
        key in payload
        for key in (
            "llm_attempted",
            "llm_used",
            "llm_fallback",
            "llm_fallback_category",
            "llm_fallback_reason",
            "requested_backend",
            "selected_backend",
        )
    ):
        return {
            "attempted": payload.get("llm_attempted"),
            "used": payload.get("llm_used"),
            "fallback": payload.get("llm_fallback"),
            "fallback_category": payload.get("llm_fallback_category"),
            "fallback_reason": payload.get("llm_fallback_reason"),
            "requested_backend": payload.get("requested_backend"),
            "selected_backend": payload.get("selected_backend"),
            "selection_reason": payload.get("backend_selection_reason"),
            "codex_preflight_attempted": payload.get("llm_codex_preflight_attempted"),
            "codex_preflight_status": payload.get("llm_codex_preflight_status"),
            "codex_preflight_category": payload.get("llm_codex_preflight_category"),
            "codex_preflight_reason": payload.get("llm_codex_preflight_reason"),
            "codex_preflight_soft_failed": payload.get("llm_codex_preflight_soft_failed"),
            "codex_preflight_soft_failure_reason": payload.get("llm_codex_preflight_soft_failure_reason"),
            "session_backend_memory_considered": payload.get("llm_session_backend_memory_considered"),
            "session_backend_memory_used": payload.get("llm_session_backend_memory_used"),
            "session_backend_memory_reason": payload.get("llm_session_backend_memory_reason"),
            "session_backend_prior_category": payload.get("llm_session_backend_prior_category"),
            "intent_primary_timeout_seconds": payload.get("llm_intent_primary_timeout_seconds"),
            "timeout_recovery_attempted": payload.get("llm_timeout_recovery_attempted"),
            "timeout_recovery_skipped": payload.get("llm_timeout_recovery_skipped"),
            "timeout_recovery_skip_reason": payload.get("llm_timeout_recovery_skip_reason"),
            "timeout_recovery_used": payload.get("llm_timeout_recovery_used"),
            "timeout_recovery_failed": payload.get("llm_timeout_recovery_failed"),
            "timeout_recovery_trigger_category": payload.get("llm_timeout_recovery_trigger_category"),
            "timeout_recovery_timeout_seconds": payload.get("llm_timeout_recovery_timeout_seconds"),
            "timeout_recovery_failure_category": payload.get("llm_timeout_recovery_failure_category"),
        }
    return None


def _backend_diagnostic_view(payload: dict | None) -> dict | None:
    if not isinstance(payload, dict):
        return None
    diagnostic = payload.get("backend_diagnostic")
    if isinstance(diagnostic, dict):
        return diagnostic
    summary = payload.get("result_summary") or {}
    diagnostic = summary.get("backend_diagnostic")
    return diagnostic if isinstance(diagnostic, dict) else None


def _llm_coherent(llm_assistance: dict | None) -> bool:
    if not isinstance(llm_assistance, dict):
        return False
    if llm_assistance.get("used"):
        return True
    if (
        llm_assistance.get("requested_backend")
        and llm_assistance.get("selected_backend") == "rules"
        and llm_assistance.get("selection_reason")
        and not llm_assistance.get("fallback")
    ):
        return True
    return bool(llm_assistance.get("fallback")) and bool(llm_assistance.get("fallback_reason"))


def _backend_validation_summary(result: dict) -> dict:
    llm_assistance = result.get("llm_assistance") or {}
    backend_diagnostic = result.get("backend_diagnostic") or {}
    return {
        "requested_backend": llm_assistance.get("requested_backend"),
        "selected_backend": llm_assistance.get("selected_backend"),
        "selection_reason": llm_assistance.get("selection_reason"),
        "used": bool(llm_assistance.get("used")),
        "fallback": bool(llm_assistance.get("fallback")),
        "fallback_category": llm_assistance.get("fallback_category"),
        "backend_status": backend_diagnostic.get("status"),
        "backend_category": backend_diagnostic.get("category"),
        "backend_detail_category": backend_diagnostic.get("detail_category"),
        "failure_origin": backend_diagnostic.get("failure_origin"),
        "recovery_mode": backend_diagnostic.get("recovery_mode"),
        "retryable_now": backend_diagnostic.get("retryable_now"),
        "codex_preflight_attempted": bool(llm_assistance.get("codex_preflight_attempted")),
        "codex_preflight_status": llm_assistance.get("codex_preflight_status"),
        "codex_preflight_category": llm_assistance.get("codex_preflight_category"),
        "codex_preflight_reason": llm_assistance.get("codex_preflight_reason"),
        "codex_preflight_soft_failed": bool(llm_assistance.get("codex_preflight_soft_failed")),
        "codex_preflight_soft_failure_reason": llm_assistance.get("codex_preflight_soft_failure_reason"),
        "session_backend_memory_considered": bool(llm_assistance.get("session_backend_memory_considered")),
        "session_backend_memory_used": bool(llm_assistance.get("session_backend_memory_used")),
        "session_backend_memory_reason": llm_assistance.get("session_backend_memory_reason"),
        "session_backend_prior_category": llm_assistance.get("session_backend_prior_category"),
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


def _workflow_outcome_coherent(outcome: dict | None, *, expect_phase: str, expect_probe_status: str) -> bool:
    if not isinstance(outcome, dict):
        return False
    if outcome.get("phase") != expect_phase:
        return False
    if outcome.get("runtime_probe_status") != expect_probe_status:
        return False
    if "generation_succeeded" not in outcome or "execution_attempted" not in outcome:
        return False
    return True


def _runtime_blocked_statuses() -> set[str]:
    return {"runtime_missing", "probe_driver_failed", "failed"}


def _runtime_probe_coherent(result: dict, expect_script: bool) -> bool:
    if not expect_script:
        if result.get("execution_status") not in {None, "not_requested"}:
            return False
        if result.get("probe_exists"):
            return False
        return result.get("probe_status") in {None, "not_requested", "requested"}
    execution_status = result.get("execution_status")
    if execution_status == "runtime_proved":
        if not result.get("probe_exists"):
            return False
        return result.get("probe_status") in {"ok", "runtime_proved"}
    if execution_status not in _runtime_blocked_statuses():
        return False
    if not result.get("probe_exists"):
        return False
    return result.get("probe_status") in _runtime_blocked_statuses()


def _expected_direct_execution_phase(result: dict) -> str:
    execution_status = result.get("execution_status")
    if execution_status == "runtime_proved":
        return "runtime_proved"
    if execution_status == "runtime_missing":
        return "runtime_missing"
    if execution_status in _runtime_blocked_statuses():
        return str(((result.get("execution_result") or {}).get("phase")) or execution_status)
    return str(((result.get("execution_result") or {}).get("phase")) or execution_status or "runtime_missing")


def _expected_direct_product_status(result: dict) -> str:
    return "runtime_proved" if result.get("execution_status") == "runtime_proved" else "generated_runtime_blocked"


def _expected_direct_probe_status(result: dict) -> str:
    return str(result.get("probe_status") or ("runtime_proved" if result.get("execution_status") == "runtime_proved" else "runtime_missing"))


def _product_path_coherent(
    result: dict,
    *,
    expect_product_status: str,
    expect_generation_phase: str,
    expect_execution_phase: str,
) -> bool:
    product_status = result.get("product_status")
    generation_result = result.get("generation_result") or {}
    execution_result = result.get("execution_result") or {}
    delivery_status = result.get("delivery_status") or {}
    delivery_generation = delivery_status.get("generation") or {}
    delivery_execution = delivery_status.get("execution") or {}
    if product_status != expect_product_status:
        return False
    if generation_result.get("phase") != expect_generation_phase:
        return False
    if execution_result.get("phase") != expect_execution_phase:
        return False
    if delivery_generation.get("phase") != expect_generation_phase:
        return False
    if delivery_execution.get("phase") != expect_execution_phase:
        return False
    return True


def _hpc_handoff_contract(payload: dict | None) -> dict | None:
    if not isinstance(payload, dict):
        return None
    handoff = payload.get("hpc_handoff")
    return handoff if isinstance(handoff, dict) else None


def _hpc_handoff_coherent(handoff: dict | None) -> bool:
    if not isinstance(handoff, dict):
        return False
    required = (
        "start_from",
        "input_path_count",
        "input_directory_policy",
        "input_mutability_policy",
        "output_directory_count",
        "output_directory_policy",
        "output_writer_policy",
        "required_modules",
        "preflight_checks",
        "probe_artifact",
    )
    if any(handoff.get(key) in (None, "", []) for key in required):
        return False
    if handoff.get("output_writer_policy") != "rank0_only":
        return False
    if not isinstance(handoff.get("required_modules"), list) or not all(
        module in handoff.get("required_modules", []) for module in ("numpy", "cupy", "pyquda_utils", "pyquda")
    ):
        return False
    if not isinstance(handoff.get("preflight_checks"), list) or len(handoff.get("preflight_checks", [])) < 3:
        return False
    if handoff.get("start_from") == "gauge":
        return (
            handoff.get("input_path_count") == 1
            and handoff.get("input_directory_policy") == "treat_gauge_input_directories_as_shared_read_only_storage_when_possible"
            and handoff.get("output_directory_policy") == "write_new_outputs_to_explicit_writable_results_directory"
            and handoff.get("output_input_overlap_forbidden") is False
        )
    if handoff.get("start_from") == "propagator":
        return (
            handoff.get("input_path_count", 0) >= 1
            and handoff.get("input_directory_policy") == "treat_input_directories_as_read_only_handoff_storage"
            and handoff.get("output_directory_policy") == "prefer_dedicated_writable_results_directory"
            and handoff.get("output_input_overlap_forbidden") is True
        )
    return False


def _handoff_validation_summary(handoff: dict | None) -> dict:
    if not isinstance(handoff, dict):
        return {
            "present": False,
            "coherent": False,
            "start_from": None,
            "input_directory_policy": None,
            "output_directory_policy": None,
            "output_writer_policy": None,
            "input_path_count": None,
            "output_directory_count": None,
            "probe_artifact_present": False,
            "required_modules": [],
            "preflight_check_count": 0,
        }
    return {
        "present": True,
        "coherent": _hpc_handoff_coherent(handoff),
        "start_from": handoff.get("start_from"),
        "input_directory_policy": handoff.get("input_directory_policy"),
        "output_directory_policy": handoff.get("output_directory_policy"),
        "output_writer_policy": handoff.get("output_writer_policy"),
        "input_path_count": handoff.get("input_path_count"),
        "output_directory_count": handoff.get("output_directory_count"),
        "probe_artifact_present": bool(handoff.get("probe_artifact")),
        "required_modules": list(handoff.get("required_modules") or []),
        "preflight_check_count": len(handoff.get("preflight_checks") or []),
    }


def _run(
    workflow: str,
    pyquda_repo: Path,
    backend: str,
    api_model: str | None,
    output_root: Path,
    llm_timeout: float,
) -> dict:
    spec = WORKFLOWS[workflow]
    gauge = pyquda_repo / "tests" / "weak_field.lime"
    rough_script = output_root / f"validate_{workflow}_rough.py"
    direct_script = output_root / f"validate_{workflow}.py"
    direct_suffix = ".h5" if workflow.startswith("quark_propagator") else ".npy"
    direct_corr = output_root / f"validate_{workflow}{direct_suffix}"
    direct_request = spec["direct_request"].format(gauge=gauge, corr=direct_corr, script=direct_script)
    rough = _run_request(
        request=spec["rough_request"],
        script_path=rough_script,
        pyquda_repo=pyquda_repo,
        backend=backend,
        api_model=api_model,
        dry_run=False,
        summary_only=True,
        llm_timeout=llm_timeout,
    )
    direct = _run_request(
        request=direct_request,
        script_path=direct_script,
        pyquda_repo=pyquda_repo,
        backend=backend,
        api_model=api_model,
        dry_run=False,
        summary_only=True,
        llm_timeout=llm_timeout,
    )
    rough_payload = rough["parsed"]
    direct_payload = direct["parsed"]
    rough_ok = (
        isinstance(rough_payload, dict)
        and rough_payload.get("status") == "needs_input"
        and _target_id(rough_payload) == spec["expected_target"]
        and _workflow_target(rough_payload) == spec["expected_workflow"]
        and rough["artifacts_exist"]
        and not rough["script_exists"]
        and _llm_coherent(rough.get("llm_assistance"))
        and _product_path_coherent(
            rough,
            expect_product_status="needs_input",
            expect_generation_phase="blocked_on_input",
            expect_execution_phase="blocked_by_generation",
        )
        and _workflow_outcome_coherent(
            rough.get("workflow_outcome"),
            expect_phase="clarification",
            expect_probe_status="pending_generation",
        )
    )
    direct_ok = (
        isinstance(direct_payload, dict)
        and direct_payload.get("status") == "ok"
        and _target_id(direct_payload) == spec["expected_target"]
        and _workflow_target(direct_payload) == spec["expected_workflow"]
        and direct["artifacts_exist"]
        and direct["script_exists"]
        and direct["placeholder_free"]
        and _llm_coherent(direct.get("llm_assistance"))
        and _product_path_coherent(
            direct,
            expect_product_status=_expected_direct_product_status(direct),
            expect_generation_phase="generated",
            expect_execution_phase=_expected_direct_execution_phase(direct),
        )
        and _runtime_probe_coherent(direct, expect_script=True)
        and _workflow_outcome_coherent(
            direct.get("workflow_outcome"),
            expect_phase="generated_and_probed",
            expect_probe_status=_expected_direct_probe_status(direct),
        )
        and _hpc_handoff_coherent(_hpc_handoff_contract(direct_payload))
    )
    rough_probe_ok = _runtime_probe_coherent(rough, expect_script=False)
    handoff_summary = _handoff_validation_summary(_hpc_handoff_contract(direct_payload))
    return {
        "workflow": workflow,
        "expected_target": spec["expected_target"],
        "expected_workflow": spec["expected_workflow"],
        "rough": rough,
        "direct": direct,
        "handoff": handoff_summary,
        "product_path": {
            "rough_product_status": rough.get("product_status"),
            "rough_generation_phase": ((rough.get("generation_result") or {}).get("phase")),
            "rough_execution_phase": ((rough.get("execution_result") or {}).get("phase")),
            "rough_backend": _backend_validation_summary(rough),
            "direct_product_status": direct.get("product_status"),
            "direct_generation_phase": ((direct.get("generation_result") or {}).get("phase")),
            "direct_execution_phase": ((direct.get("execution_result") or {}).get("phase")),
            "direct_backend": _backend_validation_summary(direct),
        },
        "coherent": rough_ok and rough_probe_ok and direct_ok,
    }


def _count_by(items: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = item.get(key)
        if value is None:
            continue
        label = str(value)
        counts[label] = counts.get(label, 0) + 1
    return counts


def _build_report_summary(results: list[dict]) -> dict:
    direct_rows = [item.get("direct") or {} for item in results]
    rough_rows = [item.get("rough") or {} for item in results]
    direct_backend_rows = [
        ((item.get("product_path") or {}).get("direct_backend") or {})
        for item in results
    ]
    rough_backend_rows = [
        ((item.get("product_path") or {}).get("rough_backend") or {})
        for item in results
    ]
    direct_execution_status_counts = _count_by(direct_rows, "execution_status")
    direct_probe_status_counts = _count_by(direct_rows, "probe_status")
    direct_backend_category_counts = _count_by(direct_backend_rows, "backend_category")
    direct_backend_detail_category_counts = _count_by(direct_backend_rows, "backend_detail_category")
    rough_backend_category_counts = _count_by(rough_backend_rows, "backend_category")
    rough_backend_detail_category_counts = _count_by(rough_backend_rows, "backend_detail_category")
    coherent_count = sum(1 for item in results if item.get("coherent"))
    direct_runtime_proved = direct_execution_status_counts.get("runtime_proved", 0)
    direct_runtime_blocked = sum(
        count for status, count in direct_execution_status_counts.items() if status in _runtime_blocked_statuses()
    )
    handoff_rows = [item.get("handoff") or {} for item in results]
    rough_backend_fallback_count = sum(1 for item in rough_backend_rows if item.get("fallback"))
    direct_backend_fallback_count = sum(1 for item in direct_backend_rows if item.get("fallback"))
    handoff_coherent_count = sum(1 for item in handoff_rows if item.get("coherent"))
    handoff_start_from_counts = _count_by(handoff_rows, "start_from")
    handoff_input_policy_counts = _count_by(handoff_rows, "input_directory_policy")
    handoff_output_policy_counts = _count_by(handoff_rows, "output_directory_policy")

    if coherent_count != len(results):
        report_status = "validation_failed"
    elif direct_runtime_proved == len(results):
        report_status = "runtime_proved"
    elif direct_runtime_blocked:
        report_status = "coherent_but_runtime_blocked"
    else:
        report_status = "coherent_mixed_runtime"

    next_action = (
        "Fix the runtime environment or generated-script probe blockers and rerun the embedded probe path to move coherent workflows from generated_runtime_blocked to runtime_proved."
        if direct_runtime_blocked
        else "Inspect any non-coherent workflow rows and rerun validation after repairing the reported backend or artifact issue."
    )
    if report_status == "runtime_proved":
        next_action = "Review the runtime-proved workflows and keep the same validation path for future workflow additions."

    return {
        "report_status": report_status,
        "workflow_count": len(results),
        "coherent_count": coherent_count,
        "rough_product_status_counts": _count_by(rough_rows, "product_status"),
        "direct_product_status_counts": _count_by(direct_rows, "product_status"),
        "direct_execution_status_counts": direct_execution_status_counts,
        "direct_probe_status_counts": direct_probe_status_counts,
        "rough_backend_fallback_count": rough_backend_fallback_count,
        "direct_backend_fallback_count": direct_backend_fallback_count,
        "rough_backend_category_counts": rough_backend_category_counts,
        "direct_backend_category_counts": direct_backend_category_counts,
        "rough_backend_detail_category_counts": rough_backend_detail_category_counts,
        "direct_backend_detail_category_counts": direct_backend_detail_category_counts,
        "hpc_handoff_coherent_count": handoff_coherent_count,
        "hpc_handoff_start_from_counts": handoff_start_from_counts,
        "hpc_handoff_input_directory_policy_counts": handoff_input_policy_counts,
        "hpc_handoff_output_directory_policy_counts": handoff_output_policy_counts,
        "unsupported_actionability_boundary": {
            "covered_here": False,
            "source_of_truth": "data/v9_product_behavior.json",
            "copyable_retry_kind": "retry_supported_workflow",
            "choice_required_kind": "choose_supported_variant",
            "note": (
                "This validator only proves supported-workflow routing and lifecycle coherence. "
                "Nearest grounded retry behavior for unsupported requests is audited separately in the v9 product-behavior report."
            ),
        },
        "next_action": next_action,
    }


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="scripts/validate_supported_workflows.py")
    args = parse_args(argv)
    pyquda_repo = args.pyquda_repo.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    output_root = output_path.parent.parent / "outputs" if output_path.parent.name == "data" else output_path.parent / "outputs"
    output_root.mkdir(parents=True, exist_ok=True)
    results = [_run(workflow, pyquda_repo, args.backend, args.api_model, output_root, args.llm_timeout) for workflow in WORKFLOWS]
    payload = {
        "backend": args.backend,
        "api_model": args.api_model,
        "llm_timeout": args.llm_timeout,
        "pyquda_repo": str(pyquda_repo),
        "workflows": results,
        "all_coherent": all(item["coherent"] for item in results),
        "summary": _build_report_summary(results),
        "runtime_validation_note": (
            "This integration check validates artifact coherence, placeholder-free script generation, product-facing run/probe summary cards, and unified run-path probe reporting. "
            "It also keeps backend failure-origin and recovery semantics visible for both rough and direct requests. "
            "It does not prove numerical execution unless the embedded runtime probe reaches runtime_proved."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote supported-workflow validation report to {output_path}")
    return 0 if payload["all_coherent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
