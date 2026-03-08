from __future__ import annotations

import json
from pathlib import Path

import pytest

from wowhead_cli.cache import (
    CacheTTLConfig,
    FileCacheStore,
    RedisCacheStore,
    load_cache_settings_from_env,
)
from wowhead_cli.wowhead_client import WowheadClient


def test_file_cache_store_roundtrips_and_expires(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = FileCacheStore(tmp_path)
    now = 1000.0
    monkeypatch.setattr("wowhead_cli.cache.time.time", lambda: now)

    store.set("search_suggestions:abc123", {"query": "thunderfury"}, ttl_seconds=60)
    assert store.get("search_suggestions:abc123") == {"query": "thunderfury"}

    cache_file = tmp_path / "search_suggestions" / "abc123.json"
    assert cache_file.exists()

    monkeypatch.setattr("wowhead_cli.cache.time.time", lambda: now + 61)
    assert store.get("search_suggestions:abc123") is None
    assert not cache_file.exists()


def test_redis_cache_store_uses_prefix_and_roundtrips() -> None:
    class FakeRedisClient:
        def __init__(self) -> None:
            self.values: dict[str, str] = {}
            self.set_calls: list[tuple[str, str, int]] = []

        def get(self, key: str) -> str | None:
            return self.values.get(key)

        def set(self, key: str, value: str, ex: int) -> None:
            self.values[key] = value
            self.set_calls.append((key, value, ex))

    fake_client = FakeRedisClient()

    class FakeRedisModule:
        @staticmethod
        def from_url(url: str, decode_responses: bool = True) -> FakeRedisClient:
            assert url == "redis://cache.example:6379/3"
            assert decode_responses is True
            return fake_client

    store = RedisCacheStore(
        redis_url="redis://cache.example:6379/3",
        prefix="wowhead_cli",
        import_module_func=lambda name: FakeRedisModule,
    )

    store.set("entity:abc123", {"entity": {"id": 19019}}, ttl_seconds=3600)
    assert fake_client.set_calls == [
        ("wowhead_cli:entity:abc123", json.dumps({"entity": {"id": 19019}}, separators=(",", ":")), 3600)
    ]
    assert store.get("entity:abc123") == {"entity": {"id": 19019}}


def test_load_cache_settings_from_env_supports_redis_and_ttl_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WOWHEAD_CACHE_BACKEND", "redis")
    monkeypatch.setenv("WOWHEAD_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("WOWHEAD_REDIS_URL", "redis://cache.example:6379/4")
    monkeypatch.setenv("WOWHEAD_REDIS_PREFIX", "wowhead_cli_test")
    monkeypatch.setenv("WOWHEAD_SEARCH_CACHE_TTL_SECONDS", "1200")
    monkeypatch.setenv("WOWHEAD_TOOLTIP_CACHE_TTL_SECONDS", "5400")

    settings = load_cache_settings_from_env()

    assert settings.enabled is True
    assert settings.backend == "redis"
    assert settings.cache_dir == (tmp_path / "cache")
    assert settings.redis_url == "redis://cache.example:6379/4"
    assert settings.prefix == "wowhead_cli_test"
    assert settings.ttls.search_suggestions == 1200
    assert settings.ttls.tooltip_meta == 5400
    assert settings.ttls.entity_page_html == 3600


def test_wowhead_client_uses_updated_default_cache_ttls() -> None:
    client = WowheadClient(cache_enabled=False, cache_ttls=CacheTTLConfig())
    assert client._cache_ttls.search_suggestions == 900
    assert client._cache_ttls.tooltip_meta == 3600
    assert client._cache_ttls.entity_page_html == 3600
    assert client._cache_ttls.guide_page_html == 3600
    assert client._cache_ttls.comment_replies == 1800
    assert client._cache_ttls.entity_response == 3600


def test_entity_response_cache_roundtrips_with_shape_flags(tmp_path: Path) -> None:
    client = WowheadClient(cache_dir=tmp_path, cache_backend="file")
    payload = {"entity": {"type": "item", "id": 19019, "name": "Thunderfury"}}

    client.set_cached_entity_response(
        payload,
        requested_type="item",
        requested_id=19019,
        data_env=None,
        include_comments=False,
        include_all_comments=False,
        linked_entity_preview_limit=0,
    )

    cached = client.get_cached_entity_response(
        requested_type="item",
        requested_id=19019,
        data_env=None,
        include_comments=False,
        include_all_comments=False,
        linked_entity_preview_limit=0,
    )
    assert cached == payload

    changed_shape = client.get_cached_entity_response(
        requested_type="item",
        requested_id=19019,
        data_env=None,
        include_comments=True,
        include_all_comments=False,
        linked_entity_preview_limit=0,
    )
    assert changed_shape is None
