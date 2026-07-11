"""Load the local PyQUDA index artifact."""

from __future__ import annotations

import json
from pathlib import Path


def load_index(index_path: Path) -> dict:
    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}")
    return json.loads(index_path.read_text(encoding="utf-8"))
