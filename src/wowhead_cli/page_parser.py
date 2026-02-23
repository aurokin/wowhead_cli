from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

from wowhead_cli.expansion_profiles import list_profiles
from wowhead_cli.wowhead_client import WOWHEAD_BASE_URL, entity_url

ENTITY_TYPES = {
    "achievement",
    "battle-pet",
    "currency",
    "faction",
    "item",
    "mount",
    "npc",
    "object",
    "pet",
    "quest",
    "recipe",
    "spell",
    "transmog-set",
    "zone",
}

GATHERER_TYPE_TO_ENTITY: dict[int, str] = {
    1: "npc",
    2: "object",
    3: "item",
    5: "quest",
    6: "spell",
}

EXPANSION_PREFIXES = frozenset(
    profile.path_prefix for profile in list_profiles() if profile.path_prefix
)

JSON_DECODER = json.JSONDecoder()

CANONICAL_RE = re.compile(
    r"""<link\b(?=[^>]*\brel=["']canonical["'])(?=[^>]*\bhref=["']([^"']+)["'])[^>]*>""",
    re.IGNORECASE,
)
META_OG_TITLE_RE = re.compile(
    r"""<meta\b(?=[^>]*\bproperty=["']og:title["'])(?=[^>]*\bcontent=["']([^"']+)["'])[^>]*>""",
    re.IGNORECASE,
)
META_DESCRIPTION_RE = re.compile(
    r"""<meta\b(?=[^>]*\bname=["']description["'])(?=[^>]*\bcontent=["']([^"']+)["'])[^>]*>""",
    re.IGNORECASE,
)
HREF_RE = re.compile(r"""href=(["'])(?P<href>.*?)\1""", re.IGNORECASE)
ENTITY_PATH_RE = re.compile(
    r"""^/(?:(?:[a-z]{2}(?:-[A-Z]{2})?|[a-z0-9-]+)/)?(?P<etype>[a-z-]+)=(?P<eid>\d+)""",
)
ASSIGNMENT_RE_TEMPLATE = r"""\bvar\s+{name}\s*="""
GATHERER_RE = re.compile(r"""WH\.Gatherer\.addData\(\s*(?P<dtype>\d+)\s*,\s*(?P<tree>\d+)\s*,\s*""")


def canonical_comment_url(page_url: str, comment_id: int) -> str:
    return f"{page_url}#comments:id={comment_id}"


def parse_page_metadata(html_text: str, *, fallback_url: str) -> dict[str, str | None]:
    canonical = _first_group(CANONICAL_RE, html_text) or fallback_url
    og_title = _first_group(META_OG_TITLE_RE, html_text)
    description = _first_group(META_DESCRIPTION_RE, html_text)
    return {
        "canonical_url": unescape(canonical),
        "title": unescape(og_title) if og_title else None,
        "description": unescape(description) if description else None,
    }


def parse_page_meta_json(html_text: str) -> dict[str, Any] | None:
    marker = 'id="data.pageMeta">'
    start_marker = html_text.find(marker)
    if start_marker < 0:
        return None
    start = start_marker + len(marker)
    end = html_text.find("</script>", start)
    if end < 0:
        return None
    payload = html_text[start:end].strip()
    if not payload:
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def extract_linked_entities_from_href(html_text: str, *, source_url: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()

    for match in HREF_RE.finditer(html_text):
        href_raw = unescape(match.group("href"))
        parsed = _parse_entity_ref(href_raw)
        if parsed is None:
            continue
        entity_type, entity_id, absolute_url = parsed
        key = (entity_type, entity_id)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            {
                "entity_type": entity_type,
                "id": entity_id,
                "name": None,
                "url": absolute_url,
                "citation_url": absolute_url,
                "source_url": source_url,
                "source_kind": "href",
            }
        )
    return records


