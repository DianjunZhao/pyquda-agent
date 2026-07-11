"""Build retrieval context for script generation."""

from __future__ import annotations

from pathlib import Path

from pyquda_agent.config import DEFAULT_INDEX_PATH
from pyquda_agent.models import ContextBundle
from pyquda_agent.models import ContextSnippet

from .index_loader import load_index
from .repo_scan import collect_documents
from .repo_scan import PINNED_PION_2PT_PYQUDA_FILES
from .search import rank_documents


def _snippet_summary(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary = lines[0] if lines else ""
    excerpt = "\n".join(lines[:12])
    return summary, excerpt


def build_context_bundle(
    *,
    task_description: str,
    task_type: str,
    workspace_root: Path,
    pyquda_repo: Path,
    index_path: Path = DEFAULT_INDEX_PATH,
    limit: int = 8,
) -> ContextBundle:
    index = load_index(index_path)
    documents = collect_documents(workspace_root=workspace_root, pyquda_repo=pyquda_repo, task_type=task_type)
    doc_by_path = {doc.path: doc for doc in documents}
    snippets: list[ContextSnippet] = []
    seen_paths: set[str] = set()

    if task_type == "pion_2pt":
        for rel_path in PINNED_PION_2PT_PYQUDA_FILES:
            path = str((pyquda_repo / rel_path))
            doc = doc_by_path.get(path)
            if doc is None:
                continue
            summary, excerpt = _snippet_summary(doc.text)
            snippets.append(
                ContextSnippet(
                    source=doc.source,
                    path=doc.path,
                    score=999.0,
                    summary=summary,
                    excerpt=excerpt,
                )
            )
            seen_paths.add(doc.path)

    ranked = rank_documents(task_description, documents, limit=limit)
    for doc, score in ranked:
        if doc.path in seen_paths:
            continue
        summary, excerpt = _snippet_summary(doc.text)
        snippets.append(
            ContextSnippet(
                source=doc.source,
                path=doc.path,
                score=score,
                summary=summary,
                excerpt=excerpt,
            )
        )
        seen_paths.add(doc.path)
    return ContextBundle(
        task_type=task_type,
        index_summary=index["summary"],
        snippets=snippets,
    )
