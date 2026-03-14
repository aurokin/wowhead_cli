from __future__ import annotations

import json

from typer.testing import CliRunner

from wowprogress_cli.client import WowProgressClient
from wowprogress_cli.main import app as wowprogress_app

runner = CliRunner()


def test_wowprogress_doctor_reports_phase_one_capabilities() -> None:
    result = runner.invoke(wowprogress_app, ["doctor"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider"] == "wowprogress"
    assert payload["status"] == "ready"
    assert payload["transport"]["mode"] == "browser_fingerprint_http"
    assert payload["capabilities"]["guild"] == "ready"
    assert payload["capabilities"]["search"] == "ready"
    assert payload["capabilities"]["sample_pve_leaderboard"] == "ready"


def test_wowprogress_search_returns_structured_hint_for_unparseable_query() -> None:
    result = runner.invoke(wowprogress_app, ["search", "liquid"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["count"] == 0
    assert payload["results"] == []
    assert "structured queries" in payload["message"]
    assert payload["suggested_queries"]


def test_wowprogress_search_returns_ranked_structured_results(monkeypatch) -> None:
    def fake_probe(self, *, region: str, realm: str, name: str, obj_type: str):  # noqa: ANN001
        assert region == "us"
        assert realm == "illidan"
        assert name == "Liquid"
        if obj_type == "char":
            return None
        return {
            "_search_kind": "guild",
            "guild": {
                "name": "Liquid",
                "region": "us",
                "realm": "US-Illidan",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
            },
        }

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.probe_search_route", fake_probe)
    result = runner.invoke(wowprogress_app, ["search", "guild us illidan Liquid"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["results"][0]["kind"] == "guild"
    assert payload["results"][0]["follow_up"]["command"] == "wowprogress guild us illidan Liquid"
    assert "type_hint" in payload["results"][0]["ranking"]["match_reasons"]
    assert payload["normalized_candidates"][0] == {"region": "us", "realm": "illidan", "name": "Liquid"}


def test_wowprogress_resolve_stays_conservative_when_multiple_results(monkeypatch) -> None:
    def fake_probe(self, *, region: str, realm: str, name: str, obj_type: str):  # noqa: ANN001
        if obj_type == "char":
            return {
                "_search_kind": "character",
                "character": {
                    "name": "Liquid",
                    "region": "us",
                    "realm": "illidan",
                    "guild_name": "Liquid",
                    "class_name": "Mage",
                    "page_url": "https://www.wowprogress.com/character/us/illidan/Liquid",
                },
            }
        return {
            "_search_kind": "guild",
            "guild": {
                "name": "Liquid",
                "region": "us",
                "realm": "illidan",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
            },
        }

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.probe_search_route", fake_probe)
    result = runner.invoke(wowprogress_app, ["resolve", "us illidan Liquid"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is False
    assert payload["confidence"] in {"medium", "low"}
    assert payload["fallback_search_command"] == 'wowprogress search "us illidan Liquid"'


def test_wowprogress_resolve_returns_command_for_typed_query(monkeypatch) -> None:
    def fake_probe(self, *, region: str, realm: str, name: str, obj_type: str):  # noqa: ANN001
        assert obj_type == "char"
        return {
            "_search_kind": "character",
            "character": {
                "name": "Imonthegcd",
                "region": "us",
                "realm": "illidan",
                "guild_name": "Liquid",
                "class_name": "Mage",
                "page_url": "https://www.wowprogress.com/character/us/illidan/Imonthegcd",
            },
        }

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.probe_search_route", fake_probe)
    result = runner.invoke(wowprogress_app, ["resolve", "character us illidan Imonthegcd"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["confidence"] == "high"
    assert payload["next_command"] == "wowprogress character us illidan Imonthegcd"


def test_wowprogress_resolve_returns_command_for_short_exact_guild_query(monkeypatch) -> None:
    def fake_probe(self, *, region: str, realm: str, name: str, obj_type: str):  # noqa: ANN001
        assert obj_type == "guild"
        return {
            "_search_kind": "guild",
            "guild": {
                "name": "xD",
                "region": "us",
                "realm": "US-Area 52",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/area-52/xD",
            },
        }

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.probe_search_route", fake_probe)
    result = runner.invoke(wowprogress_app, ["resolve", "guild us area-52 xD"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["confidence"] == "high"
    assert payload["next_command"] == "wowprogress guild us area-52 xD"
    assert "exact_target_name" in payload["match"]["ranking"]["match_reasons"]
    assert "exact_target_realm" in payload["match"]["ranking"]["match_reasons"]


def test_wowprogress_search_normalizes_multi_word_realm(monkeypatch) -> None:
    calls: list[tuple[str, str, str, str]] = []

    def fake_probe(self, *, region: str, realm: str, name: str, obj_type: str):  # noqa: ANN001
        calls.append((region, realm, name, obj_type))
        if (region, realm, name, obj_type) == ("us", "area-52", "xD", "guild"):
            return {
                "_search_kind": "guild",
                "guild": {
                    "name": "xD",
                    "region": "us",
                    "realm": "US-Area 52",
                    "faction": "Horde",
                    "page_url": "https://www.wowprogress.com/guild/us/area-52/xD",
                },
            }
        return None

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.probe_search_route", fake_probe)
    result = runner.invoke(wowprogress_app, ["search", "guild us area 52 xD"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["results"][0]["follow_up"]["command"] == "wowprogress guild us area-52 xD"
    assert {"region": "us", "realm": "area-52", "name": "xD"} in payload["normalized_candidates"]
    assert ("us", "area-52", "xD", "guild") in calls


def test_wowprogress_search_excludes_trailing_terms_with_hint(monkeypatch) -> None:
    def fake_probe(self, *, region: str, realm: str, name: str, obj_type: str):  # noqa: ANN001
        assert region == "us"
        assert realm == "illidan"
        assert name == "Liquid"
        assert obj_type == "guild"
        return {
            "_search_kind": "guild",
            "guild": {
                "name": "Liquid",
                "region": "us",
                "realm": "US-Illidan",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
            },
        }

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.probe_search_route", fake_probe)
    result = runner.invoke(wowprogress_app, ["search", "guild us illidan Liquid recruit"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["excluded_terms"] == ["recruit"]
    assert payload["normalization_hint"]["code"] == "excluded_query_terms"
    assert payload["search_query"] == "guild us illidan Liquid"


def test_wowprogress_client_search_probe_cache_reads_final_url(monkeypatch) -> None:
    client = WowProgressClient()
    try:
        monkeypatch.setattr(
            client,
            "_read_cache",
            lambda key: json.dumps(
                {
                    "html": "<html><h1>Liquid Guild</h1></html>",
                    "final_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
                }
            ),
        )
        monkeypatch.setattr(
            "wowprogress_cli.client.parse_guild_page",
            lambda html, *, url, region, realm, name: {"guild": {"name": name, "region": region, "realm": realm, "page_url": url}},
        )
        payload = client.probe_search_route(region="us", realm="illidan", name="Liquid", obj_type="guild")
    finally:
        client.close()

    assert payload is not None
    assert payload["guild"]["page_url"] == "https://www.wowprogress.com/guild/us/illidan/Liquid"


def test_wowprogress_guild_summary(monkeypatch) -> None:
    def fake_fetch(self, *, region: str, realm: str, name: str):  # noqa: ANN001
        assert region == "us"
        assert realm == "illidan"
        assert name == "Liquid"
        return {
            "guild": {
                "name": "Liquid",
                "region": "us",
                "realm": "US-Illidan",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
                "armory_url": "https://worldofwarcraft.com/en-us/guild/illidan/liquid",
            },
            "progress": {
                "summary": "8/8 (M)",
                "ranks": {"world": "1", "region": "1", "realm": "1"},
            },
            "item_level": {
                "average": 724.51,
                "group_size": "20-man",
                "ranks": {"world": "9026", "region": "4149", "realm": "238"},
            },
            "encounters": {
                "count": 1,
                "items": [{"encounter": "Dimensius, the All-Devouring", "world_rank": "1"}],
            },
            "citations": {"page": "https://www.wowprogress.com/guild/us/illidan/Liquid"},
        }

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.fetch_guild_page", fake_fetch)
    result = runner.invoke(wowprogress_app, ["guild", "us", "illidan", "Liquid"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["guild"]["name"] == "Liquid"
    assert payload["progress"]["summary"] == "8/8 (M)"
    assert payload["encounters"]["count"] == 1


def test_wowprogress_character_summary(monkeypatch) -> None:
    def fake_fetch(self, *, region: str, realm: str, name: str):  # noqa: ANN001
        assert region == "us"
        assert realm == "illidan"
        assert name == "Imonthegcd"
        return {
            "character": {
                "name": "Imonthegcd",
                "region": "us",
                "realm": "US-Illidan",
                "guild_name": "Liquid",
                "guild_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
                "race": "Void Elf",
                "class_name": "Mage",
                "level": 90,
                "page_url": "https://www.wowprogress.com/character/us/illidan/Imonthegcd",
                "armory_url": "https://worldofwarcraft.com/en-us/character/illidan/Imonthegcd",
            },
            "profile": {"languages": "English"},
            "item_level": {"value": 728.81},
            "sim_dps": {"value": 6089532.23},
            "pve": {"score": 750000.0, "raids": [{"raid": "Manaforge Omega"}]},
            "citations": {"page": "https://www.wowprogress.com/character/us/illidan/Imonthegcd"},
        }

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.fetch_character_page", fake_fetch)
    result = runner.invoke(wowprogress_app, ["character", "us", "illidan", "Imonthegcd"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["character"]["name"] == "Imonthegcd"
    assert payload["item_level"]["value"] == 728.81
    assert payload["pve"]["score"] == 750000.0


def test_wowprogress_leaderboard(monkeypatch) -> None:
    def fake_fetch(self, *, region: str, realm: str | None = None, limit: int = 25):  # noqa: ANN001
        assert region == "us"
        assert realm is None
        assert limit == 10
        return {
            "leaderboard": {
                "kind": "pve",
                "title": "US Mythic Progress",
                "region": "us",
                "realm": None,
                "active_raid": "Manaforge Omega",
                "page_url": "https://www.wowprogress.com/pve/us",
            },
            "count": 2,
            "entries": [{"rank": 1, "guild_name": "Liquid"}, {"rank": 2, "guild_name": "Echo"}],
            "citations": {"page": "https://www.wowprogress.com/pve/us"},
        }

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.fetch_pve_leaderboard", fake_fetch)
    result = runner.invoke(wowprogress_app, ["leaderboard", "pve", "us", "--limit", "10"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["leaderboard"]["active_raid"] == "Manaforge Omega"
    assert payload["count"] == 2


def test_wowprogress_error_maps_to_structured_error(monkeypatch) -> None:
    def fake_fetch(self, *, region: str, realm: str, name: str):  # noqa: ANN001
        from wowprogress_cli.client import WowProgressClientError

        raise WowProgressClientError("not_found", "WowProgress could not resolve that guild or character.")

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.fetch_guild_page", fake_fetch)
    result = runner.invoke(wowprogress_app, ["guild", "us", "illidan", "Missing"])
    assert result.exit_code == 1

    payload = json.loads(result.stderr)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"


def test_wowprogress_sample_pve_leaderboard(monkeypatch) -> None:
    def fake_fetch(self, *, region: str, realm: str | None = None, limit: int = 25):  # noqa: ANN001
        assert region == "us"
        assert realm is None
        assert limit == 10
        return {
            "leaderboard": {
                "kind": "pve",
                "title": "US Mythic Progress",
                "region": "us",
                "realm": None,
                "active_raid": "Manaforge Omega",
                "page_url": "https://www.wowprogress.com/pve/us",
            },
            "count": 2,
            "entries": [
                {
                    "rank": 1,
                    "guild_name": "Liquid",
                    "guild_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
                    "realm": "US-Illidan",
                    "realm_url": "https://www.wowprogress.com/pve/us/illidan",
                    "progress": "8/8 (M)",
                },
                {
                    "rank": 2,
                    "guild_name": "Echo",
                    "guild_url": "https://www.wowprogress.com/guild/eu/tarren-mill/Echo",
                    "realm": "EU-Tarren Mill",
                    "realm_url": "https://www.wowprogress.com/pve/eu/tarren-mill",
                    "progress": "8/8 (M)",
                },
            ],
            "citations": {"page": "https://www.wowprogress.com/pve/us"},
        }

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.fetch_pve_leaderboard", fake_fetch)
    result = runner.invoke(wowprogress_app, ["sample", "pve-leaderboard", "--region", "us", "--limit", "10"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["kind"] == "pve_leaderboard_sample"
    assert payload["sample"]["entry_count"] == 2
    assert payload["sample"]["active_raid"] == "Manaforge Omega"
    assert payload["entries"][0]["bosses_killed"] == 8
    assert payload["entries"][0]["difficulty"] == "M"


def test_wowprogress_distribution_pve_leaderboard(monkeypatch) -> None:
    def fake_fetch(self, *, region: str, realm: str | None = None, limit: int = 25):  # noqa: ANN001
        return {
            "leaderboard": {
                "kind": "pve",
                "title": "US Mythic Progress",
                "region": "us",
                "realm": None,
                "active_raid": "Manaforge Omega",
                "page_url": "https://www.wowprogress.com/pve/us",
            },
            "count": 3,
            "entries": [
                {"rank": 1, "guild_name": "Liquid", "realm": "US-Illidan", "progress": "8/8 (M)"},
                {"rank": 2, "guild_name": "Echo", "realm": "EU-Tarren Mill", "progress": "8/8 (M)"},
                {"rank": 3, "guild_name": "Method", "realm": "EU-Twisting Nether", "progress": "7/8 (M)"},
            ],
            "citations": {"page": "https://www.wowprogress.com/pve/us"},
        }

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.fetch_pve_leaderboard", fake_fetch)
    result = runner.invoke(
        wowprogress_app,
        ["distribution", "pve-leaderboard", "--region", "us", "--metric", "progress", "--limit", "10"],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["kind"] == "pve_leaderboard_distribution"
    assert payload["metric"] == "progress"
    assert payload["distribution"]["rows"][0]["value"] == "8/8 (M)"
    assert payload["distribution"]["rows"][0]["count"] == 2


def test_wowprogress_threshold_pve_leaderboard(monkeypatch) -> None:
    def fake_fetch(self, *, region: str, realm: str | None = None, limit: int = 25):  # noqa: ANN001
        return {
            "leaderboard": {
                "kind": "pve",
                "title": "US Mythic Progress",
                "region": "us",
                "realm": None,
                "active_raid": "Manaforge Omega",
                "page_url": "https://www.wowprogress.com/pve/us",
            },
            "count": 4,
            "entries": [
                {"rank": 1, "guild_name": "Liquid", "realm": "US-Illidan", "progress": "8/8 (M)"},
                {"rank": 2, "guild_name": "Echo", "realm": "EU-Tarren Mill", "progress": "8/8 (M)"},
                {"rank": 40, "guild_name": "Method", "realm": "EU-Twisting Nether", "progress": "7/8 (M)"},
                {"rank": 85, "guild_name": "Random", "realm": "US-Area 52", "progress": "6/8 (M)"},
            ],
            "citations": {"page": "https://www.wowprogress.com/pve/us"},
        }

    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.fetch_pve_leaderboard", fake_fetch)
    result = runner.invoke(
        wowprogress_app,
        ["threshold", "pve-leaderboard", "--region", "us", "--metric", "rank", "--value", "50", "--nearest", "2", "--limit", "10"],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["kind"] == "pve_leaderboard_threshold"
    assert payload["metric"] == "rank"
    assert payload["threshold"]["nearest_match_count"] == 2
    assert payload["threshold"]["estimate"]["metric"] == "bosses_killed"


def test_wowprogress_distribution_rejects_invalid_metric() -> None:
    result = runner.invoke(
        wowprogress_app,
        ["distribution", "pve-leaderboard", "--region", "us", "--metric", "invalid"],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert payload["error"]["code"] == "invalid_query"
