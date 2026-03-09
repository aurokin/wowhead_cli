from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from typer.testing import CliRunner

from wowhead_cli.main import app
from wowhead_cli.wowhead_client import WowheadClient

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
    <script type="application/ld+json">{"@context":"http://schema.org","@type":"Article","headline":"Frost Death Knight DPS Guide - Midnight","datePublished":"2015-03-11T18:36:20-05:00","dateModified":"2026-02-25T17:32:29-06:00","author":{"@type":"Person","name":"khazakdk"}}</script>
    <script type="application/json" id="data.guide.author">"khazakdk"</script>
    <script type="application/json" id="data.guide.author.profiles">{"discord":"https://discord.gg/acherus","youtube":"Khazakdk"}</script>
    <script type="application/json" id="data.guide.aboutTheAuthor.embedData">{"username":"khazakdk","bio":"Writes DK guides."}</script>
    <script type="application/json" id="data.wowhead-guide-nav">"[b]Spec Basics[/b][ul][li][url=guide/classes/death-knight/frost/overview-pve-dps]Overview[/url][/li][li][url=guide/classes/death-knight/frost/bis-gear]BiS Gear[/url][/li][/ul]"</script>
    <script type="application/json" id="data.wowhead-guide-body">"[h2 toc=\\"Overview\\"]Frost Death Knight Overview[/h2]\\r\\nWelcome to the guide.\\r\\n[h3]Strengths[/h3]\\r\\n[ul][li][spell=49020]Big damage[/li][/ul]\\r\\n[url=guide/classes/death-knight/frost/bis-gear]Best in Slot Gear[/url]"</script>
  </head>
  <body>
    <div class="interior-sidebar-rating-text">4.6/5 (<span class="guide-user-actions-rating-votes" id="guiderating-votes">70</span> Votes)</div>
    <script>
      WH.markup.printHtml(WH.getPageData("wowhead-guide-nav"), "interior-sidebar-related-markup");
      WH.markup.printHtml(WH.getPageData("wowhead-guide-body"), "guide-body", {"allow":30});
      $(document).ready(function () {
        $('#guiderating').append(GetStars(4.61597, false, 0, 3143));
      });
      WH.Gatherer.addData(3, 1, {"249277":{"name_enus":"Bellamy's Final Judgement"}});
      var lv_comments0 = [{"id": 91, "number": 0, "user": "A", "body": "Solid guide", "date": "2024-01-01T00:00:00-06:00", "rating": 7, "nreplies": 0, "replies": []}];
    </script>
    <a href="/item=249277/bellamys-final-judgement">Bellamy's Final Judgement</a>
    <a href="/spell=49020/obliterate">Obliterate</a>
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
    assert payload["entity"]["page_url"] == "https://www.wowhead.com/item=19019/thunderfury"
    assert "comments_url" not in payload["entity"]
    assert payload["citations"]["comments"] == "https://www.wowhead.com/item=19019/thunderfury#comments"
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
    assert payload["entity"]["page_url"] == "https://www.wowhead.com/item=19019/thunderfury"
    assert "comments_url" not in payload["entity"]
    assert payload["citations"]["comments"] == "https://www.wowhead.com/item=19019/thunderfury#comments"
    assert payload["comments"][0]["citation_url"].endswith("#comments:id=11")
    assert payload["linked_entities"]["count"] >= 1
    assert payload["linked_entities"]["items"][0]["type"] == "npc"


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
    assert payload["comparison"]["linked_entities"]["shared_count_total"] == 1
    assert len(payload["comparison"]["linked_entities"]["unique_by_entity"]["item:19019"]) == 1
    assert len(payload["comparison"]["linked_entities"]["unique_by_entity"]["item:19351"]) == 1
    assert payload["comparison"]["fields"]["name"]["all_equal"] is False
    assert payload["entities"][0]["comments"]["top"][0]["citation_url"].endswith("#comments:id=501")
    assert payload["entities"][0]["entity"]["page_url"] == "https://www.wowhead.com/item=19019/thunderfury"
    assert "comments_url" not in payload["entities"][0]["entity"]
    assert "page" not in payload["entities"][0]["citations"]
    assert payload["entities"][0]["citations"]["comments"] == "https://www.wowhead.com/item=19019/thunderfury#comments"
    assert "citation_url" not in payload["comparison"]["linked_entities"]["shared_items"][0]
    assert "citation_url" not in payload["comparison"]["linked_entities"]["unique_by_entity"]["item:19019"][0]
    assert "citations" not in payload


