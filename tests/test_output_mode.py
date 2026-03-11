from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from wowhead_cli.cache import FileCacheStore
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
    assert result.stdout.startswith('{"query":"thunderfury",')
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
    assert '  "query": "thunderfury",' in result.stdout


def test_search_results_include_ranking_metadata(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 3, "id": 19019, "name": "Thunderfury", "typeName": "Item", "popularity": 5},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(app, ["search", "thunderfury", "--limit", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["results"][0]["ranking"]["score"] > 0
    assert "match_reasons" in payload["results"][0]["ranking"]

def test_search_results_include_follow_up_metadata(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 3, "id": 19019, "name": "Thunderfury", "typeName": "Item", "popularity": 5},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(app, ["search", "thunderfury", "--limit", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["results"][0]["follow_up"]["recommended_surface"] == "entity"
    assert payload["results"][0]["follow_up"]["recommended_command"] == "wowhead entity item 19019"



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
    assert set(payload.keys()) == {"query", "count", "results"}
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
    result = runner.invoke(app, ["--fields", "entity.name,tooltip.quality,tooltip.summary", "entity", "item", "19019"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"entity", "tooltip"}
    assert payload["entity"]["name"] == "Thunderfury"
    assert payload["tooltip"]["quality"] == 5
    assert "summary" not in payload["tooltip"]


def test_cache_inspect_reports_file_cache_stats(tmp_path: Path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    store = FileCacheStore(cache_dir)
    now = 1000.0
    monkeypatch.setenv("WOWHEAD_CACHE_BACKEND", "file")
    monkeypatch.setenv("WOWHEAD_CACHE_DIR", str(cache_dir))
    monkeypatch.setattr("wowhead_cli.cache.time.time", lambda: now)

    store.set("search_suggestions:active", {"query": "thunderfury"}, ttl_seconds=60)
    store.set("entity_response:expired", {"entity": {"id": 19019}}, ttl_seconds=10)

    monkeypatch.setattr("wowhead_cli.cache.time.time", lambda: now + 20)
    result = runner.invoke(app, ["cache-inspect"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["settings"]["backend"] == "file"
    assert payload["stats"]["totals"] == {"total": 2, "active": 1, "expired": 1, "invalid": 0}
    assert payload["stats"]["namespaces"]["entity_response"]["expired"] == 1
    assert payload["stats"]["namespaces"]["search_suggestions"]["active"] == 1



def test_cache_clear_can_remove_expired_entries_by_namespace(tmp_path: Path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    store = FileCacheStore(cache_dir)
    now = 1000.0
    monkeypatch.setenv("WOWHEAD_CACHE_BACKEND", "file")
    monkeypatch.setenv("WOWHEAD_CACHE_DIR", str(cache_dir))
    monkeypatch.setattr("wowhead_cli.cache.time.time", lambda: now)

    store.set("search_suggestions:active", {"query": "thunderfury"}, ttl_seconds=60)
    store.set("entity_response:expired", {"entity": {"id": 19019}}, ttl_seconds=10)
    store.set("entity_response:active", {"entity": {"id": 19020}}, ttl_seconds=60)

    monkeypatch.setattr("wowhead_cli.cache.time.time", lambda: now + 20)
    result = runner.invoke(app, ["cache-clear", "--namespace", "entity_response", "--expired-only"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["removed"] == {"total": 1, "namespaces": {"entity_response": 1}}
    assert payload["remaining"]["totals"] == {"total": 2, "active": 2, "expired": 0, "invalid": 0}



def test_invalid_cache_config_returns_structured_error(monkeypatch) -> None:
    monkeypatch.setenv("WOWHEAD_CACHE_BACKEND", "broken")
    result = runner.invoke(app, ["search", "thunderfury"])
    assert result.exit_code == 1

    payload = json.loads(result.stderr)
    assert payload == {
        "ok": False,
        "error": {
            "code": "invalid_cache_config",
            "message": "WOWHEAD_CACHE_BACKEND must be one of: file, redis, none.",
        },
    }
