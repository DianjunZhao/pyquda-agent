#!/usr/bin/env python3
"""Probe a list of Python interpreters for PyQUDA runtime readiness."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_OUTPUT = REPO_ROOT / "data" / "runtime_candidates.json"
DEFAULT_PYQUDA_REPO = Path.home() / "PyQUDA"
DEFAULT_INTERPRETERS = (
    Path("/Users/zhaodianjun/.venv/bin/python"),
    Path("/Users/zhaodianjun/lamet-agent/.venv/bin/python"),
    Path("/usr/bin/python3"),
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan candidate Python interpreters for PyQUDA runtime readiness.")
    parser.add_argument("--pyquda-repo", type=Path, default=DEFAULT_PYQUDA_REPO, help="Path to the local PyQUDA checkout.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Where to write the JSON scan report.")
    parser.add_argument("--interpreters", type=Path, nargs="*", default=list(DEFAULT_INTERPRETERS), help="Interpreter paths to probe.")
    return parser.parse_args(argv)


def _probe_interpreter(interpreter: Path, pyquda_repo: Path, use_repo_pythonpath: bool) -> dict:
    requested = interpreter.expanduser()
    resolved = requested.resolve()
    if not requested.exists():
        return {
            "python": str(requested),
            "resolved_python": str(resolved),
            "exists": False,
            "used_repo_pythonpath": use_repo_pythonpath,
            "returncode": None,
            "report": None,
        }

    cmd = [
        str(requested),
        str(SCRIPT_DIR / "check_pyquda_runtime.py"),
        "--pyquda-repo",
        str(pyquda_repo),
    ]
    if use_repo_pythonpath:
        cmd.append("--use-repo-pythonpath")
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True, check=False)
    report = None
    if completed.stdout.strip():
        try:
            report = json.loads(completed.stdout)
        except json.JSONDecodeError:
            report = None
    return {
        "python": str(requested),
        "resolved_python": str(resolved),
        "exists": True,
        "used_repo_pythonpath": use_repo_pythonpath,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "report": report,
    }


def build_scan(interpreters: list[Path], pyquda_repo: Path) -> dict:
    entries = []
    for interpreter in interpreters:
        entries.append(_probe_interpreter(interpreter, pyquda_repo, use_repo_pythonpath=False))
        entries.append(_probe_interpreter(interpreter, pyquda_repo, use_repo_pythonpath=True))

    ready_candidates = [
        entry["python"]
        for entry in entries
        if entry.get("report") and entry["report"].get("ready")
    ]
    return {
        "pyquda_repo": str(pyquda_repo.expanduser().resolve()),
        "interpreters": entries,
        "ready_candidates": ready_candidates,
        "any_ready": bool(ready_candidates),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_scan(list(args.interpreters), args.pyquda_repo.expanduser().resolve())
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote runtime candidate scan to {output}")
    return 0 if report["any_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
