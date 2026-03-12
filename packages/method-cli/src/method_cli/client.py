from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import httpx

from method_cli.page_parser import guide_ref_parts, guide_url, parse_guide_page, parse_sitemap_guides
from warcraft_api.cache import CacheSettings, CacheTTLConfig, build_cache_store
from warcraft_api.http import DEFAULT_RETRY_ATTEMPTS, request_with_retries
from warcraft_content.paths import provider_cache_root

METHOD_BASE_URL = "https://www.method.gg"
METHOD_SITEMAP_URL = f"{METHOD_BASE_URL}/sitemap.xml"
DEFAULT_CACHE_DIR = provider_cache_root("method") / "http"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if value < 0:
        raise ValueError(f"{name} must be >= 0.")
    return value


def load_method_cache_settings_from_env() -> tuple[CacheSettings, int, int]:
    backend = os.getenv("METHOD_CACHE_BACKEND", "file").strip().lower()
    if backend in {"none", "off", "disabled"}:
        enabled = False
        backend = "file"
    elif backend in {"file", "redis"}:
        enabled = True
    else:
        raise ValueError("METHOD_CACHE_BACKEND must be one of: file, redis, none.")

    cache_dir = Path(os.getenv("METHOD_CACHE_DIR", str(DEFAULT_CACHE_DIR))).expanduser()
    prefix = os.getenv("METHOD_REDIS_PREFIX", "method_cli").strip()
    if not prefix:
        raise ValueError("METHOD_REDIS_PREFIX cannot be empty.")
    redis_url = os.getenv("METHOD_REDIS_URL")
    if redis_url is not None:
        redis_url = redis_url.strip() or None
    sitemap_ttl = _env_int("METHOD_SITEMAP_CACHE_TTL_SECONDS", 86400)
    page_ttl = _env_int("METHOD_PAGE_CACHE_TTL_SECONDS", 3600)
    settings = CacheSettings(
        enabled=enabled,
        backend=backend,
        cache_dir=cache_dir,
        redis_url=redis_url,
        prefix=prefix,
        ttls=CacheTTLConfig(
            search_suggestions=sitemap_ttl,
            guide_page_html=page_ttl,
            page_html=page_ttl,
        ),
    )
    return settings, sitemap_ttl, page_ttl


class MethodClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    ) -> None:
        self._http_client: httpx.Client | None = None
        settings, sitemap_ttl, page_ttl = load_method_cache_settings_from_env()
        self._timeout_seconds = timeout_seconds
        self._retry_attempts = max(1, retry_attempts)
        self._cache_settings = settings
        self._cache_store = build_cache_store(settings) if settings.enabled else None
        self._sitemap_ttl = sitemap_ttl
        self._page_ttl = page_ttl

    def close(self) -> None:
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> MethodClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=self._timeout_seconds, follow_redirects=True)
        return self._http_client

    def _cache_key(self, namespace: str, url: str) -> str:
        raw = f"{namespace}|{url}".encode("utf-8")
        return f"{namespace}:{hashlib.sha256(raw).hexdigest()}"

    def _read_cache(self, key: str) -> Any | None:
        if self._cache_store is None:
            return None
        return self._cache_store.get(key)

    def _write_cache(self, key: str, payload: Any, *, ttl_seconds: int) -> None:
        if self._cache_store is None:
            return
        self._cache_store.set(key, payload, ttl_seconds=ttl_seconds)

    def _get_text(self, url: str, *, namespace: str, ttl_seconds: int) -> str:
        key = self._cache_key(namespace, url)
        cached = self._read_cache(key)
        if isinstance(cached, str):
            return cached
        response = request_with_retries(
            self._client(),
            url,
            retry_attempts=self._retry_attempts,
        )
        text = response.text
        self._write_cache(key, text, ttl_seconds=ttl_seconds)
        return text

    def sitemap_guides(self) -> list[dict[str, Any]]:
        xml_text = self._get_text(METHOD_SITEMAP_URL, namespace="sitemap", ttl_seconds=self._sitemap_ttl)
        return parse_sitemap_guides(xml_text)

    def guide_page_html(self, guide_ref: str) -> tuple[str, str]:
        slug, section_slug = guide_ref_parts(guide_ref)
        url = guide_url(slug, section_slug)
        html = self._get_text(url, namespace="guide_page_html", ttl_seconds=self._page_ttl)
        return url, html

    def fetch_guide_page(self, guide_ref: str) -> dict[str, Any]:
        url, html = self.guide_page_html(guide_ref)
        return parse_guide_page(html, source_url=url)
