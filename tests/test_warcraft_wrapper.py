from __future__ import annotations

import json
from pathlib import Path

from method_cli.main import app as method_app
from typer.testing import CliRunner
from warcraft_cli.main import app as warcraft_app
from warcraft_content.article_bundle import write_article_bundle

runner = CliRunner()


def _comparison_payload(
    *,
    provider: str,
    slug: str,
    page_url: str,
    page_title: str,
    analysis_tags: list[str],
    build_code: str | None = None,
) -> dict[str, object]:
    build_items: list[dict[str, object]] = []
    if build_code is not None:
        build_items.append(
            {
                "kind": "build_reference",
                "reference_type": "wowhead_talent_calc_url",
                "url": f"https://www.wowhead.com/talent-calc/monk/mistweaver/{build_code}",
                "label": "Raid Build",
                "build_code": build_code,
                "build_identity": {
                    "kind": "build_identity",
                    "status": "inferred",
                    "class_spec_identity": {"identity": {"actor_class": "monk", "spec": "mistweaver"}},
                },
                "source_urls": [page_url],
            }
        )
    return {
        "guide": {
            "slug": slug,
            "page_url": page_url,
            "section_slug": "overview",
            "section_title": "Overview",
            "page_count": 1,
        },
        "page": {
            "title": page_title,
            "description": page_title,
            "canonical_url": page_url,
        },
        "navigation": {"count": 1, "items": [{"title": "Overview", "url": page_url, "section_slug": "overview", "active": True, "ordinal": 1}]},
        "pages": [
            {
                "guide": {"slug": slug, "page_url": page_url, "section_slug": "overview", "section_title": "Overview"},
                "page": {"title": page_title, "description": page_title, "canonical_url": page_url},
                "article": {
                    "html": "<h2>Overview</h2><p>Guide copy</p>",
                    "text": "Overview Guide copy",
                    "headings": [{"title": "Overview", "level": 2, "ordinal": 1}],
                    "sections": [{"title": "Overview", "level": 2, "ordinal": 1, "text": "Guide copy", "html": "<p>Guide copy</p>"}],
                },
            }
        ],
        "linked_entities": {"count": 0, "items": []},
        "build_references": {"count": len(build_items), "items": build_items},
        "analysis_surfaces": {
            "count": 1,
            "items": [
                {
                    "kind": "guide_analysis_surface",
                    "surface_tags": analysis_tags,
                    "confidence": "high",
                    "source_kind": "section_heading",
                    "provider": provider,
                    "content_family": None,
                    "page_url": page_url,
                    "section_slug": "overview",
                    "section_title": "Overview",
                    "page_title": page_title,
                    "text_preview": "Guide copy",
                    "match_reasons": ["keyword:overview"],
                    "citation": {"page_url": page_url, "section_title": "Overview", "page_title": page_title},
                }
            ],
        },
    }


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
    assert payload["wrapper"]["provider_count"] == 8
    providers = {row["provider"]: row for row in payload["providers"]}
    assert providers["wowhead"]["status"] == "ready"
    assert providers["method"]["status"] == "ready"
    assert providers["icy-veins"]["status"] == "ready"
    assert providers["raiderio"]["status"] == "partial"
    assert providers["warcraftlogs"]["status"] == "partial"
    assert providers["warcraft-wiki"]["status"] == "ready"
    assert providers["wowprogress"]["status"] == "partial"
    assert providers["simc"]["status"] == "partial"
    assert providers["wowhead"]["expansion_support"]["mode"] == "profiled"
    assert providers["wowhead"]["expansion_support"]["review_status"] == "reviewed"
    assert providers["method"]["expansion_support"]["mode"] == "fixed"
    assert providers["method"]["expansion_support"]["review_status"] == "reviewed"
    assert providers["warcraftlogs"]["expansion_support"]["mode"] == "fixed"
    assert providers["warcraftlogs"]["expansion_support"]["review_status"] == "reviewed"
    assert providers["warcraft-wiki"]["expansion_support"]["mode"] == "none"
    assert providers["warcraft-wiki"]["expansion_support"]["review_status"] == "deferred"
    assert providers["method"]["details"]["capabilities"]["guide"] == "ready"
    assert providers["icy-veins"]["details"]["capabilities"]["guide"] == "ready"
    assert providers["raiderio"]["details"]["capabilities"]["search"] == "ready"
    assert providers["warcraftlogs"]["details"]["capabilities"]["search"] == "ready_explicit_report_only"
    assert providers["warcraft-wiki"]["details"]["capabilities"]["article"] == "ready"
    assert providers["wowprogress"]["details"]["capabilities"]["leaderboard"] == "ready"
    assert providers["simc"]["details"]["capabilities"]["decode_build"] == "ready"


