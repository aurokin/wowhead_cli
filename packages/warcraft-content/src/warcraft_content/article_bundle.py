from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def default_article_export_root(provider: str, *, cwd: Path | None = None) -> Path:
    base = cwd if cwd is not None else Path.cwd()
    return base / f"{provider}_exports"


def default_article_export_dir(provider: str, ref_slug: str, *, prefix: str = "guide", cwd: Path | None = None) -> Path:
    return default_article_export_root(provider, cwd=cwd) / f"{prefix}-{ref_slug}"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_or_default(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return load_json(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            rows.append(value)
    return rows


def write_article_bundle(
    full_payload: dict[str, Any],
    *,
    provider: str,
    export_dir: Path,
    resource_key: str = "guide",
    page_resource_key: str | None = None,
    content_key: str = "article",
) -> dict[str, Any]:
    resource = dict(full_payload[resource_key])
    normalized_page_resource_key = page_resource_key or resource_key
    navigation = list((full_payload.get("navigation") or {}).get("items") or [])
    pages = list(full_payload.get("pages") or [])
    linked_entities = list((full_payload.get("linked_entities") or {}).get("items") or [])
    sections: list[dict[str, Any]] = []
    page_rows: list[dict[str, Any]] = []
    page_files: list[dict[str, Any]] = []
    html_dir = export_dir / "pages"
    for page in pages:
        page_resource = dict(page[normalized_page_resource_key])
        page_meta = dict(page["page"])
        article = dict(page[content_key])
        page_slug = page_resource["section_slug"]
        html_path = html_dir / f"{page_slug}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(article["html"], encoding="utf-8")
        page_files.append(
            {
                "section_slug": page_slug,
                "path": str(html_path.relative_to(export_dir)),
                "page_url": page_resource["page_url"],
            }
        )
        page_rows.append(
            {
                "section_slug": page_slug,
                "section_title": page_resource["section_title"],
                "page_url": page_resource["page_url"],
                "title": page_meta["title"],
                "description": page_meta.get("description"),
                "text": article["text"],
                "heading_count": len(article.get("headings") or []),
            }
        )
        for section in article.get("sections") or []:
            sections.append(
                {
                    "page_url": page_resource["page_url"],
                    "section_slug": page_slug,
                    "page_title": page_meta["title"],
                    "title": section["title"],
                    "level": section["level"],
                    "ordinal": section["ordinal"],
                    "text": section["text"],
                    "html": section["html"],
                }
            )

    manifest = {
        "export_version": 1,
        "provider": provider,
        "resource_key": resource_key,
        "page_resource_key": normalized_page_resource_key,
        "content_key": content_key,
        "output_dir": str(export_dir),
        resource_key: resource,
        "counts": {
            "pages": len(page_rows),
            "sections": len(sections),
            "navigation_links": len(navigation),
            "linked_entities": len(linked_entities),
        },
        "files": {
            "guide_json": "guide.json",
            "page_files_json": "page-files.json",
            "pages_jsonl": "pages.jsonl",
            "sections_jsonl": "sections.jsonl",
            "navigation_links_jsonl": "navigation-links.jsonl",
            "linked_entities_jsonl": "linked-entities.jsonl",
            "page_html_dir": "pages",
        },
    }
    export_dir.mkdir(parents=True, exist_ok=True)
    _write_json(export_dir / "guide.json", full_payload)
    _write_json(export_dir / "manifest.json", manifest)
    _write_json(export_dir / "page-files.json", {"pages": page_files})
    _write_jsonl(export_dir / "pages.jsonl", page_rows)
    _write_jsonl(export_dir / "sections.jsonl", sections)
    _write_jsonl(export_dir / "navigation-links.jsonl", navigation)
    _write_jsonl(export_dir / "linked-entities.jsonl", linked_entities)
    return manifest


def load_article_bundle(export_dir: Path) -> dict[str, Any]:
    manifest = load_json(export_dir / "manifest.json")
    files = manifest.get("files") or {}
    page_files = load_json_or_default(export_dir / files.get("page_files_json", "page-files.json"), {"pages": []})
    return {
        "manifest": manifest,
        "page_files": list(page_files.get("pages") or []) if isinstance(page_files, dict) else [],
        "pages": load_jsonl(export_dir / files.get("pages_jsonl", "pages.jsonl")),
        "sections": load_jsonl(export_dir / files.get("sections_jsonl", "sections.jsonl")),
        "navigation": load_jsonl(export_dir / files.get("navigation_links_jsonl", "navigation-links.jsonl")),
        "linked_entities": load_jsonl(export_dir / files.get("linked_entities_jsonl", "linked-entities.jsonl")),
    }


def _query_score(query: str, text: str) -> int:
    if not query or not text:
        return 0
    normalized_text = text.lower()
    score = 0
    if query in normalized_text:
        score += 10
    terms = [term for term in query.split() if term]
    if terms and all(term in normalized_text for term in terms):
        score += 6
    for term in terms:
        if term in normalized_text:
            score += 2
    return score


def query_article_bundle(
    bundle: dict[str, Any],
    *,
    query: str,
    limit: int,
    kinds: set[str],
    section_title_filter: str | None,
) -> dict[str, Any]:
    normalized_query = query.lower().strip()
    normalized_section_title_filter = section_title_filter.lower().strip() if section_title_filter else None
    results_by_kind: dict[str, list[dict[str, Any]]] = {"sections": [], "navigation": [], "linked_entities": []}
    if "sections" in kinds:
        for row in bundle["sections"]:
            title = str(row.get("title") or "")
            if normalized_section_title_filter and normalized_section_title_filter not in title.lower():
                continue
            haystack = f"{title} {row.get('text') or ''}"
            score = _query_score(normalized_query, haystack)
            if score <= 0:
                continue
            results_by_kind["sections"].append({"kind": "section", "score": score, **row})
    if "navigation" in kinds:
        for row in bundle["navigation"]:
            haystack = f"{row.get('title') or ''} {row.get('section_slug') or ''}"
            score = _query_score(normalized_query, haystack)
            if score <= 0:
                continue
            results_by_kind["navigation"].append({"kind": "navigation", "score": score, **row})
    if "linked_entities" in kinds:
        for row in bundle["linked_entities"]:
            haystack = f"{row.get('name') or ''} {row.get('type') or ''} {row.get('id') or ''}"
            score = _query_score(normalized_query, haystack)
            if score <= 0:
                continue
            results_by_kind["linked_entities"].append({"kind": "linked_entity", "score": score, **row})
    for rows in results_by_kind.values():
        rows.sort(key=lambda row: (-row["score"], str(row.get("title") or row.get("name") or "")))
    top: list[dict[str, Any]] = []
    for rows in results_by_kind.values():
        top.extend(rows[:limit])
    top.sort(key=lambda row: (-row["score"], row["kind"], str(row.get("title") or row.get("name") or "")))
    return {
        "query": query,
        "count": sum(len(rows) for rows in results_by_kind.values()),
        "match_counts": {kind: len(rows) for kind, rows in results_by_kind.items()},
        "matches": {kind: rows[:limit] for kind, rows in results_by_kind.items()},
        "top": top[:limit],
    }
