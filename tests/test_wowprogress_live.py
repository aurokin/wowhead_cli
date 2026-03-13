from __future__ import annotations

import pytest
from typer.testing import CliRunner

from article_provider_testkit import payload_for_live, require_live
from wowprogress_cli.main import app

pytestmark = pytest.mark.live

runner = CliRunner()


def test_live_wowprogress_structured_guild_search_contract() -> None:
    require_live("WowProgress")
    payload = payload_for_live(runner, app, ["search", "guild us illidan Liquid", "--limit", "5"], provider_name="WowProgress")

    assert payload["count"] >= 1
    first = payload["results"][0]
    assert first["kind"] == "guild"
    assert first["follow_up"]["command"] == "wowprogress guild us illidan Liquid"
    assert "type_hint" in first["ranking"]["match_reasons"]


def test_live_wowprogress_structured_character_resolve_contract() -> None:
    require_live("WowProgress")
    payload = payload_for_live(
        runner,
        app,
        ["resolve", "character us illidan Imonthegcd", "--limit", "5"],
        provider_name="WowProgress",
    )

    assert payload["resolved"] is True
    assert payload["next_command"] == "wowprogress character us illidan Imonthegcd"
    assert payload["match"]["kind"] == "character"
    assert "exact_target_name" in payload["match"]["ranking"]["match_reasons"]


def test_live_wowprogress_short_exact_guild_resolve_contract() -> None:
    require_live("WowProgress")
    payload = payload_for_live(runner, app, ["resolve", "guild us area-52 xD", "--limit", "5"], provider_name="WowProgress")

    assert payload["resolved"] is True
    assert payload["next_command"] == "wowprogress guild us area-52 xD"
    assert payload["match"]["kind"] == "guild"
    assert "exact_target_name" in payload["match"]["ranking"]["match_reasons"]
    assert "exact_target_realm" in payload["match"]["ranking"]["match_reasons"]


def test_live_wowprogress_leaderboard_contract() -> None:
    require_live("WowProgress")
    payload = payload_for_live(runner, app, ["leaderboard", "pve", "us", "--limit", "5"], provider_name="WowProgress")

    assert payload["leaderboard"]["kind"] == "pve"
    assert payload["leaderboard"]["region"] == "us"
    assert payload["count"] == 5
    assert len(payload["entries"]) == 5
