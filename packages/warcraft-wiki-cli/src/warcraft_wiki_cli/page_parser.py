from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import quote, unquote, urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

WIKI_BASE_URL = "https://warcraft.wiki.gg"


def normalize_article_ref(article_ref: str) -> str:
    value = article_ref.strip()
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        marker = "/wiki/"
        if marker in parsed.path:
            title = parsed.path.split(marker, 1)[1]
            value = unquote(title).replace("_", " ")
    elif value.startswith("/wiki/"):
        value = unquote(value.split("/wiki/", 1)[1]).replace("_", " ")
    return value.replace("_", " ").strip()


def article_slug(title: str) -> str:
    value = normalize_article_ref(title).lower()
    chars: list[str] = []
    previous_dash = False
    for ch in value:
        if ch.isalnum():
            chars.append(ch)
            previous_dash = False
            continue
        if not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-") or "article"


def article_url(title: str) -> str:
    normalized = normalize_article_ref(title).replace(" ", "_")
    return f"{WIKI_BASE_URL}/wiki/{quote(normalized, safe='/:()')}"


def _strip_html(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(" ", strip=True)


def parse_search_results(payload: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    query = payload.get("query") if isinstance(payload.get("query"), dict) else {}
    search_info = query.get("searchinfo") if isinstance(query.get("searchinfo"), dict) else {}
    total_hits = int(search_info.get("totalhits") or 0)
    rows: list[dict[str, Any]] = []
    for row in query.get("search") or []:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        snippet = _strip_html(str(row.get("snippet") or ""))
        rows.append(
            {
                "title": title,
                "pageid": row.get("pageid"),
                "timestamp": row.get("timestamp"),
                "snippet": snippet,
                "url": article_url(title),
            }
        )
    return total_hits, rows


def _heading_title(tag: Tag) -> str:
    headline = tag.find(class_="mw-headline")
    if headline is not None:
        return headline.get_text(" ", strip=True)
    return tag.get_text(" ", strip=True)


def _heading_anchor(tag: Tag, *, fallback_title: str) -> str:
    headline = tag.find(class_="mw-headline")
    if headline is not None and headline.get("id"):
        return str(headline["id"])
    if tag.get("id"):
        return str(tag["id"])
    return fallback_title.replace(" ", "_")


def _iter_root_children(root: Tag) -> Iterable[Tag | NavigableString]:
    for child in root.children:
        if isinstance(child, NavigableString):
            if child.strip():
                yield child
            continue
        if isinstance(child, Tag):
            yield child


def _render_nodes(nodes: list[Tag | NavigableString]) -> tuple[str, str]:
    html = "".join(str(node) for node in nodes).strip()
    if not html:
        return "", ""
    soup = BeautifulSoup(html, "html.parser")
    return html, soup.get_text(" ", strip=True)


def _extract_sections(root: Tag) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sections: list[dict[str, Any]] = []
    headings: list[dict[str, Any]] = []
    current_title = "Introduction"
    current_anchor = "Introduction"
    current_level = 1
    current_nodes: list[Tag | NavigableString] = []
    ordinal = 1

    def flush() -> None:
        nonlocal ordinal, current_nodes
        html, text = _render_nodes(current_nodes)
        if not text:
            current_nodes = []
            return
        sections.append(
            {
                "title": current_title,
                "level": current_level,
                "ordinal": ordinal,
                "anchor": current_anchor,
                "text": text,
                "html": html,
            }
        )
        ordinal += 1
        current_nodes = []

    for child in _iter_root_children(root):
        if isinstance(child, Tag) and child.name in {"h2", "h3", "h4", "h5", "h6"}:
            flush()
            current_title = _heading_title(child)
            current_anchor = _heading_anchor(child, fallback_title=current_title)
            current_level = int(child.name[1])
            headings.append(
                {
                    "title": current_title,
                    "level": current_level,
                    "ordinal": len(headings) + 1,
                    "anchor": current_anchor,
                }
            )
            continue
        current_nodes.append(child)
    flush()
    return headings, sections


def _extract_linked_entities(root: Tag) -> list[dict[str, Any]]:
    entities: dict[str, dict[str, Any]] = {}
    for link in root.find_all("a", href=True):
        href = str(link.get("href") or "")
        if not href.startswith("/wiki/"):
            continue
        if href.startswith("/wiki/File:") or href.startswith("/wiki/Category:") or href.startswith("/wiki/Special:"):
            continue
        if href.startswith("/wiki/Help:") or href.startswith("/wiki/Template:"):
            continue
        full_url = urljoin(WIKI_BASE_URL, href)
        if "#" in full_url:
            full_url = full_url.split("#", 1)[0]
        title = normalize_article_ref(href)
        entities[title] = {
            "type": "wiki_article",
            "id": title,
            "name": link.get_text(" ", strip=True) or title,
            "url": full_url,
        }
    return sorted(entities.values(), key=lambda row: str(row["id"]).lower())


def parse_article_page(payload: dict[str, Any], *, source_title: str) -> dict[str, Any]:
    parse = payload.get("parse") if isinstance(payload.get("parse"), dict) else {}
    title = str(parse.get("title") or source_title).strip()
    display_title = _strip_html(str(parse.get("displaytitle") or title))
    html = str((parse.get("text") or {}).get("*") or "")
    soup = BeautifulSoup(f"<div>{html}</div>", "html.parser")
    root = soup.select_one(".mw-parser-output")
    if root is None:
        root = soup.div if soup.div is not None else soup
    headings, sections = _extract_sections(root)
    text = root.get_text(" ", strip=True)
    navigation = [
        {
            "title": str(row.get("line") or ""),
            "url": f"{article_url(title)}#{row.get('anchor')}",
            "section_slug": str(row.get("anchor") or ""),
            "active": True,
            "ordinal": index + 1,
        }
        for index, row in enumerate(parse.get("sections") or [])
        if isinstance(row, dict) and row.get("line") and row.get("anchor")
    ]
    return {
        "article": {
            "title": title,
            "slug": article_slug(title),
            "display_title": display_title,
            "page_url": article_url(title),
            "section_slug": article_slug(title),
            "section_title": display_title or title,
            "page_count": 1,
        },
        "page": {
            "title": display_title or title,
            "description": sections[0]["text"][:240] if sections else text[:240],
            "canonical_url": article_url(title),
        },
        "navigation": {
            "count": len(navigation),
            "items": navigation,
        },
        "article_content": {
            "html": html,
            "text": text,
            "headings": headings,
            "sections": sections,
        },
        "linked_entities": _extract_linked_entities(root),
        "citations": {
            "page": article_url(title),
        },
    }
