from __future__ import annotations

from pathlib import Path

from warcraft_content.article_bundle import (
    default_article_export_dir,
    load_article_bundle,
    query_article_bundle,
    write_article_bundle,
)


def _method_like_payload() -> dict[str, object]:
    return {
        "guide": {
            "slug": "mistweaver-monk",
            "page_url": "https://www.method.gg/guides/mistweaver-monk",
            "section_slug": "introduction",
            "section_title": "Introduction",
            "author": "Tincell",
            "last_updated": "Last Updated: 26th Feb, 2026",
            "patch": "Patch 12.0.1",
            "page_count": 2,
        },
        "page": {
            "title": "Method Mistweaver Monk Guide - Introduction - Midnight 12.0.1",
            "description": "Intro guide",
            "canonical_url": "https://www.method.gg/guides/mistweaver-monk",
        },
        "navigation": {
            "count": 2,
            "items": [
                {"title": "Introduction", "url": "https://www.method.gg/guides/mistweaver-monk", "section_slug": "introduction", "active": True, "ordinal": 1},
                {"title": "Talents", "url": "https://www.method.gg/guides/mistweaver-monk/talents", "section_slug": "talents", "active": False, "ordinal": 2},
            ],
        },
        "pages": [
            {
                "guide": {
                    "slug": "mistweaver-monk",
                    "page_url": "https://www.method.gg/guides/mistweaver-monk",
                    "section_slug": "introduction",
                    "section_title": "Introduction",
                },
                "page": {
                    "title": "Introduction",
                    "description": "Intro page",
                    "canonical_url": "https://www.method.gg/guides/mistweaver-monk",
                },
                "article": {
                    "html": "<h2>Introduction</h2><p>Intro copy</p>",
                    "text": "Introduction Intro copy",
                    "headings": [{"title": "Introduction", "level": 2, "ordinal": 1}],
                    "sections": [{"title": "Introduction", "level": 2, "ordinal": 1, "text": "Intro copy", "html": "<p>Intro copy</p>"}],
                },
            },
            {
                "guide": {
                    "slug": "mistweaver-monk",
                    "page_url": "https://www.method.gg/guides/mistweaver-monk/talents",
                    "section_slug": "talents",
                    "section_title": "Talents",
                },
                "page": {
                    "title": "Talents",
                    "description": "Talent page",
                    "canonical_url": "https://www.method.gg/guides/mistweaver-monk/talents",
                },
                "article": {
                    "html": "<h2>Talents</h2><p>Tea of Serenity</p>",
                    "text": "Talents Tea of Serenity",
                    "headings": [{"title": "Talents", "level": 2, "ordinal": 1}],
                    "sections": [{"title": "Talents", "level": 2, "ordinal": 1, "text": "Tea of Serenity", "html": "<p>Tea of Serenity</p>"}],
                },
            },
        ],
        "linked_entities": {
            "count": 1,
            "items": [
                {"type": "spell", "id": 388020, "name": "Tea of Serenity", "url": "https://www.wowhead.com/spell=388020/tea-of-serenity", "source_urls": ["https://www.method.gg/guides/mistweaver-monk/talents"]},
            ],
        },
    }


