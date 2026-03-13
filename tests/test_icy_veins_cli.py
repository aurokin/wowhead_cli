from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from icy_veins_cli.main import app
from icy_veins_cli.page_parser import classify_guide_slug, parse_guide_page, parse_sitemap_guides

runner = CliRunner()

INTRO_HTML = """
<html>
  <head>
    <title>Mistweaver Monk Healing Guide - Midnight (12.0.1) - World of Warcraft - Icy Veins</title>
    <meta name="description" content="This guide contains everything you need to know to be an excellent Mistweaver Monk.">
    <meta property="og:title" content="Mistweaver Monk Healing Guide - Midnight (12.0.1)">
    <link rel="canonical" href="https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide">
    <script>
      dataLayer = [{
        'author': 'dhaubbs',
        'page_type': 'guides',
        'page_game': 'wow',
        'page_cat1': 'monk',
        'page_cat2': 'mistweaver',
        'page_cat3': 'intro'
      }];
    </script>
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Mistweaver Monk Healing Guide - Midnight (12.0.1)",
        "dateModified": "2026-03-05T05:19:00+00:00",
        "datePublished": "2012-09-13T02:17:00+00:00",
        "author": {"@type": "Person", "name": "Dhaubbs"},
        "description": "This guide contains everything you need to know to be an excellent Mistweaver Monk."
      }
    </script>
  </head>
  <body>
    <div class="page_content_container text_color">
      <div class="page_content_header">
        <div class="page_content_header_meta">
          <span class="page_author"><span>Last updated <span class="local_date">on <span class="local_date_date">Mar 05, 2026</span> at <span class="local_date_hour">05:19</span></span></span><span>&nbsp;by <span style="color:#fff;">Dhaubbs</span></span></span>
          <span class="page_comments"><a href="https://www.icy-veins.com/forums/topic/52937-mistweaver-monk-pve">48 comments</a></span>
        </div>
        <div class="page_content_header_intro">
          <span>General Information</span>
          <p>Welcome to our Mistweaver Monk guide for World of Warcraft.</p>
        </div>
      </div>
      <div class="toc">
        <div class="toc_page_list toc_page_list_monk">
          <div class="toc_page_center_item">
            <span class="toc_page_list_item selected">
              <a href="//www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide">
                <span class="toc_page_list_item_icon"></span>
                <span>Mistweaver Monk Guide</span>
              </a>
            </span>
          </div>
          <div class="toc_page_list_items">
            <span class="toc_page_list_item">
              <a href="//www.icy-veins.com/wow/mistweaver-monk-leveling-guide"><span></span><span>Leveling</span></a>
            </span>
            <span class="toc_page_list_item">
              <a href="//www.icy-veins.com/wow/mistweaver-monk-pve-healing-stat-priority"><span></span><span>Stat Priority</span></a>
            </span>
          </div>
        </div>
        <div class="toc_page_content">
          <div class="toc_page_content_items">
            <ul>
              <li><span><a href="//www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide#mistweaver-overview">1. Mistweaver Overview</a></span></li>
              <li><span><a href="//www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide#talents">2. Talents</a></span></li>
            </ul>
          </div>
        </div>
      </div>
      <div class="page_content">
        <div class="raider-io-links"><a href="https://raider.io/example">Ignore</a></div>
        <div class="heading_container heading_number_2"><span>1.</span><h2 id="mistweaver-overview">Mistweaver Overview</h2></div>
        <p>Use <a href="https://www.wowhead.com/spell=116670/vivify">Vivify</a> well.</p>
        <div class="heading_container heading_number_3"><span>2.</span><h3 id="talents">Talents</h3></div>
        <p>See our <a href="/wow/mistweaver-monk-pve-healing-stat-priority">Stat Priority</a> page.</p>
      </div>
    </div>
  </body>
</html>
"""

