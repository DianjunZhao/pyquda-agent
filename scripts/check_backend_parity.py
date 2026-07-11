#!/usr/bin/env python3
"""Generate the fixed first workflow with both backends and compare artifacts."""

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
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "backend_parity"
DEFAULT_REPORT = REPO_ROOT / "data" / "backend_parity.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check artifact parity between api and codex backends.")
    parser.add_argument("--pyquda-repo", type=Path, default=DEFAULT_PYQUDA_REPO, help="Path to the local PyQUDA checkout.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated backend-specific artifacts.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Where to write the JSON parity report.")
    parser.add_argument("--resource-path", default=".cache/quda", help="Resource path passed into the fixed workflow request.")
    return parser.parse_args(argv)


def _request(pyquda_repo: Path, script_output: Path, correlator_output: Path, resource_path: str) -> str:
    gauge_path = pyquda_repo / "tests" / "weak_field.lime"
    return (
        "generate complete runnable pion 2pt from gauge "
        f"{gauge_path} with clover wall source local sink zero momentum timeslice 0 "
        "lattice size 4 4 4 8 grid 1 1 1 1 "
        "mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 "
        f"tol=1e-12 maxiter=1000 gauge fixed {correlator_output} {script_output} resource_path={resource_path} cluster_launch=local"
    )


def _run_backend(backend: str, pyquda_repo: Path, script_output: Path, correlator_output: Path, resource_path: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not existing_pythonpath else f"src:{existing_pythonpath}"
    cmd = [
        sys.executable,
        "-m",
        "pyquda_agent.cli",
        "run",
        _request(pyquda_repo, script_output, correlator_output, resource_path),
        "--backend",
        backend,
        "--no-interactive",
        "--output",
        str(script_output),
        "--pyquda-repo",
        str(pyquda_repo),
    ]
    return subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True, check=False, env=env)


def _artifact_paths(script_output: Path) -> tuple[Path, Path]:
    return script_output.with_suffix(".task.json"), script_output.with_suffix(".plan.json")


def _normalize_script_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("CORRELATOR_OUTPUT = Path("):
            lines.append("CORRELATOR_OUTPUT = Path('<normalized>')")
        else:
            lines.append(line)
    return "\n".join(lines)


def _normalize_task_payload(payload: dict) -> dict:
    normalized = json.loads(json.dumps(payload))
    normalized["correlator_output_path"] = "<normalized>"
    normalized["script_output_path"] = "<normalized>"
    normalized["notes"] = "<normalized>"
    return normalized


def _normalize_plan_payload(payload: dict) -> dict:
    normalized = json.loads(json.dumps(payload))
    runtime_choices = normalized.get("runtime_choices", {})
    if runtime_choices:
        runtime_choices["correlator_output_path"] = "<normalized>"
        runtime_choices["script_output_path"] = "<normalized>"
    return normalized


def build_report(output_dir: Path, api_result: subprocess.CompletedProcess[str], codex_result: subprocess.CompletedProcess[str]) -> dict:
    api_script = output_dir / "run_pion_api.py"
    codex_script = output_dir / "run_pion_codex.py"
    api_task, api_plan = _artifact_paths(api_script)
    codex_task, codex_plan = _artifact_paths(codex_script)

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

    return {
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
        "comparisons": {
            "script": compare_script_pair(api_script, codex_script),
            "task": compare_json_pair(api_task, codex_task, _normalize_task_payload),
            "plan": compare_json_pair(api_plan, codex_plan, _normalize_plan_payload),
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pyquda_repo = args.pyquda_repo.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    api_script = output_dir / "run_pion_api.py"
    codex_script = output_dir / "run_pion_codex.py"
    api_corr = output_dir / "pion_api.npy"
    codex_corr = output_dir / "pion_codex.npy"

    api_result = _run_backend("api", pyquda_repo, api_script, api_corr, args.resource_path)
    codex_result = _run_backend("codex", pyquda_repo, codex_script, codex_corr, args.resource_path)
    report = build_report(output_dir, api_result, codex_result)

    report_path = args.report.expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote backend parity report to {report_path}")

    comparisons = report["comparisons"]
    ok = (
        report["api"]["returncode"] == 0
        and report["codex"]["returncode"] == 0
        and all(item["identical"] for item in comparisons.values())
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
