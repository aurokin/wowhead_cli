from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from wowhead_cli.expansion_profiles import (
    ExpansionProfile,
    build_comment_replies_url,
    build_entity_url,
    build_guide_lookup_url,
    build_search_suggestions_url,
    build_search_url,
    build_tooltip_url,
    resolve_expansion,
)

WOWHEAD_BASE_URL = "https://www.wowhead.com"
NETHER_BASE_URL = "https://nether.wowhead.com"

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "wowhead_cli" / "http"
DEFAULT_RETRY_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

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
    100: "guide",
}


class WowheadClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        expansion: str | ExpansionProfile | None = None,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        cache_enabled: bool = True,
        cache_dir: Path | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._retry_attempts = max(1, retry_attempts)
        self._cache_enabled = cache_enabled
        self._cache_dir = (cache_dir or DEFAULT_CACHE_DIR).expanduser()
        self._http_client: httpx.Client | None = None
        self.expansion = expansion if isinstance(expansion, ExpansionProfile) else resolve_expansion(expansion)

    def __enter__(self) -> WowheadClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    def close(self) -> None:
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def _client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=self._timeout_seconds, follow_redirects=True)
        return self._http_client

    def _request_with_retries(self, url: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        attempts = self._retry_attempts
        for attempt in range(1, attempts + 1):
            try:
                response = self._client().get(url, params=params)
            except httpx.RequestError:
                if attempt >= attempts:
                    raise
                time.sleep(self._backoff_seconds(attempt))
                continue

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < attempts:
                response.close()
                time.sleep(self._backoff_seconds(attempt))
                continue

            response.raise_for_status()
            return response

        raise AssertionError("Unreachable retry loop exit.")

    def _backoff_seconds(self, attempt: int) -> float:
        base = 0.35 * (2 ** (attempt - 1))
        jitter = random.uniform(0.0, 0.12)
        return min(4.0, base + jitter)

    def _cache_key(self, namespace: str, url: str, params: dict[str, Any] | None) -> str:
        encoded = urlencode(sorted(params.items()), doseq=True) if params else ""
        raw = f"{namespace}|{url}|{encoded}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def _read_cache(self, key: str) -> Any | None:
        if not self._cache_enabled:
            return None
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        if not isinstance(data, dict):
            return None
        expires_at = data.get("expires_at")
        if not isinstance(expires_at, (int, float)):
            return None
        if expires_at <= time.time():
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        return data.get("payload")

    def _write_cache(self, key: str, payload: Any, *, ttl_seconds: int) -> None:
        if not self._cache_enabled:
            return
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_path(key)
            temp = path.with_suffix(".tmp")
            data = {
                "expires_at": time.time() + ttl_seconds,
                "payload": payload,
            }
            temp.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
            temp.replace(path)
        except Exception:  # noqa: BLE001
            return

    def _get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        cache_ttl_seconds: int | None = None,
        cache_namespace: str = "json",
    ) -> Any:
        cache_key = None
        if cache_ttl_seconds and cache_ttl_seconds > 0:
            cache_key = self._cache_key(cache_namespace, url, params)
            cached = self._read_cache(cache_key)
            if cached is not None:
                return cached

        response = self._request_with_retries(url, params=params)
        payload = response.json()

        if cache_key is not None:
            self._write_cache(cache_key, payload, ttl_seconds=cache_ttl_seconds)
        return payload

    def _get_text(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        cache_ttl_seconds: int | None = None,
        cache_namespace: str = "text",
    ) -> str:
        cache_key = None
        if cache_ttl_seconds and cache_ttl_seconds > 0:
            cache_key = self._cache_key(cache_namespace, url, params)
            cached = self._read_cache(cache_key)
            if isinstance(cached, str):
                return cached

        response = self._request_with_retries(url, params=params)
        payload = response.text

        if cache_key is not None:
            self._write_cache(cache_key, payload, ttl_seconds=cache_ttl_seconds)
        return payload

    def search_suggestions(self, query: str) -> dict[str, Any]:
        url = build_search_suggestions_url(self.expansion)
        payload = self._get_json(
            url,
            params={"q": query},
            cache_ttl_seconds=180,
            cache_namespace="search_suggestions",
        )
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
        payload = self._get_json(
            url,
            params={"dataEnv": data_env or self.expansion.data_env},
            cache_ttl_seconds=240,
            cache_namespace="tooltip",
        )
        if isinstance(payload, dict):
            return payload
        raise ValueError("Unexpected response shape for tooltip endpoint.")

    def entity_page_html(self, entity_type: str, entity_id: int) -> str:
        return self._get_text(
            entity_url(entity_type, entity_id, expansion=self.expansion),
            cache_ttl_seconds=240,
            cache_namespace="entity_page_html",
        )

    def guide_page_html(self, guide_id: int) -> str:
        return self._get_text(
            guide_url(guide_id, expansion=self.expansion),
            cache_ttl_seconds=240,
            cache_namespace="guide_page_html",
        )

    def page_html(self, page_url: str) -> str:
        return self._get_text(
            page_url,
            cache_ttl_seconds=240,
            cache_namespace="page_html",
        )

    def comment_replies(self, comment_id: int) -> list[dict[str, Any]]:
        url = build_comment_replies_url(self.expansion)
        payload = self._get_json(url, params={"id": comment_id}, cache_ttl_seconds=90, cache_namespace="comment_replies")
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


def guide_url(guide_id: int, expansion: str | ExpansionProfile | None = None) -> str:
    profile = expansion if isinstance(expansion, ExpansionProfile) else resolve_expansion(expansion)
    return build_guide_lookup_url(profile, guide_id)


def search_url(query: str, expansion: str | ExpansionProfile | None = None) -> str:
    profile = expansion if isinstance(expansion, ExpansionProfile) else resolve_expansion(expansion)
    return build_search_url(profile, query)
