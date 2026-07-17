#!/usr/bin/env python3
"""Check whether the current Python environment can import the runtime needed by generated PyQUDA scripts."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pyquda_agent.python_version import ensure_supported_python


DEFAULT_REPO = Path.home() / "PyQUDA"
MODULE_HINTS = {
    "numpy": "Install NumPy into the target Python environment used for PyQUDA handoff.",
    "cupy": "Use a GPU-enabled Python environment with CuPy installed and matching CUDA runtime support.",
    "pyquda": "Build or install the PyQUDA core bindings in this Python environment before runtime proof.",
    "pyquda_utils": "Expose the local PyQUDA checkout on PYTHONPATH or install pyquda_utils into the runtime environment.",
    "pyquda_utils.core": "Check that pyquda_utils is importable and that the built core helpers are present.",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check whether the current Python can run generated PyQUDA scripts.")
    parser.add_argument(
        "--pyquda-repo",
        type=Path,
        default=DEFAULT_REPO,
        help="Path to the local PyQUDA checkout. Defaults to ~/PyQUDA.",
    )
    parser.add_argument(
        "--use-repo-pythonpath",
        action="store_true",
        help="Temporarily prepend the given PyQUDA checkout to sys.path before probing imports.",
    )
    return parser.parse_args(argv)


def probe_module(name: str) -> dict:
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        return {
            "module": name,
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    return {
        "module": name,
        "ok": True,
        "path": getattr(module, "__file__", None),
    }


def build_report(pyquda_repo: Path, use_repo_pythonpath: bool) -> dict:
    repo = pyquda_repo.expanduser().resolve()
    if use_repo_pythonpath:
        sys.path.insert(0, str(repo))

    results = {
        "python": sys.executable,
        "pyquda_repo": str(repo),
        "used_repo_pythonpath": use_repo_pythonpath,
        "checks": [
            probe_module("numpy"),
            probe_module("cupy"),
            probe_module("pyquda"),
            probe_module("pyquda_utils"),
            probe_module("pyquda_utils.core"),
        ],
    }
    results["ready"] = all(item["ok"] for item in results["checks"])
    results["environment_ready"] = results["ready"]
    results["runtime_level"] = "runtime_ready" if results["ready"] else "environment_missing"
    blocker_details = [
        {
            "module": item["module"],
            "error_type": item.get("error_type"),
            "error": item.get("error"),
            "suggestion": MODULE_HINTS.get(item["module"], "Inspect the failing import and align the Python environment with the target PyQUDA runtime."),
        }
        for item in results["checks"]
        if not item["ok"]
    ]
    results["evidence_levels"] = {
        "syntax_valid": None,
        "structurally_grounded": None,
        "runtime_ready": results["environment_ready"],
        "runtime_proved": False,
        "current_level": "runtime_ready" if results["environment_ready"] else "environment_missing",
        "blockers": blocker_details,
    }
    return results


def main(argv: list[str] | None = None) -> int:
    ensure_supported_python(context="scripts/check_pyquda_runtime.py")
    args = parse_args(argv)
    results = build_report(args.pyquda_repo, args.use_repo_pythonpath)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if results["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
