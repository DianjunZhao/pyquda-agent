#!/usr/bin/env python3
"""Write a machine-readable runtime readiness report for generated PyQUDA scripts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_OUTPUT = REPO_ROOT / "data" / "pyquda_runtime_check.json"

from check_pyquda_runtime import DEFAULT_REPO
from check_pyquda_runtime import build_report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh the current PyQUDA runtime readiness report.")
    parser.add_argument(
        "--pyquda-repo",
        type=Path,
        default=DEFAULT_REPO,
        help="Path to the local PyQUDA checkout. Defaults to ~/PyQUDA.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to write the JSON report.",
    )
    parser.add_argument(
        "--use-repo-pythonpath",
        action="store_true",
        help="Temporarily prepend the given PyQUDA checkout to sys.path before probing imports.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.pyquda_repo, args.use_repo_pythonpath)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote runtime check to {output}")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
