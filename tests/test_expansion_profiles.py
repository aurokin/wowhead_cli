from __future__ import annotations

from wowhead_cli.expansion_profiles import (
    build_entity_url,
    build_guide_lookup_url,
    list_profiles,
    resolve_expansion,
)
from wowhead_cli.wowhead_client import entity_url, guide_url, search_url


def test_resolve_expansion_aliases() -> None:
    assert resolve_expansion(None).key == "retail"
    assert resolve_expansion("default").key == "retail"
    assert resolve_expansion("wrath").key == "wotlk"
    assert resolve_expansion("cataclysm").key == "cata"
    assert resolve_expansion("mists").key == "mop-classic"
    assert resolve_expansion("classicptr").key == "classic-ptr"


def test_build_entity_url_with_prefix() -> None:
    profile = resolve_expansion("wotlk")
    assert build_entity_url(profile, "item", 19019) == "https://www.wowhead.com/wotlk/item=19019"


def test_profile_list_contains_expected_keys() -> None:
    keys = {profile.key for profile in list_profiles()}
    assert {"retail", "classic", "tbc", "wotlk", "cata", "mop-classic"}.issubset(keys)


def test_public_url_helpers_support_expansion() -> None:
    assert entity_url("item", 19019, expansion="classic") == "https://www.wowhead.com/classic/item=19019"
    assert search_url("thunderfury", expansion="wotlk").startswith("https://www.wowhead.com/wotlk/search?q=")
    assert guide_url(3143, expansion="retail") == "https://www.wowhead.com/guide=3143"


def test_build_guide_lookup_url_with_prefix() -> None:
    profile = resolve_expansion("wotlk")
    assert build_guide_lookup_url(profile, 3143) == "https://www.wowhead.com/wotlk/guide=3143"