def test_warcraft_doctor_reports_expansion_filtering_state() -> None:
    result = runner.invoke(warcraft_app, ["--expansion", "wotlk", "doctor"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["wrapper"]["requested_expansion"] == "wotlk"
    assert payload["wrapper"]["expansion_filter_active"] is True
    assert payload["included_providers"] == ["wowhead"]
    assert {row["provider"] for row in payload["excluded_providers"]} == {
        "method",
        "icy-veins",
        "raiderio",
        "warcraftlogs",
        "warcraft-wiki",
        "wowprogress",
        "simc",
    }


def test_warcraft_doctor_reports_retail_filter_state() -> None:
    result = runner.invoke(warcraft_app, ["--expansion", "retail", "doctor"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["wrapper"]["requested_expansion"] == "retail"
    assert payload["wrapper"]["expansion_filter_active"] is True
    assert set(payload["included_providers"]) == {
        "wowhead",
        "method",
        "icy-veins",
        "raiderio",
        "warcraftlogs",
        "wowprogress",
    }
    assert {row["provider"] for row in payload["excluded_providers"]} == {
        "warcraft-wiki",
        "simc",
    }


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
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(warcraft_app, ["search", "thunderfury", "--limit", "3"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider_count"] == 8
    assert payload["count"] == 1
    assert payload["results"][0]["provider"] == "wowhead"
    providers = {row["provider"]: row for row in payload["providers"]}
    assert providers["method"]["payload"]["count"] == 0
    assert providers["icy-veins"]["payload"]["count"] == 0
    assert providers["raiderio"]["payload"]["count"] == 0
    assert providers["warcraftlogs"]["payload"]["count"] == 0
    assert "explicit report URL or a bare report code" in providers["warcraftlogs"]["payload"]["message"]
    assert providers["warcraft-wiki"]["payload"]["count"] == 0
    assert providers["wowprogress"]["payload"]["count"] == 0
    assert "structured queries" in providers["wowprogress"]["payload"]["message"]
    assert providers["simc"]["payload"]["coming_soon"] is True
    assert providers["wowhead"]["payload"]["results"][0]["name"] == "Thunderfury"


def test_warcraft_guide_compare_returns_cross_provider_bundle_packet(tmp_path: Path) -> None:
    method_dir = tmp_path / "method-guide"
    icy_dir = tmp_path / "icy-guide"
    write_article_bundle(
        _comparison_payload(
            provider="method",
            slug="mistweaver-monk",
            page_url="https://www.method.gg/guides/mistweaver-monk/talents",
            page_title="Method Talents",
            analysis_tags=["builds_talents", "talent_recommendations"],
            build_code="ABC123",
        ),
        provider="method",
        export_dir=method_dir,
    )
    write_article_bundle(
        _comparison_payload(
            provider="icy-veins",
            slug="mistweaver-monk-pve-healing-guide",
            page_url="https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
            page_title="Icy Overview",
            analysis_tags=["overview"],
            build_code="ABC123",
        ),
        provider="icy-veins",
        export_dir=icy_dir,
    )

    result = runner.invoke(warcraft_app, ["guide-compare", str(method_dir), str(icy_dir)])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider"] == "warcraft"
    assert payload["kind"] == "guide_bundle_comparison"
    assert payload["compared_bundle_count"] == 2
    assert payload["comparison_scope"] == ["section_evidence", "analysis_surfaces", "build_references"]
    assert payload["section_evidence"]["matching_rule"] == "exact_normalized_section_title"
    assert payload["section_evidence"]["shared"] == ["overview"]
    assert payload["analysis_surface_tags"]["count"] == 3
    assert payload["build_references"]["count"] == 1
    assert payload["build_references"]["shared"] == [
        "monk::mistweaver::ABC123::https://www.wowhead.com/talent-calc/monk/mistweaver/ABC123"
    ]


def test_warcraft_guide_compare_query_orchestrates_resolve_export_and_compare(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_provider_resolve(provider: str, query: str, *, limit: int = 5, expansion: str | None = None) -> dict[str, object]:
        assert query == "mistweaver monk guide"
        assert limit == 5
        assert expansion is None
        refs = {
            "method": ("mistweaver-monk", "Method Mistweaver Monk Guide"),
            "icy-veins": ("mistweaver-monk-pve-healing-guide", "Icy Veins Mistweaver Monk Guide"),
        }
        ref, name = refs[provider]
        return {
            "provider": provider,
            "exit_code": 0,
            "payload": {
                "resolved": True,
                "confidence": "high",
                "match": {
                    "id": ref,
                    "name": name,
                    "entity_type": "guide",
                    "url": f"https://example.test/{ref}",
                },
                "next_command": f"{provider} guide {ref}",
            },
        }

    def fake_provider_invoke(provider: str, args: list[str], *, expansion: str | None = None) -> dict[str, object]:
        assert args[0] == "guide-export"
        export_dir = Path(args[3])
        payload = _comparison_payload(
            provider=provider,
            slug=args[1],
            page_url=f"https://example.test/{provider}/{args[1]}",
            page_title=f"{provider} guide",
            analysis_tags=["overview"] if provider == "icy-veins" else ["builds_talents", "talent_recommendations"],
            build_code="ABC123",
        )
        write_article_bundle(payload, provider=provider, export_dir=export_dir)
        return {
            "provider": provider,
            "exit_code": 0,
            "payload": {"output_dir": str(export_dir), "guide": payload["guide"]},
            "stdout": "",
        }

    monkeypatch.setattr("warcraft_cli.main.provider_resolve", fake_provider_resolve)
    monkeypatch.setattr("warcraft_cli.main.provider_invoke", fake_provider_invoke)

    result = runner.invoke(
        warcraft_app,
        [
            "guide-compare-query",
            "mistweaver monk guide",
            "--provider",
            "method",
            "--provider",
            "icy-veins",
            "--out-root",
            str(tmp_path / "orchestrated"),
        ],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["kind"] == "guide_bundle_comparison_orchestration"
    assert payload["exported_bundle_count"] == 2
    assert payload["comparison"]["kind"] == "guide_bundle_comparison"
    assert payload["comparison"]["compared_bundle_count"] == 2
    assert all(row["status"] == "exported" for row in payload["provider_results"])
    assert {row["candidate"]["selection_source"] for row in payload["provider_results"]} == {"resolve"}


def test_warcraft_guide_compare_query_uses_conservative_search_fallback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_provider_resolve(provider: str, query: str, *, limit: int = 5, expansion: str | None = None) -> dict[str, object]:
        if provider == "method":
            return {
                "provider": provider,
                "exit_code": 0,
                "payload": {
                    "resolved": True,
                    "confidence": "high",
                    "match": {
                        "id": "mistweaver-monk",
                        "name": "Method Mistweaver Monk Guide",
                        "entity_type": "guide",
                        "url": "https://example.test/method/mistweaver-monk",
                    },
                    "next_command": "method guide mistweaver-monk",
                },
            }
        return {
            "provider": provider,
            "exit_code": 0,
            "payload": {
                "resolved": False,
                "confidence": "none",
                "match": None,
                "next_command": None,
            },
        }

    def fake_provider_search(provider: str, query: str, *, limit: int = 5, expansion: str | None = None) -> dict[str, object]:
        if provider == "icy-veins":
            return {
                "provider": provider,
                "exit_code": 0,
                "payload": {
                    "results": [
                        {
                            "id": "mistweaver-monk-pve-healing-guide",
                            "name": "Icy Veins Mistweaver Monk Guide",
                            "entity_type": "guide",
                            "url": "https://example.test/icy-veins/mistweaver-monk-pve-healing-guide",
                            "ranking": {"score": 44},
                            "follow_up": {
                                "recommended_command": "icy-veins guide mistweaver-monk-pve-healing-guide",
                            },
                        },
                        {
                            "id": "mistweaver-monk-pvp-guide",
                            "name": "Icy Veins Mistweaver Monk PvP Guide",
                            "entity_type": "guide",
                            "url": "https://example.test/icy-veins/mistweaver-monk-pvp-guide",
                            "ranking": {"score": 20},
                        },
                    ]
                },
            }
        return {"provider": provider, "exit_code": 0, "payload": {"results": []}}

    def fake_provider_invoke(provider: str, args: list[str], *, expansion: str | None = None) -> dict[str, object]:
        export_dir = Path(args[3])
        payload = _comparison_payload(
            provider=provider,
            slug=args[1],
            page_url=f"https://example.test/{provider}/{args[1]}",
            page_title=f"{provider} guide",
            analysis_tags=["overview"] if provider == "icy-veins" else ["builds_talents", "talent_recommendations"],
            build_code="ABC123",
        )
        write_article_bundle(payload, provider=provider, export_dir=export_dir)
        return {
            "provider": provider,
            "exit_code": 0,
            "payload": {"output_dir": str(export_dir), "guide": payload["guide"]},
            "stdout": "",
        }

    monkeypatch.setattr("warcraft_cli.main.provider_resolve", fake_provider_resolve)
    monkeypatch.setattr("warcraft_cli.main.provider_search", fake_provider_search)
    monkeypatch.setattr("warcraft_cli.main.provider_invoke", fake_provider_invoke)

    result = runner.invoke(
        warcraft_app,
        [
            "guide-compare-query",
            "mistweaver monk guide",
            "--provider",
            "method",
            "--provider",
            "icy-veins",
            "--out-root",
            str(tmp_path / "orchestrated"),
        ],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["comparison"]["compared_bundle_count"] == 2
    icy_row = next(row for row in payload["provider_results"] if row["provider"] == "icy-veins")
    assert icy_row["candidate"]["selection_source"] == "search_fallback"


def test_warcraft_guide_compare_query_reuses_fresh_orchestrated_bundles(
    monkeypatch,
    tmp_path: Path,
) -> None:
    invoke_calls: list[tuple[str, str]] = []

    def fake_provider_resolve(provider: str, query: str, *, limit: int = 5, expansion: str | None = None) -> dict[str, object]:
        refs = {
            "method": ("mistweaver-monk", "Method Mistweaver Monk Guide"),
            "icy-veins": ("mistweaver-monk-pve-healing-guide", "Icy Veins Mistweaver Monk Guide"),
        }
        ref, name = refs[provider]
        return {
            "provider": provider,
            "exit_code": 0,
            "payload": {
                "resolved": True,
                "confidence": "high",
                "match": {
                    "id": ref,
                    "name": name,
                    "entity_type": "guide",
                    "url": f"https://example.test/{ref}",
                },
                "next_command": f"{provider} guide {ref}",
            },
        }

    def fake_provider_invoke(provider: str, args: list[str], *, expansion: str | None = None) -> dict[str, object]:
        invoke_calls.append((provider, args[1]))
        export_dir = Path(args[3])
        payload = _comparison_payload(
            provider=provider,
            slug=args[1],
            page_url=f"https://example.test/{provider}/{args[1]}",
            page_title=f"{provider} guide",
            analysis_tags=["overview"] if provider == "icy-veins" else ["builds_talents", "talent_recommendations"],
            build_code="ABC123",
        )
        write_article_bundle(payload, provider=provider, export_dir=export_dir)
        return {
            "provider": provider,
            "exit_code": 0,
            "payload": {"output_dir": str(export_dir), "guide": payload["guide"]},
            "stdout": "",
        }

    monkeypatch.setattr("warcraft_cli.main.provider_resolve", fake_provider_resolve)
    monkeypatch.setattr("warcraft_cli.main.provider_invoke", fake_provider_invoke)

    out_root = tmp_path / "orchestrated"
    first = runner.invoke(
        warcraft_app,
        ["guide-compare-query", "mistweaver monk guide", "--provider", "method", "--provider", "icy-veins", "--out-root", str(out_root)],
    )
    assert first.exit_code == 0
    second = runner.invoke(
        warcraft_app,
        ["guide-compare-query", "mistweaver monk guide", "--provider", "method", "--provider", "icy-veins", "--out-root", str(out_root)],
    )
    assert second.exit_code == 0

    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    assert [row["status"] for row in first_payload["provider_results"]] == ["exported", "exported"]
    assert [row["status"] for row in second_payload["provider_results"]] == ["reused", "reused"]
    assert len(invoke_calls) == 2


def test_warcraft_guide_compare_query_refreshes_stale_orchestrated_bundles(
    monkeypatch,
    tmp_path: Path,
) -> None:
    invoke_calls: list[tuple[str, str]] = []

    def fake_provider_resolve(provider: str, query: str, *, limit: int = 5, expansion: str | None = None) -> dict[str, object]:
        refs = {
            "method": ("mistweaver-monk", "Method Mistweaver Monk Guide"),
            "icy-veins": ("mistweaver-monk-pve-healing-guide", "Icy Veins Mistweaver Monk Guide"),
        }
        ref, name = refs[provider]
        return {
            "provider": provider,
            "exit_code": 0,
            "payload": {
                "resolved": True,
                "confidence": "high",
                "match": {
                    "id": ref,
                    "name": name,
                    "entity_type": "guide",
                    "url": f"https://example.test/{ref}",
                },
                "next_command": f"{provider} guide {ref}",
            },
        }

    def fake_provider_invoke(provider: str, args: list[str], *, expansion: str | None = None) -> dict[str, object]:
        invoke_calls.append((provider, args[1]))
        export_dir = Path(args[3])
        payload = _comparison_payload(
            provider=provider,
            slug=args[1],
            page_url=f"https://example.test/{provider}/{args[1]}",
            page_title=f"{provider} guide",
            analysis_tags=["overview"] if provider == "icy-veins" else ["builds_talents", "talent_recommendations"],
            build_code="ABC123",
        )
        write_article_bundle(payload, provider=provider, export_dir=export_dir)
        return {
            "provider": provider,
            "exit_code": 0,
            "payload": {"output_dir": str(export_dir), "guide": payload["guide"]},
            "stdout": "",
        }

    monkeypatch.setattr("warcraft_cli.main.provider_resolve", fake_provider_resolve)
    monkeypatch.setattr("warcraft_cli.main.provider_invoke", fake_provider_invoke)

    out_root = tmp_path / "orchestrated"
    first = runner.invoke(
        warcraft_app,
        ["guide-compare-query", "mistweaver monk guide", "--provider", "method", "--provider", "icy-veins", "--out-root", str(out_root)],
    )
    assert first.exit_code == 0

    manifest_path = out_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in manifest["providers"]:
        row["exported_at"] = "2000-01-01T00:00:00Z"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    second = runner.invoke(
        warcraft_app,
        [
            "guide-compare-query",
            "mistweaver monk guide",
            "--provider",
            "method",
            "--provider",
            "icy-veins",
            "--out-root",
            str(out_root),
            "--max-age-hours",
            "1",
        ],
    )
    assert second.exit_code == 0

    second_payload = json.loads(second.stdout)
    assert [row["status"] for row in second_payload["provider_results"]] == ["exported", "exported"]
    assert len(invoke_calls) == 4


def test_warcraft_guide_compare_query_fails_when_too_few_guides_export(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_provider_resolve(provider: str, query: str, *, limit: int = 5, expansion: str | None = None) -> dict[str, object]:
        if provider == "method":
            return {
                "provider": provider,
                "exit_code": 0,
                "payload": {
                    "resolved": True,
                    "confidence": "high",
                    "match": {
                        "id": "mistweaver-monk",
                        "name": "Method Mistweaver Monk Guide",
                        "entity_type": "guide",
                        "url": "https://example.test/method/mistweaver-monk",
                    },
                    "next_command": "method guide mistweaver-monk",
                },
            }
        return {
            "provider": provider,
            "exit_code": 0,
            "payload": {
                "resolved": False,
                "confidence": "none",
                "match": None,
                "next_command": None,
            },
        }

    def fake_provider_search(provider: str, query: str, *, limit: int = 5, expansion: str | None = None) -> dict[str, object]:
        return {
            "provider": provider,
            "exit_code": 0,
            "payload": {
                "results": [
                    {
                        "id": "mistweaver-monk-pve-healing-guide",
                        "name": "Icy Veins Mistweaver Monk Guide",
                        "entity_type": "guide",
                        "url": "https://example.test/icy-veins/mistweaver-monk-pve-healing-guide",
                        "ranking": {"score": 25},
                    },
                    {
                        "id": "mistweaver-monk-pvp-guide",
                        "name": "Icy Veins Mistweaver Monk PvP Guide",
                        "entity_type": "guide",
                        "url": "https://example.test/icy-veins/mistweaver-monk-pvp-guide",
                        "ranking": {"score": 22},
                    },
                ]
            },
        }

    def fake_provider_invoke(provider: str, args: list[str], *, expansion: str | None = None) -> dict[str, object]:
        export_dir = Path(args[3])
        payload = _comparison_payload(
            provider=provider,
            slug="mistweaver-monk",
            page_url="https://example.test/method/mistweaver-monk",
            page_title="method guide",
            analysis_tags=["builds_talents", "talent_recommendations"],
            build_code="ABC123",
        )
        write_article_bundle(payload, provider=provider, export_dir=export_dir)
        return {
            "provider": provider,
            "exit_code": 0,
            "payload": {"output_dir": str(export_dir), "guide": payload["guide"]},
            "stdout": "",
        }

    monkeypatch.setattr("warcraft_cli.main.provider_resolve", fake_provider_resolve)
    monkeypatch.setattr("warcraft_cli.main.provider_search", fake_provider_search)
    monkeypatch.setattr("warcraft_cli.main.provider_invoke", fake_provider_invoke)

    result = runner.invoke(
        warcraft_app,
        [
            "guide-compare-query",
            "mistweaver monk guide",
            "--provider",
            "method",
            "--provider",
            "icy-veins",
            "--out-root",
            str(tmp_path / "orchestrated"),
        ],
    )
    assert result.exit_code == 1

    payload = json.loads(result.stderr)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "insufficient_guides"
    assert payload["exported_bundle_count"] == 1
    assert payload["comparison"] is None
    icy_row = next(row for row in payload["provider_results"] if row["provider"] == "icy-veins")
    assert icy_row["status"] == "skipped"
    assert icy_row["reason"] == "search_top_guide_score_too_low:25"


def test_warcraft_search_sorts_results_globally_by_ranking(monkeypatch) -> None:
    def fake_wowhead_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {
                    "id": 19019,
                    "name": "Thunderfury",
                    "entity_type": "item",
                    "ranking": {"score": 15, "match_reasons": ["name_contains_query"]},
                },
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_wowhead_search)
    monkeypatch.setattr(
        "method_cli.main.MethodClient.sitemap_guides",
        lambda self: [{"slug": "mistweaver-monk", "name": "Mistweaver Monk", "url": "https://www.method.gg/guides/mistweaver-monk"}],
    )
    monkeypatch.setattr(
        "icy_veins_cli.main.IcyVeinsClient.sitemap_guides",
        lambda self: [{"slug": "frost-death-knight-pve-dps-guide", "name": "Frost Death Knight PvE DPS Guide", "url": "https://www.icy-veins.com/wow/frost-death-knight-pve-dps-guide"}],
    )
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))

    result = runner.invoke(warcraft_app, ["search", "mistweaver monk guide", "--limit", "5"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["results"][0]["provider"] == "method"
    assert payload["results"][0]["wrapper_ranking"]["score"] >= payload["results"][0]["ranking"]["score"]


def test_warcraft_search_expansion_filter_excludes_nonmatching_providers(monkeypatch) -> None:
    def fake_wowhead_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {
                    "id": 19019,
                    "name": "Thunderfury",
                    "entity_type": "item",
                    "ranking": {"score": 20, "match_reasons": ["name_contains_query"]},
                },
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_wowhead_search)
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: (_ for _ in ()).throw(AssertionError("method should be excluded")))
    monkeypatch.setattr(
        "icy_veins_cli.main.IcyVeinsClient.sitemap_guides",
        lambda self: (_ for _ in ()).throw(AssertionError("icy-veins should be excluded")),
    )
    monkeypatch.setattr(
        "raiderio_cli.main.RaiderIOClient.search",
        lambda self, *, term, kind=None: (_ for _ in ()).throw(AssertionError("raiderio should be excluded")),
    )
    monkeypatch.setattr(
        "warcraft_wiki_cli.main.WarcraftWikiClient.search_articles",
        lambda self, query, limit: (_ for _ in ()).throw(AssertionError("warcraft-wiki should be excluded")),
    )
    monkeypatch.setattr(
        "wowprogress_cli.main.WowProgressClient.probe_search_route",
        lambda self, *, region, realm, name, obj_type: (_ for _ in ()).throw(AssertionError("wowprogress should be excluded")),
    )

    result = runner.invoke(warcraft_app, ["--expansion", "wotlk", "search", "thunderfury", "--limit", "3"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["requested_expansion"] == "wotlk"
    assert payload["expansion_filter_active"] is True
    assert payload["included_providers"] == ["wowhead"]
    assert payload["results"][0]["provider"] == "wowhead"
    assert payload["results"][0]["provider_expansion"]["mode"] == "profiled"
    assert {row["provider"] for row in payload["excluded_providers"]} == {
        "method",
        "icy-veins",
        "raiderio",
        "warcraftlogs",
        "warcraft-wiki",
        "wowprogress",
        "simc",
    }
    excluded = {row["provider"]: row["expansion_support"]["exclusion_reason"] for row in payload["excluded_providers"]}
    assert excluded["method"] == "provider_fixed_to_other_expansion"
    assert excluded["warcraft-wiki"] == "provider_has_no_expansion_support"


def test_warcraft_search_compact_expansion_debug(monkeypatch) -> None:
    def fake_wowhead_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {
                    "id": 19019,
                    "name": "Thunderfury",
                    "entity_type": "item",
                    "ranking": {"score": 20, "match_reasons": ["name_contains_query"]},
                },
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_wowhead_search)
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: (_ for _ in ()).throw(AssertionError("method should be excluded")))
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: (_ for _ in ()).throw(AssertionError("icy-veins should be excluded")))
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: (_ for _ in ()).throw(AssertionError("raiderio should be excluded")))
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (_ for _ in ()).throw(AssertionError("warcraft-wiki should be excluded")))
    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.probe_search_route", lambda self, *, region, realm, name, obj_type: (_ for _ in ()).throw(AssertionError("wowprogress should be excluded")))

    result = runner.invoke(
        warcraft_app,
        ["--expansion", "wotlk", "search", "thunderfury", "--limit", "3", "--compact", "--expansion-debug"],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["providers"] == []
    assert payload["results"][0]["provider_expansion"]["mode"] == "profiled"
    snapshot = {row["provider"]: row["expansion_support"] for row in payload["expansion_debug"]}
    assert snapshot["wowhead"]["allowed"] is True
    assert snapshot["wowhead"]["review_status"] == "reviewed"
    assert snapshot["method"]["allowed"] is False
    assert snapshot["method"]["exclusion_reason"] == "provider_fixed_to_other_expansion"
    assert "retail-focused" in snapshot["method"]["policy_note"]


def test_warcraft_search_retail_filter_keeps_fixed_retail_providers_and_excludes_none(monkeypatch) -> None:
    def fake_wowhead_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {
                    "id": 19019,
                    "name": "Thunderfury",
                    "entity_type": "item",
                    "ranking": {"score": 20, "match_reasons": ["name_contains_query"]},
                },
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_wowhead_search)
    monkeypatch.setattr(
        "method_cli.main.MethodClient.sitemap_guides",
        lambda self: [{"slug": "mistweaver-monk", "name": "Mistweaver Monk", "url": "https://www.method.gg/guides/mistweaver-monk"}],
    )
    monkeypatch.setattr(
        "icy_veins_cli.main.IcyVeinsClient.sitemap_guides",
        lambda self: [{"slug": "mistweaver-monk-pve-healing-guide", "name": "Mistweaver Monk PvE Healing Guide", "url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide"}],
    )
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr(
        "warcraft_wiki_cli.main.WarcraftWikiClient.search_articles",
        lambda self, query, limit: (_ for _ in ()).throw(AssertionError("warcraft-wiki should be excluded under explicit retail filtering")),
    )
    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.probe_search_route", lambda self, *, region, realm, name, obj_type: None)

    result = runner.invoke(warcraft_app, ["--expansion", "retail", "search", "mistweaver monk guide", "--limit", "5"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["requested_expansion"] == "retail"
    assert payload["expansion_filter_active"] is True
    assert set(payload["included_providers"]) == {
        "wowhead",
        "method",
        "icy-veins",
        "raiderio",
        "warcraftlogs",
        "wowprogress",
    }
    assert {row["provider"] for row in payload["excluded_providers"]} == {"warcraft-wiki", "simc"}
    results = {row["provider"] for row in payload["results"]}
    assert {"method", "icy-veins"} & results


def test_warcraft_resolve_retail_filter_keeps_fixed_retail_profile_provider(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr(
        "raiderio_cli.main.RaiderIOClient.search",
        lambda self, *, term, kind=None: {"matches": []},
    )
    monkeypatch.setattr(
        "warcraft_wiki_cli.main.WarcraftWikiClient.search_articles",
        lambda self, query, limit: (_ for _ in ()).throw(AssertionError("warcraft-wiki should be excluded under explicit retail filtering")),
    )
    monkeypatch.setattr(
        "wowprogress_cli.main.WowProgressClient.probe_search_route",
        lambda self, *, region, realm, name, obj_type: {
            "_search_kind": "guild",
            "guild": {
                "name": "Liquid",
                "region": "us",
                "realm": "illidan",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
            },
        }
        if obj_type == "guild"
        else None,
    )

    result = runner.invoke(warcraft_app, ["--expansion", "retail", "resolve", "guild us illidan Liquid"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["requested_expansion"] == "retail"
    assert payload["expansion_filter_active"] is True
    assert payload["provider"] == "wowprogress"
    assert set(payload["included_providers"]) == {
        "wowhead",
        "method",
        "icy-veins",
        "raiderio",
        "warcraftlogs",
        "wowprogress",
    }
    assert {row["provider"] for row in payload["excluded_providers"]} == {"warcraft-wiki", "simc"}


def test_warcraft_search_prefers_profile_provider_for_structured_guild_queries(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr(
        "method_cli.main.MethodClient.sitemap_guides",
        lambda self: [{"slug": "liquid-guide", "name": "Liquid Guide", "url": "https://www.method.gg/guides/liquid-guide"}],
    )
    monkeypatch.setattr(
        "icy_veins_cli.main.IcyVeinsClient.sitemap_guides",
        lambda self: [{"slug": "liquid-guide", "name": "Liquid Guide", "url": "https://www.icy-veins.com/wow/liquid-guide"}],
    )
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))
    monkeypatch.setattr(
        "wowprogress_cli.main.WowProgressClient.probe_search_route",
        lambda self, *, region, realm, name, obj_type: {
            "_search_kind": "guild",
            "guild": {
                "name": "Liquid",
                "region": "us",
                "realm": "illidan",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
            },
        }
        if obj_type == "guild"
        else None,
    )

    result = runner.invoke(warcraft_app, ["search", "guild us illidan Liquid", "--limit", "5"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["results"][0]["provider"] == "wowprogress"
    assert any(
        "intent:structured_profile:family:profile" in reason
        for reason in payload["results"][0]["wrapper_ranking"]["reasons"]
    )


def test_warcraft_search_compact_and_ranking_debug(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))
    monkeypatch.setattr(
        "wowprogress_cli.main.WowProgressClient.probe_search_route",
        lambda self, *, region, realm, name, obj_type: {
            "_search_kind": "guild",
            "guild": {
                "name": "Liquid",
                "region": "us",
                "realm": "illidan",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
            },
        }
        if obj_type == "guild"
        else None,
    )

    result = runner.invoke(warcraft_app, ["search", "guild us illidan Liquid", "--limit", "3", "--compact", "--ranking-debug"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["providers"] == []
    assert payload["results"][0]["provider"] == "wowprogress"
    assert payload["ranking_debug"][0]["wrapper_ranking"]["provider_family"] == "profile"


def test_warcraft_search_adds_synthetic_wowprogress_leaderboard_candidate(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))

    result = runner.invoke(warcraft_app, ["search", "leaderboard us illidan", "--compact", "--ranking-debug"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["results"][0]["provider"] == "wowprogress"
    assert payload["results"][0]["kind"] == "leaderboard"
    assert payload["results"][0]["follow_up_command"] == "wowprogress leaderboard pve us --realm illidan"


def test_warcraft_resolve_prefers_stronger_later_provider(monkeypatch) -> None:
    def fake_wowhead_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 100, "id": 2594, "name": "Warlords of Draenor Mistweaver Monk Guide", "typeName": "Guide", "popularity": 8},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_wowhead_search)
    monkeypatch.setattr(
        "method_cli.main.MethodClient.sitemap_guides",
        lambda self: [{"slug": "mistweaver-monk", "name": "Mistweaver Monk", "url": "https://www.method.gg/guides/mistweaver-monk"}],
    )
    monkeypatch.setattr(
        "icy_veins_cli.main.IcyVeinsClient.sitemap_guides",
        lambda self: [{"slug": "mistweaver-monk-pve-healing-guide", "name": "Mistweaver Monk PvE Healing Guide", "url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide"}],
    )
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr(
        "warcraft_wiki_cli.main.WarcraftWikiClient.search_articles",
        lambda self, query, limit: (1, [{"title": "Mistweaver Monk", "pageid": 1, "snippet": "Reference page", "url": "https://warcraft.wiki.gg/wiki/Mistweaver_Monk"}]),
    )

    result = runner.invoke(warcraft_app, ["resolve", "mistweaver monk guide"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["provider"] == "icy-veins"
    assert payload["confidence"] == "high"
    assert payload["next_command"] == "icy-veins guide mistweaver-monk-pve-healing-guide"


def test_warcraft_resolve_expansion_filter_blocks_retail_only_resolution(monkeypatch) -> None:
    monkeypatch.setattr(
        "wowhead_cli.main.WowheadClient.search_suggestions",
        lambda self, query: {"search": query, "results": []},
    )
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: (_ for _ in ()).throw(AssertionError("method should be excluded")))
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: (_ for _ in ()).throw(AssertionError("icy-veins should be excluded")))
    monkeypatch.setattr(
        "raiderio_cli.main.RaiderIOClient.search",
        lambda self, *, term, kind=None: (_ for _ in ()).throw(AssertionError("raiderio should be excluded")),
    )
    monkeypatch.setattr(
        "warcraft_wiki_cli.main.WarcraftWikiClient.search_articles",
        lambda self, query, limit: (_ for _ in ()).throw(AssertionError("warcraft-wiki should be excluded")),
    )
    monkeypatch.setattr(
        "wowprogress_cli.main.WowProgressClient.probe_search_route",
        lambda self, *, region, realm, name, obj_type: (_ for _ in ()).throw(AssertionError("wowprogress should be excluded")),
    )

    result = runner.invoke(warcraft_app, ["--expansion", "wotlk", "resolve", "guild us illidan Liquid"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["requested_expansion"] == "wotlk"
    assert payload["expansion_filter_active"] is True
    assert payload["resolved"] is False
    assert payload["provider"] is None
    assert payload["included_providers"] == ["wowhead"]
    assert {row["provider"] for row in payload["excluded_providers"]} == {
        "method",
        "icy-veins",
        "raiderio",
        "warcraftlogs",
        "warcraft-wiki",
        "wowprogress",
        "simc",
    }


def test_warcraft_resolve_expansion_debug(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: (_ for _ in ()).throw(AssertionError("method should be excluded")))
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: (_ for _ in ()).throw(AssertionError("icy-veins should be excluded")))
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: (_ for _ in ()).throw(AssertionError("raiderio should be excluded")))
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (_ for _ in ()).throw(AssertionError("warcraft-wiki should be excluded")))
    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.probe_search_route", lambda self, *, region, realm, name, obj_type: (_ for _ in ()).throw(AssertionError("wowprogress should be excluded")))

    result = runner.invoke(
        warcraft_app,
        ["--expansion", "wotlk", "resolve", "guild us illidan Liquid", "--compact", "--expansion-debug"],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    snapshot = {row["provider"]: row["expansion_support"] for row in payload["expansion_debug"]}
    assert snapshot["wowhead"]["allowed"] is True
    assert snapshot["simc"]["allowed"] is False
    assert snapshot["simc"]["exclusion_reason"] == "provider_has_no_expansion_support"
    assert snapshot["simc"]["review_status"] == "deferred"
    assert "Local repo analysis" in snapshot["simc"]["policy_note"]


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
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(warcraft_app, ["resolve", "fairbreeze favors"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["provider"] == "wowhead"
    assert payload["next_command"] == "wowhead entity quest 86739"


def test_warcraft_resolve_can_select_raiderio(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr(
        "raiderio_cli.main.RaiderIOClient.search",
        lambda self, *, term, kind=None: {
            "matches": [
                {
                    "type": "character",
                    "name": "Roguecane",
                    "data": {
                        "id": 39943,
                        "name": "Roguecane",
                        "faction": "horde",
                        "region": {"slug": "us", "name": "United States & Oceania"},
                        "realm": {"slug": "illidan", "name": "Illidan"},
                        "class": {"name": "Rogue", "slug": "rogue"},
                    },
                }
            ]
        },
    )
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))

    result = runner.invoke(warcraft_app, ["resolve", "Roguecane"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["provider"] == "raiderio"
    assert payload["next_command"] == "raiderio character us illidan Roguecane"


def test_warcraft_resolve_prefers_raiderio_for_character_queries_when_both_resolve(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr(
        "raiderio_cli.main.RaiderIOClient.search",
        lambda self, *, term, kind=None: {
            "matches": [
                {
                    "type": "character",
                    "name": "Roguecane",
                    "data": {
                        "id": 39943,
                        "name": "Roguecane",
                        "faction": "horde",
                        "region": {"slug": "us", "name": "United States & Oceania"},
                        "realm": {"slug": "illidan", "name": "Illidan"},
                        "class": {"name": "Rogue", "slug": "rogue"},
                    },
                }
            ]
        },
    )
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))
    monkeypatch.setattr(
        "wowprogress_cli.main.WowProgressClient.probe_search_route",
        lambda self, *, region, realm, name, obj_type: {
            "_search_kind": "character",
            "character": {
                "name": "Roguecane",
                "region": "us",
                "realm": "illidan",
                "guild_name": "Liquid",
                "class_name": "Rogue",
                "page_url": "https://www.wowprogress.com/character/us/illidan/Roguecane",
            },
        }
        if obj_type == "char"
        else None,
    )

    result = runner.invoke(warcraft_app, ["resolve", "character us illidan Roguecane", "--ranking-debug"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["provider"] == "raiderio"
    assert payload["next_command"] == "raiderio character us illidan Roguecane"
    assert payload["ranking_debug"][0]["provider"] == "raiderio"


def test_warcraft_resolve_can_select_wowprogress(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))
    monkeypatch.setattr(
        "wowprogress_cli.main.WowProgressClient.probe_search_route",
        lambda self, *, region, realm, name, obj_type: {
            "_search_kind": "guild",
            "guild": {
                "name": "Liquid",
                "region": "us",
                "realm": "illidan",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
            },
        }
        if obj_type == "guild"
        else None,
    )

    result = runner.invoke(warcraft_app, ["resolve", "guild us illidan Liquid"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["provider"] == "wowprogress"
    assert payload["next_command"] == "wowprogress guild us illidan Liquid"
    assert payload["match"]["wrapper_ranking"]["provider_family"] == "profile"


def test_warcraft_resolve_can_select_warcraftlogs_for_explicit_report_reference(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))
    monkeypatch.setattr("wowprogress_cli.main.WowProgressClient.probe_search_route", lambda self, *, region, realm, name, obj_type: None)

    result = runner.invoke(warcraft_app, ["resolve", "https://www.warcraftlogs.com/reports/abcd1234#fight=3"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is True
    assert payload["provider"] == "warcraftlogs"
    assert payload["next_command"] == "warcraftlogs report-encounter abcd1234 --fight-id 3"
    assert payload["match"]["wrapper_ranking"]["provider_family"] == "logs"


def test_warcraft_resolve_compact_and_ranking_debug(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))
    monkeypatch.setattr(
        "wowprogress_cli.main.WowProgressClient.probe_search_route",
        lambda self, *, region, realm, name, obj_type: {
            "_search_kind": "guild",
            "guild": {
                "name": "Liquid",
                "region": "us",
                "realm": "illidan",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
            },
        }
        if obj_type == "guild"
        else None,
    )

    result = runner.invoke(warcraft_app, ["resolve", "guild us illidan Liquid", "--compact", "--ranking-debug"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["providers"] == []
    assert payload["match"]["provider"] == "wowprogress"
    assert payload["ranking_debug"][0]["provider"] == "wowprogress"


def test_warcraft_resolve_does_not_fabricate_synthetic_wowprogress_leaderboard_route(monkeypatch) -> None:
    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", lambda self, query: {"search": query, "results": []})
    monkeypatch.setattr("method_cli.main.MethodClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.sitemap_guides", lambda self: [])
    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.search", lambda self, *, term, kind=None: {"matches": []})
    monkeypatch.setattr("warcraft_wiki_cli.main.WarcraftWikiClient.search_articles", lambda self, query, limit: (0, []))

    result = runner.invoke(warcraft_app, ["resolve", "leaderboard us illidan", "--compact", "--ranking-debug"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["resolved"] is False
    assert payload["provider"] is None
    assert payload["next_command"] is None
    assert payload["match"] is None


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


def test_warcraft_passthrough_to_wowhead_injects_global_expansion(monkeypatch) -> None:
    def fake_search(self, query: str):  # noqa: ANN001
        return {
            "search": query,
            "results": [
                {"type": 3, "id": 19019, "name": "Thunderfury", "typeName": "Item"},
            ],
        }

    monkeypatch.setattr("wowhead_cli.main.WowheadClient.search_suggestions", fake_search)
    result = runner.invoke(warcraft_app, ["--expansion", "wotlk", "wowhead", "search", "thunderfury", "--limit", "1"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["expansion"] == "wotlk"


def test_warcraft_passthrough_rejects_unsupported_provider_expansion() -> None:
    result = runner.invoke(warcraft_app, ["--expansion", "wotlk", "method", "guide", "mistweaver-monk"])
    assert result.exit_code == 1

    payload = json.loads(result.output)
    assert payload["error"]["code"] == "unsupported_provider_expansion"
    assert payload["provider"] == "method"
    assert payload["requested_expansion"] == "wotlk"


def test_warcraft_passthrough_rejects_duplicate_wowhead_expansion() -> None:
    result = runner.invoke(
        warcraft_app,
        ["--expansion", "wotlk", "wowhead", "--expansion", "retail", "search", "thunderfury", "--limit", "1"],
    )
    assert result.exit_code == 1

    payload = json.loads(result.output)
    assert payload["error"]["code"] == "duplicate_expansion_argument"


def test_warcraft_passthrough_to_method(monkeypatch) -> None:
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


def test_warcraft_passthrough_to_icy_veins(monkeypatch) -> None:
    def fake_fetch(self, guide_ref):  # noqa: ANN001
        return {
            "guide": {
                "slug": "mistweaver-monk-pve-healing-guide",
                "page_url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
                "section_slug": "mistweaver-monk-pve-healing-guide",
                "section_title": "Mistweaver Monk Guide",
                "author": "Dhaubbs",
                "last_updated": "2026-03-05T05:19:00+00:00",
                "published_at": "2012-09-13T02:17:00+00:00",
            },
            "page": {
                "title": "Mistweaver Monk Healing Guide - Midnight (12.0.1)",
                "description": "This guide contains everything you need to know to be an excellent Mistweaver Monk.",
                "canonical_url": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide",
                "page_type": "guides",
            },
            "navigation": [],
            "page_toc": [],
            "article": {"html": "<p>Intro</p>", "text": "Intro", "intro_text": "General Information", "headings": [], "sections": []},
            "linked_entities": [],
            "citations": {"page": "https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide"},
        }

    monkeypatch.setattr("icy_veins_cli.main.IcyVeinsClient.fetch_guide_page", fake_fetch)
    result = runner.invoke(warcraft_app, ["icy-veins", "guide", "mistweaver-monk-pve-healing-guide"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["guide"]["slug"] == "mistweaver-monk-pve-healing-guide"
    assert payload["guide"]["author"] == "Dhaubbs"


def test_warcraft_passthrough_to_simc(monkeypatch, tmp_path) -> None:
    profile = tmp_path / "example.simc"
    profile.write_text('monk="example"\n')

    monkeypatch.setattr(
        "simc_cli.main.run_profile",
        lambda paths, profile_path, simc_args: type("Result", (), {"command": [str(paths.build_simc), str(profile_path)], "returncode": 0, "stdout": "Iterations: 1\n", "stderr": ""})(),
    )
    monkeypatch.setattr(
        "simc_cli.main.binary_version",
        lambda paths: type("VersionInfo", (), {"binary_path": paths.build_simc, "available": True, "version_line": "SimulationCraft 1201", "returncode": 1})(),
    )

    result = runner.invoke(warcraft_app, ["simc", "run", str(profile)])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider"] == "simc"
    assert payload["status"] == "completed"
    assert payload["version"] == "SimulationCraft 1201"


def test_warcraft_passthrough_to_raiderio(monkeypatch) -> None:
    def fake_profile(self, *, region: str, realm: str, name: str, fields: str = ""):  # noqa: ANN001
        return {
            "name": "Roguecane",
            "region": "us",
            "realm": "Illidan",
            "race": "Blood Elf",
            "class": "Rogue",
            "active_spec_name": "Subtlety",
            "faction": "horde",
            "profile_url": "https://raider.io/characters/us/illidan/Roguecane",
            "thumbnail_url": "https://example.test/thumb.jpg",
            "guild": {"name": "Liquid", "realm": "Illidan", "region": "us"},
            "raid_progression": {},
            "mythic_plus_scores_by_season": [],
            "mythic_plus_ranks": {},
            "mythic_plus_recent_runs": [],
        }

    monkeypatch.setattr("raiderio_cli.main.RaiderIOClient.character_profile_variants", fake_profile)
    result = runner.invoke(warcraft_app, ["raiderio", "character", "us", "illidan", "Roguecane"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["character"]["name"] == "Roguecane"


def test_warcraft_passthrough_to_warcraft_wiki(monkeypatch) -> None:
    monkeypatch.setattr(
        "warcraft_wiki_cli.main.WarcraftWikiClient.fetch_article_page",
        lambda self, article_ref: {
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
            "navigation": {"count": 0, "items": []},
            "article_content": {"html": "<p>FrameXML</p>", "text": "FrameXML", "headings": [], "sections": []},
            "linked_entities": [],
            "citations": {"page": "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API"},
        },
    )
    result = runner.invoke(warcraft_app, ["warcraft-wiki", "article", "World of Warcraft API"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["article"]["title"] == "World of Warcraft API"


def test_warcraft_passthrough_to_wowprogress(monkeypatch) -> None:
    monkeypatch.setattr(
        "wowprogress_cli.main.WowProgressClient.fetch_guild_page_variants",
        lambda self, *, region, realm, name: {
            "guild": {
                "name": "Liquid",
                "region": "us",
                "realm": "US-Illidan",
                "faction": "Horde",
                "page_url": "https://www.wowprogress.com/guild/us/illidan/Liquid",
                "armory_url": "https://worldofwarcraft.com/en-us/guild/illidan/liquid",
            },
            "progress": {"summary": "8/8 (M)", "ranks": {"world": "1", "region": "1", "realm": "1"}},
            "item_level": {"average": 724.51, "group_size": "20-man", "ranks": {"world": "9026", "region": "4149", "realm": "238"}},
            "encounters": {"count": 0, "items": []},
            "citations": {"page": "https://www.wowprogress.com/guild/us/illidan/Liquid"},
        },
    )
    result = runner.invoke(warcraft_app, ["wowprogress", "guild", "us", "illidan", "Liquid"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["guild"]["name"] == "Liquid"


def test_warcraft_passthrough_to_warcraftlogs() -> None:
    result = runner.invoke(
        warcraft_app,
        ["warcraftlogs", "resolve", "https://www.warcraftlogs.com/reports/abcd1234#fight=3"],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider"] == "warcraftlogs"
    assert payload["resolved"] is True
    assert payload["next_command"] == "warcraftlogs report-encounter abcd1234 --fight-id 3"


def test_warcraft_guild_merges_sources_and_normalizes_query(monkeypatch) -> None:
    def fake_ri(self, *, region: str, realm: str, name: str):  # noqa: ANN001
        assert region == "us"
        assert realm == "mal-ganis"
        assert name == "gn"
        return {
            "name": "gn",
            "region": "us",
            "realm": "Mal'Ganis",
            "faction": "horde",
            "profile_url": "https://raider.io/guilds/us/malganis/gn",
            "raid_progression": {"tier-mn-1": {"summary": "0/9 N", "total_bosses": 9}},
            "raid_rankings": {"tier-mn-1": {"normal": {"world": 0, "region": 0, "realm": 0}}},
            "members": [{"rank": 1, "character": {"name": "Fharg", "class": "Shaman", "active_spec_name": "Enhancement", "active_spec_role": "DPS", "profile_url": "https://raider.io/characters/us/malganis/Fharg"}}],
        }

    def fake_wp(self, *, region: str, realm: str, name: str):  # noqa: ANN001
        assert region == "us"
        assert realm == "mal-ganis"
        assert name == "gn"
        return {
            "guild": {"name": "gn", "region": "us", "realm": "Mal'Ganis", "faction": "Horde", "page_url": "https://www.wowprogress.com/guild/us/mal-ganis/gn"},
            "progress": {"raid": "Liberation of Undermine", "tier_key": "tier34", "summary": "8/8 (M)", "ranks": {"world": "19", "region": "6", "realm": "2"}},
            "item_level": {"average": 732.1, "ranks": {"world": "1", "region": "1", "realm": "1"}},
            "encounters": {"count": 8, "items": [{"encounter": "Chrome King Gallywix"}]},
            "citations": {"page": "https://www.wowprogress.com/guild/us/mal-ganis/gn"},
        }

    monkeypatch.setattr("warcraft_cli.main.RaiderIOClient.guild_profile_variants", fake_ri)
    monkeypatch.setattr("warcraft_cli.main.WowProgressClient.fetch_guild_page_variants", fake_wp)

    result = runner.invoke(warcraft_app, ["guild", "na", "Mal'Ganis", "gn"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["query"] == {"region": "us", "realm": "mal-ganis", "name": "gn"}
    assert payload["guild"]["name"] == "gn"
    assert payload["sources"]["raiderio"]["status"] == "ok"
    assert payload["sources"]["wowprogress"]["status"] == "ok"
    assert payload["conflicts"]["different_tier_window_detected"] is True


def test_warcraft_guild_history_and_ranks_use_wowprogress(monkeypatch) -> None:
    history_payload = {
        "provider": "wowprogress",
        "kind": "guild_history",
        "guild": {"name": "gn", "region": "us", "realm": "Mal'Ganis"},
        "history": [
            {
                "tier_key": "tier34",
                "raid": "Liberation of Undermine",
                "current": True,
                "progress": "8/8 (M)",
                "progress_ranks": {"world": "19", "region": "6", "realm": "2"},
                "item_level_average": 732.1,
                "item_level_ranks": {"world": "1", "region": "1", "realm": "1"},
                "last_kill_at": "Apr 4, 2025 02:03",
                "page_url": "https://www.wowprogress.com/guild/us/mal-ganis/gn/rating.tier34",
            }
        ],
        "citations": {"page": "https://www.wowprogress.com/guild/us/mal-ganis/gn"},
    }

    monkeypatch.setattr("warcraft_cli.main.WowProgressClient.fetch_guild_history", lambda self, **kwargs: history_payload)

    history_result = runner.invoke(warcraft_app, ["guild-history", "us", "Mal'Ganis", "gn"])
    assert history_result.exit_code == 0
    history = json.loads(history_result.stdout)
    assert history["ok"] is True
    assert history["source"] == "wowprogress"
    assert history["tiers"][0]["raid"] == "Liberation of Undermine"

    ranks_result = runner.invoke(warcraft_app, ["guild-ranks", "us", "Mal'Ganis", "gn"])
    assert ranks_result.exit_code == 0
    ranks = json.loads(ranks_result.stdout)
    assert ranks["ok"] is True
    assert ranks["tiers"][0]["progress_ranks"]["world"] == "19"