def extract_gatherer_entities(html_text: str, *, source_url: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()

    for match in GATHERER_RE.finditer(html_text):
        data_type = int(match.group("dtype"))
        json_start = match.end()
        try:
            parsed, _ = JSON_DECODER.raw_decode(html_text[json_start:])
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue

        entity_type = GATHERER_TYPE_TO_ENTITY.get(data_type)
        if entity_type is None:
            continue

        for entity_id_raw, entity_payload in parsed.items():
            try:
                entity_id = int(entity_id_raw)
            except (TypeError, ValueError):
                continue
            key = (entity_type, entity_id)
            if key in seen:
                continue
            seen.add(key)
            name = None
            if isinstance(entity_payload, dict):
                name = entity_payload.get("name_enus") or entity_payload.get("name")
            records.append(
                {
                    "entity_type": entity_type,
                    "id": entity_id,
                    "name": name,
                    "url": entity_url(entity_type, entity_id),
                    "citation_url": source_url,
                    "source_url": source_url,
                    "source_kind": "gatherer",
                    "gatherer_data_type": data_type,
                }
            )
    return records


def extract_json_assignment(html_text: str, var_name: str) -> Any:
    pattern = re.compile(ASSIGNMENT_RE_TEMPLATE.format(name=re.escape(var_name)))
    match = pattern.search(html_text)
    if match is None:
        raise ValueError(f"Assignment for {var_name!r} not found.")
    index = match.end()
    while index < len(html_text) and html_text[index].isspace():
        index += 1
    parsed, _ = JSON_DECODER.raw_decode(html_text[index:])
    return parsed


def extract_comments_dataset(html_text: str) -> list[dict[str, Any]]:
    parsed = extract_json_assignment(html_text, "lv_comments0")
    if not isinstance(parsed, list):
        raise ValueError("lv_comments0 is not a list.")
    return [row for row in parsed if isinstance(row, dict)]


def normalize_comments(
    comments: list[dict[str, Any]],
    *,
    page_url: str,
    include_replies: bool,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for row in comments:
        comment_id = row.get("id")
        if not isinstance(comment_id, int):
            continue

        replies = row.get("replies")
        normalized_replies: list[dict[str, Any]] = []
        if include_replies and isinstance(replies, list):
            for reply in replies:
                if not isinstance(reply, dict):
                    continue
                reply_id = reply.get("id")
                if not isinstance(reply_id, int):
                    continue
                normalized_replies.append(
                    {
                        "id": reply_id,
                        "comment_id": comment_id,
                        "user": reply.get("username"),
                        "date": reply.get("creationdate"),
                        "rating": reply.get("rating"),
                        "body": reply.get("body"),
                        "citation_url": canonical_comment_url(page_url, comment_id),
                        "source_url": page_url,
                    }
                )

        normalized.append(
            {
                "id": comment_id,
                "number": row.get("number"),
                "user": row.get("user"),
                "date": row.get("date"),
                "rating": row.get("rating"),
                "body": row.get("body"),
                "nreplies": row.get("nreplies"),
                "deleted": row.get("deleted"),
                "outofdate": row.get("outofdate"),
                "citation_url": canonical_comment_url(page_url, comment_id),
                "source_url": page_url,
                "replies": normalized_replies if include_replies else [],
            }
        )
    return normalized


def sort_comments(comments: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    if mode == "rating":
        return sorted(
            comments,
            key=lambda row: (_int_or_zero(row.get("rating")), _safe_iso_ts(row.get("date"))),
            reverse=True,
        )
    if mode == "oldest":
        return sorted(comments, key=lambda row: _safe_iso_ts(row.get("date")))
    return sorted(comments, key=lambda row: _safe_iso_ts(row.get("date")), reverse=True)


def _int_or_zero(value: Any) -> int:
    if isinstance(value, int):
        return value
    return 0


def _safe_iso_ts(value: Any) -> float:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).timestamp()
        except ValueError:
            pass
    return float("-inf")


def _parse_entity_ref(href: str) -> tuple[str, int, str] | None:
    if not href or href.startswith("#"):
        return None
    absolute = urljoin(WOWHEAD_BASE_URL, href)
    parsed = urlparse(absolute)
    host = parsed.hostname or ""
    if host and "wowhead.com" not in host:
        return None
    match = ENTITY_PATH_RE.match(parsed.path)
    if match is None:
        return None
    entity_type = match.group("etype")
    if entity_type not in ENTITY_TYPES:
        return None
    entity_id = int(match.group("eid"))
    path_parts = [part for part in parsed.path.split("/") if part]
    if path_parts and path_parts[0] in EXPANSION_PREFIXES:
        canonical = f"{WOWHEAD_BASE_URL}/{path_parts[0]}/{entity_type}={entity_id}"
    else:
        canonical = entity_url(entity_type, entity_id)
    return entity_type, entity_id, canonical


def _first_group(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if match is None:
        return None
    return match.group(1)
