from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import typer

from icy_veins_cli.client import IcyVeinsClient, guide_ref_parts, load_icy_veins_cache_settings_from_env
from warcraft_content.article_discovery import (
    article_candidate,
    article_resolve_payload,
    article_search_payload,
    merge_article_linked_entities,
    sort_article_candidates,
)
from warcraft_content.article_bundle import (
    default_article_export_dir,
    load_article_bundle,
    query_article_bundle,
    write_article_bundle,
)
from warcraft_core.output import emit

app = typer.Typer(add_completion=False, help="Icy Veins guide CLI.")

SEARCH_TYPE_NAME = "Guide"
NEUTRAL_SLUG_TERMS = {
    "guide",
    "guides",
    "mistweaver",
    "monk",
    "pve",
    "pvp",
    "healing",
    "tank",
    "dps",
}


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


def _client(ctx: typer.Context) -> IcyVeinsClient:
    try:
        return IcyVeinsClient()
    except ValueError as exc:
        _fail(ctx, "invalid_cache_config", str(exc))
        raise AssertionError("unreachable")


def _normalize_query(query: str) -> str:
    normalized = re.sub(r"\b(icy|veins|guide|guides)\b", " ", query.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or query.strip().lower()


def _score_text_match(query: str, candidate: str, *, slug: str) -> tuple[int, list[str]]:
    if not query or not candidate:
        return 0, []
    score = 0
    reasons: list[str] = []
    if candidate == query:
        score += 40
        reasons.append("exact_name")
    if candidate.startswith(query):
        score += 15
        reasons.append("name_prefix")
    if query in candidate:
        score += 10
        reasons.append("name_contains_query")
    query_terms = [term for term in query.split() if term]
    if query_terms and all(term in candidate for term in query_terms):
        score += 16
        reasons.append("all_terms_match")
    if slug.endswith("-guide"):
        if any(token in slug for token in ("leveling", "dps", "pvp")):
            score += 2
            reasons.append("specialized_guide")
        else:
            score += 16
            reasons.append("intro_guide")
    slug_terms = [term for term in slug.split("-") if term]
    penalty_terms = [
        term
        for term in slug_terms
        if term not in query_terms and term not in NEUTRAL_SLUG_TERMS
    ]
    if penalty_terms:
        score -= len(penalty_terms) * 3
    return score, reasons

def _search_results(client: IcyVeinsClient, query: str, *, limit: int) -> tuple[str, list[dict[str, Any]], int]:
    normalized_query = _normalize_query(query)
    matches: list[dict[str, Any]] = []
    for row in client.sitemap_guides():
        slug = row["slug"]
        name = row["name"]
        candidate = f"{name.lower()} {slug.replace('-', ' ')}"
        score, reasons = _score_text_match(normalized_query, candidate, slug=slug)
        if score <= 0:
            continue
        matches.append(
            article_candidate(
                slug=slug,
                name=name,
                url=row["url"],
                score=score,
                reasons=reasons,
                provider_command="icy-veins",
            )
        )
    sort_article_candidates(matches)
    return normalized_query, matches[:limit], len(matches)


def _build_guide_summary(page_payload: dict[str, Any]) -> dict[str, Any]:
    guide = dict(page_payload["guide"])
    page = dict(page_payload["page"])
    navigation = list(page_payload["navigation"])
    page_toc = list(page_payload["page_toc"])
    article = dict(page_payload["article"])
    linked_entities = list(page_payload["linked_entities"])
    citations = dict(page_payload.get("citations") or {})
    return {
        "guide": guide,
        "page": page,
        "navigation": {
            "count": len(navigation),
            "items": navigation,
        },
        "page_toc": {
            "count": len(page_toc),
            "items": page_toc,
        },
        "article": {
            "intro_text": article.get("intro_text") or "",
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
            "fetch_more_command": f"icy-veins guide-full {guide['slug']}",
        },
        "citations": citations,
    }

def _fetch_guide_pages(client: IcyVeinsClient, guide_ref: str) -> dict[str, Any]:
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
    linked_entities = merge_article_linked_entities(pages)
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
                "page_toc": page["page_toc"],
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
            "comments": (initial.get("citations") or {}).get("comments"),
            "pages": [page["guide"]["page_url"] for page in pages],
        },
    }


def _default_export_dir(guide_slug: str) -> Path:
    return default_article_export_dir("icy-veins", guide_slug)


