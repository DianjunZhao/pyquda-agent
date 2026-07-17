"""Build retrieval context for script generation."""

from __future__ import annotations

from pathlib import Path

from pyquda_agent.config import DEFAULT_INDEX_PATH
from pyquda_agent.models import ContextBundle
from pyquda_agent.models import ContextSnippet

from .index_loader import load_index
from .repo_scan import collect_documents
from .repo_scan import PINNED_APE_SMEAR_PYQUDA_FILES
from .repo_scan import PINNED_HYP_SMEAR_PYQUDA_FILES
from .repo_scan import PINNED_MESON_SPEC_PYQUDA_FILES
from .repo_scan import PINNED_PION_PCAC_PYQUDA_FILES
from .repo_scan import PINNED_PION_DISPERSION_PYQUDA_FILES
from .repo_scan import PINNED_PION_2PT_PYQUDA_FILES
from .repo_scan import PINNED_PION_2PT_PROPAGATOR_PYQUDA_FILES
from .repo_scan import PINNED_PROTON_2PT_PYQUDA_FILES
from .repo_scan import PINNED_PROTON_2PT_PROPAGATOR_PYQUDA_FILES
from .repo_scan import PINNED_QUARK_PROPAGATOR_PYQUDA_FILES
from .repo_scan import PINNED_RHO_VECTOR_PYQUDA_FILES
from .repo_scan import PINNED_STOUT_SMEAR_PYQUDA_FILES
from .repo_scan import PINNED_WILSON_FLOW_PYQUDA_FILES
from .search import rank_documents


def _snippet_summary(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary = lines[0] if lines else ""
    excerpt = "\n".join(lines[:12])
    return summary, excerpt


def _index_provenance(*, index: dict, index_path: Path, pyquda_repo: Path) -> dict:
    indexed_repo_root = index.get("repo_root")
    requested_repo_root = str(pyquda_repo.expanduser().resolve())
    provenance = {
        "index_path": str(index_path.expanduser().resolve()),
        "requested_repo_root": requested_repo_root,
        "indexed_repo_root": indexed_repo_root,
        "status": "unknown",
        "note": "Index provenance could not be verified against the requested PyQUDA repo.",
    }
    if not indexed_repo_root:
        return provenance
    try:
        indexed_resolved = str(Path(indexed_repo_root).expanduser().resolve())
    except OSError:
        indexed_resolved = indexed_repo_root
    provenance["indexed_repo_root"] = indexed_resolved
    if indexed_resolved == requested_repo_root:
        provenance["status"] = "matched"
        provenance["note"] = "The loaded index summary matches the requested PyQUDA repo."
    else:
        provenance["status"] = "repo_mismatch"
        provenance["note"] = (
            "The loaded index summary comes from a different PyQUDA repo than the current --pyquda-repo. "
            "Use snippets and explicit repo paths as the primary grounding, or refresh the index for this repo."
        )
    return provenance


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
    index_provenance = _index_provenance(index=index, index_path=index_path, pyquda_repo=pyquda_repo)
    documents = collect_documents(workspace_root=workspace_root, pyquda_repo=pyquda_repo, task_type=task_type)
    doc_by_path = {doc.path: doc for doc in documents}
    snippets: list[ContextSnippet] = []
    seen_paths: set[str] = set()

    if task_type == "pion_2pt":
        pinned_paths = PINNED_PION_2PT_PYQUDA_FILES
        lowered = task_description.lower()
        if "existing propagator" in lowered or "from propagator" in lowered or "读取 propagator" in lowered:
            pinned_paths = PINNED_PION_2PT_PROPAGATOR_PYQUDA_FILES
        for rel_path in pinned_paths:
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
    elif task_type == "pion_dispersion":
        for rel_path in PINNED_PION_DISPERSION_PYQUDA_FILES:
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
    elif task_type == "pion_pcac":
        for rel_path in PINNED_PION_PCAC_PYQUDA_FILES:
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
    elif task_type == "meson_spec":
        for rel_path in PINNED_MESON_SPEC_PYQUDA_FILES:
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
    elif task_type == "rho_vector":
        for rel_path in PINNED_RHO_VECTOR_PYQUDA_FILES:
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
    elif task_type == "proton_2pt":
        pinned_paths = PINNED_PROTON_2PT_PYQUDA_FILES
        lowered = task_description.lower()
        if "existing propagator" in lowered or "from propagator" in lowered or "读取 propagator" in lowered:
            pinned_paths = PINNED_PROTON_2PT_PROPAGATOR_PYQUDA_FILES
        for rel_path in pinned_paths:
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
    elif task_type == "quark_propagator":
        for rel_path in PINNED_QUARK_PROPAGATOR_PYQUDA_FILES:
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
    elif task_type == "ape_smear":
        for rel_path in PINNED_APE_SMEAR_PYQUDA_FILES:
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
    elif task_type == "hyp_smear":
        for rel_path in PINNED_HYP_SMEAR_PYQUDA_FILES:
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
    elif task_type == "wilson_flow":
        for rel_path in PINNED_WILSON_FLOW_PYQUDA_FILES:
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
    elif task_type == "stout_smear":
        for rel_path in PINNED_STOUT_SMEAR_PYQUDA_FILES:
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
        index_provenance=index_provenance,
        snippets=snippets,
    )
