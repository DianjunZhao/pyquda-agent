#!/usr/bin/env python3
"""Refresh the supported workflow demo artifacts end to end."""

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
DEFAULT_BACKEND = "api"
DEFAULT_SCRIPT_OUTPUT = REPO_ROOT / "outputs" / "run_pion_api.py"
DEFAULT_CORRELATOR_OUTPUT = REPO_ROOT / "outputs" / "pion_api.npy"
DEFAULT_API_MODEL = resolve_api_model(None)
DEFAULT_PROBE_TIMEOUT = 5.0


def _normalized_primary_output_path(workflow: str, output_path: Path) -> Path:
    if workflow == "quark_propagator" and output_path.suffix.lower() not in {".h5", ".hdf5"}:
        return output_path.with_suffix(".h5")
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh supported workflow demo artifacts.")
    parser.add_argument("--pyquda-repo", type=Path, default=DEFAULT_PYQUDA_REPO, help="Path to the local PyQUDA checkout.")
    parser.add_argument("--backend", choices=("api", "codex"), default=DEFAULT_BACKEND, help="Backend label to stamp onto generation.")
    parser.add_argument("--api-model", default=DEFAULT_API_MODEL, help="Model passed to --backend api when configured.")
    parser.add_argument(
        "--workflow",
        choices=("pion_2pt", "pion_pcac", "pion_dispersion", "meson_spec", "proton_2pt", "rho_vector", "quark_propagator", "ape_smear", "hyp_smear", "stout_smear", "wilson_flow"),
        default="pion_2pt",
        help="Supported workflow family to refresh.",
    )
    parser.add_argument("--script-output", type=Path, default=DEFAULT_SCRIPT_OUTPUT, help="Generated script output path.")
    parser.add_argument("--correlator-output", type=Path, default=DEFAULT_CORRELATOR_OUTPUT, help="Generated correlator output path.")
    parser.add_argument("--resource-path", default=".cache/quda", help="Resource path passed to the generated workflow request.")
    parser.add_argument("--llm-timeout", type=float, default=30.0, help="Timeout in seconds for LLM-assisted interpretation backends.")
    parser.set_defaults(runtime_probe=True)
    parser.add_argument(
        "--no-runtime-probe",
        dest="runtime_probe",
        action="store_false",
        help="Skip the unified run-path probe and only refresh generation artifacts.",
    )
    parser.add_argument("--probe-timeout", type=float, default=DEFAULT_PROBE_TIMEOUT, help="Timeout in seconds for the unified run-path probe.")
    parser.add_argument(
        "--probe-use-repo-pythonpath",
        action="store_true",
        help="Pass --probe-use-repo-pythonpath to the main run command so probing prepends --pyquda-repo to PYTHONPATH.",
    )
    parser.add_argument(
        "--require-local-runtime-proof",
        action="store_true",
        help="Fail when local runtime check, candidate scan, or direct script probe cannot prove execution on this workstation.",
    )
    return parser.parse_args(argv)


