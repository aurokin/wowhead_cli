from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

import typer

from method_cli.client import MethodClient, guide_ref_parts, guide_url, load_method_cache_settings_from_env
from warcraft_core.output import emit

app = typer.Typer(add_completion=False, help="Method.gg guide CLI.")

SEARCH_TYPE_NAME = "Guide"
DEFAULT_EXPORT_ROOT = Path.cwd() / "method_exports"


@dataclass(slots=True)
class RuntimeConfig:
    pretty: bool = False


def _cfg(ctx: typer.Context) -> RuntimeConfig:
    obj = ctx.obj
    if isinstance(obj, RuntimeConfig):
        return obj
    return RuntimeConfig()


def _emit(ctx: typer.Context, payload: dict[str, Any], *, err: bool = False) -> None:
    emit(payload, pretty=_cfg(ctx).pretty, err=err)


def _fail(ctx: typer.Context, code: str, message: str, *, status: int = 1) -> None:
    _emit(ctx, {"ok": False, "error": {"code": code, "message": message}}, err=True)
    raise typer.Exit(status)


def _client(ctx: typer.Context) -> MethodClient:
    try:
        return MethodClient()
    except ValueError as exc:
        _fail(ctx, "invalid_cache_config", str(exc))
        raise AssertionError("unreachable")


def _normalize_query(query: str) -> str:
    normalized = re.sub(r"\b(method|guide|guides)\b", " ", query.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or query.strip().lower()


def _score_text_match(query: str, candidate: str) -> int:
    if not query or not candidate:
        return 0
    score = 0
    if candidate == query:
        score += 40
    if candidate.startswith(query):
        score += 15
    if query in candidate:
        score += 10
    query_terms = [term for term in query.split() if term]
    if query_terms and all(term in candidate for term in query_terms):
        score += 8
    return score


def _guide_follow_up(slug: str) -> dict[str, Any]:
    return {
        "recommended_surface": "guide",
        "recommended_command": f"method guide {slug}",
        "reason": "guide_summary",
        "alternatives": [f"method guide-full {slug}", f"method guide-export {slug}"],
    }


def _search_results(client: MethodClient, query: str, *, limit: int) -> tuple[str, list[dict[str, Any]], int]:
    normalized_query = _normalize_query(query)
    matches: list[dict[str, Any]] = []
    for row in client.sitemap_guides():
        slug = row["slug"]
        name = row["name"]
        candidate = f"{name.lower()} {slug.replace('-', ' ')}"
        score = _score_text_match(normalized_query, candidate)
        reasons: list[str] = []
        if name.lower() == normalized_query:
            reasons.append("exact_name")
        if candidate.startswith(normalized_query):
            reasons.append("name_prefix")
        if normalized_query in candidate:
            reasons.append("name_contains_query")
        if normalized_query and all(term in candidate for term in normalized_query.split()):
            reasons.append("all_terms_match")
        if score <= 0:
            continue
        matches.append(
            {
                "id": slug,
                "name": name,
                "type_name": SEARCH_TYPE_NAME,
                "entity_type": "guide",
                "url": row["url"],
                "ranking": {
                    "score": score,
                    "match_reasons": reasons,
                },
                "metadata": {
                    "slug": slug,
                },
                "follow_up": _guide_follow_up(slug),
            }
        )
    matches.sort(key=lambda row: (-row["ranking"]["score"], row["name"], row["id"]))
    return normalized_query, matches[:limit], len(matches)


def _build_guide_summary(page_payload: dict[str, Any]) -> dict[str, Any]:
    guide = dict(page_payload["guide"])
    page = dict(page_payload["page"])
    navigation = list(page_payload["navigation"])
    article = dict(page_payload["article"])
    linked_entities = list(page_payload["linked_entities"])
    return {
        "guide": guide,
        "page": page,
        "navigation": {
            "count": len(navigation),
            "items": navigation,
        },
        "article": {
            "text": article["text"],
            "headings": article["headings"],
            "section_count": len(article["sections"]),
            "section_preview": [
                {
                    "title": section["title"],
                    "level": section["level"],
                    "ordinal": section["ordinal"],
                }
                for section in article["sections"][:5]
            ],
        },
        "linked_entities": {
            "count": len(linked_entities),
            "items": linked_entities[:10],
            "more_available": len(linked_entities) > 10,
            "fetch_more_command": f"method guide-full {guide['slug']}",
        },
        "citations": {
            "page": guide["page_url"],
        },
    }


def _merge_linked_entities(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, int], dict[str, Any]] = {}
    for page in pages:
        page_url = page["guide"]["page_url"]
        for row in page["linked_entities"]:
            key = (row["type"], row["id"])
            record = merged.get(key)
            if record is None:
                merged[key] = {
                    "type": row["type"],
                    "id": row["id"],
                    "name": row.get("name"),
                    "url": row["url"],
                    "source_urls": [page_url],
                }
                continue
            if not record.get("name") and row.get("name"):
                record["name"] = row["name"]
            if page_url not in record["source_urls"]:
                record["source_urls"].append(page_url)
    return sorted(merged.values(), key=lambda row: (row["type"], row["id"]))


