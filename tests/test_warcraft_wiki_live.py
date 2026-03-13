from __future__ import annotations

import pytest
from typer.testing import CliRunner

from article_provider_testkit import payload_for_live, require_live
from warcraft_wiki_cli.main import app

pytestmark = pytest.mark.live

runner = CliRunner()


def test_live_warcraft_wiki_api_search_and_resolve_contract() -> None:
    require_live("Warcraft Wiki")
    search_payload = payload_for_live(runner, app, ["search", "CreateFrame", "--limit", "5"], provider_name="Warcraft Wiki")

    assert search_payload["count"] >= 1
    first = search_payload["results"][0]
    assert first["id"] == "API CreateFrame"
    assert first["metadata"]["content_family"] == "api_function"

    resolve_payload = payload_for_live(runner, app, ["resolve", "CreateFrame", "--limit", "5"], provider_name="Warcraft Wiki")
    assert resolve_payload["resolved"] is True
    assert resolve_payload["next_command"] == "warcraft-wiki article 'API CreateFrame'"


def test_live_warcraft_wiki_handler_resolve_contract() -> None:
    require_live("Warcraft Wiki")
    payload = payload_for_live(runner, app, ["resolve", "OnKeyDown", "--limit", "5"], provider_name="Warcraft Wiki")

    assert payload["resolved"] is True
    assert payload["match"]["metadata"]["content_family"] == "ui_handler"
    assert payload["match"]["id"] == "UIHANDLER OnKeyDown"


def test_live_warcraft_wiki_faction_query_cleanup_contract() -> None:
    require_live("Warcraft Wiki")
    payload = payload_for_live(runner, app, ["resolve", "faction argent dawn", "--limit", "5"], provider_name="Warcraft Wiki")

    assert payload["search_query"] == "argent dawn"
    assert payload["excluded_terms"] == ["faction"]
    assert payload["resolved"] is True
    assert payload["match"]["id"] == "Argent Dawn"


def test_live_warcraft_wiki_programming_article_contract() -> None:
    require_live("Warcraft Wiki")
    payload = payload_for_live(runner, app, ["article", "API_CreateFrame"], provider_name="Warcraft Wiki")

    assert payload["article"]["content_family"] == "api_function"
    assert payload["reference"]["programming_reference"] is True
    assert payload["reference"]["signature"] is not None
    assert "Main Menu" not in payload["content"]["text"]
    assert all("action=edit" not in row["url"] for row in payload["linked_entities"]["items"])


def test_live_warcraft_wiki_api_changes_article_contract() -> None:
    require_live("Warcraft Wiki")
    payload = payload_for_live(runner, app, ["article", "Patch 2.1.0/API changes"], provider_name="Warcraft Wiki")

    assert payload["article"]["content_family"] == "api_changes"
    assert payload["reference"]["programming_reference"] is True
    assert payload["reference"]["summary"] is not None
    assert payload["content"]["section_count"] >= 5


def test_live_warcraft_wiki_programming_howto_contract() -> None:
    require_live("Warcraft Wiki")
    payload = payload_for_live(runner, app, ["article", "Create a WoW AddOn in 15 Minutes"], provider_name="Warcraft Wiki")

    assert payload["article"]["content_family"] == "howto_programming"
    assert payload["reference"]["programming_reference"] is True
    assert "Main Menu" not in payload["content"]["text"]
    assert payload["content"]["section_count"] >= 5


def test_live_warcraft_wiki_system_article_contract() -> None:
    require_live("Warcraft Wiki")
    payload = payload_for_live(runner, app, ["article", "Renown"], provider_name="Warcraft Wiki")

    assert payload["article"]["content_family"] == "system_reference"
    assert payload["reference"]["content_family"] == "system_reference"
    assert payload["reference"]["summary"] is not None
    assert payload["content"]["section_count"] >= 3
    assert payload["navigation"]["count"] >= 3


def test_live_warcraft_wiki_expansion_article_contract() -> None:
    require_live("Warcraft Wiki")
    payload = payload_for_live(runner, app, ["article", "Expansion"], provider_name="Warcraft Wiki")

    assert payload["article"]["content_family"] == "expansion_reference"
    assert payload["reference"]["content_family"] == "expansion_reference"
    assert payload["reference"]["summary"] is not None
    assert payload["content"]["section_count"] >= 2


def test_live_warcraft_wiki_class_article_contract() -> None:
    require_live("Warcraft Wiki")
    payload = payload_for_live(runner, app, ["article", "Druid"], provider_name="Warcraft Wiki")

    assert payload["article"]["content_family"] == "class_reference"
    assert payload["reference"]["content_family"] == "class_reference"
    assert payload["reference"]["patch_changes"] is not None
    assert payload["content"]["section_count"] >= 10


