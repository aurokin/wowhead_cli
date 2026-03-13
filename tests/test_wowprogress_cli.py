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
