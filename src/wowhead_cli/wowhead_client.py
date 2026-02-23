from __future__ import annotations

from typing import Any

import httpx
from wowhead_cli.expansion_profiles import (
    ExpansionProfile,
    build_comment_replies_url,
    build_entity_url,
    build_search_suggestions_url,
    build_search_url,
    build_tooltip_url,
    resolve_expansion,
)

WOWHEAD_BASE_URL = "https://www.wowhead.com"
NETHER_BASE_URL = "https://nether.wowhead.com"

SUGGESTION_TYPE_TO_ENTITY: dict[int, str] = {
    1: "npc",
    2: "object",
    3: "item",
    5: "quest",
    6: "spell",
    7: "achievement",
    111: "currency",
    112: "companion",
    101: "transmog-set",
}


class WowheadClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        expansion: str | ExpansionProfile | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self.expansion = expansion if isinstance(expansion, ExpansionProfile) else resolve_expansion(expansion)

    def _get_json(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        with httpx.Client(timeout=self._timeout_seconds, follow_redirects=True) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    def _get_text(self, url: str, *, params: dict[str, Any] | None = None) -> str:
        with httpx.Client(timeout=self._timeout_seconds, follow_redirects=True) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.text

    def search_suggestions(self, query: str) -> dict[str, Any]:
        url = build_search_suggestions_url(self.expansion)
        payload = self._get_json(url, params={"q": query})
        if isinstance(payload, dict):
            return payload
        raise ValueError("Unexpected response shape for search endpoint.")

    def tooltip(
        self,
        entity_type: str,
        entity_id: int,
        *,
        data_env: int | None = None,
    ) -> dict[str, Any]:
        url = build_tooltip_url(self.expansion, entity_type, entity_id)
        payload = self._get_json(url, params={"dataEnv": data_env or self.expansion.data_env})
        if isinstance(payload, dict):
            return payload
        raise ValueError("Unexpected response shape for tooltip endpoint.")

    def entity_page_html(self, entity_type: str, entity_id: int) -> str:
        return self._get_text(entity_url(entity_type, entity_id, expansion=self.expansion))

    def comment_replies(self, comment_id: int) -> list[dict[str, Any]]:
        url = build_comment_replies_url(self.expansion)
        payload = self._get_json(url, params={"id": comment_id})
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        return []


def suggestion_entity_type(result: dict[str, Any]) -> str | None:
    type_id = result.get("type")
    if not isinstance(type_id, int):
        return None
    return SUGGESTION_TYPE_TO_ENTITY.get(type_id)


def entity_url(
    entity_type: str,
    entity_id: int,
    expansion: str | ExpansionProfile | None = None,
) -> str:
    profile = expansion if isinstance(expansion, ExpansionProfile) else resolve_expansion(expansion)
    return build_entity_url(profile, entity_type, entity_id)


def search_url(query: str, expansion: str | ExpansionProfile | None = None) -> str:
    profile = expansion if isinstance(expansion, ExpansionProfile) else resolve_expansion(expansion)
    return build_search_url(profile, query)
