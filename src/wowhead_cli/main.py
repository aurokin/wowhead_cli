from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Callable
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


@dataclass(slots=True)
class EntityAccessPlan:
    requested_type: str
    requested_id: int
    page_entity_type: str
    page_entity_id: int
    tooltip_entity_type: str | None
    tooltip_entity_id: int | None
    tooltip_from_page_metadata: bool = False
    page_from_tooltip_redirect: bool = False


LOW_SIGNAL_LINK_NAMES = frozenset(
    {
        "achievement",
        "battle pet",
        "currency",
        "faction",
        "guide",
        "item",
        "mount",
        "npc",
        "object",
        "pet",
        "quest",
        "recipe",
        "spell",
        "transmog set",
        "zone",
    }
)

PREVIEW_TYPE_PRIORITY: dict[str, int] = {
    "npc": 0,
    "quest": 1,
    "spell": 2,
    "object": 3,
    "item": 4,
    "achievement": 5,
    "zone": 6,
    "faction": 7,
    "currency": 8,
    "pet": 9,
    "battle-pet": 10,
    "mount": 11,
    "recipe": 12,
    "transmog-set": 13,
    "guide": 14,
}

CONTEXTUAL_PREVIEW_TYPE_PRIORITY: dict[str, dict[str, int]] = {
    "currency": {
        "npc": 0,
        "quest": 1,
        "spell": 2,
        "object": 3,
        "faction": 4,
        "zone": 5,
        "item": 6,
        "currency": 7,
    },
    "zone": {
        "npc": 0,
        "quest": 1,
        "object": 2,
        "spell": 3,
        "item": 4,
        "zone": 5,
        "faction": 6,
    },
    "item": {
        "npc": 0,
        "quest": 1,
        "spell": 2,
        "achievement": 3,
        "zone": 4,
        "object": 5,
        "item": 6,
    },
    "npc": {
        "npc": 0,
        "quest": 1,
        "spell": 2,
        "item": 3,
        "object": 4,
    },
    "quest": {
        "npc": 0,
        "item": 1,
        "quest": 2,
        "spell": 3,
        "object": 4,
        "currency": 5,
    },
    "guide": {
        "spell": 0,
        "item": 1,
        "npc": 2,
        "quest": 3,
        "object": 4,
    },
}


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


def _build_entity_access_plan(entity_type: str, entity_id: int) -> EntityAccessPlan:
    normalized_type = entity_type.strip().lower()
    if normalized_type == "faction":
        return EntityAccessPlan(
            requested_type=normalized_type,
            requested_id=entity_id,
            page_entity_type="faction",
            page_entity_id=entity_id,
            tooltip_entity_type=None,
            tooltip_entity_id=None,
            tooltip_from_page_metadata=True,
        )
    if normalized_type == "pet":
        return EntityAccessPlan(
            requested_type=normalized_type,
            requested_id=entity_id,
            page_entity_type="pet",
            page_entity_id=entity_id,
            tooltip_entity_type=None,
            tooltip_entity_id=None,
            tooltip_from_page_metadata=True,
        )
    if normalized_type == "recipe":
        return EntityAccessPlan(
            requested_type=normalized_type,
            requested_id=entity_id,
            page_entity_type="spell",
            page_entity_id=entity_id,
            tooltip_entity_type="spell",
            tooltip_entity_id=entity_id,
        )
    if normalized_type == "mount":
        return EntityAccessPlan(
            requested_type=normalized_type,
            requested_id=entity_id,
            page_entity_type=normalized_type,
            page_entity_id=entity_id,
            tooltip_entity_type="mount",
            tooltip_entity_id=entity_id,
            page_from_tooltip_redirect=True,
        )
    if normalized_type == "battle-pet":
        return EntityAccessPlan(
            requested_type=normalized_type,
            requested_id=entity_id,
            page_entity_type=normalized_type,
            page_entity_id=entity_id,
            tooltip_entity_type="battle-pet",
            tooltip_entity_id=entity_id,
            page_from_tooltip_redirect=True,
        )
    return EntityAccessPlan(
        requested_type=normalized_type,
        requested_id=entity_id,
        page_entity_type=normalized_type,
        page_entity_id=entity_id,
        tooltip_entity_type=normalized_type,
        tooltip_entity_id=entity_id,
    )


