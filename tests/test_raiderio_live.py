from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from raiderio_cli.main import app

runner = CliRunner()


def _payload_for(args: list[str]) -> dict[str, object]:
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


@pytest.mark.live
def test_live_raiderio_structured_guild_search_uses_direct_probe() -> None:
    payload = _payload_for(["search", "guild us illidan Liquid", "--limit", "5"])

    assert payload["count"] >= 1
    assert payload["results"][0]["kind"] == "guild"
    assert payload["results"][0]["follow_up"]["command"] == "raiderio guild us illidan Liquid"
    assert "structured_probe" in payload["results"][0]["ranking"]["match_reasons"]


@pytest.mark.live
def test_live_raiderio_structured_character_resolve_uses_direct_probe() -> None:
    payload = _payload_for(["resolve", "character us illidan Roguecane", "--limit", "5"])

    assert payload["resolved"] is True
    assert payload["next_command"] == "raiderio character us illidan Roguecane"
    assert payload["match"]["kind"] == "character"
    assert "structured_probe" in payload["match"]["ranking"]["match_reasons"]
