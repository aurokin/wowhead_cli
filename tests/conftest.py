from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def disable_cache_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOWHEAD_CACHE_BACKEND", "none")
