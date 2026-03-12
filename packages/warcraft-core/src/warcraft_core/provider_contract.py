from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def confidence_rank(value: Any) -> int:
    normalized = str(value or "").strip().lower()
    if normalized == "high":
        return 3
    if normalized == "medium":
        return 2
    if normalized == "low":
        return 1
    return 0


def candidate_score(candidate: Mapping[str, Any] | None) -> int:
    if not isinstance(candidate, Mapping):
        return 0
    ranking = candidate.get("ranking")
    if not isinstance(ranking, Mapping):
        return 0
    try:
        return int(ranking.get("score") or 0)
    except (TypeError, ValueError):
        return 0


def search_result_sort_key(row: Mapping[str, Any]) -> tuple[int, str, str, str]:
    score = candidate_score(row)
    provider = str(row.get("provider") or "")
    name = str(row.get("name") or "")
    identifier = str(row.get("id") or "")
    return (-score, provider, name, identifier)


def resolve_payload_sort_key(provider: str, payload: Mapping[str, Any]) -> tuple[int, int, int, str]:
    resolved = 1 if payload.get("resolved") else 0
    confidence = confidence_rank(payload.get("confidence"))
    match = payload.get("match")
    score = candidate_score(match if isinstance(match, Mapping) else None)
    return (-resolved, -confidence, -score, provider)