def _fetch_guide_pages(client: MethodClient, guide_ref: str) -> dict[str, Any]:
    initial = client.fetch_guide_page(guide_ref)
    nav_items = initial["navigation"] or [
        {
            "title": initial["guide"]["section_title"],
            "url": initial["guide"]["page_url"],
            "section_slug": initial["guide"]["section_slug"],
            "active": True,
            "ordinal": 1,
        }
    ]
    pages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in nav_items:
        page_url = item["url"]
        if page_url in seen:
            continue
        seen.add(page_url)
        pages.append(client.fetch_guide_page(page_url))
    if initial["guide"]["page_url"] not in seen:
        pages.insert(0, initial)
    guide = dict(initial["guide"])
    guide["page_count"] = len(pages)
    linked_entities = _merge_linked_entities(pages)
    return {
        "guide": guide,
        "page": dict(initial["page"]),
        "navigation": {
            "count": len(nav_items),
            "items": nav_items,
        },
        "pages": [
            {
                "guide": page["guide"],
                "page": page["page"],
                "article": page["article"],
            }
            for page in pages
        ],
        "linked_entities": {
            "count": len(linked_entities),
            "items": linked_entities,
        },
        "citations": {
            "page": guide["page_url"],
            "pages": [page["guide"]["page_url"] for page in pages],
        },
    }


def _default_export_dir(guide_slug: str) -> Path:
    return DEFAULT_EXPORT_ROOT / f"guide-{guide_slug}"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
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


