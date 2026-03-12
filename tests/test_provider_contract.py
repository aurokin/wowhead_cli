from __future__ import annotations

from warcraft_core.provider_contract import candidate_score, confidence_rank, resolve_payload_sort_key, search_result_sort_key


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


def test_resolve_payload_sort_key_prefers_resolved_then_confidence_then_score() -> None:
    unresolved = ("wowhead", {"resolved": False, "confidence": "medium", "match": {"ranking": {"score": 90}}})
    medium = ("method", {"resolved": True, "confidence": "medium", "match": {"ranking": {"score": 20}}})
    high = ("icy-veins", {"resolved": True, "confidence": "high", "match": {"ranking": {"score": 10}}})

    ordered = sorted([medium, unresolved, high], key=lambda row: resolve_payload_sort_key(row[0], row[1]))

    assert ordered[0][0] == "icy-veins"
    assert ordered[-1][0] == "wowhead"
