from __future__ import annotations

import json

from typer.testing import CliRunner

from wowhead_cli.main import app

runner = CliRunner()

SAMPLE_PAGE_HTML = """
<html>
  <head>
    <meta property="og:title" content="Thunderfury">
    <meta name="description" content="Legendary sword">
    <link rel="canonical" href="https://www.wowhead.com/item=19019/thunderfury">
    <script type="application/json" id="data.pageMeta">{"page":"item","serverTime":"2026-02-19T09:00:00-06:00","availableDataEnvs":[1,11],"envDomain":"wowhead.com"}</script>
  </head>
  <body>
    <a href="/npc=12056/baron-geddon">Baron Geddon</a>
    <script>
      WH.Gatherer.addData(3, 1, {"19019":{"name_enus":"Thunderfury"}});
      var lv_comments0 = [{"id": 11, "number": 0, "user": "A", "body": "Useful", "date": "2024-01-01T00:00:00-06:00", "rating": 7, "nreplies": 0, "replies": []}];
    </script>
  </body>
</html>
"""

SAMPLE_GUIDE_HTML = """
<html>
  <head>
    <meta property="og:title" content="Frost Death Knight DPS Guide - Midnight">
    <meta name="description" content="Guide description">
    <link rel="canonical" href="https://www.wowhead.com/guide/classes/death-knight/frost/overview-pve-dps">
    <script type="application/json" id="data.pageMeta">{"page":"guide","serverTime":"2026-02-19T09:00:00-06:00","availableDataEnvs":[1,2,3],"envDomain":"wowhead.com"}</script>
  </head>
  <body>
    <script>
      var lv_comments0 = [{"id": 91, "number": 0, "user": "A", "body": "Solid guide", "date": "2024-01-01T00:00:00-06:00", "rating": 7, "nreplies": 0, "replies": []}];
    </script>
  </body>
</html>
"""


def test_entity_page_command_returns_links_with_citations(monkeypatch) -> None:
    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return SAMPLE_PAGE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity-page", "item", "19019", "--max-links", "10"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["linked_entities"]["count"] >= 1
    first = payload["linked_entities"]["items"][0]
    assert "citation_url" in first
    assert "source_url" in first