def test_live_warcraft_wiki_faction_article_contract() -> None:
    require_live("Warcraft Wiki")
    payload = payload_for_live(runner, app, ["article", "Argent Dawn"], provider_name="Warcraft Wiki")

    assert payload["article"]["content_family"] == "faction_reference"
    assert payload["reference"]["content_family"] == "faction_reference"
    assert payload["reference"]["patch_changes"] is not None
    assert payload["content"]["section_count"] >= 8


def test_live_warcraft_wiki_lore_query_cleanup_and_article_contract() -> None:
    require_live("Warcraft Wiki")
    resolve_payload = payload_for_live(runner, app, ["resolve", "lore jaina proudmoore", "--limit", "5"], provider_name="Warcraft Wiki")
    assert resolve_payload["search_query"] == "jaina proudmoore"
    assert resolve_payload["excluded_terms"] == ["lore"]
    assert resolve_payload["resolved"] is True
    assert resolve_payload["match"]["id"] == "Jaina Proudmoore"

    payload = payload_for_live(runner, app, ["article", "Jaina Proudmoore"], provider_name="Warcraft Wiki")
    assert payload["article"]["content_family"] == "lore_reference"
    assert payload["reference"]["content_family"] == "lore_reference"
    assert payload["reference"]["patch_changes"] is not None


def test_live_warcraft_wiki_zone_query_cleanup_and_article_contract() -> None:
    require_live("Warcraft Wiki")
    resolve_payload = payload_for_live(runner, app, ["resolve", "zone elwynn forest", "--limit", "10"], provider_name="Warcraft Wiki")
    assert resolve_payload["search_query"] == "elwynn forest"
    assert resolve_payload["excluded_terms"] == ["zone"]
    assert resolve_payload["resolved"] is True
    assert resolve_payload["match"]["id"] == "Elwynn Forest"

    payload = payload_for_live(runner, app, ["article", "Elwynn Forest"], provider_name="Warcraft Wiki")
    assert payload["article"]["content_family"] == "zone_reference"
    assert payload["reference"]["content_family"] == "zone_reference"
    assert payload["reference"]["patch_changes"] is not None


def test_live_warcraft_wiki_guide_query_cleanup_and_article_contract() -> None:
    require_live("Warcraft Wiki")
    resolve_payload = payload_for_live(runner, app, ["resolve", "guide interface customization", "--limit", "10"], provider_name="Warcraft Wiki")
    assert resolve_payload["search_query"] == "interface customization"
    assert resolve_payload["excluded_terms"] == ["guide"]
    assert resolve_payload["resolved"] is True
    assert resolve_payload["match"]["id"] == "User interface customization guide"
    assert resolve_payload["match"]["metadata"]["content_family"] == "howto_programming"


def test_live_warcraft_wiki_profession_query_cleanup_and_article_contract() -> None:
    require_live("Warcraft Wiki")
    resolve_payload = payload_for_live(runner, app, ["resolve", "profession alchemy", "--limit", "10"], provider_name="Warcraft Wiki")
    assert resolve_payload["search_query"] == "alchemy"
    assert resolve_payload["excluded_terms"] == ["profession"]
    assert resolve_payload["resolved"] is True
    assert resolve_payload["match"]["id"] == "Alchemy"

    payload = payload_for_live(runner, app, ["article", "Alchemy"], provider_name="Warcraft Wiki")
    assert payload["article"]["content_family"] == "profession_reference"
    assert payload["reference"]["content_family"] == "profession_reference"
    assert payload["reference"]["patch_changes"] is not None


def test_live_warcraft_wiki_class_query_cleanup_contract() -> None:
    require_live("Warcraft Wiki")
    resolve_payload = payload_for_live(runner, app, ["resolve", "class druid", "--limit", "10"], provider_name="Warcraft Wiki")
    assert resolve_payload["search_query"] == "druid"
    assert resolve_payload["excluded_terms"] == ["class"]
    assert resolve_payload["resolved"] is True
    assert resolve_payload["match"]["id"] == "Druid"
    assert resolve_payload["match"]["metadata"]["content_family"] == "class_reference"


def test_live_warcraft_wiki_expansion_query_cleanup_and_article_contract() -> None:
    require_live("Warcraft Wiki")
    resolve_payload = payload_for_live(runner, app, ["resolve", "expansion legion", "--limit", "10"], provider_name="Warcraft Wiki")
    assert resolve_payload["search_query"] == "legion"
    assert resolve_payload["excluded_terms"] == ["expansion"]
    assert resolve_payload["resolved"] is True
    assert resolve_payload["match"]["id"] == "World of Warcraft: Legion"
    assert resolve_payload["match"]["metadata"]["content_family"] == "expansion_reference"
