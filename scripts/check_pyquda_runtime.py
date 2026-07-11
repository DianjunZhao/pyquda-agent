#!/usr/bin/env python3
"""Check whether the current Python environment can import the runtime needed by generated PyQUDA scripts."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys


DEFAULT_REPO = Path.home() / "PyQUDA"


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
    return results


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = build_report(args.pyquda_repo, args.use_repo_pythonpath)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if results["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
