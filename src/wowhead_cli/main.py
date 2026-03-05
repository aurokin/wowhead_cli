from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
import typer

from wowhead_cli.expansion_profiles import ExpansionProfile, list_profiles, resolve_expansion
from wowhead_cli.output import emit
from wowhead_cli.page_parser import (
    extract_comments_dataset,
    extract_gatherer_entities,
    extract_linked_entities_from_href,
    normalize_comments,
    parse_page_meta_json,
    parse_page_metadata,
    sort_comments,
)
from wowhead_cli.wowhead_client import (
    WOWHEAD_BASE_URL,
    WowheadClient,
    entity_url,
    guide_url,
    search_url,
    suggestion_entity_type,
)

app = typer.Typer(
    add_completion=False,
    help="Agent-first CLI for querying Wowhead without browser automation.",
)

EXPANSION_PREFIXES = frozenset(
    profile.path_prefix for profile in list_profiles() if profile.path_prefix
)


@dataclass(slots=True)
class RuntimeConfig:
    pretty: bool = False
    expansion: ExpansionProfile = field(default_factory=lambda: resolve_expansion(None))
    normalize_canonical_to_expansion: bool = False
    compact: bool = False
    fields: tuple[str, ...] = ()


def _cfg(ctx: typer.Context) -> RuntimeConfig:
    obj = ctx.obj
    if isinstance(obj, RuntimeConfig):
        return obj
    return RuntimeConfig()


def _fail(ctx: typer.Context, code: str, message: str, *, status: int = 1) -> None:
    payload = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    _emit(ctx, payload, err=True)
    raise typer.Exit(status)


def _parse_entity_ref_token(token: str) -> tuple[str, int]:
    if ":" not in token:
        raise ValueError(f"Invalid entity reference {token!r}. Expected <type>:<id>.")
    entity_type, entity_id_raw = token.split(":", 1)
    if not entity_type:
        raise ValueError(f"Invalid entity reference {token!r}. Missing type.")
    try:
        entity_id = int(entity_id_raw)
    except ValueError as exc:
        raise ValueError(f"Invalid entity id in {token!r}.") from exc
    if entity_id <= 0:
        raise ValueError(f"Entity id must be positive in {token!r}.")
    return entity_type, entity_id


def _parse_guide_id_token(token: str) -> int | None:
    value = token.strip()
    if not value:
        return None
    if value.isdigit():
        guide_id = int(value)
    elif value.startswith("guide="):
        raw_id = value.split("=", 1)[1]
        if not raw_id.isdigit():
            raise ValueError(f"Invalid guide id in {token!r}.")
        guide_id = int(raw_id)
    else:
        return None
    if guide_id <= 0:
        raise ValueError(f"Guide id must be positive in {token!r}.")
    return guide_id


def _extract_guide_id_from_path(path: str) -> int | None:
    for segment in [part for part in path.split("/") if part]:
        if not segment.startswith("guide="):
            continue
        raw_id = segment.split("=", 1)[1]
        if not raw_id.isdigit():
            raise ValueError(f"Invalid guide id in path {path!r}.")
        guide_id = int(raw_id)
        if guide_id <= 0:
            raise ValueError(f"Guide id must be positive in path {path!r}.")
        return guide_id
    return None


def _resolve_guide_lookup_input(
    token: str,
    *,
    expansion: ExpansionProfile,
) -> tuple[str, int | None]:
    raw = token.strip()
    if not raw:
        raise ValueError("Guide reference cannot be empty.")

    direct_id = _parse_guide_id_token(raw)
    if direct_id is not None:
        return guide_url(direct_id, expansion=expansion), direct_id

    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"}:
        host = (parsed.hostname or "").lower()
        if host != "wowhead.com" and not host.endswith(".wowhead.com"):
            raise ValueError("Guide URL must point to wowhead.com.")
        if not parsed.path:
            raise ValueError("Guide URL is missing a path.")
        guide_id = _extract_guide_id_from_path(parsed.path)
        return raw, guide_id

    normalized = raw.lstrip("/")
    if not normalized:
        raise ValueError("Guide reference cannot be empty.")

    relative_id = _parse_guide_id_token(normalized)
    if relative_id is not None:
        return guide_url(relative_id, expansion=expansion), relative_id

    root_segment = normalized.split("/", 1)[0]
    if root_segment in EXPANSION_PREFIXES:
        lookup_url = f"{WOWHEAD_BASE_URL}/{normalized}"
    else:
        lookup_url = f"{expansion.wowhead_base}/{normalized}"
    guide_id = _extract_guide_id_from_path(f"/{normalized}")
    return lookup_url, guide_id


