from __future__ import annotations

from html import unescape
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

METHOD_BASE_URL = "https://www.method.gg"
WOWHEAD_LINK_RE = re.compile(
    r"^(?P<entity_type>achievement|currency|faction|item|mount|npc|object|pet|quest|spell|zone)=(?P<id>\d+)(?:/|$)"
)


def clean_text(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    text = unescape(re.sub(r"\s+", " ", value)).strip()
    return text or None


def guide_ref_parts(guide_ref: str) -> tuple[str, str | None]:
    raw = guide_ref.strip()
    if not raw:
        raise ValueError("Guide reference cannot be empty.")
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        path = parsed.path
    else:
        path = raw if raw.startswith("/") else f"/guides/{raw}"
    match = re.match(r"^/guides/(?P<slug>[^/]+)(?:/(?P<section>[^/?#]+))?/?$", path)
    if not match:
        raise ValueError(f"Unsupported Method guide reference: {guide_ref}")
    return match.group("slug"), match.group("section")


def guide_url(slug: str, section_slug: str | None = None) -> str:
    suffix = f"/{section_slug}" if section_slug else ""
    return f"{METHOD_BASE_URL}/guides/{slug}{suffix}"


def _meta_content(soup: BeautifulSoup, **attrs: str) -> str | None:
    tag = soup.find("meta", attrs=attrs)
    if tag is None:
        return None
    return clean_text(tag.get("content"))


def _link_href(soup: BeautifulSoup, **attrs: str) -> str | None:
    tag = soup.find("link", attrs=attrs)
    if tag is None:
        return None
    href = tag.get("href")
    if not isinstance(href, str):
        return None
    href = href.strip()
    return href or None


def _extract_navigation(soup: BeautifulSoup, *, current_url: str) -> list[dict[str, Any]]:
    current_path = urlparse(current_url).path.rstrip("/")
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for ordinal, anchor in enumerate(soup.select("ul.guide-navigation a"), start=1):
        href = anchor.get("href")
        if not isinstance(href, str):
            continue
        title = clean_text(anchor.get_text(" ", strip=True))
        if not title:
            continue
        url = urljoin(METHOD_BASE_URL, href)
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        path = urlparse(url).path.rstrip("/")
        _, section_slug = guide_ref_parts(url)
        parent = anchor.parent if isinstance(anchor.parent, Tag) else None
        classes = parent.get("class", []) if isinstance(parent, Tag) else []
        active = "active" in classes or path == current_path
        items.append(
            {
                "title": title,
                "url": url,
                "section_slug": section_slug or "introduction",
                "active": active,
                "ordinal": ordinal,
            }
        )
    return items


def _article_tag(soup: BeautifulSoup) -> Tag | None:
    article = soup.select_one("article.guide-main-content")
    if isinstance(article, Tag):
        return article
    return None


def _clone_article(article: Tag) -> Tag:
    cloned = BeautifulSoup(str(article), "html.parser").find("article")
    if not isinstance(cloned, Tag):
        raise ValueError("Failed to clone Method article node.")
    for node in cloned.select("script, style, noscript, .premium-video, .mobile-video-wrap"):
        node.decompose()
    return cloned


def _extract_headings(article: Tag) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    for ordinal, heading in enumerate(article.find_all(re.compile(r"^h[23]$")), start=1):
        title = clean_text(heading.get_text(" ", strip=True))
        if not title:
            continue
        headings.append(
            {
                "title": title,
                "level": int(heading.name[1]),
                "ordinal": ordinal,
            }
        )
    return headings


def _append_section_content(section: dict[str, Any], node: Any) -> None:
    if not isinstance(node, Tag):
        text = clean_text(str(node))
        if text:
            section["text_parts"].append(text)
        return
    html = str(node).strip()
    text = clean_text(node.get_text(" ", strip=True))
    if html:
        section["html_parts"].append(html)
    if text:
        section["text_parts"].append(text)


def _extract_sections(article: Tag, *, fallback_title: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    ordinal = 0
    for child in article.children:
        if not isinstance(child, Tag):
            continue
        if child.name in {"h2", "h3"}:
            title = clean_text(child.get_text(" ", strip=True))
            if not title:
                continue
            ordinal += 1
            current = {
                "title": title,
                "level": int(child.name[1]),
                "ordinal": ordinal,
                "html_parts": [],
                "text_parts": [],
            }
            sections.append(current)
            continue
        if current is None:
            ordinal += 1
            current = {
                "title": fallback_title,
                "level": 2,
                "ordinal": ordinal,
                "html_parts": [],
                "text_parts": [],
            }
            sections.append(current)
        _append_section_content(current, child)
    normalized: list[dict[str, Any]] = []
    for section in sections:
        text = clean_text(" ".join(section["text_parts"]))
        html = "\n".join(section["html_parts"]).strip()
        normalized.append(
            {
                "title": section["title"],
                "level": section["level"],
                "ordinal": section["ordinal"],
                "text": text or "",
                "html": html,
            }
        )
    return [section for section in normalized if section["text"] or section["html"]]


def _extract_linked_entities(article: Tag, *, source_url: str) -> list[dict[str, Any]]:
    items: dict[tuple[str, int], dict[str, Any]] = {}
    for anchor in article.find_all("a", href=True):
        href = anchor.get("href")
        if not isinstance(href, str):
            continue
        url = urljoin(source_url, href)
        parsed = urlparse(url)
        if "wowhead.com" not in parsed.netloc:
            continue
        path = parsed.path.lstrip("/")
        match = WOWHEAD_LINK_RE.match(path)
        if not match:
            continue
        entity_type = match.group("entity_type")
        entity_id = int(match.group("id"))
        key = (entity_type, entity_id)
        name = clean_text(anchor.get_text(" ", strip=True))
        record = items.get(key)
        if record is None:
            items[key] = {
                "type": entity_type,
                "id": entity_id,
                "name": name,
                "url": url,
                "source_url": source_url,
            }
            continue
        if not record.get("name") and name:
            record["name"] = name
    return sorted(items.values(), key=lambda row: (row["type"], row["id"]))


def parse_guide_page(html: str, *, source_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    canonical_url = _link_href(soup, rel="canonical") or source_url
    canonical_url = urljoin(METHOD_BASE_URL, canonical_url)
    guide_slug, section_slug = guide_ref_parts(canonical_url)
    page_title = clean_text(_meta_content(soup, property="og:title")) or clean_text(soup.title.get_text(" ", strip=True) if soup.title else None)
    description = _meta_content(soup, name="description")
    navigation = _extract_navigation(soup, current_url=canonical_url)
    active_nav = next((item for item in navigation if item["active"]), None)
    display_section_title = active_nav["title"] if active_nav is not None else (section_slug or "Introduction").replace("-", " ").title()
    patch = None
    patch_tag = soup.select_one(".guide-author")
    if isinstance(patch_tag, Tag):
        patch = clean_text(patch_tag.get_text(" ", strip=True))
    last_updated = None
    update_tag = soup.select_one(".guide-update-date")
    if isinstance(update_tag, Tag):
        last_updated = clean_text(update_tag.get_text(" ", strip=True))
    author = None
    author_tag = soup.select_one(".guides-author-block .author-name")
    if isinstance(author_tag, Tag):
        author = clean_text(author_tag.get_text(" ", strip=True))
    article_tag = _article_tag(soup)
    article_html = ""
    article_text = ""
    headings: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    linked_entities: list[dict[str, Any]] = []
    if article_tag is not None:
        article = _clone_article(article_tag)
        article_html = "".join(str(child) for child in article.contents).strip()
        article_text = clean_text(article.get_text("\n", strip=True)) or ""
        headings = _extract_headings(article)
        sections = _extract_sections(article, fallback_title=display_section_title)
        linked_entities = _extract_linked_entities(article, source_url=canonical_url)
    return {
        "page": {
            "title": page_title,
            "description": description,
            "canonical_url": canonical_url,
        },
        "guide": {
            "slug": guide_slug,
            "page_url": canonical_url,
            "section_slug": section_slug or "introduction",
            "section_title": display_section_title,
            "author": author,
            "last_updated": last_updated,
            "patch": patch,
        },
        "navigation": navigation,
        "article": {
            "html": article_html,
            "text": article_text,
            "headings": headings,
            "sections": sections,
        },
        "linked_entities": linked_entities,
    }


def parse_sitemap_guides(xml_text: str) -> list[dict[str, Any]]:
    urls = re.findall(r"<loc>(https://www\.method\.gg/guides/[^<]+)</loc>", xml_text)
    seen: set[str] = set()
    guides: list[dict[str, Any]] = []
    for url in urls:
        match = re.match(r"^https://www\.method\.gg/guides/(?P<slug>[^/]+)$", url)
        if not match:
            continue
        slug = match.group("slug")
        if slug in seen:
            continue
        seen.add(slug)
        name = clean_text(slug.replace("-", " ").title()) or slug
        guides.append(
            {
                "slug": slug,
                "name": name,
                "url": url,
            }
        )
    guides.sort(key=lambda row: row["name"].lower())
    return guides
