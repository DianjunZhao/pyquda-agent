#!/usr/bin/env python3
"""Run a generated workflow script and record direct execution evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pyquda_agent.python_version import ensure_supported_python

DEFAULT_SCRIPT = REPO_ROOT / "outputs" / "run_pion_api.py"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "run_pion_api_probe.json"

RUNTIME_GAP_MARKERS = (
    "Missing runtime dependency",
    "Unable to import 'pyquda_utils'",
    "Unable to import 'pyquda'",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute a generated workflow script and capture evidence.")
    parser.add_argument(
        "--script",
        type=Path,
        default=DEFAULT_SCRIPT,
        help="Path to the generated workflow script.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to write the JSON probe artifact.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Maximum execution time in seconds before terminating the script.",
    )
    parser.add_argument(
        "--pyquda-repo",
        type=Path,
        default=None,
        help="Optional PyQUDA checkout used for PYTHONPATH enrichment during probing.",
    )
    parser.add_argument(
        "--use-repo-pythonpath",
        action="store_true",
        help="Temporarily prepend --pyquda-repo to PYTHONPATH before executing the generated script.",
    )
    return parser.parse_args(argv)


def classify_probe(returncode: int, stdout: str, stderr: str) -> str:
    if returncode == 0:
        return "ok"
    combined = "\n".join(part for part in (stdout, stderr) if part)
    if any(marker in combined for marker in RUNTIME_GAP_MARKERS):
        return "runtime_missing"
    return "failed"


def build_probe(script_path: Path, timeout: float, *, pyquda_repo: Path | None = None, use_repo_pythonpath: bool = False) -> dict:
    resolved_script = script_path.expanduser().resolve()
    start = perf_counter()
    if not resolved_script.exists():
        return {
            "python": sys.executable,
            "script": str(resolved_script),
            "script_exists": False,
            "used_repo_pythonpath": use_repo_pythonpath,
            "pyquda_repo": str(pyquda_repo.expanduser().resolve()) if pyquda_repo is not None else None,
            "status": "missing_script",
            "runtime_level": "missing_script",
            "evidence_levels": {
                "syntax_valid": None,
                "structurally_grounded": None,
                "runtime_ready": False,
                "runtime_proved": False,
                "current_level": "missing_script",
                "blockers": ["generated script does not exist"],
            },
            "returncode": None,
            "duration_seconds": perf_counter() - start,
            "stdout": "",
            "stderr": "",
        }

    env = dict(os.environ)
    resolved_repo = pyquda_repo.expanduser().resolve() if pyquda_repo is not None else None
    if use_repo_pythonpath and resolved_repo is not None:
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(resolved_repo) if not existing_pythonpath else f"{resolved_repo}:{existing_pythonpath}"

    try:
        completed = subprocess.run(
            [sys.executable, str(resolved_script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "python": sys.executable,
            "script": str(resolved_script),
            "script_exists": True,
            "used_repo_pythonpath": use_repo_pythonpath,
            "pyquda_repo": str(resolved_repo) if resolved_repo is not None else None,
            "status": "timeout",
            "runtime_level": "probe_timeout",
            "evidence_levels": {
                "syntax_valid": None,
                "structurally_grounded": None,
                "runtime_ready": True,
                "runtime_proved": False,
                "current_level": "probe_timeout",
                "blockers": ["runtime probe timed out"],
            },
            "returncode": None,
            "duration_seconds": perf_counter() - start,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    status = classify_probe(completed.returncode, stdout, stderr)
    runtime_level = "runtime_proved" if status == "ok" else ("environment_missing" if status == "runtime_missing" else "probe_failed")
    return {
        "python": sys.executable,
        "script": str(resolved_script),
        "script_exists": True,
        "used_repo_pythonpath": use_repo_pythonpath,
        "pyquda_repo": str(resolved_repo) if resolved_repo is not None else None,
        "status": status,
        "runtime_level": runtime_level,
        "evidence_levels": {
            "syntax_valid": None,
            "structurally_grounded": None,
            "runtime_ready": status != "runtime_missing",
            "runtime_proved": status == "ok",
            "current_level": runtime_level,
            "blockers": [] if status == "ok" else ([stderr or stdout] if (stderr or stdout) else [status]),
        },
        "returncode": completed.returncode,
        "duration_seconds": perf_counter() - start,
        "stdout": stdout,
        "stderr": stderr,
    }


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="scripts/probe_generated_workflow.py")
    args = parse_args(argv)
    artifact = build_probe(
        args.script,
        args.timeout,
        pyquda_repo=args.pyquda_repo,
        use_repo_pythonpath=args.use_repo_pythonpath,
    )
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote workflow probe to {output}")
    return 0 if artifact["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