def _write_bundle(full_payload: dict[str, Any], *, export_dir: Path) -> dict[str, Any]:
    guide = dict(full_payload["guide"])
    navigation = list(full_payload["navigation"]["items"])
    pages = list(full_payload["pages"])
    linked_entities = list(full_payload["linked_entities"]["items"])
    sections: list[dict[str, Any]] = []
    page_rows: list[dict[str, Any]] = []
    page_files: list[dict[str, Any]] = []
    html_dir = export_dir / "pages"
    for page in pages:
        page_guide = dict(page["guide"])
        page_meta = dict(page["page"])
        article = dict(page["article"])
        page_slug = page_guide["section_slug"]
        html_path = html_dir / f"{page_slug}.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(article["html"], encoding="utf-8")
        page_files.append(
            {
                "section_slug": page_slug,
                "path": str(html_path.relative_to(export_dir)),
                "page_url": page_guide["page_url"],
            }
        )
        page_rows.append(
            {
                "section_slug": page_slug,
                "section_title": page_guide["section_title"],
                "page_url": page_guide["page_url"],
                "title": page_meta["title"],
                "description": page_meta["description"],
                "text": article["text"],
                "heading_count": len(article["headings"]),
            }
        )
        for section in article["sections"]:
            sections.append(
                {
                    "page_url": page_guide["page_url"],
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
        "provider": "method",
        "output_dir": str(export_dir),
        "guide": guide,
        "counts": {
            "pages": len(page_rows),
            "sections": len(sections),
            "navigation_links": len(navigation),
            "linked_entities": len(linked_entities),
        },
        "files": {
            "guide_json": "guide.json",
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


def _load_bundle(export_dir: Path) -> dict[str, Any]:
    manifest = _load_json(export_dir / "manifest.json")
    files = manifest.get("files") or {}
    return {
        "manifest": manifest,
        "pages": _load_jsonl(export_dir / files.get("pages_jsonl", "pages.jsonl")),
        "sections": _load_jsonl(export_dir / files.get("sections_jsonl", "sections.jsonl")),
        "navigation": _load_jsonl(export_dir / files.get("navigation_links_jsonl", "navigation-links.jsonl")),
        "linked_entities": _load_jsonl(export_dir / files.get("linked_entities_jsonl", "linked-entities.jsonl")),
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


def _query_bundle(
    bundle: dict[str, Any],
    *,
    query: str,
    limit: int,
    kinds: set[str],
    section_title_filter: str | None,
) -> dict[str, Any]:
    normalized_query = query.lower().strip()
    results_by_kind: dict[str, list[dict[str, Any]]] = {"sections": [], "navigation": [], "linked_entities": []}
    if "sections" in kinds:
        for row in bundle["sections"]:
            title = str(row.get("title") or "")
            if section_title_filter and section_title_filter not in title.lower():
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


@app.callback()
def main_callback(
    ctx: typer.Context,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    ctx.obj = RuntimeConfig(pretty=pretty)


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    try:
        settings, sitemap_ttl, page_ttl = load_method_cache_settings_from_env()
    except ValueError as exc:
        _fail(ctx, "invalid_cache_config", str(exc))
        return
    _emit(
        ctx,
        {
            "provider": "method",
            "status": "ready",
            "command": "doctor",
            "installed": True,
            "language": "python",
            "capabilities": {
                "search": "ready",
                "resolve": "ready",
                "guide": "ready",
                "guide_full": "ready",
                "guide_export": "ready",
                "guide_query": "ready",
            },
            "cache": {
                "enabled": settings.enabled,
                "backend": settings.backend,
                "cache_dir": str(settings.cache_dir),
                "redis_url": settings.redis_url,
                "prefix": settings.prefix,
                "ttls": {
                    "sitemap": sitemap_ttl,
                    "page_html": page_ttl,
                },
            },
        },
    )


@app.command("search")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Query text to match against Method guide slugs."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum results to return."),
) -> None:
    with _client(ctx) as client:
        normalized_query, results, total_count = _search_results(client, query, limit=limit)
    _emit(
        ctx,
        {
            "query": query,
            "search_query": normalized_query,
            "count": total_count,
            "results": results,
        },
    )


@app.command("resolve")
def resolve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Resolve a free-text query to the best Method guide match."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum candidates to inspect."),
) -> None:
    with _client(ctx) as client:
        normalized_query, results, total_count = _search_results(client, query, limit=limit)
    top = results[0] if results else None
    second = results[1] if len(results) > 1 else None
    top_score = top["ranking"]["score"] if top else 0
    second_score = second["ranking"]["score"] if second else 0
    resolved = top is not None and (top_score >= 50 or top_score >= second_score + 15)
    _emit(
        ctx,
        {
            "query": query,
            "search_query": normalized_query,
            "resolved": resolved,
            "confidence": "high" if resolved else ("medium" if top else "none"),
            "match": top if top else None,
            "next_command": top["follow_up"]["recommended_command"] if resolved and top else None,
            "fallback_search_command": None if resolved else f"method search {json.dumps(query)}",
            "count": total_count,
            "candidates": results,
        },
    )


@app.command("guide")
def guide(ctx: typer.Context, guide_ref: str = typer.Argument(..., help="Guide slug or Method.gg guide URL.")) -> None:
    with _client(ctx) as client:
        payload = _build_guide_summary(client.fetch_guide_page(guide_ref))
    _emit(ctx, payload)


@app.command("guide-full")
def guide_full(ctx: typer.Context, guide_ref: str = typer.Argument(..., help="Guide slug or Method.gg guide URL.")) -> None:
    with _client(ctx) as client:
        payload = _fetch_guide_pages(client, guide_ref)
    _emit(ctx, payload)


@app.command("guide-export")
def guide_export(
    ctx: typer.Context,
    guide_ref: str = typer.Argument(..., help="Guide slug or Method.gg guide URL."),
    out: Path | None = typer.Option(None, "--out", help="Output directory. Defaults to ./method_exports/guide-<slug>."),
) -> None:
    slug, _section_slug = guide_ref_parts(guide_ref)
    export_dir = out.expanduser() if out is not None else _default_export_dir(slug)
    with _client(ctx) as client:
        payload = _fetch_guide_pages(client, guide_ref)
    manifest = _write_bundle(payload, export_dir=export_dir)
    _emit(
        ctx,
        {
            "guide": payload["guide"],
            "counts": manifest["counts"],
            "output_dir": str(export_dir),
            "manifest": manifest,
        },
    )


@app.command("guide-query")
def guide_query(
    ctx: typer.Context,
    bundle_ref: str = typer.Argument(..., help="Exported bundle directory."),
    query: str = typer.Argument(..., help="Query text to search within the exported Method bundle."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum matches to return."),
    kind: list[str] = typer.Option(
        [],
        "--kind",
        help="Restrict search kinds. Repeat or pass comma-separated values from: sections, navigation, linked_entities.",
    ),
    section_title: str | None = typer.Option(
        None,
        "--section-title",
        help="Restrict section searching to section titles containing this text.",
    ),
) -> None:
    export_dir = Path(bundle_ref).expanduser()
    if not export_dir.exists():
        _fail(ctx, "invalid_bundle", f"Bundle directory not found: {export_dir}")
    bundle = _load_bundle(export_dir)
    selected_kinds = {item.strip() for raw in kind for item in raw.split(",") if item.strip()} or {
        "sections",
        "navigation",
        "linked_entities",
    }
    invalid = sorted(selected_kinds - {"sections", "navigation", "linked_entities"})
    if invalid:
        _fail(ctx, "invalid_kind", f"Unsupported guide-query kinds: {', '.join(invalid)}")
    payload = _query_bundle(
        bundle,
        query=query,
        limit=limit,
        kinds=selected_kinds,
        section_title_filter=section_title.strip().lower() if isinstance(section_title, str) and section_title.strip() else None,
    )
    payload["guide"] = bundle["manifest"]["guide"]
    payload["output_dir"] = str(export_dir)
    _emit(ctx, payload)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
