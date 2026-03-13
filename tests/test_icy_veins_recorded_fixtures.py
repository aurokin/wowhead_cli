from __future__ import annotations

from pathlib import Path

from icy_veins_cli.page_parser import parse_guide_page

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "icy_veins"


def _load(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_recorded_class_hub_fixture_contract() -> None:
    payload = parse_guide_page(
        _load("class_hub.html"),
        source_url="https://www.icy-veins.com/wow/monk-guide",
    )

    assert payload["guide"]["slug"] == "monk-guide"
    assert payload["guide"]["content_family"] == "class_hub"
    assert payload["guide"]["supported_surface"] is True
    assert payload["guide"]["traversal_scope"] == "current_page"
    assert payload["navigation"][0]["section_slug"] == "death-knight-guide"


def test_recorded_role_guide_fixture_contract() -> None:
    payload = parse_guide_page(
        _load("role_guide.html"),
        source_url="https://www.icy-veins.com/wow/healing-guide",
    )

    assert payload["guide"]["slug"] == "healing-guide"
    assert payload["guide"]["content_family"] == "role_guide"
    assert payload["guide"]["supported_surface"] is True
    assert payload["guide"]["traversal_scope"] == "current_page"
    assert len(payload["article"]["sections"]) >= 1


def test_recorded_spec_guide_fixture_contract() -> None:
    payload = parse_guide_page(
        _load("spec_guide.html"),
        source_url="https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
    )

    assert payload["guide"]["slug"] == "mistweaver-monk-pve-healing-guide"
    assert payload["guide"]["content_family"] == "spec_guide"
    assert payload["guide"]["supported_surface"] is True
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["guide"]["author"] == "Dhaubbs"
    assert len(payload["article"]["headings"]) == len({row["title"] for row in payload["article"]["headings"]})
    assert payload["linked_entities"][0]["type"] in {"page", "spell"}


def test_recorded_easy_mode_fixture_contract() -> None:
    payload = parse_guide_page(
        _load("easy_mode.html"),
        source_url="https://www.icy-veins.com/wow/fury-warrior-pve-dps-easy-mode",
    )

    assert payload["guide"]["slug"] == "fury-warrior-pve-dps-easy-mode"
    assert payload["guide"]["content_family"] == "easy_mode"
    assert payload["guide"]["supported_surface"] is True
    assert payload["guide"]["traversal_scope"] == "family_navigation"


def test_recorded_raid_guide_fixture_contract() -> None:
    payload = parse_guide_page(
        _load("raid_guide.html"),
        source_url="https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-nerub-ar-palace-raid-guide",
    )

    assert payload["guide"]["slug"] == "mistweaver-monk-pve-healing-nerub-ar-palace-raid-guide"
    assert payload["guide"]["content_family"] == "raid_guide"
    assert payload["guide"]["supported_surface"] is True
    assert payload["guide"]["traversal_scope"] == "family_navigation"


def test_recorded_expansion_guide_fixture_contract() -> None:
    payload = parse_guide_page(
        _load("expansion_guide.html"),
        source_url="https://www.icy-veins.com/wow/mistweaver-monk-the-war-within-pve-guide",
    )

    assert payload["guide"]["slug"] == "mistweaver-monk-the-war-within-pve-guide"
    assert payload["guide"]["content_family"] == "expansion_guide"
    assert payload["guide"]["supported_surface"] is True
    assert payload["guide"]["traversal_scope"] == "family_navigation"


def test_recorded_special_event_guide_fixture_contract() -> None:
    payload = parse_guide_page(
        _load("special_event_guide.html"),
        source_url="https://www.icy-veins.com/wow/mistweaver-monk-mists-of-pandaria-remix-guide",
    )

    assert payload["guide"]["slug"] == "mistweaver-monk-mists-of-pandaria-remix-guide"
    assert payload["guide"]["content_family"] == "special_event_guide"
    assert payload["guide"]["supported_surface"] is True
    assert payload["guide"]["traversal_scope"] == "family_navigation"


def test_recorded_unsupported_page_fixture_contract() -> None:
    payload = parse_guide_page(
        _load("unsupported_page.html"),
        source_url="https://www.icy-veins.com/wow/latest-class-changes",
    )

    assert payload["guide"]["slug"] == "latest-class-changes"
    assert payload["guide"]["content_family"] is None
    assert payload["guide"]["supported_surface"] is False
    assert len(payload["article"]["sections"]) >= 1
