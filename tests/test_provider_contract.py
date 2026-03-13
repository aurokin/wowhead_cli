from __future__ import annotations

import json

from warcraft_core.provider_contract import (
    candidate_score,
    compact_wrapper_candidate,
    confidence_rank,
    decorate_resolve_payload,
    decorate_search_result,
    load_wrapper_ranking_policy,
    query_intents,
    resolve_payload_sort_key,
    search_result_sort_key,
    wrapper_search_ranking,
)


def test_confidence_rank_orders_known_values() -> None:
    assert confidence_rank("high") > confidence_rank("medium") > confidence_rank("low") > confidence_rank("none")
    assert confidence_rank(None) == 0


def test_candidate_score_reads_ranking_score() -> None:
    assert candidate_score({"ranking": {"score": 27}}) == 27
    assert candidate_score({"ranking": {"score": "12"}}) == 12
    assert candidate_score({"ranking": {}}) == 0
    assert candidate_score(None) == 0


def test_search_result_sort_key_prefers_higher_scores() -> None:
    rows = [
        {"provider": "method", "name": "B", "id": "b", "ranking": {"score": 10}},
        {"provider": "wowhead", "name": "A", "id": "a", "ranking": {"score": 30}},
    ]

    rows.sort(key=search_result_sort_key)

    assert rows[0]["provider"] == "wowhead"


def test_query_intents_detect_structured_profile_and_reference() -> None:
    assert "structured_profile" in query_intents("guild us illidan Liquid")
    assert "guild_profile" in query_intents("guild us illidan Liquid")
    assert "reference" in query_intents("world of warcraft api")


def test_wrapper_search_ranking_boosts_reference_provider_for_api_queries() -> None:
    wiki = wrapper_search_ranking(
        "world of warcraft api",
        {
            "provider": "warcraft-wiki",
            "name": "World of Warcraft API",
            "entity_type": "article",
            "ranking": {"score": 18},
        },
    )
    guide = wrapper_search_ranking(
        "world of warcraft api",
        {
            "provider": "method",
            "name": "API Guide",
            "entity_type": "guide",
            "ranking": {"score": 24},
        },
    )

    assert wiki["score"] > guide["score"]
    assert any("intent:reference:family:reference" in reason for reason in wiki["reasons"])


def test_search_result_sort_key_prefers_wrapper_ranking_when_present() -> None:
    rows = [
        decorate_search_result(
            "guild us illidan Liquid",
            {"provider": "method", "name": "Liquid Guide", "entity_type": "guide", "ranking": {"score": 40}},
        ),
        decorate_search_result(
            "guild us illidan Liquid",
            {"provider": "wowprogress", "name": "Liquid", "kind": "guild", "ranking": {"score": 20}},
        ),
    ]

    rows.sort(key=search_result_sort_key)

    assert rows[0]["provider"] == "wowprogress"
    assert rows[0]["wrapper_ranking"]["score"] > rows[1]["wrapper_ranking"]["score"]


def test_load_wrapper_ranking_policy_allows_json_override(tmp_path) -> None:
    override_path = tmp_path / "wrapper_ranking.json"
    override_path.write_text(
        json.dumps(
            {
                "provider_kind_boosts": {
                    "wowprogress": {"guild": 99},
                }
            }
        ),
        encoding="utf-8",
    )

    policy = load_wrapper_ranking_policy(override_path=override_path)

    assert policy["provider_kind_boosts"]["wowprogress"]["guild"] == 99
    assert policy["provider_kind_boosts"]["raiderio"]["character"] == 12


def test_compact_wrapper_candidate_keeps_ranking_and_follow_up() -> None:
    compact = compact_wrapper_candidate(
        {
            "provider": "wowprogress",
            "kind": "guild",
            "name": "Liquid",
            "id": "guild:1",
            "follow_up": {"command": "wowprogress guild us illidan Liquid"},
            "wrapper_ranking": {
                "score": 88,
                "reasons": ["provider_score:20"],
                "intents": ["guild_profile"],
                "provider_family": "profile",
            },
        }
    )

    assert compact["provider"] == "wowprogress"
    assert compact["follow_up_command"] == "wowprogress guild us illidan Liquid"
    assert compact["wrapper_ranking"]["score"] == 88


def test_resolve_payload_sort_key_prefers_resolved_then_confidence_then_wrapper_score() -> None:
    unresolved = ("wowhead", {"resolved": False, "confidence": "medium", "match": {"ranking": {"score": 90}}})
    medium = (
        "method",
        decorate_resolve_payload(
            "mistweaver monk guide",
            "method",
            {"resolved": True, "confidence": "medium", "match": {"entity_type": "guide", "ranking": {"score": 20}}},
        ),
    )
    high = (
        "icy-veins",
        decorate_resolve_payload(
            "mistweaver monk guide",
            "icy-veins",
            {"resolved": True, "confidence": "high", "match": {"entity_type": "guide", "ranking": {"score": 10}}},
        ),
    )

    ordered = sorted([medium, unresolved, high], key=lambda row: resolve_payload_sort_key(row[0], row[1]))

    assert ordered[0][0] == "icy-veins"
    assert ordered[-1][0] == "wowhead"
