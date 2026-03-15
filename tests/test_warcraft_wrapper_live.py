from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from warcraft_cli.main import app

runner = CliRunner()


def _payload_for(args: list[str]) -> dict[str, object]:
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


@pytest.mark.live
def test_live_warcraft_search_expansion_filter_only_uses_supported_providers() -> None:
    payload = _payload_for(["--expansion", "wotlk", "search", "thunderfury", "--limit", "3"])

    assert payload["requested_expansion"] == "wotlk"
    assert payload["expansion_filter_active"] is True
    assert payload["included_providers"] == ["wowhead"]
    assert {row["provider"] for row in payload["excluded_providers"]} == {
        "method",
        "icy-veins",
        "raiderio",
        "warcraftlogs",
        "warcraft-wiki",
        "wowprogress",
        "simc",
    }
    assert all(row["provider"] == "wowhead" for row in payload["results"])


@pytest.mark.live
def test_live_warcraft_resolve_expansion_filter_does_not_resolve_to_retail_only_provider() -> None:
    payload = _payload_for(["--expansion", "wotlk", "resolve", "guild us illidan Liquid", "--limit", "3"])

    assert payload["requested_expansion"] == "wotlk"
    assert payload["expansion_filter_active"] is True
    assert payload["included_providers"] == ["wowhead"]
    assert payload["provider"] in {None, "wowhead"}
    assert payload["provider"] != "wowprogress"
    assert payload["provider"] != "raiderio"


@pytest.mark.live
def test_live_warcraft_search_retail_filter_is_not_same_as_unfiltered_search() -> None:
    payload = _payload_for(["--expansion", "retail", "search", "mistweaver monk guide", "--limit", "5"])

    assert payload["requested_expansion"] == "retail"
    assert payload["expansion_filter_active"] is True
    assert set(payload["included_providers"]) == {
        "wowhead",
        "method",
        "icy-veins",
        "raiderio",
        "warcraftlogs",
        "wowprogress",
    }
    assert {row["provider"] for row in payload["excluded_providers"]} == {"warcraft-wiki", "simc"}
    assert all(row["provider"] != "warcraft-wiki" for row in payload["results"])


@pytest.mark.live
def test_live_warcraft_resolve_retail_filter_can_use_fixed_retail_provider() -> None:
    payload = _payload_for(["--expansion", "retail", "resolve", "guild us illidan Liquid", "--limit", "3"])

    assert payload["requested_expansion"] == "retail"
    assert payload["expansion_filter_active"] is True
    assert set(payload["included_providers"]) == {
        "wowhead",
        "method",
        "icy-veins",
        "raiderio",
        "warcraftlogs",
        "wowprogress",
    }
    assert {row["provider"] for row in payload["excluded_providers"]} == {"warcraft-wiki", "simc"}
    assert payload["provider"] in {"wowprogress", "raiderio", "wowhead", None}
    assert payload["provider"] != "warcraft-wiki"


@pytest.mark.live
def test_live_warcraft_guild_contract() -> None:
    payload = _payload_for(["guild", "us", "Mal'Ganis", "gn"])

    assert payload["ok"] is True
    assert payload["query"] == {"region": "us", "realm": "mal-ganis", "name": "gn"}
    assert payload["sources"]["wowprogress"]["status"] == "ok"
    assert payload["sources"]["raiderio"]["status"] == "ok"


@pytest.mark.live
def test_live_warcraft_guild_ranks_contract() -> None:
    payload = _payload_for(["guild-ranks", "us", "Mal'Ganis", "gn"])

    assert payload["ok"] is True
    assert payload["source"] == "wowprogress"
    assert payload["count"] >= 1
    assert payload["tiers"][0]["raid"]
