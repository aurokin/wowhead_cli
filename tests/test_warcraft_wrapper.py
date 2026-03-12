from __future__ import annotations

import json

from typer.testing import CliRunner

from method_cli.main import app as method_app
from warcraft_cli.main import app as warcraft_app

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
    assert payload["wrapper"]["provider_count"] == 2
    providers = {row["provider"]: row for row in payload["providers"]}
    assert providers["wowhead"]["status"] == "ready"
    assert providers["method"]["status"] == "ready"
    assert providers["method"]["details"]["capabilities"]["guide"] == "ready"


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
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(warcraft_app, ["search", "thunderfury", "--limit", "3"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider_count"] == 2
    assert payload["count"] == 1
    assert payload["results"][0]["provider"] == "wowhead"
    providers = {row["provider"]: row for row in payload["providers"]}
    assert providers["method"]["payload"]["count"] == 0
    assert providers["wowhead"]["payload"]["results"][0]["name"] == "Thunderfury"


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
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(warcraft_app, ["resolve", "fairbreeze favors"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["provider"] == "wowhead"
    assert payload["next_command"] == "wowhead entity quest 86739"


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


def test_warcraft_passthrough_to_method_stub(monkeypatch) -> None:
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
