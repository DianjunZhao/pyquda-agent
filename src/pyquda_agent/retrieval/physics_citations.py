"""Load curated external physics citations for supported workflows."""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_PHYSICS_CITATION_DIR = Path(__file__).resolve().parents[3] / "data" / "physics_citations"


def load_physics_citations(workflow_id: str, citation_dir: Path = DEFAULT_PHYSICS_CITATION_DIR) -> list[dict]:
    path = citation_dir / f"{workflow_id}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