def _truncate_text(value: Any, *, max_chars: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _truncate_string(value: str, *, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."


def _compact_value(value: Any, *, max_chars: int) -> Any:
    if isinstance(value, str):
        return _truncate_string(value, max_chars=max_chars)
    if isinstance(value, list):
        return [_compact_value(row, max_chars=max_chars) for row in value]
    if isinstance(value, dict):
        return {key: _compact_value(val, max_chars=max_chars) for key, val in value.items()}
    return value


def _normalize_field_paths(values: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        for candidate in raw.split(","):
            path = candidate.strip()
            if not path:
                continue
            if path in seen:
                continue
            seen.add(path)
            normalized.append(path)
    return tuple(normalized)


def _extract_dict_path(payload: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = payload
    for key in path.split("."):
        if not isinstance(current, dict):
            return False, None
        if key not in current:
            return False, None
        current = current[key]
    return True, current


def _assign_dict_path(target: dict[str, Any], path: str, value: Any) -> None:
    keys = [key for key in path.split(".") if key]
    if not keys:
        return
    cursor = target
    for key in keys[:-1]:
        existing = cursor.get(key)
        if not isinstance(existing, dict):
            existing = {}
            cursor[key] = existing
        cursor = existing
    cursor[keys[-1]] = value


def _filter_payload_fields(payload: dict[str, Any], *, fields: tuple[str, ...]) -> dict[str, Any]:
    if not fields:
        return payload
    filtered: dict[str, Any] = {}
    if "ok" in payload:
        filtered["ok"] = payload["ok"]
    if payload.get("ok") is False and "error" in payload:
        filtered["error"] = payload["error"]
    for path in fields:
        found, value = _extract_dict_path(payload, path)
        if found:
            _assign_dict_path(filtered, path, value)
    return filtered


def _emit(ctx: typer.Context, payload: dict[str, Any], *, err: bool = False) -> None:
    cfg = _cfg(ctx)
    rendered: dict[str, Any] = payload
    if cfg.compact:
        rendered = _compact_value(rendered, max_chars=280)
    if cfg.fields:
        rendered = _filter_payload_fields(rendered, fields=cfg.fields)
    emit(rendered, pretty=cfg.pretty, err=err)


def _dedupe_links(
    links: list[dict[str, Any]],
    *,
    entity_type: str,
    entity_id: int,
    max_links: int,
) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for record in links:
        link_type = record.get("entity_type")
        link_id = record.get("id")
        if not isinstance(link_type, str) or not isinstance(link_id, int):
            continue
        if link_type == entity_type and link_id == entity_id:
            continue
        key = (link_type, link_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
        if len(deduped) >= max_links:
            break
    return deduped


def _fetch_entity_page(
    ctx: typer.Context,
    client: WowheadClient,
    entity_type: str,
    entity_id: int,
) -> tuple[str, dict[str, str | None]]:
    try:
        html = client.entity_page_html(entity_type, entity_id)
    except httpx.HTTPStatusError as exc:
        _fail(ctx, "http_error", f"Wowhead returned HTTP {exc.response.status_code}")
    except httpx.HTTPError as exc:
        _fail(ctx, "network_error", str(exc))
    fallback_url = entity_url(entity_type, entity_id, expansion=client.expansion)
    metadata = parse_page_metadata(html, fallback_url=fallback_url)
    return html, metadata


def _normalize_canonical_entity_url(
    raw_url: str | None,
    *,
    expansion: ExpansionProfile,
    entity_type: str,
    entity_id: int,
) -> str:
    base = entity_url(entity_type, entity_id, expansion=expansion)
    if not raw_url:
        return base
    parsed = urlparse(raw_url)
    parts = [part for part in parsed.path.split("/") if part]
    marker = f"{entity_type}={entity_id}"
    try:
        index = parts.index(marker)
    except ValueError:
        return base
    if index + 1 < len(parts):
        return f"{base}/{parts[index + 1]}"
    return base


@app.callback()
def cli(
    ctx: typer.Context,
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Pretty-print JSON for human reading. Default output is compact JSON.",
    ),
    expansion: str = typer.Option(
        "retail",
        "--expansion",
        help="Expansion profile key/alias (for example: retail, classic, tbc, wotlk, cata, mop-classic, ptr).",
    ),
    normalize_canonical_to_expansion: bool = typer.Option(
        False,
        "--normalize-canonical-to-expansion/--no-normalize-canonical-to-expansion",
        help="Rewrite canonical entity page URLs to the selected expansion path when canonical redirects across profiles.",
    ),
    compact: bool = typer.Option(
        False,
        "--compact",
        help="Truncate long string fields to reduce payload size.",
    ),
    fields: list[str] = typer.Option(
        [],
        "--fields",
        help="Return only selected fields (dot paths). Repeat or pass comma-separated values.",
    ),
) -> None:
    try:
        profile = resolve_expansion(expansion)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--expansion") from exc
    ctx.obj = RuntimeConfig(
        pretty=pretty,
        expansion=profile,
        normalize_canonical_to_expansion=normalize_canonical_to_expansion,
        compact=compact,
        fields=_normalize_field_paths(fields),
    )


@app.command("expansions")
def expansions(ctx: typer.Context) -> None:
    profiles = list_profiles()
    payload = {
        "ok": True,
        "default": resolve_expansion(None).key,
        "profiles": [
            {
                "key": profile.key,
                "label": profile.label,
                "path_prefix": profile.path_prefix,
                "data_env": profile.data_env,
                "aliases": list(profile.aliases),
                "legacy_subdomains": list(profile.legacy_subdomains),
                "wowhead_base": profile.wowhead_base,
                "nether_base": profile.nether_base,
            }
            for profile in profiles
        ],
    }
    _emit(ctx, payload)


@app.command("search")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search text."),
    limit: int = typer.Option(
        10,
        "--limit",
        min=1,
        max=50,
        help="Maximum number of results to return.",
    ),
) -> None:
    cfg = _cfg(ctx)
    client = WowheadClient(expansion=cfg.expansion)
    try:
        response = client.search_suggestions(query)
    except httpx.HTTPStatusError as exc:
        _fail(ctx, "http_error", f"Wowhead returned HTTP {exc.response.status_code}")
    except httpx.HTTPError as exc:
        _fail(ctx, "network_error", str(exc))
    except ValueError as exc:
        _fail(ctx, "parse_error", str(exc))

    results = response.get("results")
    if not isinstance(results, list):
        _fail(ctx, "unexpected_response", "Missing or invalid 'results' payload from Wowhead.")

    normalized = []
    for row in results[:limit]:
        if not isinstance(row, dict):
            continue
        entity_type = suggestion_entity_type(row)
        entity_id = row.get("id")
        candidate_url: str | None = None
        if isinstance(entity_id, int):
            if entity_type == "guide":
                candidate_url = guide_url(entity_id, expansion=cfg.expansion)
            elif entity_type:
                candidate_url = entity_url(entity_type, entity_id, expansion=cfg.expansion)
        candidate = {
            "id": entity_id,
            "name": row.get("name"),
            "type_id": row.get("type"),
            "type_name": row.get("typeName"),
            "entity_type": entity_type,
            "url": candidate_url,
            "metadata": {
                "popularity": row.get("popularity"),
                "icon": row.get("icon"),
                "quality": row.get("quality"),
                "side": row.get("side"),
                "display_name": row.get("displayName"),
            },
        }
        normalized.append(candidate)

    payload: dict[str, Any] = {
        "ok": True,
        "query": query,
        "expansion": cfg.expansion.key,
        "search_url": search_url(query, expansion=cfg.expansion),
        "count": len(normalized),
        "results": normalized,
    }
    _emit(ctx, payload)


@app.command("guide")
def guide(
    ctx: typer.Context,
    guide_ref: str = typer.Argument(
        ...,
        help="Guide id, Wowhead guide URL, or guide path.",
    ),
    comment_sample: int = typer.Option(
        3,
        "--comment-sample",
        min=0,
        max=20,
        help="Top comments to include (sorted by rating).",
    ),
    comment_chars: int = typer.Option(
        320,
        "--comment-chars",
        min=60,
        max=2000,
        help="Maximum characters for each sampled comment body.",
    ),
) -> None:
    cfg = _cfg(ctx)
    try:
        lookup_url, guide_id = _resolve_guide_lookup_input(guide_ref, expansion=cfg.expansion)
    except ValueError as exc:
        _fail(ctx, "invalid_argument", str(exc))

    client = WowheadClient(expansion=cfg.expansion)
    try:
        default_lookup = guide_url(guide_id, expansion=cfg.expansion) if guide_id is not None else None
        if guide_id is not None and lookup_url == default_lookup:
            html = client.guide_page_html(guide_id)
        else:
            html = client.page_html(lookup_url)
    except httpx.HTTPStatusError as exc:
        _fail(ctx, "http_error", f"Wowhead returned HTTP {exc.response.status_code}")
    except httpx.HTTPError as exc:
        _fail(ctx, "network_error", str(exc))

    metadata = parse_page_metadata(html, fallback_url=lookup_url)
    canonical_url = metadata["canonical_url"] or lookup_url

    raw_comments: list[dict[str, Any]]
    try:
        raw_comments = extract_comments_dataset(html)
    except ValueError:
        raw_comments = []

    sampled_comments: list[dict[str, Any]] = []
    if comment_sample > 0 and raw_comments:
        ranked = sort_comments(raw_comments, "rating")
        sampled_norm = normalize_comments(
            ranked[:comment_sample],
            page_url=canonical_url,
            include_replies=False,
        )
        for row in sampled_norm:
            sampled_comments.append(
                {
                    "id": row.get("id"),
                    "user": row.get("user"),
                    "rating": row.get("rating"),
                    "date": row.get("date"),
                    "body": _truncate_text(row.get("body"), max_chars=comment_chars),
                    "citation_url": row.get("citation_url"),
                }
            )

    page_meta_json = parse_page_meta_json(html)
    payload: dict[str, Any] = {
        "ok": True,
        "expansion": cfg.expansion.key,
        "guide": {
            "input": guide_ref,
            "id": guide_id,
            "lookup_url": lookup_url,
            "url": canonical_url,
            "comments_url": f"{canonical_url}#comments",
        },
        "query": {
            "comment_sample": comment_sample,
            "comment_chars": comment_chars,
        },
        "page": {
            "title": metadata["title"],
            "description": metadata["description"],
            "canonical_url": canonical_url,
        },
        "comments": {
            "count": len(raw_comments),
            "top": sampled_comments,
        },
        "citations": {
            "page": canonical_url,
            "comments": f"{canonical_url}#comments",
        },
    }
    if isinstance(page_meta_json, dict):
        payload["page_meta"] = {
            "page": page_meta_json.get("page"),
            "server_time": page_meta_json.get("serverTime"),
            "available_data_envs": page_meta_json.get("availableDataEnvs"),
            "env_domain": page_meta_json.get("envDomain"),
        }
    _emit(ctx, payload)


@app.command("entity")
def entity(
    ctx: typer.Context,
    entity_type: str = typer.Argument(..., help="Wowhead entity type. Example: item, quest, npc."),
    entity_id: int = typer.Argument(..., help="Wowhead entity id."),
    data_env: int | None = typer.Option(
        None,
        "--data-env",
        help="Override Wowhead tooltip dataEnv value. Defaults to selected expansion profile.",
    ),
    include_comments: bool = typer.Option(
        True,
        "--include-comments/--no-include-comments",
        help="Include page comments in entity output.",
    ),
    include_all_comments: bool = typer.Option(
        False,
        "--include-all-comments/--top-comments-only",
        help="Include all parsed comments instead of only a top-rated summary.",
    ),
) -> None:
    cfg = _cfg(ctx)
    client = WowheadClient(expansion=cfg.expansion)
    try:
        tooltip = client.tooltip(entity_type, entity_id, data_env=data_env)
    except httpx.HTTPStatusError as exc:
        _fail(ctx, "http_error", f"Wowhead returned HTTP {exc.response.status_code}")
    except httpx.HTTPError as exc:
        _fail(ctx, "network_error", str(exc))
    except ValueError as exc:
        _fail(ctx, "parse_error", str(exc))

    canonical = entity_url(entity_type, entity_id, expansion=cfg.expansion)
    page_url = canonical
    raw_comments: list[dict[str, Any]] = []
    sampled_comments: list[dict[str, Any]] = []
    all_comments: list[dict[str, Any]] = []
    top_comment_limit = 3

    if include_comments:
        html, metadata = _fetch_entity_page(ctx, client, entity_type, entity_id)
        page_url = metadata["canonical_url"] or canonical
        try:
            raw_comments = extract_comments_dataset(html)
        except ValueError:
            raw_comments = []

        if include_all_comments:
            all_comments = normalize_comments(
                sort_comments(raw_comments, "newest"),
                page_url=page_url,
                include_replies=True,
            )
        else:
            ranked = sort_comments(raw_comments, "rating")
            sampled_norm = normalize_comments(
                ranked[:top_comment_limit],
                page_url=page_url,
                include_replies=False,
            )
            for row in sampled_norm:
                sampled_comments.append(
                    {
                        "id": row.get("id"),
                        "user": row.get("user"),
                        "rating": row.get("rating"),
                        "date": row.get("date"),
                        "body": _truncate_text(row.get("body"), max_chars=320),
                        "citation_url": row.get("citation_url"),
                    }
                )

    all_comments_included = False
    if include_comments:
        if include_all_comments:
            all_comments_included = len(all_comments) == len(raw_comments)
        else:
            all_comments_included = len(sampled_comments) == len(raw_comments)

    payload = {
        "ok": True,
        "expansion": cfg.expansion.key,
        "entity": {
            "type": entity_type,
            "id": entity_id,
            "url": canonical,
            "comments_url": f"{canonical}#comments",
        },
        "data_env": data_env if data_env is not None else cfg.expansion.data_env,
        "comments_included": include_comments,
        "tooltip": tooltip,
        "citations": {
            "page": page_url,
            "comments": f"{page_url}#comments",
        },
    }
    if include_comments:
        comments_payload: dict[str, Any] = {
            "count": len(raw_comments),
            "all_comments_included": all_comments_included,
            "needs_raw_fetch": not all_comments_included,
        }
        if include_all_comments:
            comments_payload["items"] = all_comments
        else:
            comments_payload["top"] = sampled_comments
        payload["comments"] = comments_payload
    _emit(ctx, payload)


@app.command("entity-page")
def entity_page(
    ctx: typer.Context,
    entity_type: str = typer.Argument(..., help="Wowhead entity type. Example: item, quest, npc."),
    entity_id: int = typer.Argument(..., help="Wowhead entity id."),
    max_links: int = typer.Option(
        200,
        "--max-links",
        min=1,
        max=2000,
        help="Maximum linked entities to return.",
    ),
    include_gatherer: bool = typer.Option(
        True,
        "--include-gatherer/--no-include-gatherer",
        help="Include linked entities discovered from WH.Gatherer.addData payloads.",
    ),
) -> None:
    cfg = _cfg(ctx)
    client = WowheadClient(expansion=cfg.expansion)
    html, metadata = _fetch_entity_page(ctx, client, entity_type, entity_id)

    raw_canonical = metadata["canonical_url"] or entity_url(entity_type, entity_id, expansion=cfg.expansion)
    canonical_url = (
        _normalize_canonical_entity_url(
            raw_canonical,
            expansion=cfg.expansion,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        if cfg.normalize_canonical_to_expansion
        else raw_canonical
    )
    links_href = extract_linked_entities_from_href(html, source_url=canonical_url)
    links = links_href
    if include_gatherer:
        links = links + extract_gatherer_entities(html, source_url=canonical_url)

    deduped = _dedupe_links(
        links,
        entity_type=entity_type,
        entity_id=entity_id,
        max_links=max_links,
    )

    page_meta_json = parse_page_meta_json(html)

    payload: dict[str, Any] = {
        "ok": True,
        "expansion": cfg.expansion.key,
        "normalize_canonical_to_expansion": cfg.normalize_canonical_to_expansion,
        "entity": {
            "type": entity_type,
            "id": entity_id,
            "url": canonical_url,
            "comments_url": f"{canonical_url}#comments",
        },
        "page": {
            "title": metadata["title"],
            "description": metadata["description"],
            "canonical_url": canonical_url,
        },
        "linked_entities": {
            "count": len(deduped),
            "items": deduped,
        },
        "citations": {
            "page": canonical_url,
            "comments": f"{canonical_url}#comments",
        },
    }
    if isinstance(page_meta_json, dict):
        payload["page_meta"] = {
            "page": page_meta_json.get("page"),
            "server_time": page_meta_json.get("serverTime"),
            "available_data_envs": page_meta_json.get("availableDataEnvs"),
            "env_domain": page_meta_json.get("envDomain"),
        }
    _emit(ctx, payload)


@app.command("comments")
def comments(
    ctx: typer.Context,
    entity_type: str = typer.Argument(..., help="Wowhead entity type. Example: item, quest, npc."),
    entity_id: int = typer.Argument(..., help="Wowhead entity id."),
    limit: int = typer.Option(
        25,
        "--limit",
        min=1,
        max=500,
        help="Maximum number of top-level comments to return.",
    ),
    sort: str = typer.Option(
        "newest",
        "--sort",
        help="Sort mode for top-level comments: newest | oldest | rating.",
    ),
    min_rating: int | None = typer.Option(
        None,
        "--min-rating",
        help="Filter out comments below this rating.",
    ),
    include_replies: bool = typer.Option(
        True,
        "--include-replies/--no-include-replies",
        help="Include reply objects for each comment.",
    ),
    hydrate_missing_replies: bool = typer.Option(
        False,
        "--hydrate-missing-replies/--no-hydrate-missing-replies",
        help="Fetch missing replies via /comment/show-replies when embedded data is incomplete.",
    ),
) -> None:
    if sort not in {"newest", "oldest", "rating"}:
        _fail(ctx, "invalid_argument", "sort must be one of: newest, oldest, rating.")

    cfg = _cfg(ctx)
    client = WowheadClient(expansion=cfg.expansion)
    html, metadata = _fetch_entity_page(ctx, client, entity_type, entity_id)
    raw_canonical = metadata["canonical_url"] or entity_url(entity_type, entity_id, expansion=cfg.expansion)
    canonical_url = (
        _normalize_canonical_entity_url(
            raw_canonical,
            expansion=cfg.expansion,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        if cfg.normalize_canonical_to_expansion
        else raw_canonical
    )

    try:
        raw_comments = extract_comments_dataset(html)
    except ValueError as exc:
        _fail(ctx, "parse_error", str(exc))

    if min_rating is not None:
        filtered: list[dict[str, Any]] = []
        for row in raw_comments:
            rating = row.get("rating")
            if isinstance(rating, int) and rating >= min_rating:
                filtered.append(row)
        raw_comments = filtered

    raw_comments = sort_comments(raw_comments, sort)
    selected = raw_comments[:limit]

    hydrated_count = 0
    if hydrate_missing_replies and include_replies:
        for row in selected:
            if not isinstance(row, dict):
                continue
            comment_id = row.get("id")
            expected = row.get("nreplies")
            current = row.get("replies")
            if not isinstance(comment_id, int) or not isinstance(expected, int):
                continue
            current_count = len(current) if isinstance(current, list) else 0
            if expected <= current_count:
                continue
            try:
                row["replies"] = client.comment_replies(comment_id)
                hydrated_count += 1
            except httpx.HTTPError:
                continue

    normalized = normalize_comments(
        selected,
        page_url=canonical_url,
        include_replies=include_replies,
    )

    payload = {
        "ok": True,
        "expansion": cfg.expansion.key,
        "normalize_canonical_to_expansion": cfg.normalize_canonical_to_expansion,
        "entity": {
            "type": entity_type,
            "id": entity_id,
            "url": canonical_url,
            "comments_url": f"{canonical_url}#comments",
        },
        "query": {
            "limit": limit,
            "sort": sort,
            "min_rating": min_rating,
            "include_replies": include_replies,
            "hydrate_missing_replies": hydrate_missing_replies,
        },
        "counts": {
            "embedded_comments": len(raw_comments),
            "returned_comments": len(normalized),
            "hydrated_reply_threads": hydrated_count,
        },
        "comments": normalized,
        "citations": {
            "page": canonical_url,
            "comments": f"{canonical_url}#comments",
        },
    }
    _emit(ctx, payload)


@app.command("compare")
def compare(
    ctx: typer.Context,
    entities: list[str] = typer.Argument(
        ...,
        help="Entity references in <type>:<id> form. Example: item:19019 item:19351",
    ),
    max_links_per_entity: int = typer.Option(
        150,
        "--max-links-per-entity",
        min=1,
        max=2000,
        help="Maximum linked entities to parse per entity.",
    ),
    max_shared_links: int = typer.Option(
        80,
        "--max-shared-links",
        min=1,
        max=2000,
        help="Maximum shared linked entities to include in output.",
    ),
    max_unique_links: int = typer.Option(
        120,
        "--max-unique-links",
        min=1,
        max=5000,
        help="Maximum unique linked entities to include per compared entity.",
    ),
    comment_sample: int = typer.Option(
        3,
        "--comment-sample",
        min=0,
        max=20,
        help="Top comments to include per entity (sorted by rating).",
    ),
    comment_chars: int = typer.Option(
        320,
        "--comment-chars",
        min=60,
        max=2000,
        help="Maximum characters for each sampled comment body.",
    ),
    include_gatherer: bool = typer.Option(
        True,
        "--include-gatherer/--no-include-gatherer",
        help="Include linked entities from WH.Gatherer.addData payloads.",
    ),
) -> None:
    if len(entities) < 2:
        _fail(ctx, "invalid_argument", "compare requires at least two entity references.")

    parsed_refs: list[tuple[str, int, str]] = []
    for token in entities:
        try:
            entity_type, entity_id = _parse_entity_ref_token(token)
        except ValueError as exc:
            _fail(ctx, "invalid_argument", str(exc))
        parsed_refs.append((entity_type, entity_id, token))

    cfg = _cfg(ctx)
    client = WowheadClient(expansion=cfg.expansion)
    entity_records: list[dict[str, Any]] = []
    entity_link_sets: dict[str, set[tuple[str, int]]] = {}

    for entity_type, entity_id, token in parsed_refs:
        try:
            tooltip = client.tooltip(entity_type, entity_id)
        except httpx.HTTPStatusError as exc:
            _fail(ctx, "http_error", f"Wowhead returned HTTP {exc.response.status_code} for {token}")
        except httpx.HTTPError as exc:
            _fail(ctx, "network_error", f"{token}: {exc}")
        except ValueError as exc:
            _fail(ctx, "parse_error", f"{token}: {exc}")

        html, metadata = _fetch_entity_page(ctx, client, entity_type, entity_id)
        raw_canonical = metadata["canonical_url"] or entity_url(entity_type, entity_id, expansion=cfg.expansion)
        canonical_url = (
            _normalize_canonical_entity_url(
                raw_canonical,
                expansion=cfg.expansion,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            if cfg.normalize_canonical_to_expansion
            else raw_canonical
        )

        links = extract_linked_entities_from_href(html, source_url=canonical_url)
        if include_gatherer:
            links = links + extract_gatherer_entities(html, source_url=canonical_url)
        deduped_links = _dedupe_links(
            links,
            entity_type=entity_type,
            entity_id=entity_id,
            max_links=max_links_per_entity,
        )

        raw_comments: list[dict[str, Any]] = []
        try:
            raw_comments = extract_comments_dataset(html)
        except ValueError:
            raw_comments = []
        sampled_comments: list[dict[str, Any]] = []
        if comment_sample > 0 and raw_comments:
            ranked = sort_comments(raw_comments, "rating")
            sampled_norm = normalize_comments(
                ranked[:comment_sample],
                page_url=canonical_url,
                include_replies=False,
            )
            for row in sampled_norm:
                sampled_comments.append(
                    {
                        "id": row.get("id"),
                        "user": row.get("user"),
                        "rating": row.get("rating"),
                        "date": row.get("date"),
                        "body": _truncate_text(row.get("body"), max_chars=comment_chars),
                        "citation_url": row.get("citation_url"),
                    }
                )

        ref = f"{entity_type}:{entity_id}"
        link_set: set[tuple[str, int]] = set()
        for row in deduped_links:
            link_type = row.get("entity_type")
            link_id = row.get("id")
            if isinstance(link_type, str) and isinstance(link_id, int):
                link_set.add((link_type, link_id))
        entity_link_sets[ref] = link_set

        entity_records.append(
            {
                "ref": ref,
                "entity": {
                    "type": entity_type,
                    "id": entity_id,
                    "url": canonical_url,
                    "comments_url": f"{canonical_url}#comments",
                },
                "summary": {
                    "name": tooltip.get("name"),
                    "quality": tooltip.get("quality"),
                    "icon": tooltip.get("icon"),
                    "title": metadata.get("title"),
                    "description": metadata.get("description"),
                },
                "linked_entities": {
                    "count": len(deduped_links),
                    "items": deduped_links,
                },
                "comments": {
                    "count": len(raw_comments),
                    "top": sampled_comments,
                },
                "citations": {
                    "page": canonical_url,
                    "comments": f"{canonical_url}#comments",
                },
            }
        )

    refs_in_order = [row["ref"] for row in entity_records]
    comparable_fields = ["name", "quality", "icon", "title"]
    field_diffs: dict[str, Any] = {}
    for field in comparable_fields:
        values: dict[str, Any] = {}
        for row in entity_records:
            ref = row.get("ref")
            if not isinstance(ref, str):
                continue
            summary = row.get("summary")
            value = summary.get(field) if isinstance(summary, dict) else None
            values[ref] = value
        unique_values = {repr(v) for v in values.values()}
        field_diffs[field] = {
            "all_equal": len(unique_values) <= 1,
            "values": values,
        }

    all_sets = [entity_link_sets[ref] for ref in refs_in_order]
    if all_sets:
        shared = set.intersection(*all_sets)
    else:
        shared = set()

    shared_links_all = [
        {
            "entity_type": link_type,
            "id": link_id,
            "citation_url": entity_url(link_type, link_id, expansion=cfg.expansion),
            "url": entity_url(link_type, link_id, expansion=cfg.expansion),
        }
        for link_type, link_id in sorted(shared)
    ]
    shared_links = shared_links_all[:max_shared_links]

    unique_by_ref: dict[str, list[dict[str, Any]]] = {}
    unique_counts: dict[str, int] = {}
    for ref in refs_in_order:
        mine = entity_link_sets[ref]
        others_union: set[tuple[str, int]] = set()
        for other_ref, other_links in entity_link_sets.items():
            if other_ref == ref:
                continue
            others_union |= other_links
        unique_pairs = sorted(mine - others_union)
        unique_counts[ref] = len(unique_pairs)
        unique_by_ref[ref] = [
            {
                "entity_type": link_type,
                "id": link_id,
                "url": entity_url(link_type, link_id, expansion=cfg.expansion),
                "citation_url": entity_url(link_type, link_id, expansion=cfg.expansion),
            }
            for link_type, link_id in unique_pairs[:max_unique_links]
        ]

    payload = {
        "ok": True,
        "expansion": cfg.expansion.key,
        "normalize_canonical_to_expansion": cfg.normalize_canonical_to_expansion,
        "inputs": refs_in_order,
        "comparison": {
            "fields": field_diffs,
            "linked_entities": {
                "shared_count_total": len(shared_links_all),
                "shared_count_returned": len(shared_links),
                "shared_items": shared_links,
                "unique_count_total_by_entity": unique_counts,
                "unique_by_entity": unique_by_ref,
            },
        },
        "entities": entity_records,
        "citations": {
            "entity_pages": [row["entity"]["url"] for row in entity_records],
            "comment_pages": [row["entity"]["comments_url"] for row in entity_records],
        },
    }
    _emit(ctx, payload)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