def _generation_request(
    pyquda_repo: Path,
    script_output: Path,
    correlator_output: Path,
    resource_path: str,
    workflow: str,
) -> str:
    gauge_path = pyquda_repo / "tests" / "weak_field.lime"
    if workflow == "pion_dispersion":
        return (
            "please compute pion dispersion from gauge "
            f"{gauge_path} lattice size 4 4 4 8 grid 1 1 1 1 "
            "mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 "
            f"tol=1e-12 maxiter=1000 source timeslice 0 {correlator_output} {script_output} "
            f"resource_path={resource_path} cluster_launch=local"
        )
    if workflow == "pion_pcac":
        return (
            "please compute pion pcac ratio from gauge "
            f"{gauge_path} lattice size 4 4 4 8 grid 1 1 1 1 "
            "mass=-0.2770 xi_0=1.0 nu=1.0 coeff_t=1.160920226 coeff_r=1.160920226 "
            f"tol=1e-12 maxiter=1000 source timeslice 0 {correlator_output} {script_output} "
            f"resource_path={resource_path} cluster_launch=local"
        )
    if workflow == "meson_spec":
        return (
            "please compute meson spectroscopy correlators from gauge "
            f"{gauge_path} lattice size 4 4 4 8 grid 1 1 1 1 "
            "mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 "
            f"tol=1e-12 maxiter=1000 {correlator_output} {script_output} "
            f"resource_path={resource_path} cluster_launch=local"
        )
    if workflow == "proton_2pt":
        return (
            "please compute the proton two-point correlator from gauge "
            f"{gauge_path} lattice size 4 4 4 8 grid 1 1 1 1 "
            "mass=0.09253 xi_0=1.0 nu=1.0 coeff_t=1.160920226 coeff_r=1.160920226 "
            f"tol=1e-12 maxiter=1000 source timeslice 0 {correlator_output} {script_output} "
            f"resource_path={resource_path} cluster_launch=local"
        )
    if workflow == "rho_vector":
        return (
            "please compute the rho meson two-point correlator from gauge "
            f"{gauge_path} lattice size 4 4 4 8 grid 1 1 1 1 "
            "mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 "
            f"tol=1e-12 maxiter=1000 source timeslice 0 not gauge fixed {correlator_output} {script_output} "
            f"resource_path={resource_path} cluster_launch=local"
        )
    if workflow == "quark_propagator":
        return (
            "please generate a quark propagator from gauge "
            f"{gauge_path} lattice size 4 4 4 8 grid 1 1 1 1 "
            "mass=-0.2770 xi_0=1.0 nu=1.0 coeff_t=1.160920226 coeff_r=1.160920226 "
            f"tol=1e-12 maxiter=1000 source timeslice 0 point source not gauge fixed {correlator_output} {script_output} "
            f"resource_path={resource_path} cluster_launch=local"
        )
    if workflow == "ape_smear":
        return (
            "please generate an APE-smeared gauge from gauge "
            f"{gauge_path} lattice size 4 4 4 8 grid 1 1 1 1 "
            f"{correlator_output} {script_output} resource_path={resource_path} cluster_launch=local"
        )
    if workflow == "hyp_smear":
        return (
            "please generate a HYP-smeared gauge from gauge "
            f"{gauge_path} lattice size 4 4 4 8 grid 1 1 1 1 "
            f"{correlator_output} {script_output} resource_path={resource_path} cluster_launch=local"
        )
    if workflow == "stout_smear":
        return (
            "please generate a stout-smeared gauge from gauge "
            f"{gauge_path} lattice size 4 4 4 8 grid 1 1 1 1 "
            f"{correlator_output} {script_output} resource_path={resource_path} cluster_launch=local"
        )
    if workflow == "wilson_flow":
        return (
            "please run wilson flow from gauge "
            f"{gauge_path} lattice size 4 4 4 8 grid 1 1 1 1 "
            f"flow_steps=100 flow_epsilon=1.0 not gauge fixed {correlator_output} {script_output} "
            f"resource_path={resource_path} cluster_launch=local"
        )
    return (
        "generate complete runnable pion 2pt from gauge "
        f"{gauge_path} with clover wall source local sink zero momentum timeslice 0 "
        "lattice size 4 4 4 8 grid 1 1 1 1 "
        "mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 "
        f"tol=1e-12 maxiter=1000 gauge fixed {correlator_output} {script_output} resource_path={resource_path} cluster_launch=local"
    )


def _rough_request(workflow: str) -> str:
    if workflow == "pion_pcac":
        return "please compute pion pcac ratio"
    if workflow == "pion_dispersion":
        return "please compute pion dispersion with nonzero momentum"
    if workflow == "meson_spec":
        return "please compute meson spectroscopy correlators"
    if workflow == "proton_2pt":
        return "please compute the proton two-point correlator"
    if workflow == "rho_vector":
        return "please compute the rho meson two-point correlator"
    if workflow == "quark_propagator":
        return "please generate a quark propagator"
    if workflow == "ape_smear":
        return "please generate an APE-smeared gauge configuration"
    if workflow == "hyp_smear":
        return "please generate a HYP-smeared gauge configuration"
    if workflow == "stout_smear":
        return "please stout-smear this gauge configuration"
    if workflow == "wilson_flow":
        return "please run wilson flow on this gauge configuration"
    return "write a simple PyQUDA script for pi meson two-point"


