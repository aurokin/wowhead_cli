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
    assert payload["linked_entities"]["count"] >= 2
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
    assert payload["ok"] is True
    assert payload["guide"]["id"] == 3143
    assert payload["author"]["name"] == "khazakdk"
    assert payload["rating"]["votes"] == 70
    assert payload["body"]["sections"][0]["title"] == "Frost Death Knight Overview"
    assert payload["body"]["section_chunks"][0]["content_text"] == "Welcome to the guide."
    assert payload["navigation"]["links"][0]["url"] == "https://www.wowhead.com/guide/classes/death-knight/frost/overview-pve-dps"
    assert payload["linked_entities"]["count"] >= 2
    assert payload["gatherer_entities"]["items"][0]["id"] == 249277
    assert payload["comments"]["all_comments_included"] is True
    assert payload["comments"]["items"][0]["citation_url"].endswith("#comments:id=91")
    assert payload["structured_data"]["headline"] == "Frost Death Knight DPS Guide - Midnight"


def test_guide_export_writes_local_assets(monkeypatch, tmp_path) -> None:
    def fake_guide_page_html(self, guide_id: int):  # noqa: ANN001
        assert guide_id == 3143
        return SAMPLE_GUIDE_HTML

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.guide_page_html", fake_guide_page_html)
    export_dir = tmp_path / "guide-export"
    result = runner.invoke(app, ["guide-export", "3143", "--out", str(export_dir)])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["output_dir"] == str(export_dir)
    assert payload["counts"] == {
        "sections": 2,
        "navigation_links": 2,
        "linked_entities": 2,
        "gatherer_entities": 1,
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

    sections_lines = (export_dir / "sections.jsonl").read_text(encoding="utf-8").strip().splitlines()
    navigation_lines = (export_dir / "navigation-links.jsonl").read_text(encoding="utf-8").strip().splitlines()
    comments_lines = (export_dir / "comments.jsonl").read_text(encoding="utf-8").strip().splitlines()
    first_section = json.loads(sections_lines[0])
    first_nav = json.loads(navigation_lines[0])
    first_comment = json.loads(comments_lines[0])
    assert first_section["ordinal"] == 1
    assert first_section["level"] == 2
    assert first_section["title"] == "Frost Death Knight Overview"
    assert first_section["content_text"] == "Welcome to the guide."
    assert first_nav["label"] == "Overview"
    assert first_comment["citation_url"].endswith("#comments:id=91")
    assert "Welcome to the guide." in (export_dir / "body.markup.txt").read_text(encoding="utf-8")


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
    assert payload["ok"] is True
    assert payload["counts"]["gatherer_entities"] >= 1
    assert payload["matches"]["gatherer_entities"][0]["name"] == "Bellamy's Final Judgement"
    assert payload["top"][0]["score"] >= 1

    result = runner.invoke(app, ["guide-query", str(export_dir), "obliterate", "--limit", "3"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["counts"]["linked_entities"] >= 1
    assert payload["matches"]["linked_entities"][0]["entity_type"] == "spell"
    assert payload["matches"]["linked_entities"][0]["name"] == "Obliterate"

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

    result = runner.invoke(app, ["guide-query", selector_dir.name, "solid", "--root", str(root), "--kind", "comments"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["output_dir"] == str(selector_dir)
    assert payload["matches"]["comments"][0]["user"] == "A"

    missing_dir = tmp_path / "missing-corpus"
    result = runner.invoke(app, ["guide-query", str(missing_dir), "anything"])
    assert result.exit_code != 0
    assert "does not exist" in result.output


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
                "ok": True,
                "export_version": 1,
                "expansion": "retail",
                "output_dir": str(corpus_a),
                "guide": {"id": 3143, "url": "https://www.wowhead.com/guide=3143"},
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
                "ok": True,
                "export_version": 1,
                "expansion": "classic",
                "output_dir": str(corpus_b),
                "guide": {"id": 42, "url": "https://www.wowhead.com/guide=42"},
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
    assert payload["ok"] is True
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
    assert "name" not in payload["tooltip"]
    assert "tooltip" not in payload["tooltip"]


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
