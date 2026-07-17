#!/usr/bin/env python3
"""Refresh V6 demo artifacts for external-knowledge and parameterized-family paths."""

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
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "v6_demos"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh V6 demo artifacts.")
    parser.add_argument("--pyquda-repo", type=Path, default=DEFAULT_PYQUDA_REPO)
    parser.add_argument("--backend", choices=("api", "codex"), default="codex")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--api-model", default=os.environ.get("PYQUDA_AGENT_API_MODEL") or os.environ.get("DEEPSEEK_MODEL") or os.environ.get("OPENAI_MODEL"))
    return parser.parse_args(argv)


def _run(request: str, *, backend: str, script_output: Path, pyquda_repo: Path, api_model: str | None, enable_external_lookup: bool = False) -> dict:
    cmd = [
        sys.executable,
        "-m",
        "pyquda_agent.cli",
        "run",
        request,
        "--backend",
        backend,
        "--dry-run",
        "--no-interactive",
        "--output",
        str(script_output),
        "--pyquda-repo",
        str(pyquda_repo),
    ]
    if enable_external_lookup:
        cmd.append("--enable-external-lookup")
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
    payload = json.loads(completed.stdout)
    return {
        "returncode": completed.returncode,
        "payload": payload,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    external_demo = _run(
        "I want a meson correlator script but I am not sure about the exact operator",
        backend=args.backend,
        script_output=output_dir / "external_lookup_demo.py",
        pyquda_repo=args.pyquda_repo.expanduser().resolve(),
        api_model=args.api_model,
        enable_external_lookup=True,
    )
    propagator_demo = _run(
        "generate complete pion 2pt from existing propagator /tmp/pt_prop_1.npy lattice size 24 24 24 72 grid 1 1 1 2 outputs/pion_prop.npy outputs/pion_prop.py cluster_launch=local gauge fixed",
        backend=args.backend,
        script_output=output_dir / "pion_prop_demo.py",
        pyquda_repo=args.pyquda_repo.expanduser().resolve(),
        api_model=args.api_model,
    )

    report = {
        "backend": args.backend,
        "api_model": args.api_model,
        "external_lookup_demo": external_demo,
        "propagator_demo": propagator_demo,
    }
    report_path = output_dir / "v6_demo_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote V6 demo report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
