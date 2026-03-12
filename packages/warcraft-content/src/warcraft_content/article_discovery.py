from __future__ import annotations

from typing import Any


def article_follow_up(provider_command: str, slug: str) -> dict[str, Any]:
    return {
        "recommended_surface": "guide",
        "recommended_command": f"{provider_command} guide {slug}",
        "reason": "guide_summary",
        "alternatives": [
            f"{provider_command} guide-full {slug}",
            f"{provider_command} guide-export {slug}",
        ],
    }


def article_candidate(
    *,
    slug: str,
    name: str,
    url: str,
    score: int,
    reasons: list[str],
    provider_command: str,
) -> dict[str, Any]:
    return {
        "id": slug,
        "name": name,
        "type_name": "Guide",
        "entity_type": "guide",
        "url": url,
        "ranking": {
            "score": score,
            "match_reasons": reasons,
        },
        "metadata": {
            "slug": slug,
        },
        "follow_up": article_follow_up(provider_command, slug),
    }


def sort_article_candidates(candidates: list[dict[str, Any]]) -> None:
    candidates.sort(key=lambda row: (-int(row["ranking"]["score"]), row["name"], row["id"]))


def article_search_payload(
    *,
    query: str,
    search_query: str,
    results: list[dict[str, Any]],
    total_count: int,
) -> dict[str, Any]:
    return {
        "query": query,
        "search_query": search_query,
        "count": total_count,
        "results": results,
    }


def article_resolve_payload(
    *,
    provider_command: str,
    query: str,
    search_query: str,
    results: list[dict[str, Any]],
    total_count: int,
    resolved: bool,
) -> dict[str, Any]:
    top = results[0] if results else None
    return {
        "query": query,
        "search_query": search_query,
        "resolved": resolved,
        "confidence": "high" if resolved else ("medium" if top else "none"),
        "match": top if top else None,
        "next_command": top["follow_up"]["recommended_command"] if resolved and top else None,
        "fallback_search_command": None if resolved else f"{provider_command} search {query!r}",
        "count": total_count,
        "candidates": results,
    }


def merge_article_linked_entities(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for page in pages:
        page_url = page["guide"]["page_url"]
        for row in page["linked_entities"]:
            key = (str(row["type"]), str(row["id"]))
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
    return sorted(merged.values(), key=lambda row: (str(row["type"]), str(row["id"])))