def test_expansions_command_exposes_profiles() -> None:
    result = runner.invoke(app, ["expansions"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
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


def test_search_faction_result_includes_faction_url(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 8, "id": 529, "name": "Argent Dawn", "typeName": "Faction"},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(app, ["search", "argent dawn", "--limit", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["results"][0]["entity_type"] == "faction"
    assert payload["results"][0]["url"] == "https://www.wowhead.com/faction=529"


def test_search_pet_result_includes_pet_url(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 9, "id": 39, "name": "Devilsaur", "typeName": "Hunter Pet"},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(app, ["search", "devilsaur", "--limit", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["results"][0]["entity_type"] == "pet"
    assert payload["results"][0]["url"] == "https://www.wowhead.com/pet=39"


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
    assert payload["guide"]["page_url"] == "https://www.wowhead.com/guide/classes/death-knight/frost/overview-pve-dps"
    assert payload["comments"]["count"] == 1
    assert payload["comments"]["top"][0]["citation_url"].endswith("#comments:id=91")
    assert payload["linked_entities"]["count"] >= 2
    assert payload["linked_entities"]["source_counts"] == {"href": 2, "gatherer": 1, "merged": 2}
    assert payload["linked_entities"]["items"][0]["url"]


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


def test_guide_full_returns_rich_payload(monkeypatch) -> None:
    def fake_guide_page_html(self, guide_id: int):  # noqa: ANN001
        assert guide_id == 3143
        return SAMPLE_GUIDE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.guide_page_html", fake_guide_page_html)
    result = runner.invoke(app, ["guide-full", "3143"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["guide"]["id"] == 3143
    assert payload["guide"]["page_url"] == "https://www.wowhead.com/guide/classes/death-knight/frost/overview-pve-dps"
    assert payload["author"]["name"] == "khazakdk"
    assert payload["rating"]["votes"] == 70
    assert payload["body"]["sections"][0]["title"] == "Frost Death Knight Overview"
    assert payload["body"]["section_chunks"][0]["content_text"] == "Welcome to the guide."
    assert payload["navigation"]["links"][0]["url"] == "https://www.wowhead.com/guide/classes/death-knight/frost/overview-pve-dps"
    assert payload["linked_entities"]["count"] >= 2
    assert payload["linked_entities"]["source_counts"] == {"href": 2, "gatherer": 1, "merged": 2}
    assert payload["gatherer_entities"]["items"][0]["id"] == 249277
    assert payload["gatherer_entities"]["items"][0]["citation_url"] == "https://www.wowhead.com/item=249277"
    merged_item = next(row for row in payload["linked_entities"]["items"] if row["id"] == 249277)
    assert merged_item["sources"] == ["gatherer", "href"]
    assert merged_item["source_kind"] == "gatherer"
    assert payload["comments"]["all_comments_included"] is True
    assert payload["comments"]["items"][0]["citation_url"].endswith("#comments:id=91")
    assert payload["structured_data"]["headline"] == "Frost Death Knight DPS Guide - Midnight"


def test_guide_and_guide_full_share_linked_entity_count(monkeypatch) -> None:
    def fake_guide_page_html(self, guide_id: int):  # noqa: ANN001
        assert guide_id == 3143
        return SAMPLE_GUIDE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.guide_page_html", fake_guide_page_html)
    guide_result = runner.invoke(app, ["guide", "3143", "--comment-sample", "0"])
    full_result = runner.invoke(app, ["guide-full", "3143"])
    assert guide_result.exit_code == 0
    assert full_result.exit_code == 0

    guide_payload = json.loads(guide_result.stdout)
    full_payload = json.loads(full_result.stdout)
    assert guide_payload["linked_entities"]["count"] == full_payload["linked_entities"]["count"] == 2


def test_guide_export_writes_local_assets(monkeypatch, tmp_path) -> None:
    def fake_guide_page_html(self, guide_id: int):  # noqa: ANN001
        assert guide_id == 3143
        return SAMPLE_GUIDE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.guide_page_html", fake_guide_page_html)
    export_dir = tmp_path / "guide-export"
    result = runner.invoke(app, ["guide-export", "3143", "--out", str(export_dir)])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["output_dir"] == str(export_dir)
    assert payload["counts"] == {
        "sections": 2,
        "navigation_links": 2,
        "linked_entities": 2,
        "gatherer_entities": 1,
        "hydrated_entities": 0,
        "comments": 1,
    }

    expected_files = {
        "manifest.json",
        "guide.json",
        "page.html",
        "body.markup.txt",
        "navigation.markup.txt",
        "sections.jsonl",
        "navigation-links.jsonl",
        "linked-entities.jsonl",
        "gatherer-entities.jsonl",
        "comments.jsonl",
        "structured-data.json",
    }
    assert expected_files.issubset({path.name for path in export_dir.iterdir()})

    manifest = json.loads((export_dir / "manifest.json").read_text(encoding="utf-8"))
    guide_json = json.loads((export_dir / "guide.json").read_text(encoding="utf-8"))
    assert manifest["files"]["manifest_json"] == "manifest.json"
    assert manifest["files"]["guide_json"] == "guide.json"
    assert guide_json["guide"]["id"] == 3143
    assert manifest["export_version"] == 2
    assert manifest["export_options"] == {
        "guide_ref": "3143",
        "max_links": 250,
        "include_replies": False,
    }
    assert manifest["hydration"] == {
        "enabled": False,
        "types": [],
        "limit": 0,
        "hydrated_at": None,
        "source_counts": {},
    }
    assert isinstance(manifest["exported_at"], str)
    assert isinstance(manifest["guide_fetched_at"], str)

    sections_lines = (export_dir / "sections.jsonl").read_text(encoding="utf-8").strip().splitlines()
    navigation_lines = (export_dir / "navigation-links.jsonl").read_text(encoding="utf-8").strip().splitlines()
    comments_lines = (export_dir / "comments.jsonl").read_text(encoding="utf-8").strip().splitlines()
    first_section = json.loads(sections_lines[0])
    first_nav = json.loads(navigation_lines[0])
    first_comment = json.loads(comments_lines[0])
    linked_entity_lines = (export_dir / "linked-entities.jsonl").read_text(encoding="utf-8").strip().splitlines()
    linked_rows = [json.loads(line) for line in linked_entity_lines]
    merged_item = next(row for row in linked_rows if row["id"] == 249277)
    assert first_section["ordinal"] == 1
    assert first_section["level"] == 2
    assert first_section["title"] == "Frost Death Knight Overview"
    assert first_section["content_text"] == "Welcome to the guide."
    assert first_nav["label"] == "Overview"
    assert first_comment["citation_url"].endswith("#comments:id=91")
    assert merged_item["sources"] == ["gatherer", "href"]
    assert "Welcome to the guide." in (export_dir / "body.markup.txt").read_text(encoding="utf-8")


def test_guide_export_hydrates_linked_entities(monkeypatch, tmp_path: Path) -> None:
    def fake_guide_page_html(self, guide_id: int):  # noqa: ANN001
        assert guide_id == 3143
        return SAMPLE_GUIDE_HTML

    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        if (entity_type, entity_id) == ("spell", 49020):
            return {
                "name": "Obliterate",
                "tooltip": "<table><tr><td><b>Obliterate</b><br>Talent<br>Instant<br>A brutal attack.</td></tr></table>",
            }
        if (entity_type, entity_id) == ("item", 249277):
            return {
                "name": "Bellamy's Final Judgement",
                "tooltip": "<table><tr><td><b>Bellamy's Final Judgement</b><br>Item Level 639</td></tr></table>",
            }
        raise AssertionError(f"Unexpected tooltip lookup: {(entity_type, entity_id)}")

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.guide_page_html", fake_guide_page_html)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)

    export_dir = tmp_path / "guide-export"
    result = runner.invoke(
        app,
        [
            "guide-export",
            "3143",
            "--out",
            str(export_dir),
            "--hydrate-linked-entities",
            "--hydrate-type",
            "spell,item",
            "--hydrate-limit",
            "2",
        ],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["counts"]["hydrated_entities"] == 2
    assert payload["hydration"]["enabled"] is True
    assert payload["hydration"]["types"] == ["spell", "item"]
    assert payload["hydration"]["limit"] == 2
    assert isinstance(payload["hydration"]["hydrated_at"], str)

    entities_manifest = json.loads((export_dir / "entities" / "manifest.json").read_text(encoding="utf-8"))
    assert entities_manifest["count"] == 2
    assert entities_manifest["counts_by_type"] == {"item": 1, "spell": 1}
    assert entities_manifest["counts_by_storage_source"] == {"live_fetch": 2}
    assert {row["path"] for row in entities_manifest["items"]} == {
        "entities/item/249277.json",
        "entities/spell/49020.json",
    }
    assert {row["storage_source"] for row in entities_manifest["items"]} == {"live_fetch"}
    assert payload["hydration"]["source_counts"] == {"live_fetch": 2}

    hydrated_spell = json.loads((export_dir / "entities" / "spell" / "49020.json").read_text(encoding="utf-8"))
    hydrated_item = json.loads((export_dir / "entities" / "item" / "249277.json").read_text(encoding="utf-8"))
    assert hydrated_spell["entity"]["name"] == "Obliterate"
    assert hydrated_item["entity"]["name"] == "Bellamy's Final Judgement"


def test_guide_export_hydration_uses_normalized_entity_cache_before_live_fetch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WOWHEAD_CACHE_BACKEND", "file")
    monkeypatch.setenv("WOWHEAD_CACHE_DIR", str(tmp_path / "cache"))

    def fake_guide_page_html(self, guide_id: int):  # noqa: ANN001
        assert guide_id == 3143
        return SAMPLE_GUIDE_HTML

    def fail_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        raise AssertionError(f"tooltip should not be used when normalized cache is prepopulated: {(entity_type, entity_id)}")

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.guide_page_html", fake_guide_page_html)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fail_tooltip)

    cache_client = WowheadClient(cache_dir=tmp_path / "cache", cache_backend="file")
    cache_client.set_cached_entity_response(
        {
            "expansion": "retail",
            "entity": {
                "type": "spell",
                "id": 49020,
                "name": "Obliterate",
                "page_url": "https://www.wowhead.com/spell=49020/obliterate",
            },
            "tooltip": {
                "summary": "A brutal attack.",
                "text": "Obliterate Talent Instant A brutal attack.",
                "html": "<table><tr><td><b>Obliterate</b><br>Talent<br>Instant<br>A brutal attack.</td></tr></table>",
            },
        },
        requested_type="spell",
        requested_id=49020,
        data_env=None,
        include_comments=False,
        include_all_comments=False,
        linked_entity_preview_limit=0,
    )
    cache_client.set_cached_entity_response(
        {
            "expansion": "retail",
            "entity": {
                "type": "item",
                "id": 249277,
                "name": "Bellamy's Final Judgement",
                "page_url": "https://www.wowhead.com/item=249277/bellamys-final-judgement",
            },
            "tooltip": {
                "summary": "Item Level 639",
                "text": "Bellamy's Final Judgement Item Level 639",
                "html": "<table><tr><td><b>Bellamy's Final Judgement</b><br>Item Level 639</td></tr></table>",
            },
        },
        requested_type="item",
        requested_id=249277,
        data_env=None,
        include_comments=False,
        include_all_comments=False,
        linked_entity_preview_limit=0,
    )

    export_dir = tmp_path / "guide-export"
    result = runner.invoke(
        app,
        [
            "guide-export",
            "3143",
            "--out",
            str(export_dir),
            "--hydrate-linked-entities",
            "--hydrate-type",
            "spell,item",
            "--hydrate-limit",
            "2",
        ],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["hydration"]["source_counts"] == {"entity_cache": 2}
    entities_manifest = json.loads((export_dir / "entities" / "manifest.json").read_text(encoding="utf-8"))
    assert entities_manifest["counts_by_storage_source"] == {"entity_cache": 2}
    assert {row["storage_source"] for row in entities_manifest["items"]} == {"entity_cache"}

    spell_payload = json.loads((export_dir / "entities" / "spell" / "49020.json").read_text(encoding="utf-8"))
    item_payload = json.loads((export_dir / "entities" / "item" / "249277.json").read_text(encoding="utf-8"))
    assert spell_payload["entity"]["name"] == "Obliterate"
    assert item_payload["entity"]["name"] == "Bellamy's Final Judgement"


def test_guide_bundle_refresh_skips_fresh_bundle_with_default_max_age(tmp_path: Path) -> None:
    root = tmp_path / "wowhead_exports"
    bundle_dir = root / "guide-3143-frost"
    bundle_dir.mkdir(parents=True)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "export_version": 2,
                "exported_at": now,
                "guide_fetched_at": now,
                "expansion": "retail",
                "output_dir": str(bundle_dir),
                "guide": {
                    "input": "3143",
                    "id": 3143,
                    "page_url": "https://www.wowhead.com/guide/classes/death-knight/frost/overview-pve-dps",
                },
                "page": {
                    "title": "Frost Death Knight DPS Guide - Midnight",
                    "canonical_url": "https://www.wowhead.com/guide/classes/death-knight/frost/overview-pve-dps",
                },
                "counts": {
                    "sections": 11,
                    "navigation_links": 15,
                    "linked_entities": 52,
                    "gatherer_entities": 52,
                    "hydrated_entities": 0,
                    "comments": 9,
                },
                "hydration": {
                    "enabled": False,
                    "types": [],
                    "limit": 0,
                    "hydrated_at": None,
                },
                "export_options": {
                    "guide_ref": "3143",
                    "max_links": 250,
                    "include_replies": False,
                },
                "files": {"manifest_json": "manifest.json"},
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["guide-bundle-refresh", "3143", "--root", str(root)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["refresh"] == {
        "updated": False,
        "reason": "fresh",
        "max_age_hours": 24,
    }


def test_guide_bundle_refresh_updates_stale_bundle_and_reuses_manifest_settings(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_guide_page_html(self, guide_id: int):  # noqa: ANN001
        assert guide_id == 3143
        return SAMPLE_GUIDE_HTML

    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        if (entity_type, entity_id) == ("spell", 49020):
            return {
                "name": "Obliterate",
                "tooltip": "<table><tr><td><b>Obliterate</b><br>Talent<br>Instant<br>A brutal attack.</td></tr></table>",
            }
        if (entity_type, entity_id) == ("item", 249277):
            return {
                "name": "Bellamy's Final Judgement",
                "tooltip": "<table><tr><td><b>Bellamy's Final Judgement</b><br>Item Level 639</td></tr></table>",
            }
        raise AssertionError(f"Unexpected tooltip lookup: {(entity_type, entity_id)}")

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.guide_page_html", fake_guide_page_html)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)

    export_dir = tmp_path / "guide-export"
    export_result = runner.invoke(
        app,
        [
            "guide-export",
            "3143",
            "--out",
            str(export_dir),
            "--hydrate-linked-entities",
            "--hydrate-type",
            "spell,item",
            "--hydrate-limit",
            "2",
        ],
    )
    assert export_result.exit_code == 0

    manifest_path = export_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stale = (datetime.now(timezone.utc) - timedelta(hours=48)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest["exported_at"] = stale
    manifest["guide_fetched_at"] = stale
    manifest["hydration"]["hydrated_at"] = stale
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = runner.invoke(app, ["guide-bundle-refresh", str(export_dir)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["refresh"] == {
        "updated": True,
        "reason": "stale",
        "max_age_hours": 24,
    }
    assert payload["hydration"]["enabled"] is True
    assert payload["hydration"]["types"] == ["spell", "item"]
    assert payload["counts"]["hydrated_entities"] == 2
    assert (export_dir / "entities" / "manifest.json").exists()


def test_guide_bundle_refresh_rehydrates_only_stale_hydrated_entities(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tooltip_calls: dict[tuple[str, int], int] = {}

    def fake_guide_page_html(self, guide_id: int):  # noqa: ANN001
        assert guide_id == 3143
        return SAMPLE_GUIDE_HTML

    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        key = (entity_type, entity_id)
        tooltip_calls[key] = tooltip_calls.get(key, 0) + 1
        if key == ("spell", 49020):
            return {
                "name": "Obliterate",
                "tooltip": "<table><tr><td><b>Obliterate</b><br>Talent<br>Instant<br>A brutal attack.</td></tr></table>",
            }
        if key == ("item", 249277):
            return {
                "name": "Bellamy's Final Judgement",
                "tooltip": "<table><tr><td><b>Bellamy's Final Judgement</b><br>Item Level 639</td></tr></table>",
            }
        raise AssertionError(f"Unexpected tooltip lookup: {key}")

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.guide_page_html", fake_guide_page_html)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)

    export_dir = tmp_path / "guide-export"
    export_result = runner.invoke(
        app,
        [
            "guide-export",
            "3143",
            "--out",
            str(export_dir),
            "--hydrate-linked-entities",
            "--hydrate-type",
            "spell,item",
            "--hydrate-limit",
            "2",
        ],
    )
    assert export_result.exit_code == 0
    assert tooltip_calls == {
        ("spell", 49020): 1,
        ("item", 249277): 1,
    }

    tooltip_calls.clear()

    stale = (datetime.now(timezone.utc) - timedelta(hours=48)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    fresh = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    manifest_path = export_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["exported_at"] = stale
    manifest["guide_fetched_at"] = stale
    manifest["hydration"]["hydrated_at"] = stale
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    entities_manifest_path = export_dir / "entities" / "manifest.json"
    entities_manifest = json.loads(entities_manifest_path.read_text(encoding="utf-8"))
    items = entities_manifest["items"]
    for row in items:
        if row["entity_type"] == "spell":
            row["stored_at"] = fresh
        elif row["entity_type"] == "item":
            row["stored_at"] = stale
    entities_manifest["hydrated_at"] = stale
    entities_manifest_path.write_text(json.dumps(entities_manifest), encoding="utf-8")

    result = runner.invoke(app, ["guide-bundle-refresh", str(export_dir)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["refresh"] == {
        "updated": True,
        "reason": "stale",
        "max_age_hours": 24,
    }
    assert tooltip_calls == {
        ("item", 249277): 1,
    }

    refreshed_entities_manifest = json.loads(entities_manifest_path.read_text(encoding="utf-8"))
    refreshed_items = {
        (row["entity_type"], row["id"]): row
        for row in refreshed_entities_manifest["items"]
    }
    assert refreshed_items[("spell", 49020)]["stored_at"] == fresh
    assert refreshed_items[("item", 249277)]["stored_at"] != stale
    assert refreshed_items[("spell", 49020)]["storage_source"] == "bundle_store"
    assert refreshed_items[("item", 249277)]["storage_source"] == "live_fetch"
    assert refreshed_entities_manifest["counts_by_storage_source"] == {
        "bundle_store": 1,
        "live_fetch": 1,
    }
    assert payload["hydration"]["source_counts"] == {
        "bundle_store": 1,
        "live_fetch": 1,
    }


def test_guide_export_hydration_provenance_can_mix_cache_and_live_fetch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WOWHEAD_CACHE_BACKEND", "file")
    monkeypatch.setenv("WOWHEAD_CACHE_DIR", str(tmp_path / "cache"))

    def fake_guide_page_html(self, guide_id: int):  # noqa: ANN001
        assert guide_id == 3143
        return SAMPLE_GUIDE_HTML

    tooltip_calls: dict[tuple[str, int], int] = {}

    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        key = (entity_type, entity_id)
        tooltip_calls[key] = tooltip_calls.get(key, 0) + 1
        if key == ("item", 249277):
            return {
                "name": "Bellamy's Final Judgement",
                "tooltip": "<table><tr><td><b>Bellamy's Final Judgement</b><br>Item Level 639</td></tr></table>",
            }
        raise AssertionError(f"Unexpected tooltip lookup: {key}")

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.guide_page_html", fake_guide_page_html)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)

    cache_client = WowheadClient(cache_dir=tmp_path / "cache", cache_backend="file")
    cache_client.set_cached_entity_response(
        {
            "expansion": "retail",
            "entity": {
                "type": "spell",
                "id": 49020,
                "name": "Obliterate",
                "page_url": "https://www.wowhead.com/spell=49020/obliterate",
            },
            "tooltip": {
                "summary": "A brutal attack.",
                "text": "Obliterate Talent Instant A brutal attack.",
                "html": "<table><tr><td><b>Obliterate</b><br>Talent<br>Instant<br>A brutal attack.</td></tr></table>",
            },
        },
        requested_type="spell",
        requested_id=49020,
        data_env=None,
        include_comments=False,
        include_all_comments=False,
        linked_entity_preview_limit=0,
    )

    export_dir = tmp_path / "guide-export"
    result = runner.invoke(
        app,
        [
            "guide-export",
            "3143",
            "--out",
            str(export_dir),
            "--hydrate-linked-entities",
            "--hydrate-type",
            "spell,item",
            "--hydrate-limit",
            "2",
        ],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["hydration"]["source_counts"] == {
        "entity_cache": 1,
        "live_fetch": 1,
    }
    assert tooltip_calls == {
        ("item", 249277): 1,
    }
    entities_manifest = json.loads((export_dir / "entities" / "manifest.json").read_text(encoding="utf-8"))
    assert entities_manifest["counts_by_storage_source"] == {
        "entity_cache": 1,
        "live_fetch": 1,
    }
    source_by_entity = {
        (row["entity_type"], row["id"]): row["storage_source"]
        for row in entities_manifest["items"]
    }
    assert source_by_entity == {
        ("spell", 49020): "entity_cache",
        ("item", 249277): "live_fetch",
    }


def test_guide_query_reads_exported_assets(monkeypatch, tmp_path) -> None:
    def fake_guide_page_html(self, guide_id: int):  # noqa: ANN001
        assert guide_id == 3143
        return SAMPLE_GUIDE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.guide_page_html", fake_guide_page_html)
    export_dir = tmp_path / "guide-export"
    export_result = runner.invoke(app, ["guide-export", "3143", "--out", str(export_dir)])
    assert export_result.exit_code == 0

    result = runner.invoke(app, ["guide-query", str(export_dir), "bellamy", "--limit", "3"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["counts"]["gatherer_entities"] >= 1
    assert payload["matches"]["gatherer_entities"][0]["name"] == "Bellamy's Final Judgement"
    assert payload["top"][0]["kind"] == "linked_entity"
    assert payload["top"][0]["name"] == "Bellamy's Final Judgement"
    assert payload["top"][0]["sources"] == ["gatherer", "href"]

    result = runner.invoke(app, ["guide-query", str(export_dir), "obliterate", "--limit", "3"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["counts"]["linked_entities"] >= 1
    assert payload["matches"]["linked_entities"][0]["entity_type"] == "spell"
    assert payload["matches"]["linked_entities"][0]["name"] == "Obliterate"
    assert payload["top"][0]["kind"] == "linked_entity"
    assert payload["top"][0]["sources"] == ["href"]

    duplicate_entity_rows = [
        row for row in payload["top"] if row.get("entity_type") == "spell" and row.get("id") == 49020
    ]
    assert len(duplicate_entity_rows) == 1

    result = runner.invoke(app, ["guide-query", str(export_dir), "welcome guide", "--limit", "2"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["matches"]["sections"][0]["title"] == "Frost Death Knight Overview"
    assert "Welcome to the guide." in payload["matches"]["sections"][0]["preview"]

    result = runner.invoke(
        app,
        ["guide-query", str(export_dir), "welcome", "--kind", "sections", "--section-title", "overview"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["filters"] == {
        "kinds": ["sections"],
        "section_title": "overview",
        "linked_sources": [],
    }
    assert payload["counts"]["sections"] == 1
    assert payload["counts"]["comments"] == 0
    assert payload["matches"]["sections"][0]["title"] == "Frost Death Knight Overview"

    result = runner.invoke(app, ["guide-query", str(export_dir), "solid", "--kind", "comments"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["counts"]["comments"] == 1
    assert payload["counts"]["sections"] == 0
    assert payload["matches"]["comments"][0]["user"] == "A"

    root = tmp_path / "wowhead_exports"
    selector_dir = root / export_dir.name
    root.mkdir(exist_ok=True)
    export_dir.rename(selector_dir)

    result = runner.invoke(app, ["guide-query", "3143", "obliterate", "--root", str(root)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["output_dir"] == str(selector_dir)
    assert payload["matches"]["linked_entities"][0]["name"] == "Obliterate"

    result = runner.invoke(
        app,
        ["guide-query", "3143", "bellamy", "--root", str(root), "--kind", "linked_entities", "--linked-source", "multi"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["filters"]["linked_sources"] == ["multi"]
    assert payload["counts"]["linked_entities"] == 1
    assert payload["matches"]["linked_entities"][0]["name"] == "Bellamy's Final Judgement"
    assert payload["matches"]["linked_entities"][0]["sources"] == ["gatherer", "href"]

    result = runner.invoke(
        app,
        ["guide-query", "3143", "obliterate", "--root", str(root), "--kind", "linked_entities", "--linked-source", "href"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["filters"]["linked_sources"] == ["href"]
    assert payload["matches"]["linked_entities"][0]["name"] == "Obliterate"

    result = runner.invoke(app, ["guide-query", selector_dir.name, "solid", "--root", str(root), "--kind", "comments"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["output_dir"] == str(selector_dir)
    assert payload["matches"]["comments"][0]["user"] == "A"

    missing_dir = tmp_path / "missing-corpus"
    result = runner.invoke(app, ["guide-query", str(missing_dir), "anything"])
    assert result.exit_code != 0
    assert "does not exist" in result.output

    result = runner.invoke(app, ["guide-query", str(selector_dir), "anything", "--linked-source", "bad-source"])
    assert result.exit_code != 0
    assert "Unsupported linked source filter" in result.output


def test_guide_bundle_list_discovers_exported_bundles(tmp_path) -> None:
    root = tmp_path / "wowhead_exports"
    corpus_a = root / "guide-3143-frost"
    corpus_b = root / "guide-42-other"
    junk = root / "not-a-corpus"
    corpus_a.mkdir(parents=True)
    corpus_b.mkdir(parents=True)
    junk.mkdir(parents=True)

    (corpus_a / "manifest.json").write_text(
        json.dumps(
            {
                "export_version": 1,
                "expansion": "retail",
                "output_dir": str(corpus_a),
                "guide": {"id": 3143, "page_url": "https://www.wowhead.com/guide=3143"},
                "page": {
                    "title": "Frost Death Knight DPS Guide - Midnight",
                    "canonical_url": "https://www.wowhead.com/guide/classes/death-knight/frost/overview-pve-dps",
                },
                "counts": {
                    "sections": 11,
                    "navigation_links": 15,
                    "linked_entities": 27,
                    "gatherer_entities": 52,
                    "comments": 9,
                },
                "files": {"manifest_json": "manifest.json"},
            }
        ),
        encoding="utf-8",
    )
    (corpus_b / "manifest.json").write_text(
        json.dumps(
            {
                "export_version": 1,
                "expansion": "classic",
                "output_dir": str(corpus_b),
                "guide": {"id": 42, "page_url": "https://www.wowhead.com/guide=42"},
                "page": {
                    "title": "Arcane Mage Guide",
                    "canonical_url": "https://www.wowhead.com/guide/classes/mage/arcane/overview-pve-dps",
                },
                "counts": {
                    "sections": 4,
                    "navigation_links": 6,
                    "linked_entities": 5,
                    "gatherer_entities": 3,
                    "comments": 2,
                },
                "files": {"manifest_json": "manifest.json"},
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["guide-bundle-list", "--root", str(root)])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["root"] == str(root)
    assert payload["count"] == 2
    assert [row["guide_id"] for row in payload["bundles"]] == [42, 3143]
    assert payload["bundles"][0]["dir_name"] == "guide-42-other"
    assert payload["bundles"][0]["title"] == "Arcane Mage Guide"
    assert payload["bundles"][1]["counts"]["linked_entities"] == 27


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
    assert payload["entity"]["name"] == "Thunderfury"
    assert payload["entity"]["page_url"] == "https://www.wowhead.com/item=19019/thunderfury"
    assert "tooltip" not in payload
    assert payload["citations"]["comments"] == "https://www.wowhead.com/item=19019/thunderfury#comments"
    assert payload["comments"]["count"] == 1
    assert payload["comments"]["all_comments_included"] is True
    assert payload["comments"]["needs_raw_fetch"] is False
    assert payload["comments"]["top"][0]["citation_url"].endswith("#comments:id=11")
    assert payload["linked_entities"]["count"] >= 1
    assert payload["linked_entities"]["counts_by_type"]["npc"] == 1
    assert payload["linked_entities"]["fetch_more_command"] == "wowhead entity-page item 19019 --max-links 200"


def test_entity_faction_uses_page_metadata_tooltip_fallback(monkeypatch) -> None:
    html = """
    <html><head>
      <meta property="og:title" content="Argent Dawn">
      <meta name="description" content="Protect Azeroth from the Scourge.">
      <link rel="canonical" href="https://www.wowhead.com/faction=529/argent-dawn">
    </head><body><script>var lv_comments0 = [];</script></body></html>
    """

    def fail_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        raise AssertionError("tooltip should not be called for faction fallback")

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        assert (entity_type, entity_id) == ("faction", 529)
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fail_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "faction", "529", "--no-include-comments", "--linked-entity-preview-limit", "0"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["entity"] == {
        "type": "faction",
        "id": 529,
        "name": "Argent Dawn",
        "page_url": "https://www.wowhead.com/faction=529/argent-dawn",
    }
    assert payload["tooltip"]["text"] == "Argent Dawn Protect Azeroth from the Scourge."
    assert payload["tooltip"]["summary"] == "Protect Azeroth from the Scourge."


def test_entity_recipe_routes_through_spell_tooltip(monkeypatch) -> None:
    tooltip_calls = []

    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        tooltip_calls.append((entity_type, entity_id, data_env))
        return {"name": "Seasoned Wolf Kabob", "tooltip": "<b>Seasoned Wolf Kabob</b>"}

    def fail_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        raise AssertionError("entity page should not be fetched")

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fail_html)
    result = runner.invoke(app, ["entity", "recipe", "2549", "--no-include-comments", "--linked-entity-preview-limit", "0"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert tooltip_calls == [("spell", 2549, None)]
    assert payload["entity"]["type"] == "recipe"
    assert payload["entity"]["id"] == 2549
    assert payload["entity"]["page_url"] == "https://www.wowhead.com/spell=2549"
    assert payload["entity"]["name"] == "Seasoned Wolf Kabob"


def test_entity_page_mount_resolves_underlying_item_page(monkeypatch) -> None:
    page_calls = []
    html = """
    <html><head>
      <meta property="og:title" content="Reins of the Grand Expedition Yak">
      <meta name="description" content="Mount item">
      <link rel="canonical" href="https://www.wowhead.com/item=84101/reins-of-the-grand-expedition-yak">
    </head><body><a href="/npc=62809/grand-expedition-yak">Yak</a></body></html>
    """

    def fake_tooltip_with_metadata(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        assert (entity_type, entity_id) == ("mount", 460)
        return {"name": "Reins of the Grand Expedition Yak"}, "https://nether.wowhead.com/tooltip/item/84101?dataEnv=1"

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        page_calls.append((entity_type, entity_id))
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip_with_metadata", fake_tooltip_with_metadata)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity-page", "mount", "460", "--max-links", "5"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert page_calls == [("item", 84101)]
    assert payload["entity"]["type"] == "mount"
    assert payload["entity"]["id"] == 460
    assert payload["entity"]["page_url"] == "https://www.wowhead.com/item=84101/reins-of-the-grand-expedition-yak"
    assert payload["linked_entities"]["count"] == 1


def test_comments_battle_pet_resolves_underlying_npc_page(monkeypatch) -> None:
    page_calls = []
    html = """
    <html><head>
      <meta property="og:title" content="Mechanical Squirrel">
      <meta name="description" content="Battle pet">
      <link rel="canonical" href="https://www.wowhead.com/npc=2671/mechanical-squirrel">
    </head><body>
      <a href="/item=4401/mechanical-squirrel-box">Mechanical Squirrel Box</a>
      <script>
        var lv_comments0 = [{"id": 11, "number": 0, "user": "A", "body": "Useful", "date": "2024-01-01T00:00:00-06:00", "rating": 7, "nreplies": 0, "replies": []}];
      </script>
    </body></html>
    """

    def fake_tooltip_with_metadata(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        assert (entity_type, entity_id) == ("battle-pet", 39)
        return {"name": "Mechanical Squirrel"}, "https://nether.wowhead.com/tooltip/npc/2671?dataEnv=1"

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        page_calls.append((entity_type, entity_id))
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip_with_metadata", fake_tooltip_with_metadata)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["comments", "battle-pet", "39", "--limit", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert page_calls == [("npc", 2671)]
    assert payload["entity"]["type"] == "battle-pet"
    assert payload["entity"]["id"] == 39
    assert payload["entity"]["page_url"] == "https://www.wowhead.com/npc=2671/mechanical-squirrel"
    assert payload["comments"][0]["citation_url"].endswith("#comments:id=11")


def test_entity_page_merges_multi_source_linked_entities(monkeypatch) -> None:
    html = """
    <html><head>
      <meta property="og:title" content="Thunderfury">
      <meta name="description" content="Legendary sword">
      <link rel="canonical" href="https://www.wowhead.com/item=19019/thunderfury">
    </head><body>
      <a href="/spell=49020"></a>
      <script>
        WH.Gatherer.addData(6, 1, {"49020":{"name_enus":"Obliterate"}});
        var lv_comments0 = [];
      </script>
    </body></html>
    """

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity-page", "item", "19019", "--max-links", "5"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["linked_entities"]["count"] == 1
    assert payload["linked_entities"]["items"][0]["name"] == "Obliterate"
    assert payload["linked_entities"]["items"][0]["sources"] == ["gatherer", "href"]
    assert payload["linked_entities"]["items"][0]["source_kind"] == "gatherer"


def test_entity_supports_excluding_comments(monkeypatch) -> None:
    page_calls = []

    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Thunderfury"}

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        page_calls.append((entity_type, entity_id))
        return SAMPLE_PAGE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "item", "19019", "--no-include-comments", "--linked-entity-preview-limit", "0"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert "comments" not in payload
    assert "linked_entities" not in payload
    assert payload["entity"]["page_url"] == "https://www.wowhead.com/item=19019"
    assert "citations" not in payload
    assert page_calls == []


def test_entity_includes_linked_entity_preview_without_comments(monkeypatch) -> None:
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
    assert payload["linked_entities"]["count"] >= 1
    assert payload["linked_entities"]["counts_by_type"]["npc"] == 1
    assert payload["linked_entities"]["items"][0]["type"] == "npc"
    assert set(payload["linked_entities"]["items"][0].keys()) == {"type", "id", "name", "url"}
    assert payload["linked_entities"]["more_available"] is False
    assert page_calls == [("item", 19019)]


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
    assert payload["comments"]["count"] == 1
    assert payload["comments"]["all_comments_included"] is True
    assert payload["comments"]["needs_raw_fetch"] is False
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
    assert payload["comments"]["all_comments_included"] is False
    assert payload["comments"]["needs_raw_fetch"] is True
    assert payload["comments"]["count"] == 4
    assert len(payload["comments"]["top"]) == 3


def test_entity_normalizes_tooltip_name_and_html(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Thunderfury", "tooltip": "<b>Legendary</b> weapon", "quality": 5}

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return "<html><body><script>var lv_comments0 = [];</script></body></html>"

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "item", "19019"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["entity"]["name"] == "Thunderfury"
    assert payload["tooltip"]["quality"] == 5
    assert payload["tooltip"]["html"] == "<b>Legendary</b> weapon"
    assert payload["tooltip"]["text"] == "Legendary weapon"
    assert payload["tooltip"]["summary"] == "Legendary weapon"
    assert "name" not in payload["tooltip"]
    assert "tooltip" not in payload["tooltip"]


def test_entity_cleans_spell_tooltip_artifacts_and_builds_summary(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {
            "name": "Obliterate",
            "tooltip": (
                "<a href=\"/spell=49020/obliterate\"><b>Obliterate</b></a>"
                "<div>Talent</div><div>Instant</div>"
                "<div>A brutal attack [that deals [(105.751% of Attack Power)] Physical and "
                "[(105.751% of Attack Power)] Frost damage.] Physical and Frost damage.]</div>"
            ),
        }

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return "<html><body><script>var lv_comments0 = [];</script></body></html>"

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "spell", "49020"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["tooltip"]["text"] == "Obliterate Talent Instant A brutal attack Physical and Frost damage."
    assert payload["tooltip"]["summary"] == "A brutal attack Physical and Frost damage."


def test_entity_item_summary_prefers_effect_text_over_item_metadata(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {
            "name": "Thunderfury",
            "tooltip": (
                "<table><tr><td><b>Thunderfury</b><br>Item Level 40<br>Binds when picked up</td></tr></table>"
                "<table><tr><td>Chance on hit: Blasts your enemy with lightning and slows its attack speed.</td></tr></table>"
            ),
        }

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return "<html><body><script>var lv_comments0 = [];</script></body></html>"

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "item", "19019"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["tooltip"]["summary"] == "Chance on hit: Blasts your enemy with lightning and slows its attack speed."


def test_entity_mount_summary_prefers_use_text_over_mount_metadata(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {
            "name": "Grand Expedition Yak",
            "tooltip": (
                "<table><tr><td><b>Grand Expedition Yak</b><br>Item Level 10<br>Mount (Account-wide)</td></tr></table>"
                "<table><tr><td>Use: Teaches you how to summon this three-person mount with vendors.</td></tr></table>"
            ),
        }

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return "<html><body><script>var lv_comments0 = [];</script></body></html>"

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "mount", "460"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["tooltip"]["summary"] == "Use: Teaches you how to summon this three-person mount with vendors."


def test_entity_item_tooltip_text_formats_money_and_stat_spacing(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {
            "name": "Maladath",
            "tooltip": (
                "<table><tr><td><b>Maladath</b><br>+ 4 Parry<br>+ 2 Haste<br>"
                "Sell Price: 86 98</td></tr></table>"
            ),
        }

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return "<html><body><script>var lv_comments0 = [];</script></body></html>"

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "item", "19351"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["tooltip"]["text"] == "Maladath +4 Parry +2 Haste Sell Price: 86g 98s"


def test_entity_item_style_tooltip_text_drops_flavor_quotes_and_normalizes_parenthetical_level(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {
            "name": "Grand Expedition Yak",
            "tooltip": (
                "<table><tr><td><b>Grand Expedition Yak</b><br>Requires level 1 to 90 ( 90)<br>"
                "Sell Price: 30,000<br>"
                "\"These beasts of burden are known to carry over five times their own weight.\"<br>"
                "Vendor: Uncle Bigpocket<br>Cost: 120000</td></tr></table>"
            ),
        }

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return "<html><body><script>var lv_comments0 = [];</script></body></html>"

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "item", "84101"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["tooltip"]["text"] == (
        "Grand Expedition Yak Requires level 1 to 90 (90) Sell Price: 30,000g Vendor: Uncle Bigpocket Cost: 120000g"
    )


def test_entity_tooltip_summary_strips_leading_entity_name(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {
            "name": "Fairbreeze Favors",
            "tooltip": (
                "<table><tr><td><b>Fairbreeze Favors</b></td></tr></table>"
                "<table><tr><td>Help restore order in Fairbreeze Village.</td></tr></table>"
            ),
        }

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return "<html><body><script>var lv_comments0 = [];</script></body></html>"

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "quest", "86739"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["tooltip"]["text"] == "Fairbreeze Favors Help restore order in Fairbreeze Village."
    assert payload["tooltip"]["summary"] == "Help restore order in Fairbreeze Village."


def test_entity_uses_normalized_entity_cache_between_invocations(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WOWHEAD_CACHE_BACKEND", "file")
    monkeypatch.setenv("WOWHEAD_CACHE_DIR", str(tmp_path / "cache"))
    calls = {"tooltip": 0}

    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        calls["tooltip"] += 1
        return {
            "name": "Thunderfury",
            "tooltip": "<table><tr><td><b>Thunderfury</b><br>Legendary weapon</td></tr></table>",
        }

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        raise AssertionError("entity_page_html should not be used when comments and preview are disabled")

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)

    args = ["entity", "item", "19019", "--no-include-comments", "--linked-entity-preview-limit", "0"]
    first = runner.invoke(app, args)
    assert first.exit_code == 0
    second = runner.invoke(app, args)
    assert second.exit_code == 0

    assert calls["tooltip"] == 1
    assert json.loads(first.stdout) == json.loads(second.stdout)


def test_entity_preview_prefers_gatherer_name_when_href_label_missing(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Thunderfury"}

    html = """
    <html><head>
      <link rel="canonical" href="https://www.wowhead.com/item=19019/thunderfury">
    </head><body>
      <a href="/spell=49020"></a>
      <script>
        WH.Gatherer.addData(6, 1, {"49020":{"name_enus":"Obliterate"}});
        var lv_comments0 = [];
      </script>
    </body></html>
    """

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "item", "19019", "--no-include-comments"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["linked_entities"]["items"][0] == {
        "type": "spell",
        "id": 49020,
        "name": "Obliterate",
        "url": "https://www.wowhead.com/spell=49020",
    }


def test_entity_preview_prefers_multi_source_links_over_single_source_peers(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Thunderfury"}

    html = """
    <html><head>
      <link rel="canonical" href="https://www.wowhead.com/item=19019/thunderfury">
    </head><body>
      <a href="/spell=49020/obliterate">Obliterate</a>
      <a href="/spell=49184/howling-blast">Howling Blast</a>
      <script>
        WH.Gatherer.addData(6, 1, {"49020":{"name_enus":"Obliterate"}});
        var lv_comments0 = [];
      </script>
    </body></html>
    """

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "item", "19019", "--no-include-comments", "--linked-entity-preview-limit", "2"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert [row["id"] for row in payload["linked_entities"]["items"]] == [49020, 49184]


def test_entity_preview_fetch_more_command_scales_with_known_count(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Valorstones"}

    links = "\n".join(f'<a href="/item={200000 + idx}">Item {idx}</a>' for idx in range(250))
    html = f"""
    <html><head>
      <link rel="canonical" href="https://www.wowhead.com/currency=3008/valorstones">
    </head><body>
      {links}
      <script>var lv_comments0 = [];</script>
    </body></html>
    """

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "currency", "3008", "--no-include-comments"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["linked_entities"]["count"] == 250
    assert payload["linked_entities"]["fetch_more_command"] == "wowhead entity-page currency 3008 --max-links 250"


def test_entity_preview_suppresses_low_signal_names(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Hogger"}

    html = """
    <html><head>
      <link rel="canonical" href="https://www.wowhead.com/npc=448/hogger">
    </head><body>
      <a href="/item=727">item</a>
      <a href="/npc=34942/memory-of-hogger">Memory of Hogger</a>
      <a href="/spell=8732/thunderclap">Thunderclap</a>
      <script>var lv_comments0 = [];</script>
    </body></html>
    """

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "npc", "448", "--no-include-comments"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["linked_entities"]["items"][0] == {
        "type": "npc",
        "id": 34942,
        "name": "Memory of Hogger",
        "url": "https://www.wowhead.com/npc=34942",
    }
    assert payload["linked_entities"]["items"][-1]["name"] is None


def test_entity_preview_prefers_diverse_high_value_types(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Test Item"}

    html = """
    <html><head>
      <link rel="canonical" href="https://www.wowhead.com/item=1/test-item">
    </head><body>
      <a href="/item=2/item-two">Item Two</a>
      <a href="/item=3/item-three">Item Three</a>
      <a href="/npc=4/test-npc">Test NPC</a>
      <a href="/quest=5/test-quest">Test Quest</a>
      <a href="/spell=6/test-spell">Test Spell</a>
      <script>var lv_comments0 = [];</script>
    </body></html>
    """

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "item", "1", "--no-include-comments", "--linked-entity-preview-limit", "4"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert [row["type"] for row in payload["linked_entities"]["items"]] == ["npc", "quest", "spell", "item"]


def test_currency_preview_demotes_items_below_more_actionable_types(monkeypatch) -> None:
    def fake_tooltip(self, entity_type: str, entity_id: int, data_env=None):  # noqa: ANN001, ANN202
        return {"name": "Valorstones"}

    html = """
    <html><head>
      <link rel="canonical" href="https://www.wowhead.com/currency=3008/valorstones">
    </head><body>
      <a href="/item=10/item-ten">Item Ten</a>
      <a href="/item=11/item-eleven">Item Eleven</a>
      <a href="/npc=12/test-npc">Test NPC</a>
      <a href="/quest=13/test-quest">Test Quest</a>
      <a href="/spell=14/test-spell">Test Spell</a>
      <a href="/object=15/test-object">Test Object</a>
      <script>var lv_comments0 = [];</script>
    </body></html>
    """

    def fake_html(self, entity_type: str, entity_id: int):  # noqa: ANN001
        return html

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.tooltip", fake_tooltip)
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.entity_page_html", fake_html)
    result = runner.invoke(app, ["entity", "currency", "3008", "--no-include-comments", "--linked-entity-preview-limit", "4"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert [row["type"] for row in payload["linked_entities"]["items"]] == ["npc", "quest", "spell", "object"]


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
    assert [row["entity"]["page_url"] for row in payload["entities"]] == [
        "https://www.wowhead.com/wotlk/item=1",
        "https://www.wowhead.com/wotlk/item=2",
    ]
    assert payload["comparison"]["linked_entities"]["shared_items"][0]["url"] == "https://www.wowhead.com/wotlk/npc=12056"
    assert "citation_url" not in payload["comparison"]["linked_entities"]["shared_items"][0]


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
    assert default_payload["entity"]["page_url"] == "https://www.wowhead.com/item=19019/thunderfury-blessed-blade-of-the-windseeker"

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
    assert normalized_payload["entity"]["page_url"] == "https://www.wowhead.com/ptr/item=19019/thunderfury-blessed-blade-of-the-windseeker"


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
    assert payload["entity"]["page_url"] == "https://www.wowhead.com/ptr/item=19019/thunderfury-blessed-blade-of-the-windseeker"
    assert payload["comments"][0]["citation_url"] == "https://www.wowhead.com/ptr/item=19019/thunderfury-blessed-blade-of-the-windseeker#comments:id=11"
