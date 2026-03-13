from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import httpx
import typer

from icy_veins_cli.client import IcyVeinsClient, guide_ref_parts, load_icy_veins_cache_settings_from_env
from icy_veins_cli.page_parser import classify_guide_slug, guide_traversal_scope
from warcraft_content.article_discovery import (
    article_candidate,
    merge_article_linked_entities,
    sort_article_candidates,
)
from warcraft_content.article_bundle import (
    default_article_export_dir,
    load_article_bundle,
    query_article_bundle,
    write_article_bundle,
)
from warcraft_content.article_provider_cli import (
    build_article_resolve_response,
    build_article_search_response,
    fail_with_error,
)
from warcraft_core.output import emit

app = typer.Typer(add_completion=False, help="Icy Veins guide CLI.")

SEARCH_TYPE_NAME = "Guide"
UNSUPPORTED_QUERY_HINTS = {
    "patch_notes": {
        "keywords": {"patch", "notes"},
        "message": "Icy Veins patch-note and news-like WoW pages are currently out of scope for the supported guide surface.",
    },
    "class_changes": {
        "keywords": {"class", "changes"},
        "message": "Icy Veins latest-class-changes style WoW pages are currently out of scope for the supported guide surface.",
    },
    "hotfixes": {
        "keywords": {"hotfix", "hotfixes"},
        "message": "Icy Veins hotfix and news-like WoW pages are currently out of scope for the supported guide surface.",
    },
    "news": {
        "keywords": {"news"},
        "message": "Icy Veins news-like WoW pages are currently out of scope for the supported guide surface.",
    },
}
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
    fail_with_error(lambda payload, err: _emit(ctx, payload, err=err), code=code, message=message, status=status)


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


def _query_terms(query: str) -> set[str]:
    return {term for term in re.split(r"[^a-z0-9+]+", query.lower()) if term}


def _unsupported_scope_hint(query: str) -> dict[str, Any] | None:
    terms = _query_terms(query)
    if not terms:
        return None
    for code, config in UNSUPPORTED_QUERY_HINTS.items():
        keywords = set(config["keywords"])
        if keywords <= terms:
            return {
                "code": code,
                "message": config["message"],
            }
    return None


