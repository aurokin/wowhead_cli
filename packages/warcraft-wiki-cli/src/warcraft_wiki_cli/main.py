from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import httpx
import typer

from warcraft_content.article_bundle import (
    default_article_export_dir,
    load_article_bundle,
    query_article_bundle,
    write_article_bundle,
)
from warcraft_content.article_discovery import (
    article_candidate,
    article_resolve_payload,
    article_search_payload,
)
from warcraft_core.output import emit
from warcraft_wiki_cli.client import WarcraftWikiAPIError, WarcraftWikiClient, load_warcraft_wiki_cache_settings_from_env
from warcraft_wiki_cli.page_parser import article_slug, classify_article_family, normalize_article_ref

app = typer.Typer(add_completion=False, help="Warcraft Wiki reference CLI.")

API_REFERENCE_FAMILIES = {"api_function", "framework_page", "xml_schema", "cvar", "api_changes"}
EVENT_REFERENCE_FAMILIES = {"ui_handler", "framework_page"}

QUERY_FAMILY_HINT_TERMS = {
    "article",
    "articles",
    "faction",
    "factions",
    "guide",
    "guides",
    "lore",
    "reference",
    "references",
    "story",
    "stories",
    "tutorial",
    "tutorials",
}
CONDITIONAL_FAMILY_HINT_TERMS = {"zone", "zones", "class", "classes", "profession", "professions", "expansion", "expansions"}


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


def _client(ctx: typer.Context) -> WarcraftWikiClient:
    try:
        return WarcraftWikiClient()
    except ValueError as exc:
        _fail(ctx, "invalid_cache_config", str(exc))
        raise AssertionError("unreachable")


def _handle_api_error(ctx: typer.Context, exc: WarcraftWikiAPIError) -> None:
    status = 1
    code = exc.code
    if code == "missingtitle":
        code = "not_found"
    _fail(ctx, code, exc.message, status=status)


def _normalize_query(query: str) -> tuple[str, list[str]]:
    lowered = query.lower()
    base = re.sub(r"\bwiki\b", " ", lowered)
    tokens = [token for token in re.split(r"\s+", base) if token]
    excluded_terms: list[str] = []
    kept_terms = list(tokens)
    while kept_terms:
        head = kept_terms[0]
        if head in QUERY_FAMILY_HINT_TERMS:
            excluded_terms.append(kept_terms.pop(0))
            continue
        if head in CONDITIONAL_FAMILY_HINT_TERMS and len(kept_terms) >= 2 and not (head in {"zone", "zones"} and kept_terms[1] == "scaling"):
            excluded_terms.append(kept_terms.pop(0))
            continue
        break
    normalized = " ".join(kept_terms).strip()
    if not normalized:
        normalized = re.sub(r"\s+", " ", base).strip() or query.strip().lower()
        excluded_terms = []
    return normalized, excluded_terms


def _collapsed_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _query_intents(query: str) -> set[str]:
    lowered = query.lower()
    intents: set[str] = set()
    if any(token in lowered for token in ("api", "function", "widget", "framexml", "lua", "cvar", "xml", "handler", "event", "addon")):
        intents.add("programming")
    if any(token in lowered for token in ("patch", "changes", "hotfix")):
        intents.add("patch")
    if any(token in lowered for token in ("zone", "zones", "renown", "housing", "profession", "expansion", "faction")):
        intents.add("systems")
    if any(token in lowered for token in ("lore", "story", "character", "characters")):
        intents.add("lore")
    return intents