def test_comments_command_returns_comment_citations(monkeypatch) -> None:
    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return SAMPLE_PAGE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["comments", "item", "19019", "--limit", "5"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["comments"][0]["citation_url"].endswith("#comments:id=11")


def test_compare_command_returns_overlap_and_unique_links(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env: int = 11):  # noqa: ANN001
        if entity_id == 19019:
            return {"name": "Thunderfury", "quality": 5, "icon": "inv_sword_39"}
        return {"name": "Maladath", "quality": 4, "icon": "inv_sword_49"}

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        if entity_id == 19019:
            return """
            <html><head>
              <meta property="og:title" content="Thunderfury">
              <meta name="description" content="Legendary sword A">
              <link rel="canonical" href="https://www.wowhead.com/item=19019/thunderfury">
            </head><body>
              <a href="/npc=12056/baron-geddon">Shared</a>
              <a href="/quest=7786/thunderaan">UniqueA</a>
              <script>
                var lv_comments0 = [{"id": 501, "number": 0, "user": "A", "body": "A body", "date": "2024-01-01T00:00:00-06:00", "rating": 8, "nreplies": 0, "replies": []}];
              </script>
            </body></html>
            """
        return """
        <html><head>
          <meta property="og:title" content="Maladath">
          <meta name="description" content="Epic sword B">
          <link rel="canonical" href="https://www.wowhead.com/item=19351/maladath">
        </head><body>
          <a href="/npc=12056/baron-geddon">Shared</a>
          <a href="/quest=7787/other-quest">UniqueB</a>
          <script>
            var lv_comments0 = [{"id": 601, "number": 0, "user": "B", "body": "B body", "date": "2024-02-01T00:00:00-06:00", "rating": 3, "nreplies": 0, "replies": []}];
          </script>
        </body></html>
        """

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)

    result = runner.invoke(app, ["compare", "item:19019", "item:19351", "--comment-sample", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["comparison"]["linked_entities"]["shared_count_total"] == 1
    assert len(payload["comparison"]["linked_entities"]["unique_by_entity"]["item:19019"]) == 1
    assert len(payload["comparison"]["linked_entities"]["unique_by_entity"]["item:19351"]) == 1
    assert payload["comparison"]["fields"]["name"]["all_equal"] is False
    assert payload["entities"][0]["comments"]["top"][0]["citation_url"].endswith("#comments:id=501")


def test_expansions_command_exposes_profiles() -> None:
    result = runner.invoke(app, ["expansions"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["default"] == "retail"
    keys = {row["key"] for row in payload["profiles"]}
    assert "retail" in keys
    assert "wotlk" in keys


def test_search_respects_expansion_flag(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 3, "id": 19019, "name": "Thunderfury", "typeName": "Item"},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(app, ["--expansion", "wotlk", "search", "thunderfury", "--limit", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["expansion"] == "wotlk"
    assert payload["search_url"].startswith("https://www.wowhead.com/wotlk/search?q=")
    assert payload["results"][0]["url"] == "https://www.wowhead.com/wotlk/item=19019"


def test_search_guide_result_includes_guide_url(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 100, "id": 3143, "name": "Frost Death Knight DPS Guide - Midnight", "typeName": "Guide"},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(app, ["--expansion", "wotlk", "search", "frost death knight guide", "--limit", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["results"][0]["entity_type"] == "guide"
    assert payload["results"][0]["url"] == "https://www.wowhead.com/wotlk/guide=3143"


def test_guide_command_supports_id_lookup(monkeypatch) -> None:
    calls = []

    def fake_guide_page_html(self, guide_id: int):  # noqa: ANN001
        calls.append(guide_id)
        return SAMPLE_GUIDE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.guide_page_html", fake_guide_page_html)
    result = runner.invoke(app, ["--expansion", "wotlk", "guide", "3143", "--comment-sample", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert calls == [3143]
    assert payload["guide"]["id"] == 3143
    assert payload["guide"]["lookup_url"] == "https://www.wowhead.com/wotlk/guide=3143"
    assert payload["guide"]["url"] == "https://www.wowhead.com/guide/classes/death-knight/frost/overview-pve-dps"
    assert payload["comments"]["count"] == 1
    assert payload["comments"]["top"][0]["citation_url"].endswith("#comments:id=91")


def test_guide_command_supports_full_wowhead_url(monkeypatch) -> None:
    calls = []

    def fake_page_html(self, page_url: str):  # noqa: ANN001
        calls.append(page_url)
        return SAMPLE_GUIDE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.page_html", fake_page_html)
    guide_url = "https://www.wowhead.com/guide/classes/death-knight/frost/overview-pve-dps"
    result = runner.invoke(app, ["guide", guide_url, "--comment-sample", "0"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert calls == [guide_url]
    assert payload["guide"]["id"] is None
    assert payload["guide"]["lookup_url"] == guide_url
    assert payload["comments"]["top"] == []


def test_guide_command_rejects_non_wowhead_url() -> None:
    result = runner.invoke(app, ["guide", "https://example.com/guide=3143"])
    assert result.exit_code != 0
    assert "Guide URL must point to wowhead.com" in result.output


def test_entity_respects_expansion_flag(monkeypatch) -> None:
    calls = []

    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        calls.append((self.expansion.key, data_env))
        return {"name": "Thunderfury"}

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return SAMPLE_PAGE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["--expansion", "classic", "entity", "item", "19019"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert calls == [("classic", None)]
    assert payload["expansion"] == "classic"
    assert payload["entity"]["url"] == "https://www.wowhead.com/classic/item=19019"
    assert payload["entity"]["comments_url"] == "https://www.wowhead.com/classic/item=19019#comments"
    assert payload["data_env"] == 4
    assert payload["comments"]["count"] == 1
    assert payload["comments"]["all_comments_included"] is True
    assert payload["comments"]["top"][0]["citation_url"].endswith("#comments:id=11")


def test_entity_supports_excluding_comments(monkeypatch) -> None:
    page_calls = []

    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Thunderfury"}

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        page_calls.append((entity_type, entity_id))
        return SAMPLE_PAGE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "item", "19019", "--no-include-comments"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["comments_included"] is False
    assert payload["all_comments_included"] is False
    assert "comments" not in payload
    assert payload["citations"]["page"] == "https://www.wowhead.com/item=19019"
    assert page_calls == []


def test_entity_supports_include_all_comments(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Thunderfury"}

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return SAMPLE_PAGE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "item", "19019", "--include-all-comments"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["comments_included"] is True
    assert payload["all_comments_included"] is True
    assert payload["comments"]["count"] == 1
    assert payload["comments"]["all_comments_included"] is True
    assert "items" in payload["comments"]
    assert "top" not in payload["comments"]
    assert payload["comments"]["items"][0]["id"] == 11


def test_entity_marks_partial_comments_when_more_than_top_limit(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Thunderfury"}

    html = """
    <html><body><script>
      var lv_comments0 = [
        {"id": 1, "number": 0, "user": "A", "body": "One", "date": "2024-01-01T00:00:00-06:00", "rating": 1, "nreplies": 0, "replies": []},
        {"id": 2, "number": 1, "user": "B", "body": "Two", "date": "2024-01-02T00:00:00-06:00", "rating": 2, "nreplies": 0, "replies": []},
        {"id": 3, "number": 2, "user": "C", "body": "Three", "date": "2024-01-03T00:00:00-06:00", "rating": 3, "nreplies": 0, "replies": []},
        {"id": 4, "number": 3, "user": "D", "body": "Four", "date": "2024-01-04T00:00:00-06:00", "rating": 4, "nreplies": 0, "replies": []}
      ];
    </script></body></html>
    """

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "item", "19019"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["all_comments_included"] is False
    assert payload["comments"]["all_comments_included"] is False
    assert payload["comments"]["count"] == 4
    assert len(payload["comments"]["top"]) == 3


def test_compare_respects_expansion_flag_for_generated_urls(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": f"Item {entity_id}", "quality": 1, "icon": "inv_misc_questionmark"}

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        if entity_id == 1:
            return """
            <html><body>
              <a href="/npc=12056/baron-geddon">Shared</a>
              <a href="/quest=7786/unique-a">UniqueA</a>
              <script>var lv_comments0 = [];</script>
            </body></html>
            """
        return """
        <html><body>
          <a href="/npc=12056/baron-geddon">Shared</a>
          <a href="/quest=7787/unique-b">UniqueB</a>
          <script>var lv_comments0 = [];</script>
        </body></html>
        """

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(
        app,
        ["--expansion", "wotlk", "compare", "item:1", "item:2", "--comment-sample", "0", "--max-links-per-entity", "10"],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["expansion"] == "wotlk"
    assert payload["citations"]["entity_pages"] == [
        "https://www.wowhead.com/wotlk/item=1",
        "https://www.wowhead.com/wotlk/item=2",
    ]
    assert payload["comparison"]["linked_entities"]["shared_items"][0]["url"] == "https://www.wowhead.com/wotlk/npc=12056"


def test_invalid_expansion_is_rejected() -> None:
    result = runner.invoke(app, ["--expansion", "not-a-real-expansion", "search", "defias"])
    assert result.exit_code != 0
    assert "Unknown expansion" in result.output


def test_canonical_normalization_flag_for_entity_page(monkeypatch) -> None:
    html = """
    <html><head>
      <meta property="og:title" content="Thunderfury">
      <meta name="description" content="Legendary sword">
      <link rel="canonical" href="https://www.wowhead.com/item=19019/thunderfury-blessed-blade-of-the-windseeker">
    </head><body>
      <a href="/ptr/npc=12056/baron-geddon">Baron Geddon</a>
    </body></html>
    """

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)

    default_result = runner.invoke(app, ["--expansion", "ptr", "entity-page", "item", "19019", "--max-links", "1"])
    assert default_result.exit_code == 0
    default_payload = json.loads(default_result.stdout)
    assert default_payload["normalize_canonical_to_expansion"] is False
    assert default_payload["entity"]["url"] == "https://www.wowhead.com/item=19019/thunderfury-blessed-blade-of-the-windseeker"

    normalized_result = runner.invoke(
        app,
        [
            "--expansion",
            "ptr",
            "--normalize-canonical-to-expansion",
            "entity-page",
            "item",
            "19019",
            "--max-links",
            "1",
        ],
    )
    assert normalized_result.exit_code == 0
    normalized_payload = json.loads(normalized_result.stdout)
    assert normalized_payload["normalize_canonical_to_expansion"] is True
    assert normalized_payload["entity"]["url"] == "https://www.wowhead.com/ptr/item=19019/thunderfury-blessed-blade-of-the-windseeker"


def test_canonical_normalization_flag_for_comments_citations(monkeypatch) -> None:
    html = """
    <html><head>
      <link rel="canonical" href="https://www.wowhead.com/item=19019/thunderfury-blessed-blade-of-the-windseeker">
    </head><body>
      <script>
        var lv_comments0 = [{"id": 11, "number": 0, "user": "A", "body": "Useful", "date": "2024-01-01T00:00:00-06:00", "rating": 7, "nreplies": 0, "replies": []}];
      </script>
    </body></html>
    """

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(
        app,
        [
            "--expansion",
            "ptr",
            "--normalize-canonical-to-expansion",
            "comments",
            "item",
            "19019",
            "--limit",
            "1",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["normalize_canonical_to_expansion"] is True
    assert payload["entity"]["url"] == "https://www.wowhead.com/ptr/item=19019/thunderfury-blessed-blade-of-the-windseeker"
    assert payload["comments"][0]["citation_url"] == "https://www.wowhead.com/ptr/item=19019/thunderfury-blessed-blade-of-the-windseeker#comments:id=11"
