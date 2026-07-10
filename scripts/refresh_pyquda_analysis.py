#!/usr/bin/env python3
"""Run the full local PyQUDA indexing and summary pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_INDEX = REPO_ROOT / "data" / "pyquda_index.json"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from index_pyquda_repo import DEFAULT_SCOPE
from index_pyquda_repo import DEFAULT_REPO as INDEX_DEFAULT_REPO
from index_pyquda_repo import build_index
from render_pyquda_architecture import DEFAULT_OUTPUT
from render_pyquda_architecture import render_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh both the PyQUDA JSON index and Markdown architecture summary.")
    parser.add_argument(
        "--repo",
        type=Path,
        default=INDEX_DEFAULT_REPO,
        help="Path to the PyQUDA checkout. Defaults to ~/PyQUDA.",
    )
    parser.add_argument("--index-output", type=Path, default=DEFAULT_INDEX, help="Where to write the JSON index.")
    parser.add_argument("--doc-output", type=Path, default=DEFAULT_OUTPUT, help="Where to write the Markdown summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo.expanduser().resolve()
    index_output = args.index_output.expanduser().resolve()
    doc_output = args.doc_output.expanduser().resolve()

    index = build_index(repo_root, list(DEFAULT_SCOPE))
    index_output.parent.mkdir(parents=True, exist_ok=True)
    index_output.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    doc_output.parent.mkdir(parents=True, exist_ok=True)
    doc_output.write_text(render_markdown(index), encoding="utf-8")

    print(f"Wrote index to {index_output}")
    print(f"Wrote architecture summary to {doc_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