STATS_HTML = """
<html>
  <head>
    <title>Mistweaver Monk Stat Priority - Midnight (12.0.1) - World of Warcraft - Icy Veins</title>
    <meta name="description" content="Learn the Mistweaver Monk stat priority.">
    <meta property="og:title" content="Mistweaver Monk Stat Priority - Midnight (12.0.1)">
    <link rel="canonical" href="https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-stat-priority">
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Mistweaver Monk Stat Priority - Midnight (12.0.1)",
        "dateModified": "2026-03-05T05:19:00+00:00",
        "datePublished": "2012-09-13T02:17:00+00:00",
        "author": {"@type": "Person", "name": "Dhaubbs"},
        "description": "Learn the Mistweaver Monk stat priority."
      }
    </script>
  </head>
  <body>
    <div class="page_content_container text_color">
      <div class="toc">
        <div class="toc_page_list toc_page_list_monk">
          <div class="toc_page_center_item">
            <span class="toc_page_list_item">
              <a href="//www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide"><span></span><span>Mistweaver Monk Guide</span></a>
            </span>
          </div>
          <div class="toc_page_list_items">
            <span class="toc_page_list_item selected">
              <a href="//www.icy-veins.com/wow/mistweaver-monk-pve-healing-stat-priority"><span></span><span>Stat Priority</span></a>
            </span>
          </div>
        </div>
      </div>
      <div class="page_content">
        <div class="heading_container heading_number_2"><span>1.</span><h2 id="stats">Stat Priority</h2></div>
        <p>Prioritize Critical Strike and Versatility.</p>
      </div>
    </div>
  </body>
</html>
"""

LEVELING_HTML = """
<html>
  <head>
    <title>Mistweaver Monk Leveling Guide - Midnight (12.0.1) - World of Warcraft - Icy Veins</title>
    <meta name="description" content="Leveling as Mistweaver Monk.">
    <meta property="og:title" content="Mistweaver Monk Leveling Guide - Midnight (12.0.1)">
    <link rel="canonical" href="https://www.icy-veins.com/wow/mistweaver-monk-leveling-guide">
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Mistweaver Monk Leveling Guide - Midnight (12.0.1)",
        "dateModified": "2026-03-05T05:19:00+00:00",
        "datePublished": "2012-09-13T02:17:00+00:00",
        "author": {"@type": "Person", "name": "Dhaubbs"},
        "description": "Leveling as Mistweaver Monk."
      }
    </script>
  </head>
  <body>
    <div class="page_content_container text_color">
      <div class="toc">
        <div class="toc_page_list toc_page_list_monk">
          <div class="toc_page_center_item">
            <span class="toc_page_list_item">
              <a href="//www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide"><span></span><span>Mistweaver Monk Guide</span></a>
            </span>
          </div>
          <div class="toc_page_list_items">
            <span class="toc_page_list_item selected">
              <a href="//www.icy-veins.com/wow/mistweaver-monk-leveling-guide"><span></span><span>Leveling</span></a>
            </span>
          </div>
        </div>
      </div>
      <div class="page_content">
        <div class="heading_container heading_number_2"><span>1.</span><h2 id="leveling">Leveling</h2></div>
        <p>Level with Tiger Palm and Vivify.</p>
      </div>
    </div>
  </body>
</html>
"""

CLASS_HUB_HTML = """
<html>
  <head>
    <title>Monk Guide - Midnight (12.0.1) - World of Warcraft - Icy Veins</title>
    <meta name="description" content="Monk hub guide.">
    <meta property="og:title" content="Monk Guide - Midnight (12.0.1)">
    <link rel="canonical" href="https://www.icy-veins.com/wow/monk-guide">
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Monk Guide - Midnight (12.0.1)",
        "dateModified": "2026-03-05T05:19:00+00:00",
        "author": {"@type": "Person", "name": "Dhaubbs"},
        "description": "Monk hub guide."
      }
    </script>
  </head>
  <body>
    <div class="page_content_container text_color">
      <div class="toc">
        <div class="toc_page_list toc_page_list_classes">
          <div class="toc_page_list_items">
            <span class="toc_page_list_item">
              <a href="//www.icy-veins.com/wow/death-knight-guide"><span></span><span>Death Knight</span></a>
            </span>
            <span class="toc_page_list_item selected">
              <a href="//www.icy-veins.com/wow/monk-guide"><span></span><span>Monk</span></a>
            </span>
            <span class="toc_page_list_item">
              <a href="//www.icy-veins.com/wow/warrior-guide"><span></span><span>Warrior</span></a>
            </span>
          </div>
        </div>
      </div>
      <div class="page_content">
        <div class="heading_container heading_number_2"><span>1.</span><h2 id="midnight-monk-specializations">Midnight Monk Specializations</h2></div>
        <p>See the monk specializations and related guides.</p>
      </div>
    </div>
  </body>
</html>
"""

