from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SRC_DIRS = (
    ROOT / "packages" / "warcraft-core" / "src",
    ROOT / "packages" / "warcraft-api" / "src",
    ROOT / "packages" / "warcraft-content" / "src",
    ROOT / "packages" / "warcraft-cli" / "src",
    ROOT / "packages" / "wowhead-cli" / "src",
    ROOT / "packages" / "method-cli" / "src",
    ROOT / "packages" / "icy-veins-cli" / "src",
)

for package_src in reversed(PACKAGE_SRC_DIRS):
    path_str = str(package_src)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@pytest.fixture(autouse=True)
def disable_cache_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOWHEAD_CACHE_BACKEND", "none")