def _score_text_match(original_query: str, query: str, title: str, snippet: str, *, ordinal: int) -> tuple[int, list[str], str]:
    haystack = f"{title.lower()} {snippet.lower()}".strip()
    family = classify_article_family(title)
    score = max(0, 40 - ordinal * 2)
    reasons: list[str] = []
    intents = _query_intents(original_query)
    normalized_query = _collapsed_text(query)
    normalized_title = _collapsed_text(title)
    if title.lower() == query:
        score += 50
        reasons.append("exact_title")
    if family == "api_function" and normalized_title == f"api{normalized_query}":
        score += 40
        reasons.append("exact_api_title")
    if family == "ui_handler" and normalized_title == f"uihandler{normalized_query}":
        score += 40
        reasons.append("exact_handler_title")
    if title.lower().startswith(query):
        score += 20
        reasons.append("title_prefix")
    if query in title.lower():
        score += 12
        reasons.append("title_contains_query")
    if normalized_query and normalized_query in normalized_title:
        score += 10
        reasons.append("normalized_title_match")
    terms = [term for term in query.split() if term]
    if terms and all(term in haystack for term in terms):
        score += 10
        reasons.append("all_terms_match")
    if terms and all(term in title.lower() for term in terms) and family in {"howto_programming", "guide_reference"}:
        score += 36
        reasons.append("guide_title_terms")
    if snippet and any(term in snippet.lower() for term in terms):
        score += 4
        reasons.append("snippet_match")
    if "programming" in intents and family in {"api_function", "ui_handler", "framework_page", "xml_schema", "cvar", "api_changes", "howto_programming"}:
        score += 20
        reasons.append("intent_programming")
    if "systems" in intents and family in {"system_reference", "expansion_reference", "profession_reference", "class_reference", "faction_reference", "zone_reference"}:
        score += 18
        reasons.append("intent_systems")
    if "patch" in intents and family in {"patch_reference", "api_changes"}:
        score += 18
        reasons.append("intent_patch")
    if "lore" in intents and family == "lore_reference":
        score += 16
        reasons.append("intent_lore")
    if family == "api_function":
        score += 8
        reasons.append("family_api_function")
    elif family == "ui_handler":
        score += 8
        reasons.append("family_ui_handler")
    elif family in {
        "framework_page",
        "system_reference",
        "expansion_reference",
        "profession_reference",
        "class_reference",
        "zone_reference",
        "patch_reference",
    }:
        score += 4
        reasons.append(f"family_{family}")
    if family == "expansion_reference" and title.lower().startswith("world of warcraft:"):
        suffix = title.lower().split(":", 1)[1].strip()
        if query == suffix:
            score += 24
            reasons.append("expansion_alias_match")
    return score, reasons, family


def _search_results(client: WarcraftWikiClient, query: str, *, limit: int) -> tuple[str, list[str], list[dict[str, Any]], int]:
    normalized_query, excluded_terms = _normalize_query(query)
    fetch_limit = max(limit * 5, 25)
    total_count, rows = client.search_articles(normalized_query, limit=fetch_limit)
    matches: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        title = row["title"]
        score, reasons, family = _score_text_match(query, normalized_query, title, row.get("snippet") or "", ordinal=index)
        if score <= 0:
            continue
        matches.append(
            article_candidate(
                ref=title,
                name=title,
                url=row["url"],
                score=score,
                reasons=reasons,
                provider_command="warcraft-wiki",
                surface="article",
                type_name="Article",
                entity_type="article",
                metadata_key="title",
                metadata={"title": title, "content_family": family},
            )
        )
    matches.sort(key=lambda row: (-int(row["ranking"]["score"]), row["name"], row["id"]))
    return normalized_query, excluded_terms, matches[:limit], total_count


def _build_article_summary(page_payload: dict[str, Any]) -> dict[str, Any]:
    article = dict(page_payload["article"])
    page = dict(page_payload["page"])
    navigation = list((page_payload.get("navigation") or {}).get("items") or [])
    content = dict(page_payload["article_content"])
    reference = dict(page_payload.get("reference") or {})
    linked_entities = list(page_payload["linked_entities"])
    return {
        "article": article,
        "page": page,
        "reference": reference,
        "navigation": {
            "count": len(navigation),
            "items": navigation[:25],
        },
        "content": {
            "text": content["text"],
            "headings": content["headings"],
            "section_count": len(content["sections"]),
            "section_preview": [
                {
                    "title": section["title"],
                    "level": section["level"],
                    "ordinal": section["ordinal"],
                }
                for section in content["sections"][:10]
            ],
        },
        "linked_entities": {
            "count": len(linked_entities),
            "items": linked_entities[:10],
            "more_available": len(linked_entities) > 10,
            "fetch_more_command": f"warcraft-wiki article-full {article['title']!r}",
        },
        "citations": {
            "page": article["page_url"],
        },
    }


def _fetch_article_payload(client: WarcraftWikiClient, article_ref: str) -> dict[str, Any]:
    initial = client.fetch_article_page(article_ref)
    return _article_payload_from_initial(initial)


def _article_payload_from_initial(initial: dict[str, Any]) -> dict[str, Any]:
    article = dict(initial["article"])
    article["page_count"] = 1
    return {
        "article": article,
        "page": dict(initial["page"]),
        "reference": dict(initial.get("reference") or {}),
        "navigation": dict(initial["navigation"]),
        "pages": [
            {
                "article_meta": dict(initial["article"]),
                "page": dict(initial["page"]),
                "reference": dict(initial.get("reference") or {}),
                "article": dict(initial["article_content"]),
            }
        ],
        "linked_entities": {
            "count": len(initial["linked_entities"]),
            "items": list(initial["linked_entities"]),
        },
        "citations": dict(initial["citations"]),
    }


