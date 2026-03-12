from __future__ import annotations

import json

from typer.testing import CliRunner

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
    assert payload["capabilities"]["search"] == "coming_soon"


def test_wowprogress_search_is_structured_coming_soon() -> None:
    result = runner.invoke(wowprogress_app, ["search", "liquid"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["coming_soon"] is True
    assert payload["count"] == 0
    assert payload["results"] == []


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