def _parse_tooltip_final_ref(final_url: str) -> tuple[str, int] | None:
    parsed = urlparse(final_url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 3 or parts[0] != "tooltip":
        return None
    entity_type = parts[1]
    raw_id = parts[2]
    if not raw_id.isdigit():
        return None
    return entity_type, int(raw_id)


def _build_tooltip_from_page_metadata(metadata: dict[str, str | None]) -> tuple[str | None, dict[str, Any]]:
    title = metadata.get("title")
    description = metadata.get("description")
    parts = [part.strip() for part in (title, description) if isinstance(part, str) and part.strip()]
    payload: dict[str, Any] = {}
    if parts:
        payload["text"] = " ".join(parts)
    return title if isinstance(title, str) and title.strip() else None, payload


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
    if payload.get("ok") is False:
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


def _normalize_link_name(value: Any, *, entity_type: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    name = value.strip()
    if not name:
        return None
    normalized = name.lower()
    if normalized.startswith("http") or normalized.startswith("www.") or "wowhead.com/" in normalized:
        return None
    if entity_type:
        normalized_type = entity_type.replace("-", " ").strip().lower()
        if normalized == normalized_type or normalized == normalized_type.replace(" ", ""):
            return None
    if normalized in LOW_SIGNAL_LINK_NAMES:
        return None
    return name


def _link_name_rank(record: dict[str, Any]) -> int:
    entity_type = record.get("entity_type") if isinstance(record.get("entity_type"), str) else None
    return 0 if _normalize_link_name(record.get("name"), entity_type=entity_type) is not None else 1


def _link_source_rank(record: dict[str, Any]) -> int:
    sources = _link_source_kinds(record)
    if len(sources) > 1:
        return 0
    if "gatherer" in sources:
        return 1
    if "href" in sources:
        return 2
    source_kind = record.get("source_kind")
    if source_kind == "gatherer":
        return 1
    if source_kind == "href":
        return 2
    return 3


def _preview_type_rank(record: dict[str, Any], *, source_entity_type: str) -> int:
    entity_type = record.get("entity_type")
    if not isinstance(entity_type, str):
        return 99
    contextual = CONTEXTUAL_PREVIEW_TYPE_PRIORITY.get(source_entity_type)
    if contextual is not None and entity_type in contextual:
        return contextual[entity_type]
    return PREVIEW_TYPE_PRIORITY.get(entity_type, 99)


def _preview_sort_key(record: dict[str, Any], *, source_entity_type: str) -> tuple[int, int, int, int]:
    link_id = record.get("id")
    return (
        _link_name_rank(record),
        _preview_type_rank(record, source_entity_type=source_entity_type),
        _link_source_rank(record),
        link_id if isinstance(link_id, int) else 0,
    )


SOURCE_KIND_PRIORITY = {
    "gatherer": 0,
    "href": 1,
}


def _link_source_kinds(record: dict[str, Any]) -> list[str]:
    raw_sources = record.get("sources")
    values: list[str] = []
    if isinstance(raw_sources, list):
        for raw in raw_sources:
            if isinstance(raw, str) and raw not in values:
                values.append(raw)
    source_kind = record.get("source_kind")
    if isinstance(source_kind, str) and source_kind not in values:
        values.append(source_kind)
    if not values:
        return []
    return sorted(values, key=lambda value: (SOURCE_KIND_PRIORITY.get(value, 99), value))


def _preferred_source_kind(record: dict[str, Any]) -> str | None:
    sources = _link_source_kinds(record)
    if sources:
        return sources[0]
    source_kind = record.get("source_kind")
    if isinstance(source_kind, str):
        return source_kind
    return None


def _merge_link_records(existing: dict[str, Any], candidate: dict[str, Any], *, link_type: str) -> dict[str, Any]:
    merged = dict(existing)

    existing_name = _normalize_link_name(merged.get("name"), entity_type=link_type)
    candidate_name = _normalize_link_name(candidate.get("name"), entity_type=link_type)
    if existing_name is None and candidate_name is not None:
        merged["name"] = candidate_name
    elif existing_name is not None:
        merged["name"] = existing_name

    for field in (
        "url",
        "citation_url",
        "source_url",
        "gatherer_data_type",
    ):
        if merged.get(field) in (None, "") and candidate.get(field) not in (None, ""):
            merged[field] = candidate[field]

    source_urls: list[str] = []
    for value in (merged.get("source_url"), candidate.get("source_url")):
        if isinstance(value, str) and value and value not in source_urls:
            source_urls.append(value)
    if source_urls:
        merged["source_urls"] = source_urls

    source_kinds: list[str] = []
    for value in _link_source_kinds(existing) + _link_source_kinds(candidate):
        if value not in source_kinds:
            source_kinds.append(value)
    if source_kinds:
        merged["sources"] = sorted(source_kinds, key=lambda value: (SOURCE_KIND_PRIORITY.get(value, 99), value))

    preferred_source_kind = _preferred_source_kind(merged) or _preferred_source_kind(candidate)
    if preferred_source_kind is not None:
        merged["source_kind"] = preferred_source_kind

    return merged


def _normalize_link_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    sources = _link_source_kinds(normalized)
    if sources:
        normalized["sources"] = sources
        normalized["source_kind"] = sources[0]
    elif "sources" in normalized:
        normalized.pop("sources", None)
    source_url = normalized.get("source_url")
    if isinstance(source_url, str) and source_url:
        normalized["source_urls"] = [source_url]
    return normalized


def _select_preview_records(
    records: list[dict[str, Any]],
    *,
    source_entity_type: str,
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0 or not records:
        return []
    ranked = sorted(records, key=lambda record: _preview_sort_key(record, source_entity_type=source_entity_type))
    selected: list[dict[str, Any]] = []
    selected_keys: set[tuple[str, int]] = set()
    used_types: set[str] = set()

    for unique_type_only in (True, False):
        for record in ranked:
            entity_type = record.get("entity_type")
            entity_id = record.get("id")
            if not isinstance(entity_type, str) or not isinstance(entity_id, int):
                continue
            key = (entity_type, entity_id)
            if key in selected_keys:
                continue
            if unique_type_only and entity_type in used_types:
                continue
            selected.append(record)
            selected_keys.add(key)
            used_types.add(entity_type)
            if len(selected) >= limit:
                return selected
    return selected[:limit]


def _dedupe_links(
    links: list[dict[str, Any]],
    *,
    entity_type: str,
    entity_id: int,
    max_links: int,
) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_index: dict[tuple[str, int], int] = {}
    for record in links:
        link_type = record.get("entity_type")
        link_id = record.get("id")
        if not isinstance(link_type, str) or not isinstance(link_id, int):
            continue
        if link_type == entity_type and link_id == entity_id:
            continue
        key = (link_type, link_id)
        existing_index = seen_index.get(key)
        if existing_index is not None:
            existing = deduped[existing_index]
            deduped[existing_index] = _merge_link_records(existing, record, link_type=link_type)
            continue
        seen_index[key] = len(deduped)
        deduped.append(_normalize_link_record(record))
        if len(deduped) >= max_links:
            break
    return deduped


BRACKET_FRAGMENT_RE = re.compile(r"""\[[^\]]*\]""")
ADJACENT_SENTENCE_RE = re.compile(r"""(?P<sentence>[A-Z][^.?!]{8,}?)(?:[.?!])\s+(?P=sentence)(?:[.?!])""")


def _clean_tooltip_text(text: str) -> str:
    cleaned = BRACKET_FRAGMENT_RE.sub(" ", text)
    cleaned = cleaned.replace("[", " ").replace("]", " ")
    cleaned = cleaned.replace(" .", ".").replace(" ,", ",")
    cleaned = " ".join(cleaned.split())
    while True:
        collapsed = ADJACENT_SENTENCE_RE.sub(r"\g<sentence>.", cleaned)
        if collapsed == cleaned:
            break
        cleaned = collapsed
    return cleaned.strip()


def _strip_leading_entity_name(text: str, *, entity_name: str | None) -> str:
    if not entity_name:
        return text
    if not text.startswith(entity_name):
        return text
    remainder = text[len(entity_name) :].lstrip(" :-")
    return remainder.strip() or text


def _build_tooltip_summary(text: str, *, entity_name: str | None, max_chars: int = 220) -> str | None:
    if not text:
        return None
    summary = _strip_leading_entity_name(text, entity_name=entity_name)
    if len(summary) <= max_chars:
        return summary
    clipped = summary[: max_chars - 3]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip(" ,;:-") + "..."


def _normalize_tooltip_payload(tooltip: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    entity_name = tooltip.get("name")
    name = entity_name if isinstance(entity_name, str) and entity_name.strip() else None

    tooltip_payload = dict(tooltip)
    tooltip_html = tooltip_payload.pop("tooltip", None)
    tooltip_payload.pop("name", None)

    if isinstance(tooltip_html, str):
        tooltip_payload["html"] = tooltip_html
        tooltip_text = _clean_tooltip_text(clean_markup_text(tooltip_html))
        tooltip_payload["text"] = tooltip_text
        tooltip_summary = _build_tooltip_summary(tooltip_text, entity_name=name)
        if tooltip_summary:
            tooltip_payload["summary"] = tooltip_summary

    return name, tooltip_payload


def _summarize_linked_entity(record: dict[str, Any]) -> dict[str, Any]:
    entity_type = record.get("entity_type") if isinstance(record.get("entity_type"), str) else None
    return {
        "type": record.get("entity_type"),
        "id": record.get("id"),
        "name": _normalize_link_name(record.get("name"), entity_type=entity_type),
        "url": record.get("url"),
    }


def _entity_page_fetch_more_command(entity_type: str, entity_id: int, link_count: int) -> str:
    max_links = min(max(link_count, 200), 2000)
    return f"wowhead entity-page {entity_type} {entity_id} --max-links {max_links}"


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


def _resolve_page_fetch_target(
    ctx: typer.Context,
    client: WowheadClient,
    *,
    entity_type: str,
    entity_id: int,
    data_env: int | None = None,
) -> EntityAccessPlan:
    plan = _build_entity_access_plan(entity_type, entity_id)
    if not plan.page_from_tooltip_redirect:
        return plan
    if plan.tooltip_entity_type is None or plan.tooltip_entity_id is None:
        _fail(ctx, "unsupported_entity_type", f"{entity_type!r} does not define a tooltip route for page resolution.")
    try:
        _, final_url = client.tooltip_with_metadata(
            plan.tooltip_entity_type,
            plan.tooltip_entity_id,
            data_env=data_env,
        )
    except httpx.HTTPStatusError as exc:
        _fail(ctx, "http_error", f"Wowhead returned HTTP {exc.response.status_code}")
    except httpx.HTTPError as exc:
        _fail(ctx, "network_error", str(exc))
    except ValueError as exc:
        _fail(ctx, "parse_error", str(exc))

    resolved = _parse_tooltip_final_ref(final_url)
    if resolved is None:
        _fail(ctx, "unexpected_response", f"Could not resolve a page target for {entity_type} {entity_id}.")
    page_entity_type, page_entity_id = resolved
    plan.page_entity_type = page_entity_type
    plan.page_entity_id = page_entity_id
    return plan


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


def _normalize_link_source_filters(values: list[str]) -> tuple[str, ...]:
    allowed = {"href", "gatherer", "multi"}
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        for candidate in raw.split(","):
            value = candidate.strip().lower()
            if not value:
                continue
            if value not in allowed:
                raise ValueError(
                    f"Unsupported linked source filter {value!r}. Expected one of: {', '.join(sorted(allowed))}."
                )
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
    return tuple(normalized)


def _linked_source_filter_matches(record: dict[str, Any], *, selected_sources: tuple[str, ...]) -> bool:
    if not selected_sources:
        return True
    sources = set(_link_source_kinds(record))
    if "multi" in selected_sources and len(sources) > 1:
        return True
    for source in selected_sources:
        if source == "multi":
            continue
        if source in sources:
            return True
    return False


def _linked_source_match_rank(record: dict[str, Any]) -> int:
    sources = _link_source_kinds(record)
    if len(sources) > 1:
        return 0
    if "gatherer" in sources:
        return 1
    if "href" in sources:
        return 2
    return 3


def _linked_entity_query_score(row: dict[str, Any], *, query: str) -> int:
    score = _score_text_match(query, row.get("name"), row.get("entity_type"), row.get("url"))
    if score <= 0:
        return 0
    score += _score_text_match(query, row.get("name"))
    if len(_link_source_kinds(row)) > 1:
        score += 1
    return score


GUIDE_QUERY_KIND_PRIORITY = {
    "linked_entity": 0,
    "section": 1,
    "navigation": 2,
    "comment": 3,
    "gatherer_entity": 4,
}


def _guide_query_match_sort_key(row: dict[str, Any]) -> tuple[int, int, int, int, str, int]:
    kind = row.get("kind") if isinstance(row.get("kind"), str) else ""
    entity_type = row.get("entity_type") if isinstance(row.get("entity_type"), str) else ""
    link_id = row.get("id")
    ordinal = row.get("ordinal")
    numeric = ordinal if isinstance(ordinal, int) else (link_id if isinstance(link_id, int) else 0)
    if kind == "linked_entity":
        return (
            -int(row.get("score") or 0),
            GUIDE_QUERY_KIND_PRIORITY.get(kind, 99),
            _linked_source_match_rank(row),
            _preview_type_rank(row, source_entity_type="guide"),
            entity_type,
            numeric,
        )
    return (
        -int(row.get("score") or 0),
        GUIDE_QUERY_KIND_PRIORITY.get(kind, 99),
        99,
        99,
        entity_type or kind,
        numeric,
    )


def _guide_query_top_dedupe_key(row: dict[str, Any]) -> tuple[str, int] | None:
    kind = row.get("kind")
    if kind not in {"linked_entity", "gatherer_entity"}:
        return None
    entity_type = row.get("entity_type")
    entity_id = row.get("id")
    if not isinstance(entity_type, str) or not isinstance(entity_id, int):
        return None
    return entity_type, entity_id


def _build_linked_entity_preview(
    links: list[dict[str, Any]],
    *,
    entity_type: str,
    entity_id: int,
    preview_limit: int,
    fetch_more_command: str | None = None,
    fetch_more_command_builder: Callable[[int], str] | None = None,
) -> dict[str, Any]:
    def render_fetch_more(count: int) -> str | None:
        if fetch_more_command_builder is not None:
            return fetch_more_command_builder(count)
        return fetch_more_command

    if preview_limit <= 0:
        return {
            "count": 0,
            "counts_by_type": {},
            "items": [],
            "more_available": False,
            "fetch_more_command": render_fetch_more(0),
        }
    deduped = _dedupe_links(
        links,
        entity_type=entity_type,
        entity_id=entity_id,
        max_links=max(len(links), 1),
    )
    preview_items = _select_preview_records(deduped, source_entity_type=entity_type, limit=preview_limit)
    counts_by_type: dict[str, int] = {}
    for row in deduped:
        link_type = row.get("entity_type")
        if not isinstance(link_type, str):
            continue
        counts_by_type[link_type] = counts_by_type.get(link_type, 0) + 1
    return {
        "count": len(deduped),
        "counts_by_type": counts_by_type,
        "items": [_summarize_linked_entity(row) for row in preview_items],
        "more_available": len(deduped) > len(preview_items),
        "fetch_more_command": render_fetch_more(len(deduped)),
    }


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


def _collect_guide_linked_entities(
    *,
    html: str,
    canonical_url: str,
    guide_id: int | None,
    max_links: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    guide_entity_id = guide_id or 0
    href_entities = _dedupe_links(
        extract_linked_entities_from_href(html, source_url=canonical_url),
        entity_type="guide",
        entity_id=guide_entity_id,
        max_links=max_links,
    )
    gatherer_entities = extract_gatherer_entities(html, source_url=canonical_url)
    merged_entities = _dedupe_links(
        href_entities + gatherer_entities,
        entity_type="guide",
        entity_id=guide_entity_id,
        max_links=max_links,
    )
    return href_entities, gatherer_entities, merged_entities


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

    href_entities, gatherer_entities, linked_entities = _collect_guide_linked_entities(
        html=html,
        canonical_url=canonical_url,
        guide_id=guide_id,
        max_links=max_links,
    )

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
        "expansion": cfg.expansion.key,
        "guide": {
            "input": guide_ref,
            "id": guide_id,
            "lookup_url": lookup_url,
            "page_url": canonical_url,
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
            "source_counts": {
                "href": len(href_entities),
                "gatherer": len(gatherer_entities),
                "merged": len(linked_entities),
            },
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
    linked_entity_preview_limit: int = typer.Option(
        5,
        "--linked-entity-preview-limit",
        min=0,
        max=50,
        help="Maximum linked entities to include as a lightweight preview. Set to 0 to disable.",
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

    href_entities, gatherer_entities, merged_entities = _collect_guide_linked_entities(
        html=html,
        canonical_url=canonical_url,
        guide_id=guide_id,
        max_links=5000,
    )
    linked_preview = _build_linked_entity_preview(
        merged_entities,
        entity_type="guide",
        entity_id=guide_id or 0,
        preview_limit=linked_entity_preview_limit,
        fetch_more_command=f"wowhead guide-full {guide_ref}",
    )
    linked_preview["source_counts"] = {
        "href": len(href_entities),
        "gatherer": len(gatherer_entities),
        "merged": linked_preview["count"],
    }

    page_meta_json = parse_page_meta_json(html)
    payload: dict[str, Any] = {
        "expansion": cfg.expansion.key,
        "guide": {
            "input": guide_ref,
            "id": guide_id,
            "lookup_url": lookup_url,
            "page_url": canonical_url,
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
        "linked_entities": linked_preview,
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
    linked_source: list[str] = typer.Option(
        [],
        "--linked-source",
        help="Restrict merged linked-entity matches by provenance. Repeat or pass comma-separated values from: href, gatherer, multi.",
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
    try:
        selected_link_sources = _normalize_link_source_filters(linked_source)
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
            if not _linked_source_filter_matches(row, selected_sources=selected_link_sources):
                continue
            score = _linked_entity_query_score(row, query=query)
            if score <= 0:
                continue
            linked_entity_matches.append(
                {
                    "kind": "linked_entity",
                    "score": score,
                    "entity_type": row.get("entity_type"),
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "url": row.get("url"),
                    "citation_url": row.get("citation_url"),
                    "sources": _link_source_kinds(row),
                }
            )
    linked_entity_matches.sort(key=_guide_query_match_sort_key)

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
    top_matches.sort(key=_guide_query_match_sort_key)
    deduped_top_matches: list[dict[str, Any]] = []
    seen_top_keys: set[tuple[str, int]] = set()
    for row in top_matches:
        dedupe_key = _guide_query_top_dedupe_key(row)
        if dedupe_key is not None:
            if dedupe_key in seen_top_keys:
                continue
            seen_top_keys.add(dedupe_key)
        deduped_top_matches.append(row)

    payload = {
        "query": query,
        "output_dir": str(export_dir),
        "guide": guide,
        "page": page,
        "filters": {
            "kinds": list(selected_kinds),
            "section_title": section_title_filter,
            "linked_sources": list(selected_link_sources),
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
        "top": deduped_top_matches[:limit],
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
    linked_entity_preview_limit: int = typer.Option(
        5,
        "--linked-entity-preview-limit",
        min=0,
        max=50,
        help="Maximum linked entities to include as a lightweight preview. Set to 0 to disable.",
    ),
) -> None:
    cfg = _cfg(ctx)
    client = WowheadClient(expansion=cfg.expansion)
    plan = _build_entity_access_plan(entity_type, entity_id)
    tooltip: dict[str, Any] = {}
    tooltip_final_url: str | None = None
    try:
        if plan.tooltip_entity_type is not None and plan.tooltip_entity_id is not None:
            if plan.page_from_tooltip_redirect:
                tooltip, tooltip_final_url = client.tooltip_with_metadata(
                    plan.tooltip_entity_type,
                    plan.tooltip_entity_id,
                    data_env=data_env,
                )
            else:
                tooltip = client.tooltip(
                    plan.tooltip_entity_type,
                    plan.tooltip_entity_id,
                    data_env=data_env,
                )
    except httpx.HTTPStatusError as exc:
        _fail(ctx, "http_error", f"Wowhead returned HTTP {exc.response.status_code}")
    except httpx.HTTPError as exc:
        _fail(ctx, "network_error", str(exc))
    except ValueError as exc:
        _fail(ctx, "parse_error", str(exc))

    if plan.page_from_tooltip_redirect and tooltip_final_url is not None:
        resolved = _parse_tooltip_final_ref(tooltip_final_url)
        if resolved is None:
            _fail(ctx, "unexpected_response", f"Could not resolve a page target for {entity_type} {entity_id}.")
        plan.page_entity_type, plan.page_entity_id = resolved

    canonical = entity_url(plan.page_entity_type, plan.page_entity_id, expansion=cfg.expansion)
    page_url = canonical
    entity_name, tooltip_payload = _normalize_tooltip_payload(tooltip)
    html: str | None = None
    metadata: dict[str, str | None] | None = None
    raw_comments: list[dict[str, Any]] = []
    sampled_comments: list[dict[str, Any]] = []
    all_comments: list[dict[str, Any]] = []
    top_comment_limit = 3

    if include_comments or linked_entity_preview_limit > 0:
        html, metadata = _fetch_entity_page(ctx, client, plan.page_entity_type, plan.page_entity_id)
        page_url = metadata["canonical_url"] or canonical
    elif plan.tooltip_from_page_metadata:
        html, metadata = _fetch_entity_page(ctx, client, plan.page_entity_type, plan.page_entity_id)
        page_url = metadata["canonical_url"] or canonical

    if plan.tooltip_from_page_metadata and metadata is not None:
        entity_name, tooltip_payload = _build_tooltip_from_page_metadata(metadata)

    if include_comments and html is not None:
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
        "expansion": cfg.expansion.key,
        "entity": {
            "type": entity_type,
            "id": entity_id,
            "name": entity_name,
            "page_url": page_url,
        },
    }
    if tooltip_payload:
        payload["tooltip"] = tooltip_payload
    if include_comments:
        payload["citations"] = {
            "comments": f"{page_url}#comments",
        }
    if html is not None and linked_entity_preview_limit > 0:
        payload["linked_entities"] = _build_linked_entity_preview(
            extract_linked_entities_from_href(html, source_url=page_url)
            + extract_gatherer_entities(html, source_url=page_url),
            entity_type=plan.page_entity_type,
            entity_id=plan.page_entity_id,
            preview_limit=linked_entity_preview_limit,
            fetch_more_command_builder=lambda count: _entity_page_fetch_more_command(entity_type, entity_id, count),
        )
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
    plan = _resolve_page_fetch_target(
        ctx,
        client,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    html, metadata = _fetch_entity_page(ctx, client, plan.page_entity_type, plan.page_entity_id)

    raw_canonical = metadata["canonical_url"] or entity_url(plan.page_entity_type, plan.page_entity_id, expansion=cfg.expansion)
    canonical_url = (
        _normalize_canonical_entity_url(
            raw_canonical,
            expansion=cfg.expansion,
            entity_type=plan.page_entity_type,
            entity_id=plan.page_entity_id,
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
        entity_type=plan.page_entity_type,
        entity_id=plan.page_entity_id,
        max_links=max_links,
    )

    page_meta_json = parse_page_meta_json(html)

    payload: dict[str, Any] = {
        "expansion": cfg.expansion.key,
        "normalize_canonical_to_expansion": cfg.normalize_canonical_to_expansion,
        "entity": {
            "type": entity_type,
            "id": entity_id,
            "page_url": canonical_url,
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
    linked_entity_preview_limit: int = typer.Option(
        5,
        "--linked-entity-preview-limit",
        min=0,
        max=50,
        help="Maximum linked entities to include as a lightweight preview. Set to 0 to disable.",
    ),
) -> None:
    if sort not in {"newest", "oldest", "rating"}:
        _fail(ctx, "invalid_argument", "sort must be one of: newest, oldest, rating.")

    cfg = _cfg(ctx)
    client = WowheadClient(expansion=cfg.expansion)
    plan = _resolve_page_fetch_target(
        ctx,
        client,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    html, metadata = _fetch_entity_page(ctx, client, plan.page_entity_type, plan.page_entity_id)
    raw_canonical = metadata["canonical_url"] or entity_url(plan.page_entity_type, plan.page_entity_id, expansion=cfg.expansion)
    canonical_url = (
        _normalize_canonical_entity_url(
            raw_canonical,
            expansion=cfg.expansion,
            entity_type=plan.page_entity_type,
            entity_id=plan.page_entity_id,
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
        "expansion": cfg.expansion.key,
        "normalize_canonical_to_expansion": cfg.normalize_canonical_to_expansion,
        "entity": {
            "type": entity_type,
            "id": entity_id,
            "page_url": canonical_url,
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
    if linked_entity_preview_limit > 0:
        payload["linked_entities"] = _build_linked_entity_preview(
            extract_linked_entities_from_href(html, source_url=canonical_url)
            + extract_gatherer_entities(html, source_url=canonical_url),
            entity_type=plan.page_entity_type,
            entity_id=plan.page_entity_id,
            preview_limit=linked_entity_preview_limit,
            fetch_more_command_builder=lambda count: _entity_page_fetch_more_command(entity_type, entity_id, count),
        )
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
                    "page_url": canonical_url,
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
            }
            for link_type, link_id in unique_pairs[:max_unique_links]
        ]

    payload = {
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
    }
    _emit(ctx, payload)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