def _icy_like_payload() -> dict[str, object]:
    return {
        "guide": {
            "slug": "mistweaver-monk-pve-healing-guide",
            "page_url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
            "section_slug": "intro",
            "section_title": "General Information",
            "author": "Dhaubbs",
            "last_updated": "Mar 05, 2026",
            "patch": "Midnight (12.0.1)",
            "page_count": 1,
        },
        "page": {
            "title": "Mistweaver Monk Healing Guide - Midnight (12.0.1)",
            "description": "Icy intro guide",
            "canonical_url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
        },
        "navigation": {
            "count": 3,
            "items": [
                {"title": "Mistweaver Monk Guide", "url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide", "section_slug": "intro", "active": True, "ordinal": 1},
                {"title": "Builds and Talents", "url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-spec-builds-talents", "section_slug": "builds-and-talents", "active": False, "ordinal": 2},
                {"title": "Rotation, Cooldowns, and Abilities", "url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-rotation-cooldowns-abilities", "section_slug": "rotation-cooldowns-and-abilities", "active": False, "ordinal": 3},
            ],
        },
        "pages": [
            {
                "guide": {
                    "slug": "mistweaver-monk-pve-healing-guide",
                    "page_url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
                    "section_slug": "intro",
                    "section_title": "General Information",
                },
                "page": {
                    "title": "Mistweaver Monk Healing Guide - Midnight (12.0.1)",
                    "description": "Icy intro guide",
                    "canonical_url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
                },
                "article": {
                    "html": "<h2>Mistweaver Monk Overview</h2><p>Healing intro</p>",
                    "text": "Mistweaver Monk Overview Healing intro",
                    "headings": [{"title": "Mistweaver Monk Overview", "level": 2, "ordinal": 1}],
                    "sections": [{"title": "Mistweaver Monk Overview", "level": 2, "ordinal": 1, "text": "Healing intro", "html": "<p>Healing intro</p>"}],
                },
            }
        ],
        "linked_entities": {
            "count": 1,
            "items": [
                {"type": "page", "id": 1, "name": "Builds and Talents", "url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-spec-builds-talents", "source_urls": ["https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide"]},
            ],
        },
    }


def test_default_article_export_dir_uses_provider_root() -> None:
    path = default_article_export_dir("method", "mistweaver-monk", cwd=Path("/tmp/example"))
    assert path == Path("/tmp/example/method_exports/guide-mistweaver-monk")


def test_write_and_query_article_bundle_for_method_shape(tmp_path: Path) -> None:
    export_dir = tmp_path / "method-guide"
    manifest = write_article_bundle(_method_like_payload(), provider="method", export_dir=export_dir)
    assert manifest["counts"] == {"pages": 2, "sections": 2, "navigation_links": 2, "linked_entities": 1}
    assert manifest["files"]["page_files_json"] == "page-files.json"
    bundle = load_article_bundle(export_dir)
    assert bundle["page_files"][0]["section_slug"] == "introduction"
    result = query_article_bundle(bundle, query="tea serenity", limit=5, kinds={"sections", "navigation", "linked_entities"}, section_title_filter=None)
    assert result["match_counts"]["linked_entities"] == 1
    assert result["top"][0]["name"] == "Tea of Serenity"


def test_write_and_query_article_bundle_for_icy_shape(tmp_path: Path) -> None:
    export_dir = tmp_path / "icy-guide"
    manifest = write_article_bundle(_icy_like_payload(), provider="icy-veins", export_dir=export_dir)
    assert manifest["provider"] == "icy-veins"
    assert manifest["counts"] == {"pages": 1, "sections": 1, "navigation_links": 3, "linked_entities": 1}
    bundle = load_article_bundle(export_dir)
    result = query_article_bundle(bundle, query="builds talents", limit=5, kinds={"navigation", "linked_entities"}, section_title_filter=None)
    assert result["match_counts"]["navigation"] >= 1
    assert result["matches"]["navigation"][0]["title"] == "Builds and Talents"


def test_query_article_bundle_normalizes_section_title_filter(tmp_path: Path) -> None:
    export_dir = tmp_path / "method-guide"
    write_article_bundle(_method_like_payload(), provider="method", export_dir=export_dir)
    bundle = load_article_bundle(export_dir)

    result = query_article_bundle(
        bundle,
        query="tea serenity",
        limit=5,
        kinds={"sections"},
        section_title_filter="TALENTS",
    )

    assert result["match_counts"]["sections"] == 1
    assert result["top"][0]["title"] == "Talents"


def test_load_article_bundle_tolerates_missing_page_files_metadata(tmp_path: Path) -> None:
    export_dir = tmp_path / "icy-guide"
    write_article_bundle(_icy_like_payload(), provider="icy-veins", export_dir=export_dir)
    (export_dir / "page-files.json").unlink()

    bundle = load_article_bundle(export_dir)

    assert bundle["page_files"] == []
