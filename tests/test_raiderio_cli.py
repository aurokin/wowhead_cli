from __future__ import annotations

import json

import httpx
from typer.testing import CliRunner

from raiderio_cli.main import app as raiderio_app

runner = CliRunner()


def test_raiderio_doctor_reports_phase_one_capabilities() -> None:
    result = runner.invoke(raiderio_app, ["doctor"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider"] == "raiderio"
    assert payload["status"] == "ready"
    assert payload["auth"]["required"] is False
    assert payload["auth"]["deferred"] is True
    assert payload["capabilities"]["character"] == "ready"
    assert payload["capabilities"]["search"] == "ready"


def test_raiderio_search_returns_ranked_matches(monkeypatch) -> None:
    monkeypatch.setattr(
        "raiderio_cli.main.RaiderIOClient.search",
        lambda self, *, term, kind=None: {
            "matches": [
                {
                    "type": "guild",
                    "name": "Liquid",
                    "data": {
                        "id": 1,
                        "name": "Liquid",
                        "displayName": "Liquid",
                        "faction": "horde",
                        "region": {"slug": "us", "name": "United States & Oceania"},
                        "realm": {"slug": "illidan", "name": "Illidan"},
                        "path": "/guilds/us/illidan/Liquid",
                    },
                },
                {
                    "type": "guild",
                    "name": "Liquid",
                    "data": {
                        "id": 2,
                        "name": "Liquid",
                        "displayName": "Liquid",
                        "faction": "alliance",
                        "region": {"slug": "us", "name": "United States & Oceania"},
                        "realm": {"slug": "gnomeregan", "name": "Gnomeregan"},
                        "path": "/guilds/us/gnomeregan/Liquid",
                    },
                },
            ]
        },
    )
    result = runner.invoke(raiderio_app, ["search", "Liquid guild", "--limit", "5"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["count"] == 2
    assert payload["results"][0]["kind"] == "guild"
    assert payload["results"][0]["realm"] == "illidan"
    assert "type_hint" in payload["results"][0]["ranking"]["match_reasons"]
    assert payload["results"][0]["follow_up"]["command"] == "raiderio guild us illidan Liquid"


def test_raiderio_resolve_returns_conservative_next_command(monkeypatch) -> None:
    monkeypatch.setattr(
        "raiderio_cli.main.RaiderIOClient.search",
        lambda self, *, term, kind=None: {
            "matches": [
                {
                    "type": "character",
                    "name": "Roguecane",
                    "data": {
                        "id": 39943,
                        "name": "Roguecane",
                        "faction": "horde",
                        "region": {"slug": "us", "name": "United States & Oceania"},
                        "realm": {"slug": "illidan", "name": "Illidan"},
                        "class": {"name": "Rogue", "slug": "rogue"},
                    },
                }
            ]
        },
    )
    result = runner.invoke(raiderio_app, ["resolve", "Roguecane"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["confidence"] == "high"
    assert payload["next_command"] == "raiderio character us illidan Roguecane"


def test_raiderio_resolve_stays_unresolved_for_ambiguous_match_set(monkeypatch) -> None:
    monkeypatch.setattr(
        "raiderio_cli.main.RaiderIOClient.search",
        lambda self, *, term, kind=None: {
            "matches": [
                {
                    "type": "guild",
                    "name": "Liquid",
                    "data": {
                        "id": 1,
                        "name": "Liquid",
                        "displayName": "Liquid",
                        "faction": "horde",
                        "region": {"slug": "us", "name": "United States & Oceania"},
                        "realm": {"slug": "illidan", "name": "Illidan"},
                        "path": "/guilds/us/illidan/Liquid",
                    },
                },
                {
                    "type": "guild",
                    "name": "Liquid",
                    "data": {
                        "id": 2,
                        "name": "Liquid",
                        "displayName": "Liquid",
                        "faction": "horde",
                        "region": {"slug": "us", "name": "United States & Oceania"},
                        "realm": {"slug": "area-52", "name": "Area 52"},
                        "path": "/guilds/us/area-52/Liquid",
                    },
                },
            ]
        },
    )
    result = runner.invoke(raiderio_app, ["resolve", "Liquid guild"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["resolved"] is False
    assert payload["next_command"] is None
    assert payload["fallback_search_command"] == 'raiderio search "Liquid"'


def test_raiderio_character_summary(monkeypatch) -> None:
    def fake_profile(self, *, region: str, realm: str, name: str, fields: str = ""):  # noqa: ANN001
        assert region == "us"
        assert realm == "illidan"
        assert name == "Roguecane"
        return {
            "name": "Roguecane",
            "region": "us",
            "realm": "Illidan",
            "race": "Blood Elf",
            "class": "Rogue",
            "active_spec_name": "Subtlety",
            "faction": "horde",
            "profile_url": "https://raider.io/characters/us/illidan/Roguecane",
            "thumbnail_url": "https://example.test/thumb.jpg",
            "guild": {"name": "Liquid", "realm": "Illidan", "region": "us"},
            "raid_progression": {
                "tier-mn-1": {
                    "summary": "3/8H",
                    "total_bosses": 8,
                    "normal_bosses_killed": 8,
                    "heroic_bosses_killed": 3,
                    "mythic_bosses_killed": 0,
                }
            },
            "mythic_plus_scores_by_season": [
                {
                    "season": "season-tww-3",
                    "scores": {"all": 1234.5},
                    "segments": {"all": {"color": "#abcdef"}},
                }
            ],
            "mythic_plus_ranks": {"overall": {"world": 50, "region": 10, "realm": 1}},
            "mythic_plus_recent_runs": [
                {
                    "mythic_level": 12,
                    "completed_at": "2026-03-10T12:00:00Z",
                    "num_chests": 2,
                    "clear_time_ms": 1200000,
                    "keystone_time_ms": 1500000,
                    "dungeon": {"name": "The Dawnbreaker", "slug": "the-dawnbreaker"},
                }
            ],
        }

    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.character_profile", fake_profile)
    result = runner.invoke(raiderio_app, ["character", "us", "illidan", "Roguecane"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["character"]["name"] == "Roguecane"
    assert payload["guild"]["name"] == "Liquid"
    assert payload["mythic_plus"]["current_score"] == 1234.5
    assert payload["raiding"]["progression"][0]["raid_slug"] == "tier-mn-1"


def test_raiderio_guild_summary(monkeypatch) -> None:
    def fake_profile(self, *, region: str, realm: str, name: str, fields: str = ""):  # noqa: ANN001
        return {
            "name": "Liquid",
            "region": "us",
            "realm": "Illidan",
            "faction": "horde",
            "profile_url": "https://raider.io/guilds/us/illidan/Liquid",
            "raid_progression": {
                "tier-mn-1": {
                    "summary": "8/8M",
                    "total_bosses": 8,
                    "normal_bosses_killed": 8,
                    "heroic_bosses_killed": 8,
                    "mythic_bosses_killed": 8,
                }
            },
            "raid_rankings": {
                "tier-mn-1": {
                    "normal": {"world": 0, "region": 0, "realm": 0},
                    "heroic": {"world": 0, "region": 0, "realm": 0},
                    "mythic": {"world": 1, "region": 1, "realm": 1},
                }
            },
            "members": [
                {"character": {"name": "Roguecane", "realm": "Illidan", "class": "Rogue", "active_spec_name": "Subtlety"}},
                {"character": {"name": "Ruinmkv", "realm": "Illidan", "class": "Paladin", "active_spec_name": "Retribution"}},
            ],
        }

    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.guild_profile", fake_profile)
    result = runner.invoke(raiderio_app, ["guild", "us", "illidan", "Liquid"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["guild"]["name"] == "Liquid"
    assert payload["guild"]["member_count"] == 2
    assert payload["raiding"]["rankings"][0]["raid_slug"] == "tier-mn-1"
    assert payload["roster_preview"][0]["name"] == "Roguecane"


def test_raiderio_mythic_plus_runs_summary(monkeypatch) -> None:
    def fake_runs(self, *, season: str | None, region: str, dungeon: str, affixes: str | None, page: int):  # noqa: ANN001
        assert region == "world"
        return {
            "season": "season-tww-3",
            "region": "world",
            "dungeon": "all",
            "rankings": [
                {
                    "rank": 1,
                    "score": 581.5,
                    "run": {
                        "mythic_level": 26,
                        "completed_at": "2026-01-21T18:27:09.000Z",
                        "weekly_modifiers": [{"slug": "tyrannical"}],
                        "dungeon": {"name": "The Dawnbreaker", "slug": "the-dawnbreaker"},
                        "roster": [
                            {"character": {"name": "Cotti", "realm": {"slug": "tarren-mill"}, "region": {"slug": "eu"}}, "role": "dps"}
                        ],
                    },
                }
            ],
        }

    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.mythic_plus_runs", fake_runs)
    result = runner.invoke(raiderio_app, ["mythic-plus-runs"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["runs"][0]["rank"] == 1
    assert payload["runs"][0]["roster"][0]["name"] == "Cotti"


def test_raiderio_http_error_maps_to_structured_error(monkeypatch) -> None:
    request = httpx.Request("GET", "https://raider.io/api/v1/characters/profile")
    response = httpx.Response(404, request=request, json={"message": "Character not found"})

    def fake_profile(self, *, region: str, realm: str, name: str, fields: str = ""):  # noqa: ANN001
        raise httpx.HTTPStatusError("not found", request=request, response=response)

    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.character_profile", fake_profile)
    result = runner.invoke(raiderio_app, ["character", "us", "illidan", "Missing"])
    assert result.exit_code == 1

    payload = json.loads(result.stderr)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"