def _typed_search_queries(query: str, *, surface: str) -> list[str]:
    normalized = normalize_article_ref(query)
    candidates = [normalized]
    lowered = normalized.lower()
    if surface == "api":
        if not lowered.startswith("api "):
            candidates.append(f"API {normalized}")
    elif surface == "event":
        if not lowered.startswith("uihandler "):
            candidates.append(f"UIHANDLER {normalized}")
        if lowered != "events":
            candidates.append(f"event {normalized}")
    ordered: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        value = candidate.strip()
        if value and value.lower() not in seen:
            ordered.append(value)
            seen.add(value.lower())
    return ordered


def _typed_article_payload(
    client: WarcraftWikiClient,
    query: str,
    *,
    surface: str,
    full: bool,
    limit: int = 10,
) -> dict[str, Any]:
    allowed_families = API_REFERENCE_FAMILIES if surface == "api" else EVENT_REFERENCE_FAMILIES
    direct_refs = _typed_search_queries(query, surface=surface)
    for candidate_ref in direct_refs:
        try:
            initial = client.fetch_article_page(candidate_ref)
        except WarcraftWikiAPIError:
            continue
        if initial["article"]["content_family"] in allowed_families:
            payload = _article_payload_from_initial(initial)
            result = payload if full else _build_article_summary(initial)
            result["query"] = query
            result["search_queries"] = direct_refs
            result["resolved_from"] = "direct_fetch"
            result["resolved_surface"] = surface
            return result

    ranked: dict[str, dict[str, Any]] = {}
    query_trace: list[str] = []
    total_count = 0
    for search_query in _typed_search_queries(query, surface=surface):
        normalized_query, _excluded_terms, rows, total_count_part = _search_results(client, search_query, limit=limit)
        query_trace.append(normalized_query)
        total_count = max(total_count, total_count_part)
        for row in rows:
            family = str((row.get("metadata") or {}).get("content_family") or "")
            if family not in allowed_families:
                continue
            existing = ranked.get(row["id"])
            if existing is None or int(row["ranking"]["score"]) > int(existing["ranking"]["score"]):
                ranked[row["id"]] = row

    results = sorted(ranked.values(), key=lambda row: (-int(row["ranking"]["score"]), row["name"], row["id"]))[:limit]
    top = results[0] if results else None
    second = results[1] if len(results) > 1 else None
    top_score = int((top or {}).get("ranking", {}).get("score") or 0)
    second_score = int((second or {}).get("ranking", {}).get("score") or 0)
    resolved = top is not None and (top_score >= 70 or top_score >= second_score + 18)
    if not resolved or top is None:
        raise WarcraftWikiAPIError(
            f"invalid_{surface}_ref",
            f"Unable to resolve {surface} reference from query: {query}",
        )

    initial = client.fetch_article_page(str(top["id"]))
    if initial["article"]["content_family"] not in allowed_families:
        raise WarcraftWikiAPIError(
            f"invalid_{surface}_ref",
            f"Resolved article is not a supported {surface} reference: {initial['article']['title']}",
        )
    payload = _article_payload_from_initial(initial)
    result = payload if full else _build_article_summary(initial)
    result["query"] = query
    result["search_queries"] = query_trace
    result["resolved_from"] = "search"
    result["resolved_surface"] = surface
    result["resolution"] = {
        "resolved": True,
        "match": top,
        "candidates": results,
        "count": total_count,
    }
    return result


def _default_export_dir(article_title: str) -> Path:
    return default_article_export_dir("warcraft-wiki", article_slug(article_title), prefix="article")


@app.callback()
def main_callback(
    ctx: typer.Context,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    ctx.obj = RuntimeConfig(pretty=pretty)


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    try:
        settings, search_ttl, page_ttl = load_warcraft_wiki_cache_settings_from_env()
    except ValueError as exc:
        _fail(ctx, "invalid_cache_config", str(exc))
        return
    _emit(
        ctx,
        {
            "provider": "warcraft-wiki",
            "status": "ready",
            "command": "doctor",
            "installed": True,
            "language": "python",
            "capabilities": {
                "search": "ready",
                "resolve": "ready",
                "article": "ready",
                "article_full": "ready",
                "api": "ready",
                "api_full": "ready",
                "event": "ready",
                "event_full": "ready",
                "article_export": "ready",
                "article_query": "ready",
            },
            "cache": {
                "enabled": settings.enabled,
                "backend": settings.backend,
                "cache_dir": str(settings.cache_dir),
                "redis_url": settings.redis_url,
                "prefix": settings.prefix,
                "ttls": {
                    "search": search_ttl,
                    "page_html": page_ttl,
                },
            },
        },
    )


@app.command("search")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Query text to match against Warcraft Wiki article titles."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum results to return."),
) -> None:
    with _client(ctx) as client:
        normalized_query, excluded_terms, results, total_count = _search_results(client, query, limit=limit)
    payload = article_search_payload(query=query, search_query=normalized_query, results=results, total_count=total_count)
    if excluded_terms:
        payload["excluded_terms"] = excluded_terms
        payload["normalization_hint"] = "excluded_family_hint_terms"
    _emit(ctx, payload)


