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