@app.callback()
def main_callback(
    ctx: typer.Context,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    ctx.obj = RuntimeConfig(pretty=pretty)


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    try:
        settings, sitemap_ttl, page_ttl = load_icy_veins_cache_settings_from_env()
    except ValueError as exc:
        _fail(ctx, "invalid_cache_config", str(exc))
        return
    _emit(
        ctx,
        {
            "provider": "icy-veins",
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
    query: str = typer.Argument(..., help="Query text to match against Icy Veins WoW guide slugs."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum results to return."),
) -> None:
    with _client(ctx) as client:
        normalized_query, results, total_count = _search_results(client, query, limit=limit)
    _emit(ctx, article_search_payload(query=query, search_query=normalized_query, results=results, total_count=total_count))


@app.command("resolve")
def resolve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Resolve a free-text query to the best Icy Veins guide match."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum candidates to inspect."),
) -> None:
    with _client(ctx) as client:
        normalized_query, results, total_count = _search_results(client, query, limit=limit)
    top = results[0] if results else None
    second = results[1] if len(results) > 1 else None
    top_score = top["ranking"]["score"] if top else 0
    second_score = second["ranking"]["score"] if second else 0
    top_reasons = set(top["ranking"]["match_reasons"]) if top else set()
    resolved = top is not None and (
        top_score >= 50
        or top_score >= second_score + 15
        or ("intro_guide" in top_reasons and top_score >= second_score + 6 and top_score >= 30)
    )
    _emit(
        ctx,
        article_resolve_payload(
            provider_command="icy-veins",
            query=query,
            search_query=normalized_query,
            results=results,
            total_count=total_count,
            resolved=resolved,
        ),
    )


@app.command("guide")
def guide(ctx: typer.Context, guide_ref: str = typer.Argument(..., help="Guide slug or Icy Veins guide URL.")) -> None:
    with _client(ctx) as client:
        payload = _build_guide_summary(client.fetch_guide_page(guide_ref))
    _emit(ctx, payload)


@app.command("guide-full")
def guide_full(ctx: typer.Context, guide_ref: str = typer.Argument(..., help="Guide slug or Icy Veins guide URL.")) -> None:
    with _client(ctx) as client:
        payload = _fetch_guide_pages(client, guide_ref)
    _emit(ctx, payload)


@app.command("guide-export")
def guide_export(
    ctx: typer.Context,
    guide_ref: str = typer.Argument(..., help="Guide slug or Icy Veins guide URL."),
    out: Path | None = typer.Option(None, "--out", help="Output directory. Defaults to ./icy-veins_exports/guide-<slug>."),
) -> None:
    slug = guide_ref_parts(guide_ref)
    export_dir = out.expanduser() if out is not None else _default_export_dir(slug)
    with _client(ctx) as client:
        payload = _fetch_guide_pages(client, guide_ref)
    manifest = write_article_bundle(payload, provider="icy-veins", export_dir=export_dir)
    _emit(
        ctx,
        {
            "provider": "icy-veins",
            "guide": payload["guide"],
            "output_dir": str(export_dir),
            "counts": manifest["counts"],
            "files": manifest["files"],
        },
    )


@app.command("guide-query")
def guide_query(
    ctx: typer.Context,
    bundle: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=False),
    query: str = typer.Argument(..., help="Query text to match against the exported article bundle."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum matches to return per kind."),
    kind: list[str] | None = typer.Option(
        None,
        "--kind",
        help="Kinds to search. Repeat for multiple values. Defaults to sections,navigation,linked_entities.",
    ),
    section_title: str | None = typer.Option(None, "--section-title", help="Restrict section matches to a title substring."),
) -> None:
    selected_kinds = set(kind or ["sections", "navigation", "linked_entities"])
    allowed_kinds = {"sections", "navigation", "linked_entities"}
    invalid = sorted(selected_kinds - allowed_kinds)
    if invalid:
        _fail(ctx, "invalid_query_kind", f"Unsupported query kinds: {', '.join(invalid)}")
    bundle_payload = load_article_bundle(bundle.expanduser())
    result = query_article_bundle(
        bundle_payload,
        query=query,
        limit=limit,
        kinds=selected_kinds,
        section_title_filter=section_title.lower() if section_title else None,
    )
    _emit(
        ctx,
        {
            "provider": "icy-veins",
            "bundle": str(bundle),
            **result,
        },
    )


def run() -> None:
    app()


if __name__ == "__main__":
    run()
