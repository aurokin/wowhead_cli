from __future__ import annotations

import json

from typer.testing import CliRunner
from warcraftlogs_cli.client import load_warcraftlogs_auth_config
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

    def expansions(self) -> list[dict[str, object]]:
        return [
            {
                "id": 12,
                "name": "Midnight",
                "zones": [
                    {"id": 38, "name": "Manaforge Omega", "frozen": False},
                ],
            }
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

    def zone(self, *, zone_id: int) -> dict[str, object]:
        assert zone_id == 38
        return {
            "id": 38,
            "name": "Manaforge Omega",
            "frozen": False,
            "expansion": {"id": 12, "name": "Midnight"},
            "difficulties": [{"id": 5, "name": "Mythic", "sizes": []}],
            "encounters": [{"id": 3012, "name": "Dimensius", "journalID": 9001}],
            "partitions": [{"id": 1, "name": "Default", "compactName": "Default", "default": True}],
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

    def guild_rankings(
        self,
        *,
        region: str,
        realm: str,
        name: str,
        zone_id: int | None = None,
        size: int | None = None,
        difficulty: int | None = None,
    ) -> dict[str, object]:
        assert region == "us"
        assert realm == "illidan"
        assert name == "Liquid"
        assert zone_id == 38
        assert size == 20
        assert difficulty == 5
        return {
            "id": 5,
            "name": "Liquid",
            "server": {
                "id": 10,
                "name": "Illidan",
                "normalizedName": "Illidan",
                "slug": "illidan",
                "region": {"id": 1, "compactName": "US", "name": "North America", "slug": "us"},
                "subregion": {"id": 100, "name": "Chicago"},
            },
            "zoneRanking": {
                "progress": {
                    "worldRank": {"number": 2, "color": "legendary", "percentile": None},
                    "regionRank": {"number": 1, "color": "legendary", "percentile": None},
                    "serverRank": {"number": 1, "color": "legendary", "percentile": None},
                },
                "speed": {
                    "worldRank": {"number": 4, "color": "epic", "percentile": None},
                    "regionRank": {"number": 2, "color": "epic", "percentile": None},
                    "serverRank": {"number": 1, "color": "epic", "percentile": None},
                },
                "completeRaidSpeed": None,
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

    def character_rankings(
        self,
        *,
        region: str,
        realm: str,
        name: str,
        zone_id: int | None = None,
        difficulty: int | None = None,
        metric: str | None = None,
        size: int | None = None,
        spec_name: str | None = None,
    ) -> dict[str, object]:
        assert region == "us"
        assert realm == "illidan"
        assert name == "Roguecane"
        assert zone_id == 38
        assert difficulty == 5
        assert metric == "dps"
        assert size == 20
        assert spec_name == "assassination"
        return {
            "id": 77,
            "canonicalID": 88,
            "name": "Roguecane",
            "level": 80,
            "classID": 4,
            "faction": {"id": 1, "name": "Horde"},
            "server": {
                "id": 10,
                "name": "Illidan",
                "normalizedName": "Illidan",
                "slug": "illidan",
                "region": {"id": 1, "compactName": "US", "name": "North America", "slug": "us"},
                "subregion": {"id": 100, "name": "Chicago"},
            },
            "zoneRankings": {
                "zone": 38,
                "difficulty": 5,
                "metric": "dps",
                "partition": 1,
                "size": 20,
                "bestPerformanceAverage": 85.4,
                "medianPerformanceAverage": 77.2,
                "allStars": [
                    {
                        "spec": "Assassination",
                        "points": 263.29,
                        "possiblePoints": 960,
                        "rank": 21679,
                        "rankPercent": 37.7,
                        "regionRank": 7393,
                        "serverRank": 660,
                        "total": 34818,
                    }
                ],
                "rankings": [
                    {
                        "encounter": {"id": 3012, "name": "Dimensius"},
                        "spec": "Assassination",
                        "bestSpec": "Assassination",
                        "rankPercent": 65.7,
                        "medianPercent": 65.7,
                        "totalKills": 1,
                        "allStars": {"points": 66.06},
                        "bestRank": {"rank_id": 123},
                        "bestAmount": 2999570.9,
                        "fastestKill": 223706,
                    }
                ],
            },
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
            "archiveStatus": {
                "isArchived": True,
                "isAccessible": True,
                "archiveDate": 789,
            },
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

    def reports(
        self,
        *,
        guild_region: str | None = None,
        guild_realm: str | None = None,
        guild_name: str | None = None,
        limit: int = 25,
        page: int = 1,
        start_time: float | None = None,
        end_time: float | None = None,
        zone_id: int | None = None,
        game_zone_id: int | None = None,
    ) -> dict[str, object]:
        assert guild_region == "us"
        assert guild_realm == "illidan"
        assert guild_name == "Liquid"
        assert limit == 10
        assert page == 2
        assert zone_id == 38
        assert game_zone_id == 12961
        assert start_time == 1000.0
        assert end_time == 2000.0
        return {
            "data": [
                {
                    "code": "abcd1234",
                    "title": "Manaforge Omega - Liquid",
                    "startTime": 123,
                    "endTime": 456,
                    "visibility": "public",
                    "archiveStatus": {
                        "isArchived": True,
                        "isAccessible": True,
                        "archiveDate": 789,
                    },
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
                        },
                    },
                }
            ],
            "total": 25,
            "per_page": 10,
            "current_page": 2,
            "from": 11,
            "to": 20,
            "last_page": 3,
            "has_more_pages": True,
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

    def report_events(self, *, code: str, allow_unlisted: bool = False, options) -> dict[str, object]:  # noqa: ANN001
        assert code == "abcd1234"
        assert allow_unlisted is False
        assert options.data_type == "Casts"
        assert options.difficulty == 5
        assert options.encounter_id == 3012
        assert options.fight_ids == [1, 2]
        assert options.limit == 50
        assert options.source_id == 9
        return {
            "code": "abcd1234",
            "title": "Manaforge Omega - Liquid",
            "zone": {"id": 38, "name": "Manaforge Omega"},
            "events": {
                "data": [{"type": "cast", "abilityGameID": 12345}],
                "nextPageTimestamp": 999.0,
            },
        }

    def report_table(self, *, code: str, allow_unlisted: bool = False, options) -> dict[str, object]:  # noqa: ANN001
        assert code == "abcd1234"
        assert allow_unlisted is True
        assert options.data_type == "DamageDone"
        assert options.view_by == "Source"
        return {
            "code": "abcd1234",
            "title": "Manaforge Omega - Liquid",
            "zone": {"id": 38, "name": "Manaforge Omega"},
            "table": {"entries": [{"name": "Auropower", "total": 123456}]},
        }

    def report_graph(self, *, code: str, allow_unlisted: bool = False, options) -> dict[str, object]:  # noqa: ANN001
        assert code == "abcd1234"
        assert allow_unlisted is False
        assert options.data_type == "DamageDone"
        assert options.view_by == "Target"
        return {
            "code": "abcd1234",
            "title": "Manaforge Omega - Liquid",
            "zone": {"id": 38, "name": "Manaforge Omega"},
            "graph": {"series": [{"name": "Damage", "data": [1, 2, 3]}]},
        }

    def report_master_data(
        self,
        *,
        code: str,
        allow_unlisted: bool = False,
        translate: bool | None = None,
        actor_type: str | None = None,
        actor_sub_type: str | None = None,
    ) -> dict[str, object]:
        assert code == "abcd1234"
        assert allow_unlisted is False
        assert translate is False
        assert actor_type == "Player"
        assert actor_sub_type == "Paladin"
        return {
            "code": "abcd1234",
            "title": "Manaforge Omega - Liquid",
            "zone": {"id": 38, "name": "Manaforge Omega"},
            "masterData": {
                "logVersion": 47,
                "gameVersion": 120001,
                "lang": "en",
                "abilities": [{"gameID": 20473, "icon": "spell_holy_holybolt", "name": "Holy Shock", "type": "Holy"}],
                "actors": [
                    {
                        "gameID": 0,
                        "icon": "classicon_paladin",
                        "id": 9,
                        "name": "Auropower",
                        "petOwner": None,
                        "server": "Mal'Ganis",
                        "subType": "Paladin",
                        "type": "Player",
                    }
                ],
            },
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
    assert payload["auth"]["credential_source"] == "/tmp/.env.local"
    assert payload["auth"]["lookup_order"][0] == ".env.local"
    assert payload["auth"]["lookup_order"][-1] == "environment"
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

    expansions_result = runner.invoke(warcraftlogs_app, ["expansions"])
    assert expansions_result.exit_code == 0
    expansions_payload = json.loads(expansions_result.stdout)
    assert expansions_payload["count"] == 1
    assert expansions_payload["expansions"][0]["zone_count"] == 1

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

    zone_result = runner.invoke(warcraftlogs_app, ["zone", "38"])
    assert zone_result.exit_code == 0
    zone_payload = json.loads(zone_result.stdout)
    assert zone_payload["zone"]["partitions"][0]["default"] is True


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

    guild_rankings_result = runner.invoke(
        warcraftlogs_app,
        ["guild-rankings", "us", "illidan", "Liquid", "--zone-id", "38", "--size", "20", "--difficulty", "5"],
    )
    assert guild_rankings_result.exit_code == 0
    guild_rankings_payload = json.loads(guild_rankings_result.stdout)
    assert guild_rankings_payload["guild_rankings"]["zone_ranking"]["speed"]["world"]["number"] == 4

    character_rankings_result = runner.invoke(
        warcraftlogs_app,
        [
            "character-rankings",
            "us",
            "illidan",
            "Roguecane",
            "--zone-id",
            "38",
            "--difficulty",
            "5",
            "--metric",
            "dps",
            "--size",
            "20",
            "--spec-name",
            "assassination",
        ],
    )
    assert character_rankings_result.exit_code == 0
    character_rankings_payload = json.loads(character_rankings_result.stdout)
    assert character_rankings_payload["character_rankings"]["summary"]["best_performance_average"] == 85.4
    assert character_rankings_payload["character_rankings"]["rankings"][0]["encounter"]["name"] == "Dimensius"

    report_result = runner.invoke(warcraftlogs_app, ["report", "abcd1234", "--allow-unlisted"])
    assert report_result.exit_code == 0
    report_payload = json.loads(report_result.stdout)
    assert report_payload["report"]["zone"]["name"] == "Manaforge Omega"
    assert report_payload["report"]["archive_status"]["is_archived"] is True

    reports_result = runner.invoke(
        warcraftlogs_app,
        [
            "reports",
            "--guild-region",
            "us",
            "--guild-realm",
            "illidan",
            "--guild-name",
            "Liquid",
            "--limit",
            "10",
            "--page",
            "2",
            "--start-time",
            "1000",
            "--end-time",
            "2000",
            "--zone-id",
            "38",
            "--game-zone-id",
            "12961",
        ],
    )
    assert reports_result.exit_code == 0
    reports_payload = json.loads(reports_result.stdout)
    assert reports_payload["pagination"]["current_page"] == 2
    assert reports_payload["count"] == 1
    assert reports_payload["reports"][0]["archive_status"]["archive_date"] == 789

    fights_result = runner.invoke(warcraftlogs_app, ["report-fights", "abcd1234", "--difficulty", "5"])
    assert fights_result.exit_code == 0
    fights_payload = json.loads(fights_result.stdout)
    assert fights_payload["count"] == 1
    assert fights_payload["fights"][0]["encounter_id"] == 3012

    events_result = runner.invoke(
        warcraftlogs_app,
        [
            "report-events",
            "abcd1234",
            "--data-type",
            "casts",
            "--difficulty",
            "5",
            "--encounter-id",
            "3012",
            "--fight-id",
            "1",
            "--fight-id",
            "2",
            "--limit",
            "50",
            "--source-id",
            "9",
        ],
    )
    assert events_result.exit_code == 0
    events_payload = json.loads(events_result.stdout)
    assert events_payload["next_page_timestamp"] == 999.0
    assert events_payload["events"][0]["type"] == "cast"

    table_result = runner.invoke(
        warcraftlogs_app,
        ["report-table", "abcd1234", "--allow-unlisted", "--data-type", "damage-done", "--view-by", "source"],
    )
    assert table_result.exit_code == 0
    table_payload = json.loads(table_result.stdout)
    assert table_payload["table"]["entries"][0]["name"] == "Auropower"

    graph_result = runner.invoke(
        warcraftlogs_app,
        ["report-graph", "abcd1234", "--data-type", "damage-done", "--view-by", "target"],
    )
    assert graph_result.exit_code == 0
    graph_payload = json.loads(graph_result.stdout)
    assert graph_payload["graph"]["series"][0]["name"] == "Damage"

    master_data_result = runner.invoke(
        warcraftlogs_app,
        ["report-master-data", "abcd1234", "--no-translate", "--actor-type", "Player", "--actor-sub-type", "Paladin"],
    )
    assert master_data_result.exit_code == 0
    master_data_payload = json.loads(master_data_result.stdout)
    assert master_data_payload["master_data"]["log_version"] == 47
    assert master_data_payload["master_data"]["actors"][0]["name"] == "Auropower"


def test_warcraftlogs_report_events_requires_scope(monkeypatch) -> None:
    monkeypatch.setattr("warcraftlogs_cli.main._client", lambda ctx: _FakeWarcraftLogsClient())

    result = runner.invoke(warcraftlogs_app, ["report-events", "abcd1234", "--limit", "5"])
    assert result.exit_code == 1

    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "missing_scope"


def test_warcraftlogs_character_rankings_surfaces_provider_permission_errors(monkeypatch) -> None:
    class _PermissionClient(_FakeWarcraftLogsClient):
        def character_rankings(
            self,
            *,
            region: str,
            realm: str,
            name: str,
            zone_id: int | None = None,
            difficulty: int | None = None,
            metric: str | None = None,
            size: int | None = None,
            spec_name: str | None = None,
        ) -> dict[str, object]:
            return {
                "id": 99,
                "canonicalID": 99,
                "name": name,
                "classID": 6,
                "level": 90,
                "faction": {"id": 1, "name": "Alliance"},
                "server": {
                    "id": 10,
                    "name": "Illidan",
                    "normalizedName": "Illidan",
                    "slug": "illidan",
                    "region": {"id": 1, "compactName": "US", "name": "North America", "slug": "us"},
                    "subregion": {"id": 100, "name": "Chicago"},
                },
                "zoneRankings": {"error": "You do not have permission to see this character's rankings."},
            }

    monkeypatch.setattr("warcraftlogs_cli.main._client", lambda ctx: _PermissionClient())

    result = runner.invoke(
        warcraftlogs_app,
        ["character-rankings", "us", "illidan", "Driney", "--zone-id", "38", "--difficulty", "5", "--metric", "dps"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["character_rankings"]["summary"] is None
    assert payload["character_rankings"]["error"] == "You do not have permission to see this character's rankings."
    assert payload["character_rankings"]["rankings"] == []


def test_warcraftlogs_auth_prefers_local_env_before_xdg_provider_env(monkeypatch, tmp_path) -> None:
    repo_env = tmp_path / ".env.local"
    repo_env.write_text("WARCRAFTLOGS_CLIENT_ID=repo-id\nWARCRAFTLOGS_CLIENT_SECRET=repo-secret\n")
    config_home = tmp_path / "config-home"
    provider_env = config_home / "warcraft" / "providers" / "warcraftlogs.env"
    provider_env.parent.mkdir(parents=True)
    provider_env.write_text("WARCRAFTLOGS_CLIENT_ID=provider-id\nWARCRAFTLOGS_CLIENT_SECRET=provider-secret\n")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.delenv("WARCRAFTLOGS_CLIENT_ID", raising=False)
    monkeypatch.delenv("WARCRAFTLOGS_CLIENT_SECRET", raising=False)

    auth = load_warcraftlogs_auth_config(start_dir=str(tmp_path))

    assert auth.configured is True
    assert auth.client_id == "repo-id"
    assert auth.client_secret == "repo-secret"
    assert auth.env_file == str(repo_env)


def test_warcraftlogs_auth_falls_back_to_xdg_provider_env(monkeypatch, tmp_path) -> None:
    config_home = tmp_path / "config-home"
    provider_env = config_home / "warcraft" / "providers" / "warcraftlogs.env"
    provider_env.parent.mkdir(parents=True)
    provider_env.write_text("WARCRAFTLOGS_CLIENT_ID=provider-id\nWARCRAFTLOGS_CLIENT_SECRET=provider-secret\n")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.delenv("WARCRAFTLOGS_CLIENT_ID", raising=False)
    monkeypatch.delenv("WARCRAFTLOGS_CLIENT_SECRET", raising=False)

    auth = load_warcraftlogs_auth_config(start_dir=str(tmp_path))

    assert auth.configured is True
    assert auth.client_id == "provider-id"
    assert auth.client_secret == "provider-secret"
    assert auth.env_file == str(provider_env)
