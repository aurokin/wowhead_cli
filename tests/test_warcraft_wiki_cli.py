from __future__ import annotations

import json

from typer.testing import CliRunner

from warcraft_wiki_cli.main import app as warcraft_wiki_app

runner = CliRunner()


def _page_payload() -> dict[str, object]:
    return {
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
        "navigation": {
            "count": 2,
            "items": [
                {"title": "API systems", "url": "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API#API_systems", "section_slug": "API_systems", "active": True, "ordinal": 1},
                {"title": "Object APIs", "url": "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API#Object_APIs", "section_slug": "Object_APIs", "active": True, "ordinal": 2},
            ],
        },
        "article_content": {
            "html": "<h2><span class='mw-headline' id='API_systems'>API systems</span></h2><p>FrameXML reference.</p>",
            "text": "API systems FrameXML reference.",
            "headings": [{"title": "API systems", "level": 2, "ordinal": 1, "anchor": "API_systems"}],
            "sections": [{"title": "API systems", "level": 2, "ordinal": 1, "anchor": "API_systems", "text": "FrameXML reference.", "html": "<p>FrameXML reference.</p>"}],
        },
        "linked_entities": [
            {"type": "wiki_article", "id": "UIOBJECT Frame", "name": "UIOBJECT Frame", "url": "https://warcraft.wiki.gg/wiki/UIOBJECT_Frame"},
        ],
        "citations": {"page": "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API"},
    }


def test_warcraft_wiki_doctor_reports_ready_capabilities() -> None:
    result = runner.invoke(warcraft_wiki_app, ["doctor"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider"] == "warcraft-wiki"
    assert payload["capabilities"]["search"] == "ready"
    assert payload["capabilities"]["article_query"] == "ready"


def test_warcraft_wiki_search_and_resolve(monkeypatch) -> None:
    monkeypatch.setattr(
        "warcraft_wiki_cli.main.WarcraftWikiClient.search_articles",
        lambda self, query, limit: (
            2,
            [
                {"title": "World of Warcraft API", "pageid": 1, "snippet": "API systems and FrameXML.", "url": "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API"},
                {"title": "API", "pageid": 2, "snippet": "General API page.", "url": "https://warcraft.wiki.gg/wiki/API"},
            ],
        ),
    )

    search_result = runner.invoke(warcraft_wiki_app, ["search", "world of warcraft api"])
    assert search_result.exit_code == 0
    search_payload = json.loads(search_result.stdout)
    assert search_payload["results"][0]["entity_type"] == "article"

    resolve_result = runner.invoke(warcraft_wiki_app, ["resolve", "world of warcraft api"])
    assert resolve_result.exit_code == 0
    resolve_payload = json.loads(resolve_result.stdout)
    assert resolve_payload["resolved"] is True
    assert resolve_payload["next_command"] == "warcraft-wiki article 'World of Warcraft API'"


def test_warcraft_wiki_article_and_export(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.fetch_article_page", lambda self, article_ref: _page_payload())

    article_result = runner.invoke(warcraft_wiki_app, ["article", "World of Warcraft API"])
    assert article_result.exit_code == 0
    article_payload = json.loads(article_result.stdout)
    assert article_payload["article"]["title"] == "World of Warcraft API"
    assert article_payload["content"]["section_count"] == 1

    export_dir = tmp_path / "wiki-article"
    export_result = runner.invoke(warcraft_wiki_app, ["article-export", "World of Warcraft API", "--out", str(export_dir)])
    assert export_result.exit_code == 0
    export_payload = json.loads(export_result.stdout)
    assert export_payload["article"]["slug"] == "world-of-warcraft-api"
    assert export_payload["counts"]["sections"] == 1


def test_warcraft_wiki_article_query(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.fetch_article_page", lambda self, article_ref: _page_payload())
    export_dir = tmp_path / "wiki-article"
    export_result = runner.invoke(warcraft_wiki_app, ["article-export", "World of Warcraft API", "--out", str(export_dir)])
    assert export_result.exit_code == 0

    query_result = runner.invoke(warcraft_wiki_app, ["article-query", str(export_dir), "framexml"])
    assert query_result.exit_code == 0
    payload = json.loads(query_result.stdout)
    assert payload["article"]["title"] == "World of Warcraft API"
    assert payload["match_counts"]["sections"] >= 1