EASY_MODE_HTML = """
<html>
  <head>
    <title>Fury Warrior DPS Easy Mode - Midnight (12.0.1) - World of Warcraft - Icy Veins</title>
    <meta name="description" content="Easy mode for Fury Warrior.">
    <meta property="og:title" content="Fury Warrior DPS Easy Mode - Midnight (12.0.1)">
    <link rel="canonical" href="https://www.icy-veins.com/wow/fury-warrior-pve-dps-easy-mode">
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Fury Warrior DPS Easy Mode - Midnight (12.0.1)",
        "dateModified": "2026-03-05T05:19:00+00:00",
        "author": {"@type": "Person", "name": "Archimtiros"},
        "description": "Easy mode for Fury Warrior."
      }
    </script>
  </head>
  <body>
    <div class="page_content_container text_color">
      <div class="toc">
        <div class="toc_page_list toc_page_list_warrior">
          <div class="toc_page_center_item">
            <span class="toc_page_list_item">
              <a href="//www.icy-veins.com/wow/fury-warrior-pve-dps-guide"><span></span><span>Fury Warrior Guide</span></a>
            </span>
          </div>
          <div class="toc_page_list_items">
            <span class="toc_page_list_item selected">
              <a href="//www.icy-veins.com/wow/fury-warrior-pve-dps-easy-mode"><span></span><span>Easy Mode</span></a>
            </span>
            <span class="toc_page_list_item">
              <a href="//www.icy-veins.com/wow/fury-warrior-pve-dps-stat-priority"><span></span><span>Stat Priority</span></a>
            </span>
          </div>
        </div>
      </div>
      <div class="page_content">
        <div class="heading_container heading_number_2"><span>1.</span><h2 id="foreword">Foreword</h2></div>
        <p>Simple Fury Warrior guidance.</p>
      </div>
    </div>
  </body>
</html>
"""

SITEMAP_XML = """
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide</loc></url>
  <url><loc>https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-stat-priority</loc></url>
  <url><loc>https://www.icy-veins.com/wow/mistweaver-monk-leveling-guide</loc></url>
  <url><loc>https://www.icy-veins.com/wow/news-roundup</loc></url>
  <url><loc>https://www.icy-veins.com/hearthstone/decks</loc></url>
</urlset>
"""


def _fake_fetch_guide_page(guide_ref: str) -> dict[str, object]:
    if str(guide_ref).endswith("fury-warrior-pve-dps-easy-mode"):
        return parse_guide_page(
            EASY_MODE_HTML,
            source_url="https://www.icy-veins.com/wow/fury-warrior-pve-dps-easy-mode",
        )
    if str(guide_ref).endswith("monk-guide"):
        return parse_guide_page(
            CLASS_HUB_HTML,
            source_url="https://www.icy-veins.com/wow/monk-guide",
        )
    if str(guide_ref).endswith("mistweaver-monk-pve-healing-stat-priority"):
        return parse_guide_page(
            STATS_HTML,
            source_url="https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-stat-priority",
        )
    if str(guide_ref).endswith("mistweaver-monk-leveling-guide"):
        return parse_guide_page(
            LEVELING_HTML,
            source_url="https://www.icy-veins.com/wow/mistweaver-monk-leveling-guide",
        )
    return parse_guide_page(
        INTRO_HTML,
        source_url="https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
    )


