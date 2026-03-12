from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from method_cli.main import app
from method_cli.page_parser import parse_guide_page, parse_sitemap_guides

runner = CliRunner()

INTRO_HTML = """
<html>
  <head>
    <title>Method Mistweaver Monk Guide - Introduction - Midnight 12.0.1</title>
    <meta name="description" content="Learn the Mistweaver Monk basics.">
    <meta property="og:title" content="Method Mistweaver Monk Guide - Introduction - Midnight 12.0.1">
    <link rel="canonical" href="https://www.method.gg/guides/mistweaver-monk">
  </head>
  <body>
    <nav>
      <ul class="guide-navigation">
        <li class="active"><a href="/guides/mistweaver-monk">Introduction</a></li>
        <li><a href="/guides/mistweaver-monk/talents">Talents</a></li>
      </ul>
    </nav>
    <div class="guides-titles">
      <span class="guide-author">Patch 12.0.1</span>
      <span class="guide-update-date"><strong>Last Updated: </strong>26th Feb, 2026</span>
    </div>
    <div class="guides-author-block">
      <span class="author-name">Tincell</span>
    </div>
    <article class="guide-main-content">
      <div class="guide-section-title"><h2>Introduction</h2></div>
      <p>Intro copy for Mistweaver Monk.</p>
      <h3>Mistweaver Monk Overview</h3>
      <p>Use <a href="https://www.wowhead.com/spell=116670/vivify">Vivify</a> well.</p>
    </article>
  </body>
</html>
"""

TALENTS_HTML = """
<html>
  <head>
    <title>Method Mistweaver Monk Guide - Talents - Midnight 12.0.1</title>
    <meta name="description" content="Learn the Mistweaver Monk talents.">
    <meta property="og:title" content="Method Mistweaver Monk Guide - Talents - Midnight 12.0.1">
    <link rel="canonical" href="https://www.method.gg/guides/mistweaver-monk/talents">
  </head>
  <body>
    <nav>
      <ul class="guide-navigation">
        <li><a href="/guides/mistweaver-monk">Introduction</a></li>
        <li class="active"><a href="/guides/mistweaver-monk/talents">Talents</a></li>
      </ul>
    </nav>
    <div class="guides-titles">
      <span class="guide-author">Patch 12.0.1</span>
      <span class="guide-update-date"><strong>Last Updated: </strong>26th Feb, 2026</span>
    </div>
    <div class="guides-author-block">
      <span class="author-name">Tincell</span>
    </div>
    <article class="guide-main-content">
      <div class="guide-section-title"><h2>Talents</h2></div>
      <p>Talent page copy.</p>
      <h3>Raid Talents</h3>
      <p>Pick <a href="https://www.wowhead.com/spell=388020/tea-of-serenity">Tea of Serenity</a>.</p>
    </article>
  </body>
</html>
"""

SITEMAP_XML = """
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.method.gg/guides/mistweaver-monk</loc></url>
  <url><loc>https://www.method.gg/guides/mistweaver-monk/talents</loc></url>
  <url><loc>https://www.method.gg/guides/restoration-shaman</loc></url>
</urlset>
"""


def _fake_fetch_guide_page(guide_ref: str) -> dict[str, object]:
    if str(guide_ref).endswith("/talents"):
        return parse_guide_page(TALENTS_HTML, source_url="https://www.method.gg/guides/mistweaver-monk/talents")
    return parse_guide_page(INTRO_HTML, source_url="https://www.method.gg/guides/mistweaver-monk")


def test_parse_sitemap_guides_filters_intro_pages() -> None:
    guides = parse_sitemap_guides(SITEMAP_XML)
    assert guides == [
        {"slug": "mistweaver-monk", "name": "Mistweaver Monk", "url": "https://www.method.gg/guides/mistweaver-monk"},
        {"slug": "restoration-shaman", "name": "Restoration Shaman", "url": "https://www.method.gg/guides/restoration-shaman"},
    ]


def test_parse_guide_page_extracts_sections_navigation_and_links() -> None:
    payload = parse_guide_page(INTRO_HTML, source_url="https://www.method.gg/guides/mistweaver-monk")
    assert payload["guide"]["slug"] == "mistweaver-monk"
    assert payload["guide"]["section_slug"] == "introduction"
    assert payload["guide"]["author"] == "Tincell"
    assert payload["guide"]["patch"] == "Patch 12.0.1"
    assert payload["navigation"][0]["active"] is True
    assert payload["article"]["sections"][0]["title"] == "Introduction"
    assert payload["linked_entities"][0]["type"] == "spell"
    assert payload["linked_entities"][0]["id"] == 116670


def test_method_search_command_uses_sitemap_guides(monkeypatch) -> None:
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: parse_sitemap_guides(SITEMAP_XML))
    result = runner.invoke(app, ["search", "mistweaver monk guide", "--limit", "5"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["results"][0]["id"] == "mistweaver-monk"
    assert payload["results"][0]["follow_up"]["recommended_command"] == "method guide mistweaver-monk"


def test_method_resolve_command_returns_best_guide(monkeypatch) -> None:
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: parse_sitemap_guides(SITEMAP_XML))
    result = runner.invoke(app, ["resolve", "mistweaver monk"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["next_command"] == "method guide mistweaver-monk"


def test_method_guide_and_guide_full(monkeypatch) -> None:
    monkeypatch.setattr("method_cli.main.MethodClient.fetch_guide_page", lambda self, guide_ref: _fake_fetch_guide_page(guide_ref))
    guide_result = runner.invoke(app, ["guide", "mistweaver-monk"])
    assert guide_result.exit_code == 0
    guide_payload = json.loads(guide_result.stdout)
    assert guide_payload["guide"]["slug"] == "mistweaver-monk"
    assert guide_payload["linked_entities"]["count"] == 1

    full_result = runner.invoke(app, ["guide-full", "mistweaver-monk"])
    assert full_result.exit_code == 0
    full_payload = json.loads(full_result.stdout)
    assert full_payload["guide"]["page_count"] == 2
    assert full_payload["linked_entities"]["count"] == 2
    assert full_payload["pages"][1]["guide"]["section_slug"] == "talents"


def test_method_guide_export_and_query(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("method_cli.main.MethodClient.fetch_guide_page", lambda self, guide_ref: _fake_fetch_guide_page(guide_ref))
    export_dir = tmp_path / "guide-mistweaver-monk"

    export_result = runner.invoke(app, ["guide-export", "mistweaver-monk", "--out", str(export_dir)])
    assert export_result.exit_code == 0
    export_payload = json.loads(export_result.stdout)
    assert export_payload["counts"]["pages"] == 2
    assert (export_dir / "manifest.json").exists()
    assert (export_dir / "pages" / "talents.html").exists()

    query_result = runner.invoke(app, ["guide-query", str(export_dir), "tea serenity", "--kind", "linked_entities"])
    assert query_result.exit_code == 0
    query_payload = json.loads(query_result.stdout)
    assert query_payload["count"] == 1
    assert query_payload["top"][0]["name"] == "Tea of Serenity"

    section_query = runner.invoke(app, ["guide-query", str(export_dir), "mistweaver", "--kind", "sections", "--section-title", "introduction"])
    assert section_query.exit_code == 0
    section_payload = json.loads(section_query.stdout)
    assert section_payload["match_counts"]["sections"] >= 1
