"""Optional live external knowledge lookup."""

from __future__ import annotations

import json
from urllib import parse
from urllib import request

from pyquda_agent.intent.interpreter import MESON_UNSPECIFIED_TARGET_ID
from pyquda_agent.intent.schema import PhysicsTargetArtifact


ARXIV_API_URL = "https://export.arxiv.org/api/query"


def _default_record(*, enabled: bool) -> dict:
    return {
        "enabled": enabled,
        "attempted": False,
        "used": False,
        "status": "disabled" if not enabled else "not_needed",
        "reason": None,
        "queries": [],
        "results": [],
        "source_kind": "live_online_lookup",
        "effect_on_interpretation": "none",
    }


def _should_attempt_lookup(physics: PhysicsTargetArtifact) -> bool:
    target_id = (physics.inferred_interpretation or {}).get("target_id")
    return target_id == MESON_UNSPECIFIED_TARGET_ID


def _append_live_formula_proposal(physics: PhysicsTargetArtifact, results: list[dict]) -> None:
    if not results:
        return
    if any(item.get("provenance") == "live_online_lookup" for item in physics.formula_proposals):
        return
    first = results[0]
    physics.formula_proposals.append(
        {
            "proposal_id": "live_lookup_meson_ps_candidate",
            "target_id": MESON_UNSPECIFIED_TARGET_ID,
            "label": "Live-lookup meson 2pt candidate",
            "operator": "Pseudoscalar meson operator candidate",
            "correlator": "C(t) = sum_x <O(x,t) O^dagger(0)>",
            "convention": "Live lookup enriched the operator explanation for an otherwise underspecified meson request. It does not confirm a supported workflow by itself.",
            "provenance": "live_online_lookup",
            "citations": [first.get("url")] if first.get("url") else [],
            "local_references": [],
        }
    )


def _query_arxiv(query: str, max_results: int = 2, timeout: float = 20.0) -> list[dict]:
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
    }
    url = f"{ARXIV_API_URL}?{parse.urlencode(params)}"
    with request.urlopen(url, timeout=timeout) as resp:  # pragma: no cover - network dependent
        xml_text = resp.read().decode("utf-8", errors="ignore")
    entries: list[dict] = []
    for chunk in xml_text.split("<entry>")[1:]:
        title = chunk.split("<title>", 1)[1].split("</title>", 1)[0].strip() if "<title>" in chunk else ""
        entry_id = chunk.split("<id>", 1)[1].split("</id>", 1)[0].strip() if "<id>" in chunk else ""
        summary = chunk.split("<summary>", 1)[1].split("</summary>", 1)[0].strip() if "<summary>" in chunk else ""
        if title or entry_id:
            entries.append(
                {
                    "title": " ".join(title.split()),
                    "url": entry_id,
                    "summary": " ".join(summary.split()),
                    "source_kind": "live_online_lookup",
                    "provider": "arxiv_api",
                }
            )
    return entries


def maybe_lookup_external_knowledge(
    physics: PhysicsTargetArtifact,
    *,
    enabled: bool,
) -> PhysicsTargetArtifact:
    record = _default_record(enabled=enabled)
    physics.knowledge_boundary.setdefault(
        "live_online_lookup",
        {
            "implemented": True,
            "used": False,
            "enabled": enabled,
            "note": "Live online lookup is opt-in and only used when local PyQUDA evidence is insufficient for the physics-side target definition.",
        },
    )
    physics.knowledge_boundary["live_online_lookup"]["enabled"] = enabled

    if not enabled:
        record["reason"] = "External lookup is disabled by default. Re-run with --enable-external-lookup to allow live online lookup."
        physics.knowledge_boundary["live_online_lookup"]["used"] = False
        physics.knowledge_boundary["live_online_lookup"]["status"] = "disabled"
        physics.external_lookup = record
        return physics

    if not _should_attempt_lookup(physics):
        record["reason"] = "Live online lookup is only considered for underspecified meson-like requests when local grounding is insufficient to define the physics target."
        record["status"] = "not_needed"
        physics.knowledge_boundary["live_online_lookup"]["used"] = False
        physics.knowledge_boundary["live_online_lookup"]["status"] = "not_needed"
        physics.external_lookup = record
        return physics

    record["attempted"] = True
    query = "all:meson two-point correlator interpolating operator"
    record["queries"].append({"provider": "arxiv_api", "query": query})
    try:
        results = _query_arxiv(query)
    except Exception as exc:  # pragma: no cover - network dependent
        record["status"] = "failed"
        record["reason"] = f"Live online lookup failed: {type(exc).__name__}: {exc}"
        physics.knowledge_boundary["live_online_lookup"]["used"] = False
        physics.knowledge_boundary["live_online_lookup"]["status"] = "failed"
        physics.external_lookup = record
        return physics

    record["results"] = results
    record["used"] = bool(results)
    record["status"] = "ok" if results else "empty"
    record["reason"] = None if results else "Live online lookup completed but returned no results."
    record["effect_on_interpretation"] = "formula_proposal_enrichment" if results else "none"
    physics.knowledge_boundary["live_online_lookup"]["used"] = bool(results)
    physics.knowledge_boundary["live_online_lookup"]["status"] = record["status"]
    if results:
        physics.external_citations.extend(
            {
                "id": f"live-online-{idx}",
                "title": item["title"],
                "url": item["url"],
                "summary": item["summary"],
                "citation_source_kind": "live_online_lookup",
                "online_lookup_used": True,
            }
            for idx, item in enumerate(results, start=1)
        )
        _append_live_formula_proposal(physics, results)
    physics.external_lookup = record
    return physics
