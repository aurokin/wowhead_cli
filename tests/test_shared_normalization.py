from __future__ import annotations

from warcraft_core.wow_normalization import normalize_name, normalize_region, primary_realm_slug, realm_matches, realm_slug_variants


def test_shared_normalization_region_and_name() -> None:
    assert normalize_region("NA") == "us"
    assert normalize_region("north-america") == "us"
    assert normalize_name("  gn   ") == "gn"


def test_shared_normalization_realm_variants_and_matching() -> None:
    assert realm_slug_variants("Mal'Ganis") == ["mal-ganis", "malganis"]
    assert primary_realm_slug("Area 52") == "area-52"
    assert realm_matches("Mal'Ganis", "malganis") is True
    assert realm_matches("Area 52", "US-Area 52") is True
