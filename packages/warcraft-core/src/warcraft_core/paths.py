from __future__ import annotations

import os
from pathlib import Path


def _xdg_root(env_name: str, fallback_suffix: tuple[str, ...]) -> Path:
    value = os.getenv(env_name)
    if value and value.strip():
        return Path(value).expanduser() / "warcraft"
    return Path.home().joinpath(*fallback_suffix, "warcraft")


def config_root() -> Path:
    return _xdg_root("XDG_CONFIG_HOME", (".config",))


def data_root() -> Path:
    return _xdg_root("XDG_DATA_HOME", (".local", "share"))


def cache_root() -> Path:
    return _xdg_root("XDG_CACHE_HOME", (".cache",))


def shared_root() -> Path:
    return data_root() / "shared"


def provider_data_root(provider: str) -> Path:
    return data_root() / provider


def provider_config_root(provider: str) -> Path:
    return config_root() / provider


def provider_cache_root(provider: str) -> Path:
    return cache_root() / provider
