#!/usr/bin/env python3
"""Generate a supported runnable workflow with both backends and compare artifacts."""

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
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "backend_parity"
DEFAULT_REPORT = REPO_ROOT / "data" / "backend_parity.json"
DEFAULT_API_MODEL = resolve_api_model(None)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check artifact parity between api and codex backends.")
    parser.add_argument("--pyquda-repo", type=Path, default=DEFAULT_PYQUDA_REPO, help="Path to the local PyQUDA checkout.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated backend-specific artifacts.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Where to write the JSON parity report.")
    parser.add_argument("--resource-path", default=".cache/quda", help="Resource path passed into the supported workflow request.")
    parser.add_argument(
        "--workflow",
        choices=("pion_2pt", "pion_pcac", "pion_dispersion", "meson_spec", "proton_2pt", "rho_vector", "quark_propagator", "ape_smear", "hyp_smear", "stout_smear", "wilson_flow"),
        default="pion_2pt",
        help="Supported workflow family to exercise for parity.",
    )
    parser.add_argument(
        "--api-model",
        default=DEFAULT_API_MODEL,
        help="Model passed to --backend api. Defaults to PYQUDA_AGENT_API_MODEL/OPENAI_MODEL when set.",
    )
    return parser.parse_args(argv)


def _request(
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


def _run_backend(
    backend: str,
    pyquda_repo: Path,
    script_output: Path,
    correlator_output: Path,
    resource_path: str,
    workflow: str,
    api_model: str | None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not existing_pythonpath else f"src:{existing_pythonpath}"
    cmd = [
        sys.executable,
        "-m",
        "pyquda_agent.cli",
        "run",
        _request(pyquda_repo, script_output, correlator_output, resource_path, workflow),
        "--backend",
        backend,
        "--no-interactive",
        "--runtime-probe",
        "--probe-timeout",
        "5",
        "--output",
        str(script_output),
        "--pyquda-repo",
        str(pyquda_repo),
    ]
    if backend == "api" and api_model:
        cmd.extend(["--model", api_model])
    return subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True, check=False, env=env)


def _artifact_paths(script_output: Path) -> tuple[Path, Path, Path, Path]:
    return (
        script_output.with_suffix(".physics.json"),
        script_output.with_suffix(".task.json"),
        script_output.with_suffix(".plan.json"),
        script_output.with_suffix(".probe.json"),
    )


def _normalize_script_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("CORRELATOR_OUTPUT = Path("):
            lines.append("CORRELATOR_OUTPUT = Path('<normalized>')")
        elif line.startswith("PROPAGATOR_OUTPUT = Path("):
            lines.append("PROPAGATOR_OUTPUT = Path('<normalized>')")
        elif line.startswith("SMEARED_GAUGE_OUTPUT = Path("):
            lines.append("SMEARED_GAUGE_OUTPUT = Path('<normalized>')")
        else:
            lines.append(line)
    return "\n".join(lines)


def _normalize_task_payload(payload: dict) -> dict:
    normalized = json.loads(json.dumps(payload))
    normalized["correlator_output_path"] = "<normalized>"
    normalized["script_output_path"] = "<normalized>"
    normalized["notes"] = "<normalized>"
    normalized["user_request"] = "<normalized>"
    user_confirmed = normalized.get("user_confirmed_fields")
    if isinstance(user_confirmed, dict):
        if "correlator_output_path" in user_confirmed:
            user_confirmed["correlator_output_path"] = "<normalized>"
        if "script_output_path" in user_confirmed:
            user_confirmed["script_output_path"] = "<normalized>"
    return normalized


def _normalize_plan_payload(payload: dict) -> dict:
    normalized = json.loads(json.dumps(payload))
    runtime_choices = normalized.get("runtime_choices", {})
    if runtime_choices:
        runtime_choices["correlator_output_path"] = "<normalized>"
        runtime_choices["script_output_path"] = "<normalized>"
    runtime_readiness = normalized.get("runtime_readiness", {})
    if runtime_readiness:
        runtime_readiness["generated_script_path"] = "<normalized>"
        artifact_chain = runtime_readiness.get("artifact_chain", {})
        if artifact_chain:
            artifact_chain["task_artifact"] = "<normalized>"
            artifact_chain["physics_artifact"] = "<normalized>"
            artifact_chain["plan_artifact"] = "<normalized>"
        generated_probe = runtime_readiness.get("generated_script_probe", {})
        if generated_probe:
            generated_probe["artifact_path"] = "<normalized>"
            generated_probe["command"] = "<normalized>"
            result = generated_probe.get("result", {})
            if result:
                result["script"] = "<normalized>"
                result["python"] = "<normalized>"
                result["duration_seconds"] = "<normalized>"
                if result.get("pyquda_repo") is not None:
                    result["pyquda_repo"] = "<normalized>"
    normalized["user_request"] = "<normalized>"
    return normalized


def _normalize_physics_payload(payload: dict) -> dict:
    normalized = json.loads(json.dumps(payload))
    normalized["user_request"] = "<normalized>"
    normalized["normalized_request"] = "<normalized>"
    llm_assistance = normalized.get("llm_assistance", {})
    if llm_assistance:
        llm_assistance["requested_backend"] = "<normalized>"
        llm_assistance["configured_backend"] = "<normalized>"
        llm_assistance["backend_executable"] = "<normalized>"
    return normalized


def _normalize_probe_payload(payload: dict) -> dict:
    normalized = json.loads(json.dumps(payload))
    normalized["script"] = "<normalized>"
    normalized["python"] = "<normalized>"
    normalized["duration_seconds"] = "<normalized>"
    if normalized.get("pyquda_repo") is not None:
        normalized["pyquda_repo"] = "<normalized>"
    return normalized


def build_report(
    output_dir: Path,
    api_result: subprocess.CompletedProcess[str],
    codex_result: subprocess.CompletedProcess[str],
    workflow: str,
) -> dict:
    if workflow == "pion_dispersion":
        stem = "run_pion_dispersion"
    elif workflow == "pion_pcac":
        stem = "run_pion_pcac"
    elif workflow == "meson_spec":
        stem = "run_meson_spec"
    elif workflow == "proton_2pt":
        stem = "run_proton"
    elif workflow == "rho_vector":
        stem = "run_rho_vector"
    elif workflow == "quark_propagator":
        stem = "run_quark_propagator"
    elif workflow == "ape_smear":
        stem = "run_ape_smear"
    elif workflow == "hyp_smear":
        stem = "run_hyp_smear"
    elif workflow == "stout_smear":
        stem = "run_stout_smear"
    elif workflow == "wilson_flow":
        stem = "run_wilson_flow"
    else:
        stem = "run_pion"
    api_script = output_dir / f"{stem}_api.py"
    codex_script = output_dir / f"{stem}_codex.py"
    api_physics, api_task, api_plan, api_probe = _artifact_paths(api_script)
    codex_physics, codex_task, codex_plan, codex_probe = _artifact_paths(codex_script)

    def compare_script_pair(lhs: Path, rhs: Path) -> dict:
        exists = lhs.exists() and rhs.exists()
        identical = False
        if exists:
            identical = _normalize_script_text(lhs.read_text(encoding="utf-8")) == _normalize_script_text(
                rhs.read_text(encoding="utf-8")
            )
        return {
            "left": str(lhs),
            "right": str(rhs),
            "both_exist": exists,
            "identical": identical,
        }

    def compare_json_pair(lhs: Path, rhs: Path, normalizer) -> dict:
        exists = lhs.exists() and rhs.exists()
        identical = False
        if exists:
            identical = normalizer(json.loads(lhs.read_text(encoding="utf-8"))) == normalizer(
                json.loads(rhs.read_text(encoding="utf-8"))
            )
        return {
            "left": str(lhs),
            "right": str(rhs),
            "both_exist": exists,
            "identical": identical,
        }

    comparisons = {
        "script": compare_script_pair(api_script, codex_script),
        "physics": compare_json_pair(api_physics, codex_physics, _normalize_physics_payload),
        "task": compare_json_pair(api_task, codex_task, _normalize_task_payload),
        "plan": compare_json_pair(api_plan, codex_plan, _normalize_plan_payload),
        "probe": compare_json_pair(api_probe, codex_probe, _normalize_probe_payload),
    }
    implementation_equivalent = (
        comparisons["script"]["identical"]
        and comparisons["task"]["identical"]
        and comparisons["probe"]["identical"]
    )
    return {
        "workflow": workflow,
        "api": {
            "returncode": api_result.returncode,
            "stdout": api_result.stdout.strip(),
            "stderr": api_result.stderr.strip(),
        },
        "codex": {
            "returncode": codex_result.returncode,
            "stdout": codex_result.stdout.strip(),
            "stderr": codex_result.stderr.strip(),
        },
        "comparisons": comparisons,
        "equivalence": {
            "implementation_equivalent": implementation_equivalent,
            "note": (
                "Script, task, and probe parity are treated as the primary implementation-equivalence check. "
                "Physics and plan artifacts may still differ in backend-specific LLM provenance and fallback metadata."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="scripts/check_backend_parity.py")
    args = parse_args(argv)
    pyquda_repo = args.pyquda_repo.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.workflow == "pion_dispersion":
        stem = "run_pion_dispersion"
    elif args.workflow == "pion_pcac":
        stem = "run_pion_pcac"
    elif args.workflow == "proton_2pt":
        stem = "run_proton"
    elif args.workflow == "rho_vector":
        stem = "run_rho_vector"
    elif args.workflow == "quark_propagator":
        stem = "run_quark_propagator"
    elif args.workflow == "ape_smear":
        stem = "run_ape_smear"
    elif args.workflow == "hyp_smear":
        stem = "run_hyp_smear"
    elif args.workflow == "stout_smear":
        stem = "run_stout_smear"
    elif args.workflow == "wilson_flow":
        stem = "run_wilson_flow"
    else:
        stem = "run_pion"
    api_script = output_dir / f"{stem}_api.py"
    codex_script = output_dir / f"{stem}_codex.py"
    output_suffix = ".h5" if args.workflow == "quark_propagator" else ".npy"
    api_corr = output_dir / f"{stem}_api{output_suffix}"
    codex_corr = output_dir / f"{stem}_codex{output_suffix}"

    api_result = _run_backend("api", pyquda_repo, api_script, api_corr, args.resource_path, args.workflow, args.api_model)
    codex_result = _run_backend("codex", pyquda_repo, codex_script, codex_corr, args.resource_path, args.workflow, args.api_model)
    report = build_report(output_dir, api_result, codex_result, args.workflow)

    report_path = args.report.expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote backend parity report to {report_path}")

    comparisons = report["comparisons"]
    ok = (
        report["api"]["returncode"] == 0
        and report["codex"]["returncode"] == 0
        and report["equivalence"]["implementation_equivalent"]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