def test_parse_sitemap_guides_filters_wow_guide_like_pages() -> None:
    guides = parse_sitemap_guides(SITEMAP_XML)
    assert guides == [
        {
            "content_family": "leveling",
            "slug": "mistweaver-monk-leveling-guide",
            "name": "Mistweaver Monk Leveling Guide",
            "url": "https://www.icy-veins.com/wow/mistweaver-monk-leveling-guide",
        },
        {
            "content_family": "spec_guide",
            "slug": "mistweaver-monk-pve-healing-guide",
            "name": "Mistweaver Monk PvE Healing Guide",
            "url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
        },
        {
            "content_family": "stat_priority",
            "slug": "mistweaver-monk-pve-healing-stat-priority",
            "name": "Mistweaver Monk PvE Healing Stat Priority",
            "url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-stat-priority",
        },
    ]


def test_parse_guide_page_extracts_navigation_toc_sections_and_links() -> None:
    payload = parse_guide_page(
        INTRO_HTML,
        source_url="https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
    )
    assert payload["guide"]["slug"] == "mistweaver-monk-pve-healing-guide"
    assert payload["guide"]["author"] == "Dhaubbs"
    assert payload["guide"]["content_family"] == "spec_guide"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["guide"]["last_updated"] == "2026-03-05T05:19:00+00:00"
    assert payload["page"]["page_type"] == "guides"
    assert payload["navigation"][0]["active"] is True
    assert payload["page_toc"][0]["title"] == "Mistweaver Overview"
    assert payload["article"]["intro_text"].startswith("General Information")
    assert payload["article"]["sections"][0]["title"] == "Mistweaver Overview"
    assert [row["title"] for row in payload["article"]["headings"]] == ["Mistweaver Overview", "Talents"]
    linked = {(row["type"], row["id"]) for row in payload["linked_entities"]}
    assert ("spell", 116670) in linked
    assert ("page", "mistweaver-monk-pve-healing-stat-priority") in linked


def test_classify_guide_slug_distinguishes_supported_families() -> None:
    assert classify_guide_slug("monk-guide") == "class_hub"
    assert classify_guide_slug("healing-guide") == "role_guide"
    assert classify_guide_slug("mistweaver-monk-pve-healing-guide") == "spec_guide"
    assert classify_guide_slug("fury-warrior-pve-dps-easy-mode") == "easy_mode"
    assert classify_guide_slug("mistweaver-monk-leveling-guide") == "leveling"
    assert classify_guide_slug("mistweaver-monk-pvp-guide") == "pvp"
    assert classify_guide_slug("mistweaver-monk-pve-healing-stat-priority") == "stat_priority"
    assert classify_guide_slug("mistweaver-monk-pve-healing-nerub-ar-palace-raid-guide") == "raid_guide"
    assert classify_guide_slug("mistweaver-monk-the-war-within-pve-guide") == "expansion_guide"
    assert classify_guide_slug("mistweaver-monk-mists-of-pandaria-remix-guide") == "special_event_guide"
    assert classify_guide_slug("news-roundup") is None


