from __future__ import annotations

import json

from typer.testing import CliRunner

from icy_veins_cli.main import app as icy_veins_app
from raiderio_cli.main import app as raiderio_app
from method_cli.main import app as method_app
from simc_cli.main import app as simc_app
from warcraft_cli.main import app as warcraft_app
from wowprogress_cli.main import app as wowprogress_app

runner = CliRunner()


def test_method_stub_commands_expose_coming_soon_contract() -> None:
    result = runner.invoke(method_app, ["doctor"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider"] == "method"
    assert payload["status"] == "ready"
    assert payload["capabilities"]["search"] == "ready"
    assert payload["capabilities"]["resolve"] == "ready"


def test_warcraft_doctor_reports_ready_and_stubbed_providers() -> None:
    result = runner.invoke(warcraft_app, ["doctor"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["wrapper"]["provider_count"] == 7
    providers = {row["provider"]: row for row in payload["providers"]}
    assert providers["wowhead"]["status"] == "ready"
    assert providers["method"]["status"] == "ready"
    assert providers["icy-veins"]["status"] == "ready"
    assert providers["raiderio"]["status"] == "ready"
    assert providers["warcraft-wiki"]["status"] == "ready"
    assert providers["wowprogress"]["status"] == "ready"
    assert providers["simc"]["status"] == "ready"
    assert providers["method"]["details"]["capabilities"]["guide"] == "ready"
    assert providers["icy-veins"]["details"]["capabilities"]["guide"] == "ready"
    assert providers["raiderio"]["details"]["capabilities"]["search"] == "ready"
    assert providers["warcraft-wiki"]["details"]["capabilities"]["article"] == "ready"
    assert providers["wowprogress"]["details"]["capabilities"]["leaderboard"] == "ready"
    assert providers["simc"]["details"]["capabilities"]["decode_build"] == "ready"


def test_warcraft_search_fans_out_across_providers(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 3, "id": 19019, "name": "Thunderfury", "typeName": "Item", "popularity": 10},
            ],
        }

    monkeypatch.setattr(
        "method_cli.main.MethodClient.sitemap_guides",
        lambda self: [{"slug": "mistweaver-monk", "name": "Mistweaver Monk", "url": "https://www.method.gg/guides/mistweaver-monk"}],
    )
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(warcraft_app, ["search", "thunderfury", "--limit", "3"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider_count"] == 7
    assert payload["count"] == 1
    assert payload["results"][0]["provider"] == "wowhead"
    providers = {row["provider"]: row for row in payload["providers"]}
    assert providers["method"]["payload"]["count"] == 0
    assert providers["icy-veins"]["payload"]["count"] == 0
    assert providers["raiderio"]["payload"]["count"] == 0
    assert providers["warcraft-wiki"]["payload"]["count"] == 0
    assert providers["wowprogress"]["payload"]["coming_soon"] is True
    assert providers["simc"]["payload"]["coming_soon"] is True
    assert providers["wowhead"]["payload"]["results"][0]["name"] == "Thunderfury"


def test_warcraft_search_sorts_results_globally_by_ranking(monkeypatch) -> None:
    def fake_wowhead_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {
                    "id": 19019,
                    "name": "Thunderfury",
                    "entity_type": "item",
                    "ranking": {"score": 15, "match_reasons": ["name_contains_query"]},
                },
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_wowhead_search)
    monkeypatch.setattr(
        "method_cli.main.MethodClient.sitemap_guides",
        lambda self: [{"slug": "mistweaver-monk", "name": "Mistweaver Monk", "url": "https://www.method.gg/guides/mistweaver-monk"}],
    )
    monkeypatch.setattr(
        "icy_veins_cli.main.IcyVeinsClient.sitemap_guides",
        lambda self: [{"slug": "frost-death-knight-pve-dps-guide", "name": "Frost Death Knight PvE DPS Guide", "url": "https://www.icy-veins.com/wow/frost-death-knight-pve-dps-guide"}],
    )
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))

    result = runner.invoke(warcraft_app, ["search", "mistweaver monk guide", "--limit", "5"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["results"][0]["provider"] == "method"


def test_warcraft_resolve_prefers_stronger_later_provider(monkeypatch) -> None:
    def fake_wowhead_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 100, "id": 2594, "name": "Warlords of Draenor Mistweaver Monk Guide", "typeName": "Guide", "popularity": 8},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_wowhead_search)
    monkeypatch.setattr(
        "method_cli.main.MethodClient.sitemap_guides",
        lambda self: [{"slug": "mistweaver-monk", "name": "Mistweaver Monk", "url": "https://www.method.gg/guides/mistweaver-monk"}],
    )
    monkeypatch.setattr(
        "icy_veins_cli.main.IcyVeinsClient.sitemap_guides",
        lambda self: [{"slug": "mistweaver-monk-pve-healing-guide", "name": "Mistweaver Monk PvE Healing Guide", "url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide"}],
    )
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr(
        "warcraft_wiki_cli.main.WarcraftWikiClient.search_articles",
        lambda self, query, limit: (1, [{"title": "Mistweaver Monk", "pageid": 1, "snippet": "Reference page", "url": "https://warcraft.wiki.gg/wiki/Mistweaver_Monk"}]),
    )

    result = runner.invoke(warcraft_app, ["resolve", "mistweaver monk guide"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["provider"] == "icy-veins"
    assert payload["confidence"] == "high"
    assert payload["next_command"] == "icy-veins guide mistweaver-monk-pve-healing-guide"


def test_warcraft_resolve_prefers_ready_provider(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 5, "id": 86739, "name": "Fairbreeze Favors", "typeName": "Quest", "popularity": 7},
            ],
        }

    monkeypatch.setattr(
        "method_cli.main.MethodClient.sitemap_guides",
        lambda self: [{"slug": "mistweaver-monk", "name": "Mistweaver Monk", "url": "https://www.method.gg/guides/mistweaver-monk"}],
    )
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(warcraft_app, ["resolve", "fairbreeze favors"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["provider"] == "wowhead"
    assert payload["next_command"] == "wowhead entity quest 86739"


def test_warcraft_resolve_can_select_raiderio(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
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
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))

    result = runner.invoke(warcraft_app, ["resolve", "Roguecane"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["provider"] == "raiderio"
    assert payload["next_command"] == "raiderio character us illidan Roguecane"


def test_warcraft_passthrough_to_wowhead(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 3, "id": 19019, "name": "Thunderfury", "typeName": "Item"},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(warcraft_app, ["wowhead", "search", "thunderfury", "--limit", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["query"] == "thunderfury"
    assert payload["results"][0]["name"] == "Thunderfury"


def test_warcraft_passthrough_to_method(monkeypatch) -> None:
    def fake_fetch(self, guide_ref):  # noqa: ANN001
        return {
            "guide": {
                "slug": "mistweaver-monk",
                "page_url": "https://www.method.gg/guides/mistweaver-monk",
                "section_slug": "introduction",
                "section_title": "Introduction",
                "author": "Tincell",
                "last_updated": "Last Updated: 26th Feb, 2026",
                "patch": "Patch 12.0.1",
            },
            "page": {
                "title": "Method Mistweaver Monk Guide - Introduction - Midnight 12.0.1",
                "description": "Learn the Mistweaver Monk basics.",
                "canonical_url": "https://www.method.gg/guides/mistweaver-monk",
            },
            "navigation": [],
            "article": {"html": "<p>Intro</p>", "text": "Intro", "headings": [], "sections": []},
            "linked_entities": [],
        }

    monkeypatch.setattr("method_cli.main.MethodClient.fetch_guide_page", fake_fetch)
    result = runner.invoke(warcraft_app, ["method", "guide", "mistweaver-monk"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["guide"]["slug"] == "mistweaver-monk"
    assert payload["guide"]["author"] == "Tincell"


def test_warcraft_passthrough_to_icy_veins(monkeypatch) -> None:
    def fake_fetch(self, guide_ref):  # noqa: ANN001
        return {
            "guide": {
                "slug": "mistweaver-monk-pve-healing-guide",
                "page_url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
                "section_slug": "mistweaver-monk-pve-healing-guide",
                "section_title": "Mistweaver Monk Guide",
                "author": "Dhaubbs",
                "last_updated": "2026-03-05T05:19:00+00:00",
                "published_at": "2012-09-13T02:17:00+00:00",
            },
            "page": {
                "title": "Mistweaver Monk Healing Guide - Midnight (12.0.1)",
                "description": "This guide contains everything you need to know to be an excellent Mistweaver Monk.",
                "canonical_url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
                "page_type": "guides",
            },
            "navigation": [],
            "page_toc": [],
            "article": {"html": "<p>Intro</p>", "text": "Intro", "intro_text": "General Information", "headings": [], "sections": []},
            "linked_entities": [],
            "citations": {"page": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide"},
        }

    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.fetch_guide_page", fake_fetch)
    result = runner.invoke(warcraft_app, ["icy-veins", "guide", "mistweaver-monk-pve-healing-guide"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["guide"]["slug"] == "mistweaver-monk-pve-healing-guide"
    assert payload["guide"]["author"] == "Dhaubbs"


def test_warcraft_passthrough_to_simc(monkeypatch, tmp_path) -> None:
    profile = tmp_path / "example.simc"
    profile.write_text('monk="example"\n')

    monkeypatch.setattr(
        "simc_cli.main.run_profile",
        lambda paths, profile_path, simc_args: type("Result", (), {"command": [str(paths.build_simc), str(profile_path)], "returncode": 0, "stdout": "Iterations: 1\n", "stderr": ""})(),
    )
    monkeypatch.setattr(
        "simc_cli.main.binary_version",
        lambda paths: type("VersionInfo", (), {"binary_path": paths.build_simc, "available": True, "version_line": "SimulationCraft 1201", "returncode": 1})(),
    )

    result = runner.invoke(warcraft_app, ["simc", "run", str(profile)])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider"] == "simc"
    assert payload["status"] == "completed"
    assert payload["version"] == "SimulationCraft 1201"


def test_warcraft_passthrough_to_raiderio(monkeypatch) -> None:
    def fake_profile(self, *, region: str, realm: str, name: str, fields: str = ""):  # noqa: ANN001
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
            "raid_progression": {},
            "mythic_plus_scores_by_season": [],
            "mythic_plus_ranks": {},
            "mythic_plus_recent_runs": [],
        }

    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.character_profile", fake_profile)
    result = runner.invoke(warcraft_app, ["raiderio", "character", "us", "illidan", "Roguecane"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["character"]["name"] == "Roguecane"


def test_warcraft_passthrough_to_warcraft_wiki(monkeypatch) -> None:
    monkeypatch.setattr(
        "warcraft_wiki_cli.main.WarcraftWikiClient.fetch_article_page",
        lambda self, article_ref: {
            "article": {
                "title": "World of Warcraft API",
                "slug": "world-of-warcraft-api",
                "display_title": "World of Warcraft API",
                "page_url": "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API",
                "section_slug": "world-of-warcraft-api",
                "section_title": "World of Warcraft API",
                "page_count": 1,
            },
            "page": {
                "title": "World of Warcraft API",
                "description": "Programming reference",
                "canonical_url": "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API",
            },
            "navigation": {"count": 0, "items": []},
            "article_content": {"html": "<p>FrameXML</p>", "text": "FrameXML", "headings": [], "sections": []},
            "linked_entities": [],
            "citations": {"page": "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API"},
        },
    )
    result = runner.invoke(warcraft_app, ["warcraft-wiki", "article", "World of Warcraft API"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["article"]["title"] == "World of Warcraft API"


def test_warcraft_passthrough_to_wowprogress(monkeypatch) -> None:
    monkeypatch.setattr(
        "wowprogress_cli.main.WowProgressClient.fetch_guild_page",
        lambda self, *, region, realm, name: {
            "guild": {
                "name": "Liquid",
                "region": "us",
                "realm": "US-Illidan",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
                "armory_url": "https://worldofwarcraft.com/en-us/guild/illidan/liquid",
            },
            "progress": {"summary": "8/8 (M)", "ranks": {"world": "1", "region": "1", "realm": "1"}},
            "item_level": {"average": 724.51, "group_size": "20-man", "ranks": {"world": "9026", "region": "4149", "realm": "238"}},
            "encounters": {"count": 0, "items": []},
            "citations": {"page": "https://www.wowprogress.com/guild/us/illidan/Liquid"},
        },
    )
    result = runner.invoke(warcraft_app, ["wowprogress", "guild", "us", "illidan", "Liquid"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["guild"]["name"] == "Liquid"
