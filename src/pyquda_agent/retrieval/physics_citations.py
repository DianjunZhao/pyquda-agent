"""Load curated external physics citations for supported workflows."""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_PHYSICS_CITATION_DIR = Path(__file__).resolve().parents[3] / "data" / "physics_citations"


def load_physics_citations(workflow_id: str, citation_dir: Path = DEFAULT_PHYSICS_CITATION_DIR) -> list[dict]:
    path = citation_dir / f"{workflow_id}.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    for item in payload:
        item.setdefault("citation_source_kind", "local_curated_json")
        item.setdefault("online_lookup_used", False)
        item.setdefault(
            "knowledge_boundary_note",
            "This citation record comes from a local curated JSON artifact, not from a live online lookup during the current run.",
        )
    return payload
