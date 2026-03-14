from __future__ import annotations

import json

from typer.testing import CliRunner
from warcraftlogs_cli.main import app as warcraftlogs_app

runner = CliRunner()


class _FakeWarcraftLogsClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def rate_limit(self) -> dict[str, object]:
        return {
            "limitPerHour": 3600,
            "pointsSpentThisHour": 42,
            "pointsResetIn": 1800,
        }

    def regions(self) -> list[dict[str, object]]:
        return [
            {"id": 1, "compactName": "US", "name": "North America", "slug": "us"},
            {"id": 2, "compactName": "EU", "name": "Europe", "slug": "eu"},
        ]

    def server(self, *, region: str, slug: str) -> dict[str, object]:
        assert region == "us"
        assert slug == "illidan"
        return {
            "id": 10,
            "name": "Illidan",
            "normalizedName": "Illidan",
            "slug": "illidan",
            "region": {"id": 1, "compactName": "US", "name": "North America", "slug": "us"},
            "subregion": {"id": 100, "name": "Chicago"},
            "connectedRealmID": 57,
            "seasonID": 3,
        }

    def zones(self, *, expansion_id: int | None = None) -> list[dict[str, object]]:
        assert expansion_id == 12
        return [
            {
                "id": 38,
                "name": "Manaforge Omega",
                "frozen": False,
                "expansion": {"id": 12, "name": "Midnight"},
                "difficulties": [{"id": 5, "name": "Mythic", "sizes": []}],
                "encounters": [{"id": 3012, "name": "Dimensius", "journalID": 9001}],
            }
        ]

    def encounter(self, *, encounter_id: int) -> dict[str, object]:
        assert encounter_id == 3012
        return {
            "id": 3012,
            "name": "Dimensius, the All-Devouring",
            "journalID": 9001,
            "zone": {"id": 38, "name": "Manaforge Omega", "expansion": {"id": 12, "name": "Midnight"}},
        }

    def guild(self, *, region: str, realm: str, name: str, zone_id: int | None = None) -> dict[str, object]:
        assert region == "us"
        assert realm == "illidan"
        assert name == "Liquid"
        assert zone_id == 38
        return {
            "id": 5,
            "name": "Liquid",
            "description": "Top raiding guild",
            "competitionMode": False,
            "stealthMode": False,
            "tags": ["hall-of-fame"],
            "faction": {"id": 1, "name": "Horde"},
            "server": {
                "id": 10,
                "name": "Illidan",
                "normalizedName": "Illidan",
                "slug": "illidan",
                "region": {"id": 1, "compactName": "US", "name": "North America", "slug": "us"},
                "subregion": {"id": 100, "name": "Chicago"},
                "connectedRealmID": 57,
                "seasonID": 3,
            },
            "zoneRanking": {
                "progress": {
                    "worldRank": {"number": 2, "color": "legendary", "percentile": None},
                    "regionRank": {"number": 1, "color": "legendary", "percentile": None},
                    "serverRank": {"number": 1, "color": "legendary", "percentile": None},
                }
            },
        }

    def character(self, *, region: str, realm: str, name: str) -> dict[str, object]:
        assert region == "us"
        assert realm == "illidan"
        assert name == "Roguecane"
        return {
            "id": 77,
            "canonicalID": 88,
            "name": "Roguecane",
            "level": 80,
            "classID": 4,
            "hidden": False,
            "faction": {"id": 1, "name": "Horde"},
            "guildRank": 3,
            "server": {
                "id": 10,
                "name": "Illidan",
                "normalizedName": "Illidan",
                "slug": "illidan",
                "region": {"id": 1, "compactName": "US", "name": "North America", "slug": "us"},
                "subregion": {"id": 100, "name": "Chicago"},
                "connectedRealmID": 57,
                "seasonID": 3,
            },
            "guilds": [
                {
                    "id": 5,
                    "name": "Liquid",
                    "server": {
                        "id": 10,
                        "name": "Illidan",
                        "normalizedName": "Illidan",
                        "slug": "illidan",
                        "region": {"id": 1, "compactName": "US", "name": "North America", "slug": "us"},
                        "subregion": {"id": 100, "name": "Chicago"},
                        "connectedRealmID": 57,
                        "seasonID": 3,
                    },
                }
            ],
        }

    def report(self, *, code: str, allow_unlisted: bool = False) -> dict[str, object]:
        assert code == "abcd1234"
        assert allow_unlisted is True
        return {
            "code": "abcd1234",
            "title": "Manaforge Omega - Liquid",
            "startTime": 123,
            "endTime": 456,
            "visibility": "public",
            "archiveStatus": "archived",
            "segments": 1,
            "exportedSegments": 0,
            "zone": {"id": 38, "name": "Manaforge Omega"},
            "guild": {
                "id": 5,
                "name": "Liquid",
                "server": {
                    "id": 10,
                    "name": "Illidan",
                    "normalizedName": "Illidan",
                    "slug": "illidan",
                    "region": {"id": 1, "compactName": "US", "name": "North America", "slug": "us"},
                    "subregion": {"id": 100, "name": "Chicago"},
                    "connectedRealmID": 57,
                    "seasonID": 3,
                },
            },
        }

    def report_fights(self, *, code: str, difficulty: int | None = None, allow_unlisted: bool = False) -> dict[str, object]:
        assert code == "abcd1234"
        assert difficulty == 5
        assert allow_unlisted is False
        return {
            "code": "abcd1234",
            "title": "Manaforge Omega - Liquid",
            "zone": {"id": 38, "name": "Manaforge Omega"},
            "fights": [
                {
                    "id": 1,
                    "name": "Dimensius, the All-Devouring",
                    "encounterID": 3012,
                    "difficulty": 5,
                    "kill": True,
                    "completeRaid": False,
                    "startTime": 100,
                    "endTime": 200,
                    "fightPercentage": 100,
                    "bossPercentage": 0,
                    "averageItemLevel": 685.2,
                    "size": 20,
                }
            ],
        }