@app.command("resolve")
def resolve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Resolve a free-text query to the best Warcraft Wiki article match."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum candidates to inspect."),
) -> None:
    with _client(ctx) as client:
        normalized_query, excluded_terms, results, total_count = _search_results(client, query, limit=limit)
    top = results[0] if results else None
    second = results[1] if len(results) > 1 else None
    top_score = top["ranking"]["score"] if top else 0
    second_score = second["ranking"]["score"] if second else 0
    resolved = top is not None and (top_score >= 70 or top_score >= second_score + 18)
    payload = article_resolve_payload(
        provider_command="warcraft-wiki",
        query=query,
        search_query=normalized_query,
        results=results,
        total_count=total_count,
        resolved=resolved,
    )
    if excluded_terms:
        payload["excluded_terms"] = excluded_terms
        payload["normalization_hint"] = "excluded_family_hint_terms"
    _emit(ctx, payload)


@app.command("article")
def article(ctx: typer.Context, article_ref: str = typer.Argument(..., help="Wiki article title or URL.")) -> None:
    try:
        with _client(ctx) as client:
            payload = _build_article_summary(client.fetch_article_page(article_ref))
    except WarcraftWikiAPIError as exc:
        _handle_api_error(ctx, exc)
        return
    _emit(ctx, payload)


@app.command("article-full")
def article_full(ctx: typer.Context, article_ref: str = typer.Argument(..., help="Wiki article title or URL.")) -> None:
    try:
        with _client(ctx) as client:
            payload = _fetch_article_payload(client, article_ref)
    except WarcraftWikiAPIError as exc:
        _handle_api_error(ctx, exc)
        return
    _emit(ctx, payload)


@app.command("api")
def api_reference(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="API or programming reference query, title, or URL."),
) -> None:
    try:
        with _client(ctx) as client:
            payload = _typed_article_payload(client, query, surface="api", full=False)
    except WarcraftWikiAPIError as exc:
        _handle_api_error(ctx, exc)
        return
    _emit(ctx, payload)


@app.command("api-full")
def api_reference_full(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="API or programming reference query, title, or URL."),
) -> None:
    try:
        with _client(ctx) as client:
            payload = _typed_article_payload(client, query, surface="api", full=True)
    except WarcraftWikiAPIError as exc:
        _handle_api_error(ctx, exc)
        return
    _emit(ctx, payload)


@app.command("event")
def event_reference(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Event or UI handler query, title, or URL."),
) -> None:
    try:
        with _client(ctx) as client:
            payload = _typed_article_payload(client, query, surface="event", full=False)
    except WarcraftWikiAPIError as exc:
        _handle_api_error(ctx, exc)
        return
    _emit(ctx, payload)


@app.command("event-full")
def event_reference_full(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Event or UI handler query, title, or URL."),
) -> None:
    try:
        with _client(ctx) as client:
            payload = _typed_article_payload(client, query, surface="event", full=True)
    except WarcraftWikiAPIError as exc:
        _handle_api_error(ctx, exc)
        return
    _emit(ctx, payload)


@app.command("article-export")
def article_export(
    ctx: typer.Context,
    article_ref: str = typer.Argument(..., help="Wiki article title or URL."),
    out: Path | None = typer.Option(None, "--out", help="Output directory. Defaults to ./warcraft-wiki_exports/article-<slug>."),
) -> None:
    article_title = normalize_article_ref(article_ref)
    export_dir = out.expanduser() if out is not None else _default_export_dir(article_title)
    try:
        with _client(ctx) as client:
            payload = _fetch_article_payload(client, article_ref)
    except WarcraftWikiAPIError as exc:
        _handle_api_error(ctx, exc)
        return
    manifest = write_article_bundle(
        payload,
        provider="warcraft-wiki",
        export_dir=export_dir,
        resource_key="article",
        page_resource_key="article_meta",
    )
    _emit(
        ctx,
        {
            "provider": "warcraft-wiki",
            "article": payload["article"],
            "output_dir": str(export_dir),
            "counts": manifest["counts"],
            "files": manifest["files"],
        },
    )


@app.command("article-query")
def article_query(
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
    resource_key = str(bundle_payload["manifest"].get("resource_key") or "guide")
    _emit(
        ctx,
        {
            "provider": "warcraft-wiki",
            resource_key: bundle_payload["manifest"].get(resource_key),
            "bundle": str(bundle),
            **result,
        },
    )


def run() -> None:
    app()


if __name__ == "__main__":
    run()
