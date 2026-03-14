from __future__ import annotations

from warcraft_core.analytics import (
    categorical_distribution,
    count_map,
    distribution_response,
    numeric_distribution,
    numeric_summary,
)


def test_count_map_sorts_by_frequency_then_value() -> None:
    assert count_map(["b", "a", "b"]) == [
        {"value": "b", "count": 2, "percent": 66.67},
        {"value": "a", "count": 1, "percent": 33.33},
    ]


def test_numeric_summary_and_distribution() -> None:
    assert numeric_summary([1, 2, 3]) == {
        "min": 1,
        "max": 3,
        "average": 2.0,
        "median": 2,
    }
    assert numeric_summary([]) is None
    assert numeric_distribution([2, 2, 3], unit="runs") == {
        "unit": "runs",
        "rows": [
            {"value": "2", "count": 2, "percent": 66.67},
            {"value": "3", "count": 1, "percent": 33.33},
        ],
        "statistics": {
            "min": 2,
            "max": 3,
            "average": 2.33,
            "median": 2,
        },
    }


def test_categorical_distribution_and_response() -> None:
    distribution = categorical_distribution(["us", "eu", "us"], unit="players")
    assert distribution == {
        "unit": "players",
        "rows": [
            {"value": "us", "count": 2, "percent": 66.67},
            {"value": "eu", "count": 1, "percent": 33.33},
        ],
        "statistics": None,
    }
    assert distribution_response(
        provider="raiderio",
        kind="mythic_plus_runs_distribution",
        metric="player_region",
        query={"region": "world"},
        sample={"run_count": 10},
        distribution=distribution,
        freshness={"sampled_at": "2026-03-14T00:00:00+00:00", "cache_ttl_seconds": 3600},
        citations={"leaderboard_urls": ["https://raider.io"]},
    ) == {
        "provider": "raiderio",
        "kind": "mythic_plus_runs_distribution",
        "metric": "player_region",
        "query": {"region": "world"},
        "sample": {"run_count": 10},
        "distribution": distribution,
        "freshness": {"sampled_at": "2026-03-14T00:00:00+00:00", "cache_ttl_seconds": 3600},
        "citations": {"leaderboard_urls": ["https://raider.io"]},
    }
