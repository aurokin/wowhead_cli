from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
import os
from pathlib import Path
import time
from typing import Any, Protocol

DEFAULT_CACHE_ROOT = Path.home() / ".cache" / "wowhead_cli"
DEFAULT_HTTP_CACHE_DIR = DEFAULT_CACHE_ROOT / "http"
DEFAULT_CACHE_PREFIX = "wowhead_cli"


@dataclass(frozen=True, slots=True)
class CacheTTLConfig:
    search_suggestions: int = 900
    tooltip_meta: int = 3600
    entity_page_html: int = 3600
    guide_page_html: int = 3600
    page_html: int = 3600
    comment_replies: int = 1800


@dataclass(frozen=True, slots=True)
class CacheSettings:
    enabled: bool
    backend: str
    cache_dir: Path
    redis_url: str | None
    prefix: str
    ttls: CacheTTLConfig


class CacheStore(Protocol):
    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, payload: Any, *, ttl_seconds: int) -> None: ...


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


def load_cache_settings_from_env() -> CacheSettings:
    backend = os.getenv("WOWHEAD_CACHE_BACKEND", "file").strip().lower()
    if backend in {"none", "off", "disabled"}:
        enabled = False
        backend = "file"
    elif backend in {"file", "redis"}:
        enabled = True
    else:
        raise ValueError("WOWHEAD_CACHE_BACKEND must be one of: file, redis, none.")

    cache_dir = Path(os.getenv("WOWHEAD_CACHE_DIR", str(DEFAULT_HTTP_CACHE_DIR))).expanduser()
    prefix = os.getenv("WOWHEAD_REDIS_PREFIX", DEFAULT_CACHE_PREFIX).strip()
    if not prefix:
        raise ValueError("WOWHEAD_REDIS_PREFIX cannot be empty.")

    redis_url = os.getenv("WOWHEAD_REDIS_URL")
    if redis_url is not None:
        redis_url = redis_url.strip() or None

    ttls = CacheTTLConfig(
        search_suggestions=_env_int("WOWHEAD_SEARCH_CACHE_TTL_SECONDS", 900),
        tooltip_meta=_env_int("WOWHEAD_TOOLTIP_CACHE_TTL_SECONDS", 3600),
        entity_page_html=_env_int("WOWHEAD_ENTITY_PAGE_CACHE_TTL_SECONDS", 3600),
        guide_page_html=_env_int("WOWHEAD_GUIDE_PAGE_CACHE_TTL_SECONDS", 3600),
        page_html=_env_int("WOWHEAD_PAGE_CACHE_TTL_SECONDS", 3600),
        comment_replies=_env_int("WOWHEAD_COMMENT_REPLIES_CACHE_TTL_SECONDS", 1800),
    )
    return CacheSettings(
        enabled=enabled,
        backend=backend,
        cache_dir=cache_dir,
        redis_url=redis_url,
        prefix=prefix,
        ttls=ttls,
    )


class FileCacheStore:
    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir.expanduser()

    def _path_for_key(self, key: str) -> Path:
        parts = [part for part in key.split(":") if part]
        if not parts:
            parts = ["cache"]
        return self._cache_dir.joinpath(*parts).with_suffix(".json")

    def get(self, key: str) -> Any | None:
        path = self._path_for_key(key)
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

    def set(self, key: str, payload: Any, *, ttl_seconds: int) -> None:
        try:
            path = self._path_for_key(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix(".tmp")
            data = {
                "expires_at": time.time() + ttl_seconds,
                "payload": payload,
            }
            temp.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
            temp.replace(path)
        except Exception:  # noqa: BLE001
            return


class RedisCacheStore:
    def __init__(
        self,
        *,
        redis_url: str,
        prefix: str,
        import_module_func: Any = importlib.import_module,
    ) -> None:
        if not redis_url:
            raise ValueError("WOWHEAD_REDIS_URL is required when WOWHEAD_CACHE_BACKEND=redis.")
        redis_module = import_module_func("redis")
        client = None
        from_url = getattr(redis_module, "from_url", None)
        if callable(from_url):
            client = from_url(redis_url, decode_responses=True)
        else:
            redis_cls = getattr(redis_module, "Redis", None)
            if redis_cls is not None:
                redis_cls_from_url = getattr(redis_cls, "from_url", None)
                if callable(redis_cls_from_url):
                    client = redis_cls_from_url(redis_url, decode_responses=True)
        if client is None:
            raise ValueError("Redis backend requires the 'redis' package with from_url support.")
        self._client = client
        self._prefix = prefix

    def _redis_key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def get(self, key: str) -> Any | None:
        try:
            raw = self._client.get(self._redis_key(key))
        except Exception:  # noqa: BLE001
            return None
        if raw in (None, ""):
            return None
        try:
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return None

    def set(self, key: str, payload: Any, *, ttl_seconds: int) -> None:
        try:
            self._client.set(
                self._redis_key(key),
                json.dumps(payload, separators=(",", ":")),
                ex=ttl_seconds,
            )
        except Exception:  # noqa: BLE001
            return


def build_cache_store(settings: CacheSettings) -> CacheStore | None:
    if not settings.enabled:
        return None
    if settings.backend == "file":
        return FileCacheStore(settings.cache_dir)
    if settings.backend == "redis":
        return RedisCacheStore(redis_url=settings.redis_url or "", prefix=settings.prefix)
    raise ValueError(f"Unsupported cache backend: {settings.backend}")
