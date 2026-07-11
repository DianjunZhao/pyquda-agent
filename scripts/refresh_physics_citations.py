#!/usr/bin/env python3
"""Refresh curated physics citation artifacts from source manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib import parse
from urllib import request
import xml.etree.ElementTree as ET


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "physics_citations"

ARXIV_METADATA = {
    "https://arxiv.org/abs/2203.03230": {
        "title": "Hadron Spectroscopy with Lattice QCD",
        "authors": [
            "John Bulava",
            "Raul Briceno",
            "William Detmold",
            "et al."
        ],
        "year": 2022,
    },
    "https://arxiv.org/abs/1508.05658": {
        "title": "The sigma meson from lattice QCD with two-pion interpolating operators",
        "authors": [
            "Dean Howarth",
            "Joel Giedt"
        ],
        "year": 2015,
    },
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh curated external physics citation artifacts.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing *.sources.json manifests and rendered citation JSON files.",
    )
    parser.add_argument(
        "--enrich-from-arxiv",
        action="store_true",
        help="Fetch title/author/year metadata from the arXiv API when possible, with curated fallback otherwise.",
    )
    return parser.parse_args(argv)


def _curated_metadata(url: str) -> dict:
    metadata = ARXIV_METADATA.get(url)
    if metadata is None:
        raise KeyError(f"No curated metadata available for citation URL: {url}")
    return metadata


def _arxiv_id_from_url(url: str) -> str:
    prefix = "https://arxiv.org/abs/"
    if not url.startswith(prefix):
        raise ValueError(f"Expected arXiv abs URL, got: {url}")
    return url[len(prefix) :]


def fetch_arxiv_metadata(url: str, timeout: int = 30) -> dict:
    arxiv_id = _arxiv_id_from_url(url)
    query = parse.urlencode({"id_list": arxiv_id})
    api_url = f"https://export.arxiv.org/api/query?{query}"
    with request.urlopen(api_url, timeout=timeout) as resp:  # pragma: no cover - network dependent
        payload = resp.read()

    root = ET.fromstring(payload)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        raise RuntimeError(f"arXiv API returned no entry for {arxiv_id}")

    title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
    published = (entry.findtext("atom:published", default="", namespaces=ns) or "").strip()
    authors = [
        (author.findtext("atom:name", default="", namespaces=ns) or "").strip()
        for author in entry.findall("atom:author", ns)
    ]
    authors = [name for name in authors if name]
    if not title or not published:
        raise RuntimeError(f"Incomplete arXiv API metadata for {arxiv_id}")
    return {
        "title": " ".join(title.split()),
        "authors": authors,
        "year": int(published[:4]),
    }


def render_citation_entry(source: dict, enrich_from_arxiv: bool = False) -> dict:
    metadata_source = "curated_fallback"
    refresh_note = "curated_fallback"
    if enrich_from_arxiv:
        try:
            metadata = fetch_arxiv_metadata(source["url"])
            metadata_source = "arxiv_api"
            refresh_note = "arxiv_api"
        except Exception:
            metadata = _curated_metadata(source["url"])
            metadata_source = "curated_fallback"
            refresh_note = "arxiv_api_failed_fallback_to_curated"
    else:
        metadata = _curated_metadata(source["url"])
    return {
        "id": source["id"],
        "type": source["type"],
        "title": metadata["title"],
        "authors": metadata["authors"],
        "year": metadata["year"],
        "url": source["url"],
        "metadata_source": metadata_source,
        "metadata_refresh": refresh_note,
        "supports": list(source["supports"]),
        "chosen_convention": source["chosen_convention"],
        "why_needed": source["why_needed"],
    }


def refresh_citation_file(source_path: Path, enrich_from_arxiv: bool = False) -> Path:
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    rendered = [render_citation_entry(item, enrich_from_arxiv=enrich_from_arxiv) for item in payload]
    output_name = source_path.name.replace(".sources.json", ".json")
    output_path = source_path.with_name(output_name)
    output_path.write_text(json.dumps(rendered, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    data_dir = args.data_dir.expanduser().resolve()
    refreshed: list[Path] = []
    for source_path in sorted(data_dir.glob("*.sources.json")):
        refreshed.append(refresh_citation_file(source_path, enrich_from_arxiv=args.enrich_from_arxiv))
    for output_path in refreshed:
        print(f"Refreshed physics citations: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
