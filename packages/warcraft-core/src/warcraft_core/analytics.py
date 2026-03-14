from __future__ import annotations

from statistics import median
from typing import Any


def count_map(values: list[str]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    total = sum(counts.values()) or 1
    return [
        {
            "value": key,
            "count": count,
            "percent": round((count / total) * 100, 2),
        }
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def numeric_summary(values: list[int | float]) -> dict[str, Any] | None:
    if not values:
        return None
    sorted_values = sorted(values)
    return {
        "min": sorted_values[0],
        "max": sorted_values[-1],
        "average": round(sum(values) / len(values), 2),
        "median": median(sorted_values),
    }


def numeric_distribution(values: list[int | float], *, unit: str) -> dict[str, Any]:
    return {
        "unit": unit,
        "rows": count_map([str(value) for value in values]),
        "statistics": numeric_summary(values),
    }


def categorical_distribution(values: list[str], *, unit: str) -> dict[str, Any]:
    return {
        "unit": unit,
        "rows": count_map(values),
        "statistics": None,
    }


def distribution_response(
    *,
    provider: str,
    kind: str,
    metric: str,
    query: dict[str, Any],
    sample: dict[str, Any],
    distribution: dict[str, Any],
    freshness: dict[str, Any],
    citations: dict[str, Any],
) -> dict[str, Any]:
    return {
        "provider": provider,
        "kind": kind,
        "metric": metric,
        "query": query,
        "sample": sample,
        "distribution": distribution,
        "freshness": freshness,
        "citations": citations,
    }
