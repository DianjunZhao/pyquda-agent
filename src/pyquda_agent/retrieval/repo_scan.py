"""Read candidate files from the workspace and the read-only PyQUDA checkout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


WORKFLOW_FILES = (
    "docs/RUNNABLE_PION_2PT_SPEC.md",
    "docs/TASK_SCHEMAS.md",
    "docs/RUN_WORKFLOW.md",
)

PION_2PT_PYQUDA_FILES = (
    "examples/3_Pion_Proton_2pt.py",
    "examples/5_Pion_Dispersion.py",
    "tests/test_mesonspec.py",
    "tests/test_io.py",
    "pyquda_utils/io/__init__.py",
    "pyquda_utils/source.py",
    "pyquda_utils/core.py",
    "pyquda_utils/gamma.py",
)

PINNED_PION_2PT_PYQUDA_FILES = PION_2PT_PYQUDA_FILES


@dataclass
class RepoDocument:
    source: str
    path: str
    text: str


def _read_file(path: Path, max_chars: int = 4000) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]


def collect_documents(*, workspace_root: Path, pyquda_repo: Path, task_type: str) -> list[RepoDocument]:
    docs: list[RepoDocument] = []
    for rel_path in WORKFLOW_FILES:
        path = workspace_root / rel_path
        if path.exists():
            docs.append(RepoDocument(source="workspace", path=str(path), text=_read_file(path)))
    if task_type == "pion_2pt":
        for rel_path in PION_2PT_PYQUDA_FILES:
            path = pyquda_repo / rel_path
            if path.exists():
                docs.append(RepoDocument(source="pyquda", path=str(path), text=_read_file(path)))
    return docs
