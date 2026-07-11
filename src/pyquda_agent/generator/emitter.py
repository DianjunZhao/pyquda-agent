"""Write generated code to disk."""

from __future__ import annotations

from pathlib import Path


def emit_script(output_path: Path, code: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(code, encoding="utf-8")
