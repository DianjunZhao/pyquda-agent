#!/usr/bin/env python3
"""Refresh the fixed first workflow artifacts end to end."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_PYQUDA_REPO = Path.home() / "PyQUDA"
DEFAULT_BACKEND = "api"
DEFAULT_SCRIPT_OUTPUT = REPO_ROOT / "outputs" / "run_pion_api.py"
DEFAULT_CORRELATOR_OUTPUT = REPO_ROOT / "outputs" / "pion_api.npy"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh the first runnable pion 2pt workflow artifacts.")
    parser.add_argument("--pyquda-repo", type=Path, default=DEFAULT_PYQUDA_REPO, help="Path to the local PyQUDA checkout.")
    parser.add_argument("--backend", choices=("api", "codex"), default=DEFAULT_BACKEND, help="Backend label to stamp onto generation.")
    parser.add_argument("--script-output", type=Path, default=DEFAULT_SCRIPT_OUTPUT, help="Generated script output path.")
    parser.add_argument("--correlator-output", type=Path, default=DEFAULT_CORRELATOR_OUTPUT, help="Generated correlator output path.")
    parser.add_argument("--resource-path", default=".cache/quda", help="Resource path passed to the generated workflow request.")
    parser.add_argument(
        "--require-local-runtime-proof",
        action="store_true",
        help="Fail when local runtime check, candidate scan, or direct script probe cannot prove execution on this workstation.",
    )
    return parser.parse_args(argv)


def _generation_request(pyquda_repo: Path, script_output: Path, correlator_output: Path, resource_path: str) -> str:
    gauge_path = pyquda_repo / "tests" / "weak_field.lime"
    return (
        "generate complete runnable pion 2pt from gauge "
        f"{gauge_path} with clover wall source local sink zero momentum timeslice 0 "
        "lattice size 4 4 4 8 grid 1 1 1 1 "
        "mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 "
        f"tol=1e-12 maxiter=1000 gauge fixed {correlator_output} {script_output} resource_path={resource_path} cluster_launch=local"
    )


def build_summary(results: dict[str, subprocess.CompletedProcess[str]]) -> dict:
    summary: dict[str, dict] = {}
    for name, completed in results.items():
        summary[name] = {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    return summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pyquda_repo = args.pyquda_repo.expanduser().resolve()
    script_output = args.script_output.expanduser().resolve()
    correlator_output = args.correlator_output.expanduser().resolve()

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
        "generate_workflow": [
            sys.executable,
            "-m",
            "pyquda_agent.cli",
            "run",
            _generation_request(pyquda_repo, script_output, correlator_output, args.resource_path),
            "--backend",
            args.backend,
            "--no-interactive",
            "--output",
            str(script_output),
            "--pyquda-repo",
            str(pyquda_repo),
        ],
        "probe_workflow": [
            sys.executable,
            "scripts/probe_generated_workflow.py",
            "--script",
            str(script_output),
            "--output",
            str(REPO_ROOT / "data" / "run_pion_api_probe.json"),
        ],
        "check_backend_parity": [
            sys.executable,
            "scripts/check_backend_parity.py",
            "--pyquda-repo",
            str(pyquda_repo),
        ],
        "refresh_goal_audit": [
            sys.executable,
            "scripts/refresh_goal_audit.py",
        ],
    }

    env = dict(PYTHONPATH="src")
    results: dict[str, subprocess.CompletedProcess[str]] = {}
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not existing_pythonpath else f"src:{existing_pythonpath}"
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

    summary = build_summary(results)
    if argv is None:
        print(json.dumps(summary, indent=2, sort_keys=True))

    fatal_steps = [
        "refresh_analysis",
        "refresh_citations",
        "generate_workflow",
        "check_backend_parity",
        "refresh_goal_audit",
    ]
    if args.require_local_runtime_proof:
        fatal_steps.extend(
            [
                "refresh_runtime",
                "scan_runtime_candidates",
                "probe_workflow",
            ]
        )
    return 0 if all(results[name].returncode == 0 for name in fatal_steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
