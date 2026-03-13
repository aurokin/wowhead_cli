from __future__ import annotations

from warcraft_core.paths import provider_cache_root, provider_config_root, provider_data_root


def test_provider_roots_use_xdg_homes(monkeypatch, tmp_path) -> None:  # noqa: ANN001
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    assert provider_config_root("simc") == (tmp_path / "config" / "warcraft" / "simc")
    assert provider_data_root("simc") == (tmp_path / "data" / "warcraft" / "simc")
    assert provider_cache_root("simc") == (tmp_path / "cache" / "warcraft" / "simc")
