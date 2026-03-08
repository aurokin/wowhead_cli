from __future__ import annotations

import json

from typer.testing import CliRunner

from wowhead_cli.main import app

runner = CliRunner()


def test_search_defaults_to_compact_json(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 3, "id": 19019, "name": "Thunderfury", "typeName": "Item"},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(app, ["search", "thunderfury"])
    assert result.exit_code == 0
    assert result.stdout.startswith('{"ok":true,')
    assert result.stdout.count("\n") == 1


def test_pretty_flag_emits_indented_json(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 3, "id": 19019, "name": "Thunderfury", "typeName": "Item"},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(app, ["--pretty", "search", "thunderfury"])
    assert result.exit_code == 0
    assert result.stdout.startswith("{\n")
    assert '  "ok": true,' in result.stdout


def test_compact_flag_truncates_long_string_fields(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {
            "name": "Thunderfury",
            "tooltip": "x" * 800,
        }

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return "<html><body><script>var lv_comments0 = [];</script></body></html>"

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["--compact", "entity", "item", "19019"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    tooltip = payload["tooltip"]["html"]
    assert isinstance(tooltip, str)
    assert len(tooltip) == 280
    assert tooltip.endswith("...")


def test_fields_flag_projects_requested_fields(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 3, "id": 19019, "name": "Thunderfury", "typeName": "Item"},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(app, ["--fields", "query,count,results", "search", "thunderfury", "--limit", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"ok", "query", "count", "results"}
    assert payload["query"] == "thunderfury"
    assert payload["count"] == 1
    assert payload["results"][0]["id"] == 19019


def test_fields_flag_supports_nested_paths(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Thunderfury", "quality": 5}

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return "<html><body><script>var lv_comments0 = [];</script></body></html>"

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["--fields", "entity.name,tooltip.quality", "entity", "item", "19019"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"entity", "tooltip"}
    assert payload["entity"]["name"] == "Thunderfury"
    assert payload["tooltip"]["quality"] == 5
