from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

PROVIDER_FAMILIES: dict[str, str] = {
    "wowhead": "entity",
    "method": "article",
    "icy-veins": "article",
    "raiderio": "profile",
    "warcraft-wiki": "reference",
    "wowprogress": "profile",
    "simc": "local_tool",
}

KNOWN_REGION_TERMS = frozenset({"us", "eu", "kr", "tw", "cn", "world"})

INTENT_KEYWORDS: dict[str, frozenset[str]] = {
    "guide": frozenset({"guide", "guides", "build", "builds", "rotation", "talent", "talents", "bis"}),
    "reference": frozenset({"wiki", "article", "articles", "api", "addon", "addons", "lua", "reference", "lore", "story"}),
    "entity": frozenset(
        {
            "achievement",
            "comment",
            "comments",
            "currency",
            "faction",
            "item",
            "items",
            "mount",
            "mounts",
            "npc",
            "npcs",
            "object",
            "objects",
            "pet",
            "pets",
            "quest",
            "quests",
            "recipe",
            "recipes",
            "spell",
            "spells",
            "tooltip",
            "zone",
            "zones",
        }
    ),
    "guild_profile": frozenset({"guild", "guilds", "roster", "progression", "leaderboard", "leaderboards"}),
    "character_profile": frozenset({"character", "characters", "rio", "score", "scores", "keys", "runs", "m+", "mythic+", "mythicplus"}),
    "simc": frozenset(
        {
            "simc",
            "simulationcraft",
            "apl",
            "action",
            "actions",
            "profile",
            "profiles",
            "decode-build",
            "branch",
            "branches",
            "trace",
        }
    ),
}

INTENT_FAMILY_BOOSTS: dict[str, dict[str, int]] = {
    "guide": {"article": 26, "entity": 10, "reference": -6, "profile": -18, "local_tool": -22},
    "reference": {"reference": 32, "entity": 8, "article": -10, "profile": -18, "local_tool": -12},
    "entity": {"entity": 30, "article": -10, "reference": -6, "profile": -16, "local_tool": -18},
    "guild_profile": {"profile": 30, "article": -14, "reference": -10, "entity": -12, "local_tool": -20},
    "character_profile": {"profile": 28, "entity": 6, "article": -14, "reference": -10, "local_tool": -18},
    "structured_profile": {"profile": 34, "article": -16, "reference": -12, "entity": -10, "local_tool": -18},
    "simc": {"local_tool": 40, "article": -18, "reference": -14, "entity": -14, "profile": -20},
}

INTENT_KIND_BOOSTS: dict[str, dict[str, int]] = {
    "guide": {"guide": 18},
    "reference": {"article": 18},
    "entity": {
        "achievement": 12,
        "currency": 12,
        "faction": 10,
        "item": 16,
        "npc": 16,
        "object": 10,
        "quest": 18,
        "recipe": 12,
        "spell": 18,
        "zone": 10,
    },
    "guild_profile": {"guild": 24, "leaderboard": 18},
    "character_profile": {"character": 24, "mythic_plus_runs": 12},
    "structured_profile": {"guild": 20, "character": 20},
    "simc": {
        "analysis": 16,
        "apl": 20,
        "decode_build": 18,
        "inspect": 12,
        "run": 10,
    },
}

PROVIDER_KIND_BOOSTS: dict[str, dict[str, int]] = {
    "wowhead": {"guide": 4, "item": 4, "npc": 4, "quest": 6, "spell": 6},
    "method": {"guide": 6},
    "icy-veins": {"guide": 6},
    "raiderio": {"character": 8, "guild": 8, "mythic_plus_runs": 6},
    "warcraft-wiki": {"article": 8},
    "wowprogress": {"character": 8, "guild": 10, "leaderboard": 8},
    "simc": {"analysis": 8, "apl": 10, "decode_build": 10, "inspect": 8, "run": 8},
}

TYPE_NAME_KIND_MAP = {
    "article": "article",
    "guide": "guide",
    "character": "character",
    "guild": "guild",
    "leaderboard": "leaderboard",
}


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


def _query_tokens(query: str) -> tuple[str, set[str]]:
    normalized = query.strip().lower()
    tokens = set(re.findall(r"[a-z0-9+]+", normalized))
    if "m+" in normalized:
        tokens.add("m+")
    if "mythic+" in normalized:
        tokens.add("mythic+")
    return normalized, tokens


