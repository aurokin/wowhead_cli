from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import typer

from wowhead_cli.expansion_profiles import ExpansionProfile, list_profiles, resolve_expansion
from wowhead_cli.output import emit
from wowhead_cli.page_parser import (
    clean_markup_text,
    extract_comments_dataset,
    extract_gatherer_entities,
    extract_guide_rating,
    extract_guide_section_chunks,
    extract_guide_sections,
    extract_linked_entities_from_href,
    extract_json_ld,
    extract_json_script,
    extract_markup_by_target,
    extract_markup_urls,
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


def _slugify_path_fragment(value: str) -> str:
    slug_chars: list[str] = []
    last_dash = False
    for char in value.lower():
        if char.isalnum():
            slug_chars.append(char)
            last_dash = False
            continue
        if last_dash:
            continue
        slug_chars.append("-")
        last_dash = True
    rendered = "".join(slug_chars).strip("-")
    return rendered or "guide"


def _guide_export_root() -> Path:
    return Path.cwd() / "wowhead_exports"


def _default_guide_export_dir(payload: dict[str, Any]) -> Path:
    guide = payload.get("guide")
    page = payload.get("page")
    guide_id = guide.get("id") if isinstance(guide, dict) else None
    title = page.get("title") if isinstance(page, dict) else None
    slug_source = title if isinstance(title, str) and title.strip() else str(guide_id or "guide")
    if isinstance(guide_id, int):
        name = f"guide-{guide_id}-{_slugify_path_fragment(slug_source)}"
    else:
        name = f"guide-{_slugify_path_fragment(slug_source)}"
    return _guide_export_root() / name


def _write_json_file(path: Path, payload: Any) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    path.write_text(f"{rendered}\n", encoding="utf-8")


def _write_jsonl_file(path: Path, rows: list[Any]) -> None:
    content = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(content, encoding="utf-8")


def _write_optional_text_file(path: Path, value: Any) -> bool:
    if not isinstance(value, str):
        return False
    path.write_text(value, encoding="utf-8")
    return True


def _read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl_file(path: Path) -> list[Any]:
    rows: list[Any] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def _query_terms(query: str) -> list[str]:
    normalized = " ".join(query.lower().split())
    return [term for term in normalized.split(" ") if term]


def _score_text_match(query: str, *values: Any) -> int:
    terms = _query_terms(query)
    if not terms:
        return 0
    haystacks = []
    for value in values:
        if isinstance(value, str) and value.strip():
            haystacks.append(value.lower())
    if not haystacks:
        return 0
    score = 0
    for term in terms:
        for haystack in haystacks:
            if term in haystack:
                score += 1
    joined = " ".join(haystacks)
    query_normalized = " ".join(query.lower().split())
    if query_normalized and query_normalized in joined:
        score += max(2, len(terms))
    return score


def _truncate_preview(value: str, *, max_chars: int = 220) -> str:
    text = " ".join(value.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _normalize_query_kinds(values: list[str]) -> tuple[str, ...]:
    allowed = {
        "sections",
        "navigation",
        "linked_entities",
        "gatherer_entities",
        "comments",
    }
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        for candidate in raw.split(","):
            value = candidate.strip().lower()
            if not value:
                continue
            if value not in allowed:
                raise ValueError(
                    f"Unsupported query kind {value!r}. Expected one of: {', '.join(sorted(allowed))}."
                )
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
    return tuple(normalized)


def _fetch_guide_page(
    ctx: typer.Context,
    client: WowheadClient,
    *,
    guide_ref: str,
) -> tuple[str, int | None, str, dict[str, str | None], str]:
    try:
        lookup_url, guide_id = _resolve_guide_lookup_input(guide_ref, expansion=client.expansion)
    except ValueError as exc:
        _fail(ctx, "invalid_argument", str(exc))

    try:
        default_lookup = guide_url(guide_id, expansion=client.expansion) if guide_id is not None else None
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
    return html, guide_id, lookup_url, metadata, canonical_url


def _build_guide_full_payload(
    ctx: typer.Context,
    *,
    guide_ref: str,
    max_links: int,
    include_replies: bool,
) -> tuple[dict[str, Any], str]:
    cfg = _cfg(ctx)
    client = WowheadClient(expansion=cfg.expansion)
    html, guide_id, lookup_url, metadata, canonical_url = _fetch_guide_page(
        ctx,
        client,
        guide_ref=guide_ref,
    )

    raw_comments: list[dict[str, Any]]
    try:
        raw_comments = extract_comments_dataset(html)
    except ValueError:
        raw_comments = []
    comments = normalize_comments(
        raw_comments,
        page_url=canonical_url,
        include_replies=include_replies,
    )

    linked_entities = _dedupe_links(
        extract_linked_entities_from_href(html, source_url=canonical_url),
        entity_type="guide",
        entity_id=guide_id or 0,
        max_links=max_links,
    )
    gatherer_entities = extract_gatherer_entities(html, source_url=canonical_url)

    page_meta_json = parse_page_meta_json(html)
    json_ld = extract_json_ld(html)
    guide_body_markup = extract_markup_by_target(html, target="guide-body")
    guide_nav_markup = extract_markup_by_target(html, target="interior-sidebar-related-markup")
    author_name = None
    author_profiles: dict[str, Any] | None = None
    author_embed: dict[str, Any] | None = None

    try:
        parsed_author = extract_json_script(html, "data.guide.author")
        if isinstance(parsed_author, str):
            author_name = parsed_author
    except (ValueError, json.JSONDecodeError):
        author_name = None

    try:
        parsed_profiles = extract_json_script(html, "data.guide.author.profiles")
        if isinstance(parsed_profiles, dict):
            author_profiles = parsed_profiles
    except (ValueError, json.JSONDecodeError):
        author_profiles = None

    try:
        parsed_embed = extract_json_script(html, "data.guide.aboutTheAuthor.embedData")
        if isinstance(parsed_embed, dict):
            author_embed = parsed_embed
    except (ValueError, json.JSONDecodeError):
        author_embed = None

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
        "page": {
            "title": metadata["title"],
            "description": metadata["description"],
            "canonical_url": canonical_url,
        },
        "author": {
            "name": author_name,
            "profiles": author_profiles or {},
            "about": author_embed or {},
        },
        "rating": extract_guide_rating(html),
        "body": {
            "raw_markup": guide_body_markup,
            "sections": extract_guide_sections(guide_body_markup) if isinstance(guide_body_markup, str) else [],
            "section_chunks": extract_guide_section_chunks(guide_body_markup)
            if isinstance(guide_body_markup, str)
            else [],
            "summary": clean_markup_text(guide_body_markup[:2000]) if isinstance(guide_body_markup, str) else None,
        },
        "navigation": {
            "raw_markup": guide_nav_markup,
            "links": extract_markup_urls(guide_nav_markup, source_url=canonical_url)
            if isinstance(guide_nav_markup, str)
            else [],
        },
        "linked_entities": {
            "count": len(linked_entities),
            "items": linked_entities,
        },
        "gatherer_entities": {
            "count": len(gatherer_entities),
            "items": gatherer_entities,
        },
        "comments": {
            "count": len(comments),
            "include_replies": include_replies,
            "all_comments_included": True,
            "items": comments,
        },
        "structured_data": json_ld,
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
    return payload, html


def _load_guide_export(export_dir: Path) -> dict[str, Any]:
    manifest_path = export_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Missing manifest file at {manifest_path}.")
    manifest = _read_json_file(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError("Guide export manifest is not a JSON object.")

    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("Guide export manifest is missing its files map.")

    def load_jsonl_from_manifest(key: str) -> list[Any]:
        filename = files.get(key)
        if not isinstance(filename, str):
            return []
        path = export_dir / filename
        if not path.exists():
            return []
        return _read_jsonl_file(path)

    return {
        "manifest": manifest,
        "sections": load_jsonl_from_manifest("sections_jsonl"),
        "navigation_links": load_jsonl_from_manifest("navigation_links_jsonl"),
        "linked_entities": load_jsonl_from_manifest("linked_entities_jsonl"),
        "gatherer_entities": load_jsonl_from_manifest("gatherer_entities_jsonl"),
        "comments": load_jsonl_from_manifest("comments_jsonl"),
    }


def _discover_guide_corpora(root: Path) -> list[dict[str, Any]]:
    if not root.exists() or not root.is_dir():
        return []

    corpora: list[dict[str, Any]] = []
    for child in sorted(root.iterdir(), key=lambda path: path.name):
        if not child.is_dir():
            continue
        manifest_path = child / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = _read_json_file(manifest_path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(manifest, dict):
            continue

        guide = manifest.get("guide")
        page = manifest.get("page")
        counts = manifest.get("counts")
        corpora.append(
            {
                "path": str(child),
                "dir_name": child.name,
                "guide_id": guide.get("id") if isinstance(guide, dict) else None,
                "title": page.get("title") if isinstance(page, dict) else None,
                "canonical_url": page.get("canonical_url") if isinstance(page, dict) else None,
                "expansion": manifest.get("expansion"),
                "export_version": manifest.get("export_version"),
                "counts": counts if isinstance(counts, dict) else {},
            }
        )
    corpora.sort(key=lambda row: ((row.get("title") or "").lower(), row["path"]))
    return corpora


def _looks_like_path(value: str) -> bool:
    return value.startswith(("/", ".", "~")) or "/" in value


def _resolve_corpus_ref(corpus_ref: str, *, root: Path | None) -> Path:
    raw = corpus_ref.strip()
    if not raw:
        raise ValueError("Bundle reference cannot be empty.")

    expanded = Path(raw).expanduser()
    if expanded.exists():
        if not expanded.is_dir():
            raise ValueError(f"Bundle path {expanded} is not a directory.")
        return expanded.resolve()
    if _looks_like_path(raw):
        raise ValueError(f"Bundle path {expanded} does not exist.")

    search_root = (root or _guide_export_root()).expanduser()
    corpora = _discover_guide_corpora(search_root)
    if not corpora:
        raise ValueError(f"No exported bundles found under {search_root}.")

    lowered = raw.lower()

    def exact_matches() -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for row in corpora:
            guide_id = row.get("guide_id")
            title = row.get("title")
            dir_name = row.get("dir_name")
            if isinstance(guide_id, int) and str(guide_id) == raw:
                matches.append(row)
                continue
            if isinstance(dir_name, str) and dir_name.lower() == lowered:
                matches.append(row)
                continue
            if isinstance(title, str) and title.lower() == lowered:
                matches.append(row)
        return matches

    matches = exact_matches()
    if not matches:
        matches = []
        for row in corpora:
            title = row.get("title")
            dir_name = row.get("dir_name")
            if isinstance(title, str) and lowered in title.lower():
                matches.append(row)
                continue
            if isinstance(dir_name, str) and lowered in dir_name.lower():
                matches.append(row)

    if not matches:
        raise ValueError(f"No bundle matched {raw!r} under {search_root}.")
    if len(matches) > 1:
        options = ", ".join(row.get("dir_name") or row["path"] for row in matches[:5])
        raise ValueError(f"Bundle selector {raw!r} is ambiguous under {search_root}. Matches: {options}")
    return Path(matches[0]["path"])


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
    client = WowheadClient(expansion=cfg.expansion)
    html, guide_id, lookup_url, metadata, canonical_url = _fetch_guide_page(
        ctx,
        client,
        guide_ref=guide_ref,
    )

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


@app.command("guide-full")
def guide_full(
    ctx: typer.Context,
    guide_ref: str = typer.Argument(
        ...,
        help="Guide id, Wowhead guide URL, or guide path.",
    ),
    max_links: int = typer.Option(
        250,
        "--max-links",
        min=1,
        max=2000,
        help="Maximum linked entities to return.",
    ),
    include_replies: bool = typer.Option(
        False,
        "--include-replies/--no-include-replies",
        help="Include inline replies already present in the embedded comments payload.",
    ),
) -> None:
    payload, _html = _build_guide_full_payload(
        ctx,
        guide_ref=guide_ref,
        max_links=max_links,
        include_replies=include_replies,
    )
    _emit(ctx, payload)


@app.command("guide-export")
def guide_export(
    ctx: typer.Context,
    guide_ref: str = typer.Argument(
        ...,
        help="Guide id, Wowhead guide URL, or guide path.",
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True,
        help="Directory to write exported guide assets into. Defaults to ./wowhead_exports/<guide-slug>/",
    ),
    max_links: int = typer.Option(
        250,
        "--max-links",
        min=1,
        max=2000,
        help="Maximum linked entities to return.",
    ),
    include_replies: bool = typer.Option(
        False,
        "--include-replies/--no-include-replies",
        help="Include inline replies already present in the embedded comments payload.",
    ),
) -> None:
    payload, html = _build_guide_full_payload(
        ctx,
        guide_ref=guide_ref,
        max_links=max_links,
        include_replies=include_replies,
    )
    export_dir = (out or _default_guide_export_dir(payload)).expanduser()
    export_dir.mkdir(parents=True, exist_ok=True)

    files_written: dict[str, str] = {}

    guide_json_path = export_dir / "guide.json"
    _write_json_file(guide_json_path, payload)
    files_written["guide_json"] = guide_json_path.name

    page_html_path = export_dir / "page.html"
    page_html_path.write_text(html, encoding="utf-8")
    files_written["page_html"] = page_html_path.name

    body = payload.get("body")
    if isinstance(body, dict) and _write_optional_text_file(export_dir / "body.markup.txt", body.get("raw_markup")):
        files_written["body_markup"] = "body.markup.txt"

    navigation = payload.get("navigation")
    if isinstance(navigation, dict) and _write_optional_text_file(
        export_dir / "navigation.markup.txt",
        navigation.get("raw_markup"),
    ):
        files_written["navigation_markup"] = "navigation.markup.txt"

    sections = body.get("section_chunks") if isinstance(body, dict) else []
    if isinstance(sections, list):
        _write_jsonl_file(export_dir / "sections.jsonl", sections)
        files_written["sections_jsonl"] = "sections.jsonl"

    nav_links = navigation.get("links") if isinstance(navigation, dict) else []
    if isinstance(nav_links, list):
        _write_jsonl_file(export_dir / "navigation-links.jsonl", nav_links)
        files_written["navigation_links_jsonl"] = "navigation-links.jsonl"

    linked_entities = payload.get("linked_entities")
    linked_items = linked_entities.get("items") if isinstance(linked_entities, dict) else []
    if isinstance(linked_items, list):
        _write_jsonl_file(export_dir / "linked-entities.jsonl", linked_items)
        files_written["linked_entities_jsonl"] = "linked-entities.jsonl"

    gatherer_entities = payload.get("gatherer_entities")
    gatherer_items = gatherer_entities.get("items") if isinstance(gatherer_entities, dict) else []
    if isinstance(gatherer_items, list):
        _write_jsonl_file(export_dir / "gatherer-entities.jsonl", gatherer_items)
        files_written["gatherer_entities_jsonl"] = "gatherer-entities.jsonl"

    comments = payload.get("comments")
    comment_items = comments.get("items") if isinstance(comments, dict) else []
    if isinstance(comment_items, list):
        _write_jsonl_file(export_dir / "comments.jsonl", comment_items)
        files_written["comments_jsonl"] = "comments.jsonl"

    structured_data = payload.get("structured_data")
    if structured_data is not None:
        structured_data_path = export_dir / "structured-data.json"
        _write_json_file(structured_data_path, structured_data)
        files_written["structured_data_json"] = structured_data_path.name

    manifest = {
        "ok": True,
        "export_version": 1,
        "expansion": payload.get("expansion"),
        "output_dir": str(export_dir),
        "guide": payload.get("guide"),
        "page": {
            "title": payload.get("page", {}).get("title") if isinstance(payload.get("page"), dict) else None,
            "canonical_url": payload.get("page", {}).get("canonical_url")
            if isinstance(payload.get("page"), dict)
            else None,
        },
        "counts": {
            "sections": len(sections) if isinstance(sections, list) else 0,
            "navigation_links": len(nav_links) if isinstance(nav_links, list) else 0,
            "linked_entities": len(linked_items) if isinstance(linked_items, list) else 0,
            "gatherer_entities": len(gatherer_items) if isinstance(gatherer_items, list) else 0,
            "comments": len(comment_items) if isinstance(comment_items, list) else 0,
        },
        "files": files_written,
    }
    manifest_path = export_dir / "manifest.json"
    _write_json_file(manifest_path, manifest)
    manifest["files"]["manifest_json"] = manifest_path.name
    _write_json_file(manifest_path, manifest)

    _emit(ctx, manifest)


@app.command("guide-query")
def guide_query(
    ctx: typer.Context,
    bundle_ref: str = typer.Argument(
        ...,
        help="Bundle directory path or selector (guide id, bundle dir name, or title match).",
    ),
    query: str = typer.Argument(..., help="Query text to search within the exported bundle."),
    limit: int = typer.Option(
        5,
        "--limit",
        min=1,
        max=50,
        help="Maximum matches to return per category and in the flattened top list.",
    ),
    kind: list[str] = typer.Option(
        [],
        "--kind",
        help="Restrict search kinds. Repeat or pass comma-separated values from: sections, navigation, linked_entities, gatherer_entities, comments.",
    ),
    section_title: str | None = typer.Option(
        None,
        "--section-title",
        help="Restrict section searching to section titles containing this text.",
    ),
    root: Path | None = typer.Option(
        None,
        "--root",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Root directory used to resolve non-path bundle selectors. Defaults to ./wowhead_exports/.",
    ),
) -> None:
    try:
        export_dir = _resolve_corpus_ref(bundle_ref, root=root)
        corpus = _load_guide_export(export_dir)
    except (ValueError, json.JSONDecodeError) as exc:
        _fail(ctx, "invalid_bundle", str(exc))
    try:
        selected_kinds = _normalize_query_kinds(kind)
    except ValueError as exc:
        _fail(ctx, "invalid_argument", str(exc))

    def kind_enabled(value: str) -> bool:
        if not selected_kinds:
            return True
        return value in selected_kinds

    manifest = corpus["manifest"]
    page = manifest.get("page") if isinstance(manifest, dict) else {}
    guide = manifest.get("guide") if isinstance(manifest, dict) else {}
    page_url = page.get("canonical_url") if isinstance(page, dict) else None
    section_title_filter = section_title.strip().lower() if isinstance(section_title, str) and section_title.strip() else None

    section_matches: list[dict[str, Any]] = []
    if kind_enabled("sections"):
        for row in corpus["sections"]:
            if not isinstance(row, dict):
                continue
            title = row.get("title")
            if section_title_filter and (
                not isinstance(title, str) or section_title_filter not in title.lower()
            ):
                continue
            score = _score_text_match(query, row.get("title"), row.get("content_text"))
            if score <= 0:
                continue
            section_matches.append(
                {
                    "kind": "section",
                    "score": score + _score_text_match(query, row.get("title")),
                    "ordinal": row.get("ordinal"),
                    "level": row.get("level"),
                    "title": row.get("title"),
                    "preview": _truncate_preview(row.get("content_text") or ""),
                    "citation_url": page_url,
                }
            )
    section_matches.sort(key=lambda row: (-row["score"], row.get("ordinal") or 0))

    navigation_matches: list[dict[str, Any]] = []
    if kind_enabled("navigation"):
        for row in corpus["navigation_links"]:
            if not isinstance(row, dict):
                continue
            score = _score_text_match(query, row.get("label"), row.get("url"))
            if score <= 0:
                continue
            navigation_matches.append(
                {
                    "kind": "navigation",
                    "score": score + _score_text_match(query, row.get("label")),
                    "label": row.get("label"),
                    "url": row.get("url"),
                    "citation_url": row.get("source_url") or page_url,
                }
            )
    navigation_matches.sort(key=lambda row: (-row["score"], row.get("label") or ""))

    linked_entity_matches: list[dict[str, Any]] = []
    if kind_enabled("linked_entities"):
        for row in corpus["linked_entities"]:
            if not isinstance(row, dict):
                continue
            score = _score_text_match(query, row.get("name"), row.get("entity_type"), row.get("url"))
            if score <= 0:
                continue
            linked_entity_matches.append(
                {
                    "kind": "linked_entity",
                    "score": score + _score_text_match(query, row.get("name")),
                    "entity_type": row.get("entity_type"),
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "url": row.get("url"),
                    "citation_url": row.get("citation_url"),
                }
            )
    linked_entity_matches.sort(key=lambda row: (-row["score"], row.get("entity_type") or "", row.get("id") or 0))

    gatherer_matches: list[dict[str, Any]] = []
    if kind_enabled("gatherer_entities"):
        for row in corpus["gatherer_entities"]:
            if not isinstance(row, dict):
                continue
            score = _score_text_match(query, row.get("name"), row.get("entity_type"), row.get("url"))
            if score <= 0:
                continue
            gatherer_matches.append(
                {
                    "kind": "gatherer_entity",
                    "score": score + _score_text_match(query, row.get("name")),
                    "entity_type": row.get("entity_type"),
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "url": row.get("url"),
                    "citation_url": row.get("citation_url"),
                }
            )
    gatherer_matches.sort(key=lambda row: (-row["score"], row.get("entity_type") or "", row.get("id") or 0))

    comment_matches: list[dict[str, Any]] = []
    if kind_enabled("comments"):
        for row in corpus["comments"]:
            if not isinstance(row, dict):
                continue
            score = _score_text_match(query, row.get("user"), row.get("body"))
            if score <= 0:
                continue
            comment_matches.append(
                {
                    "kind": "comment",
                    "score": score + _score_text_match(query, row.get("user")),
                    "id": row.get("id"),
                    "user": row.get("user"),
                    "preview": _truncate_preview(row.get("body") or ""),
                    "citation_url": row.get("citation_url"),
                }
            )
    comment_matches.sort(key=lambda row: (-row["score"], row.get("id") or 0))

    top_matches = (
        section_matches[:limit]
        + navigation_matches[:limit]
        + linked_entity_matches[:limit]
        + gatherer_matches[:limit]
        + comment_matches[:limit]
    )
    top_matches.sort(key=lambda row: (-row["score"], row.get("kind") or ""))

    payload = {
        "ok": True,
        "query": query,
        "output_dir": str(export_dir),
        "guide": guide,
        "page": page,
        "filters": {
            "kinds": list(selected_kinds),
            "section_title": section_title_filter,
        },
        "matches": {
            "sections": section_matches[:limit],
            "navigation": navigation_matches[:limit],
            "linked_entities": linked_entity_matches[:limit],
            "gatherer_entities": gatherer_matches[:limit],
            "comments": comment_matches[:limit],
        },
        "counts": {
            "sections": len(section_matches),
            "navigation": len(navigation_matches),
            "linked_entities": len(linked_entity_matches),
            "gatherer_entities": len(gatherer_matches),
            "comments": len(comment_matches),
        },
        "top": top_matches[:limit],
    }
    _emit(ctx, payload)


@app.command("guide-bundle-list")
def guide_bundle_list(
    ctx: typer.Context,
    root: Path | None = typer.Option(
        None,
        "--root",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Root directory containing exported guide bundles. Defaults to ./wowhead_exports/.",
    ),
) -> None:
    resolved_root = (root or _guide_export_root()).expanduser()
    bundles = _discover_guide_corpora(resolved_root)
    payload = {
        "ok": True,
        "root": str(resolved_root),
        "count": len(bundles),
        "bundles": bundles,
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