def _score_family_match(query: str, *, content_family: str | None) -> tuple[int, list[str]]:
    if not query or not content_family:
        return 0, []
    score = 0
    reasons: list[str] = []
    terms = _query_terms(query)
    joined = f" {query.lower()} "
    specialized_terms = {
        "easy",
        "mode",
        "leveling",
        "pvp",
        "build",
        "builds",
        "talent",
        "talents",
        "rotation",
        "cooldown",
        "cooldowns",
        "abilities",
        "stats",
        "gems",
        "enchants",
        "consumables",
        "gear",
        "bis",
        "resources",
        "mythic+",
        "mythic",
        "plus",
        "macros",
        "addons",
        "ui",
        "simulation",
        "simulations",
        "sim",
        "raid",
        "remix",
        "torghast",
        "expansion",
        "midnight",
    }
    if content_family == "class_hub" and len(terms) == 1 and not (terms & specialized_terms):
        score += 18
        reasons.append("family_class_hub")
    if content_family == "role_guide" and len(terms) == 1 and ({"healing", "tank", "dps"} & terms):
        score += 18
        reasons.append("family_role_guide")
    if "easy" in terms and "mode" in terms and content_family == "easy_mode":
        score += 28
        reasons.append("family_easy_mode")
    if "leveling" in terms and content_family == "leveling":
        score += 24
        reasons.append("family_leveling")
    if "pvp" in terms and content_family == "pvp":
        score += 24
        reasons.append("family_pvp")
    if content_family == "spec_builds_talents" and ({"build", "builds", "talent", "talents"} & terms):
        score += 24
        reasons.append("family_builds_talents")
    if content_family == "rotation_guide" and ({"rotation", "cooldown", "cooldowns", "abilities"} & terms):
        score += 24
        reasons.append("family_rotation")
    if content_family == "stat_priority" and (" stat priority " in joined or " stats " in joined):
        score += 24
        reasons.append("family_stat_priority")
    if content_family == "gems_enchants_consumables" and ({"gems", "enchants", "consumables"} & terms):
        score += 24
        reasons.append("family_gems_enchants")
    if content_family == "gear_best_in_slot" and ({"gear", "bis"} & terms or " best in slot " in joined):
        score += 24
        reasons.append("family_gear")
    if content_family == "spell_summary" and (" spell summary " in joined or " spell list " in joined or " glossary " in joined):
        score += 24
        reasons.append("family_spell_summary")
    if content_family == "resources" and "resources" in terms:
        score += 18
        reasons.append("family_resources")
    if content_family == "mythic_plus_tips" and ("mythic+" in joined or " mythic plus " in joined):
        score += 18
        reasons.append("family_mythic_plus")
    if content_family == "macros_addons" and ({"macros", "addons", "ui"} & terms or "add-ons" in query.lower()):
        score += 18
        reasons.append("family_macros_addons")
    if content_family == "simulations" and ({"simulation", "simulations", "sim"} & terms):
        score += 18
        reasons.append("family_simulations")
    if content_family == "raid_guide" and "raid" in terms:
        score += 18
        reasons.append("family_raid_guide")
    if content_family == "expansion_guide" and (" war within " in joined or " midnight " in joined or " expansion " in terms):
        score += 18
        reasons.append("family_expansion_guide")
    if content_family == "special_event_guide" and ({"remix", "torghast"} & terms):
        score += 18
        reasons.append("family_special_event")
    if content_family in {"class_hub", "role_guide"} and (terms & specialized_terms):
        score -= 14
        reasons.append("penalty_broad_hub")
    if content_family == "raid_guide" and "raid" not in terms:
        score -= 12
        reasons.append("penalty_raid_variant")
    if content_family in {"expansion_guide", "special_event_guide"} and not (
        {"remix", "torghast", "midnight", "expansion"} & terms or " war within " in joined
    ):
        score -= 10
        reasons.append("penalty_specialized_variant")
    return score, reasons


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

def _search_results(client: IcyVeinsClient, query: str, *, limit: int) -> tuple[str, list[dict[str, Any]], int, dict[str, Any] | None]:
    normalized_query = _normalize_query(query)
    scope_hint = _unsupported_scope_hint(normalized_query)
    if scope_hint is not None:
        return normalized_query, [], 0, scope_hint
    matches: list[dict[str, Any]] = []
    for row in client.sitemap_guides():
        slug = row["slug"]
        name = row["name"]
        content_family = row.get("content_family")
        candidate = f"{name.lower()} {slug.replace('-', ' ')}"
        score, reasons = _score_text_match(normalized_query, candidate, slug=slug)
        family_score, family_reasons = _score_family_match(normalized_query, content_family=content_family)
        score += family_score
        reasons.extend(family_reasons)
        if normalized_query and reasons and set(reasons) <= {"intro_guide", "specialized_guide"}:
            continue
        if score <= 0:
            continue
        candidate_row = article_candidate(
            ref=slug,
            name=name,
            url=row["url"],
            score=score,
            reasons=reasons,
            provider_command="icy-veins",
        )
        candidate_row["metadata"]["content_family"] = content_family
        matches.append(candidate_row)
    sort_article_candidates(matches)
    return normalized_query, matches[:limit], len(matches), None


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


def _guide_ref_slug(guide_ref: str) -> str:
    return guide_ref_parts(guide_ref)


def _ensure_supported_guide_ref(ctx: typer.Context, guide_ref: str) -> tuple[str, str]:
    try:
        slug = _guide_ref_slug(guide_ref)
    except ValueError as exc:
        _fail(ctx, "invalid_guide_ref", str(exc))
        raise AssertionError("unreachable")
    content_family = classify_guide_slug(slug)
    if content_family is None:
        _fail(ctx, "invalid_guide_ref", f"Unsupported Icy Veins guide reference: {guide_ref}")
        raise AssertionError("unreachable")
    return slug, content_family