def test_warcraftlogs_doctor_reports_phase_one_capabilities(monkeypatch) -> None:
    monkeypatch.setattr(
        "warcraftlogs_cli.main.load_warcraftlogs_auth_config",
        lambda: type("Auth", (), {"configured": True, "env_file": "/tmp/.env.local"})(),
    )
    result = runner.invoke(warcraftlogs_app, ["doctor"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider"] == "warcraftlogs"
    assert payload["status"] == "ready"
    assert payload["auth"]["configured"] is True
    assert payload["capabilities"]["guild"] == "ready"
    assert payload["capabilities"]["report_fights"] == "ready"


def test_warcraftlogs_rate_limit_and_world_metadata_commands(monkeypatch) -> None:
    monkeypatch.setattr("warcraftlogs_cli.main._client", lambda ctx: _FakeWarcraftLogsClient())

    rate_limit_result = runner.invoke(warcraftlogs_app, ["rate-limit"])
    assert rate_limit_result.exit_code == 0
    rate_limit_payload = json.loads(rate_limit_result.stdout)
    assert rate_limit_payload["rate_limit"]["limit_per_hour"] == 3600

    regions_result = runner.invoke(warcraftlogs_app, ["regions"])
    assert regions_result.exit_code == 0
    regions_payload = json.loads(regions_result.stdout)
    assert regions_payload["count"] == 2
    assert regions_payload["regions"][0]["slug"] == "us"

    server_result = runner.invoke(warcraftlogs_app, ["server", "us", "illidan"])
    assert server_result.exit_code == 0
    server_payload = json.loads(server_result.stdout)
    assert server_payload["server"]["slug"] == "illidan"

    zones_result = runner.invoke(warcraftlogs_app, ["zones", "--expansion-id", "12"])
    assert zones_result.exit_code == 0
    zones_payload = json.loads(zones_result.stdout)
    assert zones_payload["count"] == 1
    assert zones_payload["zones"][0]["encounters"][0]["journal_id"] == 9001

    encounter_result = runner.invoke(warcraftlogs_app, ["encounter", "3012"])
    assert encounter_result.exit_code == 0
    encounter_payload = json.loads(encounter_result.stdout)
    assert encounter_payload["encounter"]["zone"]["expansion"]["name"] == "Midnight"


def test_warcraftlogs_guild_character_and_report_commands(monkeypatch) -> None:
    monkeypatch.setattr("warcraftlogs_cli.main._client", lambda ctx: _FakeWarcraftLogsClient())

    guild_result = runner.invoke(warcraftlogs_app, ["guild", "us", "illidan", "Liquid", "--zone-id", "38"])
    assert guild_result.exit_code == 0
    guild_payload = json.loads(guild_result.stdout)
    assert guild_payload["guild"]["zone_ranking"]["progress"]["world"]["number"] == 2

    character_result = runner.invoke(warcraftlogs_app, ["character", "us", "illidan", "Roguecane"])
    assert character_result.exit_code == 0
    character_payload = json.loads(character_result.stdout)
    assert character_payload["character"]["server"]["slug"] == "illidan"
    assert character_payload["character"]["guild_rank"] == 3
    assert character_payload["character"]["guilds"][0]["name"] == "Liquid"

    report_result = runner.invoke(warcraftlogs_app, ["report", "abcd1234", "--allow-unlisted"])
    assert report_result.exit_code == 0
    report_payload = json.loads(report_result.stdout)
    assert report_payload["report"]["zone"]["name"] == "Manaforge Omega"

    fights_result = runner.invoke(warcraftlogs_app, ["report-fights", "abcd1234", "--difficulty", "5"])
    assert fights_result.exit_code == 0
    fights_payload = json.loads(fights_result.stdout)
    assert fights_payload["count"] == 1
    assert fights_payload["fights"][0]["encounter_id"] == 3012
