#!/usr/bin/env python3
"""Run a generated workflow script and record direct execution evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
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
    return parser.parse_args(argv)


def classify_probe(returncode: int, stdout: str, stderr: str) -> str:
    if returncode == 0:
        return "ok"
    combined = "\n".join(part for part in (stdout, stderr) if part)
    if any(marker in combined for marker in RUNTIME_GAP_MARKERS):
        return "runtime_missing"
    return "failed"


def build_probe(script_path: Path, timeout: float) -> dict:
    resolved_script = script_path.expanduser().resolve()
    start = perf_counter()
    if not resolved_script.exists():
        return {
            "python": sys.executable,
            "script": str(resolved_script),
            "script_exists": False,
            "status": "missing_script",
            "returncode": None,
            "duration_seconds": perf_counter() - start,
            "stdout": "",
            "stderr": "",
        }

    try:
        completed = subprocess.run(
            [sys.executable, str(resolved_script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "python": sys.executable,
            "script": str(resolved_script),
            "script_exists": True,
            "status": "timeout",
            "returncode": None,
            "duration_seconds": perf_counter() - start,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    status = classify_probe(completed.returncode, stdout, stderr)
    return {
        "python": sys.executable,
        "script": str(resolved_script),
        "script_exists": True,
        "status": status,
        "returncode": completed.returncode,
        "duration_seconds": perf_counter() - start,
        "stdout": stdout,
        "stderr": stderr,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    artifact = build_probe(args.script, args.timeout)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote workflow probe to {output}")
    return 0 if artifact["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