def _fetch_supported_guide_page(ctx: typer.Context, client: IcyVeinsClient, guide_ref: str) -> dict[str, Any]:
    _ensure_supported_guide_ref(ctx, guide_ref)
    try:
        return client.fetch_guide_page(guide_ref)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            _fail(ctx, "invalid_guide_ref", f"Guide not found: {guide_ref}")
        _fail(ctx, "upstream_fetch_failed", f"Icy Veins request failed with status {exc.response.status_code}")
        raise AssertionError("unreachable")


def _fetch_guide_pages(client: IcyVeinsClient, guide_ref: str) -> dict[str, Any]:
    initial = client.fetch_guide_page(guide_ref)
    traversal_scope = guide_traversal_scope(initial["guide"].get("content_family"))
    nav_items = initial["navigation"] if traversal_scope == "family_navigation" else []
    nav_items = nav_items or [
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
        normalized_query, results, total_count, scope_hint = _search_results(client, query, limit=limit)
    payload = build_article_search_response(
        query=query,
        search_query=normalized_query,
        results=results,
        total_count=total_count,
        scope_hint=scope_hint,
    )
    _emit(ctx, payload)


@app.command("resolve")
def resolve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Resolve a free-text query to the best Icy Veins guide match."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum candidates to inspect."),
) -> None:
    with _client(ctx) as client:
        normalized_query, results, total_count, scope_hint = _search_results(client, query, limit=limit)
    top = results[0] if results else None
    second = results[1] if len(results) > 1 else None
    top_score = top["ranking"]["score"] if top else 0
    second_score = second["ranking"]["score"] if second else 0
    top_reasons = set(top["ranking"]["match_reasons"]) if top else set()
    resolved = top is not None and (
        top_score >= 50
        or top_score >= second_score + 15
        or ("family_easy_mode" in top_reasons and top_score >= second_score + 10 and top_score >= 35)
        or ("intro_guide" in top_reasons and top_score >= second_score + 6 and top_score >= 30)
    )
    _emit(
        ctx,
        build_article_resolve_response(
            provider_command="icy-veins",
            query=query,
            search_query=normalized_query,
            results=results,
            total_count=total_count,
            resolved=resolved,
            scope_hint=scope_hint,
        ),
    )


@app.command("guide")
def guide(ctx: typer.Context, guide_ref: str = typer.Argument(..., help="Guide slug or Icy Veins guide URL.")) -> None:
    with _client(ctx) as client:
        payload = _build_guide_summary(_fetch_supported_guide_page(ctx, client, guide_ref))
    _emit(ctx, payload)


@app.command("guide-full")
def guide_full(ctx: typer.Context, guide_ref: str = typer.Argument(..., help="Guide slug or Icy Veins guide URL.")) -> None:
    _ensure_supported_guide_ref(ctx, guide_ref)
    with _client(ctx) as client:
        try:
            payload = _fetch_guide_pages(client, guide_ref)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                _fail(ctx, "invalid_guide_ref", f"Guide not found: {guide_ref}")
            _fail(ctx, "upstream_fetch_failed", f"Icy Veins request failed with status {exc.response.status_code}")
            raise AssertionError("unreachable")
    _emit(ctx, payload)


@app.command("guide-export")
def guide_export(
    ctx: typer.Context,
    guide_ref: str = typer.Argument(..., help="Guide slug or Icy Veins guide URL."),
    out: Path | None = typer.Option(None, "--out", help="Output directory. Defaults to ./icy-veins_exports/guide-<slug>."),
) -> None:
    slug, _ = _ensure_supported_guide_ref(ctx, guide_ref)
    export_dir = out.expanduser() if out is not None else _default_export_dir(slug)
    with _client(ctx) as client:
        try:
            payload = _fetch_guide_pages(client, guide_ref)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                _fail(ctx, "invalid_guide_ref", f"Guide not found: {guide_ref}")
            _fail(ctx, "upstream_fetch_failed", f"Icy Veins request failed with status {exc.response.status_code}")
            raise AssertionError("unreachable")
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
