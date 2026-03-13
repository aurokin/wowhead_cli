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
