from __future__ import annotations

from warcraft_content.article_discovery import (
    article_candidate,
    article_follow_up,
    article_resolve_payload,
    article_search_payload,
    merge_article_linked_entities,
    sort_article_candidates,
)


def test_article_follow_up_uses_provider_command() -> None:
    follow_up = article_follow_up("method", "mistweaver-monk")

    assert follow_up == {
        "recommended_surface": "guide",
        "recommended_command": "method guide mistweaver-monk",
        "reason": "guide_summary",
        "alternatives": [
            "method guide-full mistweaver-monk",
            "method guide-export mistweaver-monk",
        ],
    }


def test_article_candidate_builds_shared_shape() -> None:
    row = article_candidate(
        slug="mistweaver-monk",
        name="Mistweaver Monk",
        url="https://www.method.gg/guides/mistweaver-monk",
        score=33,
        reasons=["exact_name", "all_terms_match"],
        provider_command="method",
    )

    assert row["id"] == "mistweaver-monk"
    assert row["ranking"]["score"] == 33
    assert row["follow_up"]["recommended_command"] == "method guide mistweaver-monk"


def test_sort_article_candidates_orders_by_score_then_name() -> None:
    rows = [
        article_candidate(
            slug="b",
            name="B Guide",
            url="https://example.invalid/b",
            score=10,
            reasons=["name_contains_query"],
            provider_command="method",
        ),
        article_candidate(
            slug="a",
            name="A Guide",
            url="https://example.invalid/a",
            score=30,
            reasons=["name_contains_query"],
            provider_command="method",
        ),
    ]

    sort_article_candidates(rows)

    assert rows[0]["id"] == "a"


def test_article_search_and_resolve_payloads_keep_contract_shape() -> None:
    rows = [
        article_candidate(
            slug="mistweaver-monk",
            name="Mistweaver Monk",
            url="https://www.method.gg/guides/mistweaver-monk",
            score=33,
            reasons=["exact_name"],
            provider_command="method",
        )
    ]

    search_payload = article_search_payload(
        query="mistweaver monk guide",
        search_query="mistweaver monk",
        results=rows,
        total_count=1,
    )
    resolve_payload = article_resolve_payload(
        provider_command="method",
        query="mistweaver monk guide",
        search_query="mistweaver monk",
        results=rows,
        total_count=1,
        resolved=True,
    )

    assert search_payload["results"][0]["id"] == "mistweaver-monk"
    assert resolve_payload["resolved"] is True
    assert resolve_payload["next_command"] == "method guide mistweaver-monk"
    assert resolve_payload["confidence"] == "high"


def test_merge_article_linked_entities_dedupes_and_preserves_source_urls() -> None:
    pages = [
        {
            "guide": {"page_url": "https://example.invalid/intro"},
            "linked_entities": [
                {"type": "spell", "id": 123, "name": None, "url": "https://wowhead.com/spell=123"},
            ],
        },
        {
            "guide": {"page_url": "https://example.invalid/talents"},
            "linked_entities": [
                {"type": "spell", "id": 123, "name": "Example Spell", "url": "https://wowhead.com/spell=123"},
            ],
        },
    ]

    merged = merge_article_linked_entities(pages)

    assert merged == [
        {
            "type": "spell",
            "id": 123,
            "name": "Example Spell",
            "url": "https://wowhead.com/spell=123",
            "source_urls": [
                "https://example.invalid/intro",
                "https://example.invalid/talents",
            ],
        }
    ]