def query_intents(query: str) -> list[str]:
    normalized, tokens = _query_tokens(query)
    intents: set[str] = set()
    for intent, keywords in INTENT_KEYWORDS.items():
        if tokens & keywords:
            intents.add(intent)
    ordered_tokens = [token for token in normalized.split() if token]
    if len(ordered_tokens) >= 3 and ordered_tokens[0] in KNOWN_REGION_TERMS:
        intents.add("structured_profile")
    if {"guild", "character"} & tokens:
        intents.add("structured_profile")
    return sorted(intents)


def candidate_kind(candidate: Mapping[str, Any] | None) -> str | None:
    if not isinstance(candidate, Mapping):
        return None
    for key in ("kind", "entity_type"):
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower().replace(" ", "_")
    follow_up = candidate.get("follow_up")
    if isinstance(follow_up, Mapping):
        for key in ("surface", "recommended_surface"):
            value = follow_up.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower().replace(" ", "_")
    type_name = candidate.get("type_name")
    if isinstance(type_name, str):
        normalized = type_name.strip().lower()
        return TYPE_NAME_KIND_MAP.get(normalized, normalized.replace(" ", "_")) if normalized else None
    return None


def wrapper_search_ranking(query: str, row: Mapping[str, Any]) -> dict[str, Any]:
    provider = str(row.get("provider") or "").strip()
    family = PROVIDER_FAMILIES.get(provider, "unknown")
    kind = candidate_kind(row)
    score = candidate_score(row)
    reasons: list[str] = [f"provider_score:{score}"]
    intents = query_intents(query)
    for intent in intents:
        family_boost = INTENT_FAMILY_BOOSTS.get(intent, {}).get(family, 0)
        if family_boost:
            score += family_boost
            reasons.append(f"intent:{intent}:family:{family}:{family_boost:+d}")
        if kind:
            kind_boost = INTENT_KIND_BOOSTS.get(intent, {}).get(kind, 0)
            if kind_boost:
                score += kind_boost
                reasons.append(f"intent:{intent}:kind:{kind}:{kind_boost:+d}")
    if kind:
        provider_kind_boost = PROVIDER_KIND_BOOSTS.get(provider, {}).get(kind, 0)
        if provider_kind_boost:
            score += provider_kind_boost
            reasons.append(f"provider_kind:{provider}:{kind}:{provider_kind_boost:+d}")
    return {
        "score": score,
        "reasons": reasons,
        "intents": intents,
        "provider_family": family,
        "kind": kind,
        "provider_score": candidate_score(row),
    }


def decorate_search_result(query: str, row: Mapping[str, Any]) -> dict[str, Any]:
    decorated = dict(row)
    decorated["wrapper_ranking"] = wrapper_search_ranking(query, row)
    return decorated


def search_result_sort_key(row: Mapping[str, Any]) -> tuple[int, int, str, str, str]:
    wrapper = row.get("wrapper_ranking")
    if isinstance(wrapper, Mapping):
        try:
            wrapper_score = int(wrapper.get("score") or 0)
        except (TypeError, ValueError):
            wrapper_score = 0
    else:
        wrapper_score = candidate_score(row)
    score = candidate_score(row)
    provider = str(row.get("provider") or "")
    name = str(row.get("name") or "")
    identifier = str(row.get("id") or "")
    return (-wrapper_score, -score, provider, name, identifier)


def decorate_resolve_payload(query: str, provider: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    decorated = dict(payload)
    match = payload.get("match")
    if isinstance(match, Mapping):
        decorated_match = decorate_search_result(query, {"provider": provider, **dict(match)})
        decorated["match"] = decorated_match
        decorated["wrapper_ranking"] = decorated_match["wrapper_ranking"]
    return decorated


def resolve_payload_sort_key(provider: str, payload: Mapping[str, Any]) -> tuple[int, int, int, int, str]:
    resolved = 1 if payload.get("resolved") else 0
    confidence = confidence_rank(payload.get("confidence"))
    wrapper = payload.get("wrapper_ranking")
    if isinstance(wrapper, Mapping):
        try:
            wrapper_score = int(wrapper.get("score") or 0)
        except (TypeError, ValueError):
            wrapper_score = 0
    else:
        wrapper_score = 0
    match = payload.get("match")
    score = candidate_score(match if isinstance(match, Mapping) else None)
    return (-resolved, -confidence, -wrapper_score, -score, provider)
