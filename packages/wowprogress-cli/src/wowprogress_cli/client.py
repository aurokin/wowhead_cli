from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from curl_cffi import requests

from warcraft_api.cache import CacheSettings, CacheTTLConfig, build_cache_store, load_prefixed_cache_settings_from_env
from warcraft_api.http import DEFAULT_RETRY_ATTEMPTS, RETRYABLE_STATUS_CODES, backoff_seconds
from warcraft_content.paths import provider_cache_root
from wowprogress_cli.page_parser import (
    WOWPROGRESS_BASE_URL,
    character_url,
    guild_url,
    leaderboard_url,
    parse_character_page,
    parse_guild_page,
    parse_pve_leaderboard_page,
)

DEFAULT_CACHE_DIR = provider_cache_root("wowprogress") / "http"
DEFAULT_IMPERSONATE = "chrome136"


class WowProgressClientError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def load_wowprogress_cache_settings_from_env() -> tuple[CacheSettings, int, int, int]:
    settings = load_prefixed_cache_settings_from_env(
        env_prefix="WOWPROGRESS",
        default_cache_dir=DEFAULT_CACHE_DIR,
        default_redis_prefix="wowprogress_cli",
        ttl_defaults=CacheTTLConfig(entity_page_html=900, guide_page_html=900, page_html=300),
        ttl_env_overrides={
            "entity_page_html": "WOWPROGRESS_GUILD_CACHE_TTL_SECONDS",
            "guide_page_html": "WOWPROGRESS_CHARACTER_CACHE_TTL_SECONDS",
            "page_html": "WOWPROGRESS_LEADERBOARD_CACHE_TTL_SECONDS",
        },
    )
    return settings, settings.ttls.entity_page_html, settings.ttls.guide_page_html, settings.ttls.page_html


class WowProgressClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        impersonate: str = DEFAULT_IMPERSONATE,
    ) -> None:
        self._session: requests.Session | None = None
        settings, guild_ttl, character_ttl, leaderboard_ttl = load_wowprogress_cache_settings_from_env()
        self._timeout_seconds = timeout_seconds
        self._retry_attempts = max(1, retry_attempts)
        self._impersonate = impersonate
        self._cache_store = build_cache_store(settings) if settings.enabled else None
        self._guild_ttl = guild_ttl
        self._character_ttl = character_ttl
        self._leaderboard_ttl = leaderboard_ttl

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None

    def __enter__(self) -> WowProgressClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _client(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _cache_key(self, namespace: str, params: dict[str, Any]) -> str:
        raw = json.dumps({"namespace": namespace, "params": params}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return f"{namespace}:{hashlib.sha256(raw).hexdigest()}"

    def _read_cache(self, key: str) -> str | None:
        if self._cache_store is None:
            return None
        payload = self._cache_store.get(key)
        return payload if isinstance(payload, str) else None

    def _write_cache(self, key: str, payload: str, *, ttl_seconds: int) -> None:
        if self._cache_store is None:
            return
        self._cache_store.set(key, payload, ttl_seconds=ttl_seconds)

    def _fetch_html(self, url: str, *, namespace: str, ttl_seconds: int) -> str:
        key = self._cache_key(namespace, {"url": url, "impersonate": self._impersonate})
        cached = self._read_cache(key)
        if cached is not None:
            return cached
        attempts = max(1, self._retry_attempts)
        for attempt in range(1, attempts + 1):
            try:
                response = self._client().get(
                    url,
                    impersonate=self._impersonate,
                    timeout=self._timeout_seconds,
                    allow_redirects=True,
                )
            except Exception as exc:  # noqa: BLE001
                if attempt >= attempts:
                    raise WowProgressClientError("network_error", f"WowProgress request failed: {exc}") from exc
                time.sleep(backoff_seconds(attempt))
                continue

            status_code = int(response.status_code)
            final_url = str(response.url)
            if status_code in RETRYABLE_STATUS_CODES and attempt < attempts:
                time.sleep(backoff_seconds(attempt))
                continue
            if status_code == 403 and "/search?" in final_url:
                raise WowProgressClientError("not_found", "WowProgress could not resolve that guild or character.")
            if status_code >= 400:
                raise WowProgressClientError("upstream_error", f"WowProgress request failed with HTTP {status_code}.")
            html = str(response.text)
            title_probe = html[:512].lower()
            if "just a moment" in title_probe:
                raise WowProgressClientError("blocked", "WowProgress returned a bot-protection challenge page.")
            self._write_cache(key, html, ttl_seconds=ttl_seconds)
            return html
        raise AssertionError("Unreachable retry loop exit.")

    def fetch_guild_page(self, *, region: str, realm: str, name: str) -> dict[str, Any]:
        url = guild_url(region, realm, name)
        html = self._fetch_html(url, namespace="guild_page", ttl_seconds=self._guild_ttl)
        return parse_guild_page(html, url=url, region=region, realm=realm, name=name)

    def fetch_character_page(self, *, region: str, realm: str, name: str) -> dict[str, Any]:
        url = character_url(region, realm, name)
        html = self._fetch_html(url, namespace="character_page", ttl_seconds=self._character_ttl)
        return parse_character_page(html, url=url, region=region, realm=realm, name=name)

    def fetch_pve_leaderboard(self, *, region: str, realm: str | None = None, limit: int = 25) -> dict[str, Any]:
        url = leaderboard_url(region, realm)
        html = self._fetch_html(url, namespace="pve_leaderboard", ttl_seconds=self._leaderboard_ttl)
        return parse_pve_leaderboard_page(html, url=url, region=region, realm=realm, limit=limit)
