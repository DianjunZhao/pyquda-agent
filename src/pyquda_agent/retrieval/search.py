"""Lightweight lexical ranking for local retrieval."""

from __future__ import annotations

import re

from .repo_scan import RepoDocument


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def score_document(query: str, document: RepoDocument) -> float:
    query_tokens = tokenize(query)
    doc_tokens = tokenize(document.path) | tokenize(document.text)
    overlap = len(query_tokens & doc_tokens)
    score = float(overlap)
    path_lower = document.path.lower()
    if "pion" in query_tokens and "pion" in document.path.lower():
        score += 3.0
    if "2pt" in query_tokens and "2pt" in document.path.lower():
        score += 2.0
    if "test_mesonspec.py" in path_lower:
        score += 3.0
    if "3_pion_proton_2pt.py" in path_lower:
        score += 2.5
    if "5_pion_dispersion.py" in path_lower:
        score += 1.5
    if "pyquda_utils/io/__init__.py" in path_lower or "pyquda_utils/core.py" in path_lower:
        score += 1.0
    if document.source == "pyquda":
        score += 0.5
    return score


def rank_documents(query: str, documents: list[RepoDocument], limit: int = 8) -> list[tuple[RepoDocument, float]]:
    ranked = [(doc, score_document(query, doc)) for doc in documents]
    ranked = [item for item in ranked if item[1] > 0]
    ranked.sort(key=lambda item: (-item[1], item[0].path))
    return ranked[:limit]