def _try_parse_json(text: str) -> dict | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def build_summary(results: dict[str, subprocess.CompletedProcess[str]], *, script_output: Path) -> dict:
    summary: dict[str, dict] = {}
    probe_artifact = script_output.with_suffix(".probe.json")
    for name, completed in results.items():
        entry = {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
        payload = _try_parse_json(completed.stdout)
        if payload is not None:
            entry["status"] = payload.get("status")
            entry["product_status"] = payload.get("product_status")
            entry["execution_status"] = payload.get("execution_status")
            entry["physics_target"] = payload.get("physics_target") or ((payload.get("physics") or {}).get("confirmed_interpretation") or {}).get("target_id")
            entry["workflow_target"] = payload.get("workflow_target") or ((payload.get("workflow_match") or {}).get("workflow_target"))
            entry["task_artifact"] = payload.get("task_artifact") or ((payload.get("artifacts") or {}).get("task"))
            entry["physics_artifact"] = payload.get("physics_artifact") or ((payload.get("artifacts") or {}).get("physics"))
            entry["plan_artifact"] = payload.get("plan_artifact") or ((payload.get("artifacts") or {}).get("plan"))
            entry["workflow_outcome"] = payload.get("workflow_outcome")
            entry["generation_result"] = payload.get("generation_result")
            entry["execution_result"] = payload.get("execution_result")
            entry["delivery_status"] = payload.get("delivery_status")
            entry["next_action"] = payload.get("next_action")
            entry["probe_hint"] = payload.get("probe_hint")
            if isinstance(payload.get("probe"), dict):
                entry["probe_status"] = payload["probe"].get("status")
            elif isinstance(payload.get("workflow_outcome"), dict):
                entry["probe_status"] = payload["workflow_outcome"].get("runtime_probe_status")
        summary[name] = entry
    if probe_artifact.exists():
        probe_payload = _try_parse_json(probe_artifact.read_text(encoding="utf-8"))
        summary["probe_artifact"] = {
            "path": str(probe_artifact),
            "exists": True,
            "status": (probe_payload or {}).get("status"),
            "runtime_level": (probe_payload or {}).get("runtime_level"),
        }
    else:
        summary["probe_artifact"] = {
            "path": str(probe_artifact),
            "exists": False,
        }
    return summary


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="scripts/refresh_first_workflow_demo.py")
    args = parse_args(argv)
    pyquda_repo = args.pyquda_repo.expanduser().resolve()
    script_output = args.script_output.expanduser().resolve()
    correlator_output = _normalized_primary_output_path(args.workflow, args.correlator_output.expanduser().resolve())
    rough_script_output = script_output.with_name(f"{script_output.stem}_rough.py")

    steps = {
        "refresh_analysis": [
            sys.executable,
            "scripts/refresh_pyquda_analysis.py",
            "--repo",
            str(pyquda_repo),
        ],
        "refresh_citations": [
            sys.executable,
            "scripts/refresh_physics_citations.py",
        ],
        "refresh_runtime": [
            sys.executable,
            "scripts/refresh_runtime_check.py",
            "--pyquda-repo",
            str(pyquda_repo),
        ],
        "scan_runtime_candidates": [
            sys.executable,
            "scripts/scan_runtime_candidates.py",
            "--pyquda-repo",
            str(pyquda_repo),
        ],
        "preview_rough_request": [
            sys.executable,
            "-m",
            "pyquda_agent.cli",
            "run",
            _rough_request(args.workflow),
            "--backend",
            args.backend,
            "--llm-timeout",
            str(args.llm_timeout),
            "--dry-run",
            "--no-interactive",
            "--result-format",
            "summary",
            "--output",
            str(rough_script_output),
            "--pyquda-repo",
            str(pyquda_repo),
        ],
        "generate_workflow": [
            sys.executable,
            "-m",
            "pyquda_agent.cli",
            "run",
            _generation_request(pyquda_repo, script_output, correlator_output, args.resource_path, args.workflow),
            "--backend",
            args.backend,
            "--llm-timeout",
            str(args.llm_timeout),
            "--no-interactive",
            "--result-format",
            "summary",
            "--output",
            str(script_output),
            "--pyquda-repo",
            str(pyquda_repo),
        ],
        "check_backend_parity": [
            sys.executable,
            "scripts/check_backend_parity.py",
            "--pyquda-repo",
            str(pyquda_repo),
            "--workflow",
            args.workflow,
        ],
        "refresh_goal_audit": [
            sys.executable,
            "scripts/refresh_goal_audit.py",
        ],
    }
    if args.runtime_probe:
        steps["generate_workflow"].extend(["--runtime-probe", "--probe-timeout", str(args.probe_timeout)])
        if args.probe_use_repo_pythonpath:
            steps["generate_workflow"].append("--probe-use-repo-pythonpath")

    results: dict[str, subprocess.CompletedProcess[str]] = {}
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not existing_pythonpath else f"src:{existing_pythonpath}"
    if args.backend == "api" and args.api_model:
        env.setdefault("PYQUDA_AGENT_API_MODEL", args.api_model)
    for step_name, cmd in steps.items():
        completed = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
        results[step_name] = completed

    summary = build_summary(results, script_output=script_output)
    summary_path = script_output.parent / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if argv is None:
        print(json.dumps(summary, indent=2, sort_keys=True))

    fatal_steps = [
        "refresh_analysis",
        "refresh_citations",
        "generate_workflow",
        "preview_rough_request",
        "check_backend_parity",
        "refresh_goal_audit",
    ]
    if args.require_local_runtime_proof:
        fatal_steps.extend(
            [
                "refresh_runtime",
                "scan_runtime_candidates",
            ]
        )
    success = all(results[name].returncode == 0 for name in fatal_steps)
    if args.require_local_runtime_proof:
        generate_payload = _try_parse_json(results["generate_workflow"].stdout)
        success = success and bool(generate_payload) and generate_payload.get("execution_status") == "runtime_proved"
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