def test_icy_veins_search_command_uses_sitemap_guides(monkeypatch) -> None:
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: parse_sitemap_guides(SITEMAP_XML))
    result = runner.invoke(app, ["search", "mistweaver monk guide", "--limit", "5"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["count"] == 3
    assert payload["results"][0]["id"] == "mistweaver-monk-pve-healing-guide"
    assert payload["results"][0]["metadata"]["content_family"] == "spec_guide"
    assert payload["results"][0]["follow_up"]["recommended_command"] == "icy-veins guide mistweaver-monk-pve-healing-guide"


def test_icy_veins_resolve_command_returns_best_guide(monkeypatch) -> None:
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: parse_sitemap_guides(SITEMAP_XML))
    result = runner.invoke(app, ["resolve", "mistweaver monk guide"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["next_command"] == "icy-veins guide mistweaver-monk-pve-healing-guide"


def test_icy_veins_resolve_command_prefers_easy_mode_when_query_matches(monkeypatch) -> None:
    sitemap = parse_sitemap_guides(SITEMAP_XML) + [
        {
            "slug": "fury-warrior-pve-dps-easy-mode",
            "name": "Fury Warrior PvE DPS Easy Mode",
            "url": "https://www.icy-veins.com/wow/fury-warrior-pve-dps-easy-mode",
            "content_family": "easy_mode",
        },
        {
            "slug": "warrior-guide",
            "name": "Warrior Guide",
            "url": "https://www.icy-veins.com/wow/warrior-guide",
            "content_family": "class_hub",
        },
    ]
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: sitemap)
    result = runner.invoke(app, ["resolve", "fury warrior easy mode"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["match"]["id"] == "fury-warrior-pve-dps-easy-mode"
    assert payload["resolved"] is True
    assert payload["next_command"] == "icy-veins guide fury-warrior-pve-dps-easy-mode"


def test_icy_veins_guide_and_guide_full(monkeypatch) -> None:
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.fetch_guide_page", lambda self, guide_ref: _fake_fetch_guide_page(guide_ref))
    guide_result = runner.invoke(app, ["guide", "mistweaver-monk-pve-healing-guide"])
    assert guide_result.exit_code == 0
    guide_payload = json.loads(guide_result.stdout)
    assert guide_payload["guide"]["slug"] == "mistweaver-monk-pve-healing-guide"
    assert guide_payload["linked_entities"]["count"] == 2
    assert guide_payload["page_toc"]["count"] == 2

    full_result = runner.invoke(app, ["guide-full", "mistweaver-monk-pve-healing-guide"])
    assert full_result.exit_code == 0
    full_payload = json.loads(full_result.stdout)
    assert full_payload["guide"]["page_count"] == 3
    assert full_payload["linked_entities"]["count"] >= 2
    assert full_payload["pages"][1]["guide"]["section_slug"] in {
        "mistweaver-monk-leveling-guide",
        "mistweaver-monk-pve-healing-stat-priority",
    }


def test_icy_veins_guide_full_keeps_class_hubs_local(monkeypatch) -> None:
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.fetch_guide_page", lambda self, guide_ref: _fake_fetch_guide_page(guide_ref))
    result = runner.invoke(app, ["guide-full", "monk-guide"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["guide"]["content_family"] == "class_hub"
    assert payload["guide"]["page_count"] == 1
    assert payload["navigation"]["count"] == 1
    assert payload["pages"][0]["guide"]["slug"] == "monk-guide"


def test_icy_veins_guide_export_and_query(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.fetch_guide_page", lambda self, guide_ref: _fake_fetch_guide_page(guide_ref))
    export_dir = tmp_path / "guide-mistweaver-monk"

    export_result = runner.invoke(app, ["guide-export", "mistweaver-monk-pve-healing-guide", "--out", str(export_dir)])
    assert export_result.exit_code == 0
    export_payload = json.loads(export_result.stdout)
    assert export_payload["counts"]["pages"] == 3
    assert (export_dir / "manifest.json").exists()
    assert (export_dir / "pages" / "mistweaver-monk-pve-healing-guide.html").exists()

    query_result = runner.invoke(app, ["guide-query", str(export_dir), "vivify", "--kind", "linked_entities"])
    assert query_result.exit_code == 0
    query_payload = json.loads(query_result.stdout)
    assert query_payload["count"] == 1
    assert query_payload["top"][0]["name"] == "Vivify"

    section_query = runner.invoke(
        app,
        ["guide-query", str(export_dir), "critical strike", "--kind", "sections", "--section-title", "stat"],
    )
    assert section_query.exit_code == 0
    section_payload = json.loads(section_query.stdout)
    assert section_payload["match_counts"]["sections"] >= 1


def test_icy_veins_invalid_guide_ref_fails_structured() -> None:
    result = runner.invoke(app, ["guide", "news-roundup"])
    assert result.exit_code == 1

    payload = json.loads(result.stderr or result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_guide_ref"
