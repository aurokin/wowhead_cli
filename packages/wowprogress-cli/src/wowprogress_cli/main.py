from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import shlex
import re
from statistics import median
from typing import Any

import typer

from warcraft_core.output import emit
from wowprogress_cli.client import DEFAULT_IMPERSONATE, WowProgressClient, WowProgressClientError, load_wowprogress_cache_settings_from_env

app = typer.Typer(add_completion=False, help="WowProgress rankings and profile CLI.")
sample_app = typer.Typer(add_completion=False, help="Sample-backed WowProgress analytics primitives.")
distribution_app = typer.Typer(add_completion=False, help="Derived distributions built from WowProgress samples.")
threshold_app = typer.Typer(add_completion=False, help="Threshold-style estimates derived from sampled WowProgress leaderboard rows.")
app.add_typer(sample_app, name="sample")
app.add_typer(distribution_app, name="distribution")
app.add_typer(threshold_app, name="threshold")

EXCLUDED_QUERY_TERMS = frozenset(
    {
        "recruit",
        "recruiting",
        "recruitment",
        "apply",
        "application",
        "applications",
        "roster",
        "progression",
    }
)


@dataclass(slots=True)
class RuntimeConfig:
    pretty: bool = False


def _cfg(ctx: typer.Context) -> RuntimeConfig:
    obj = ctx.obj
    if isinstance(obj, RuntimeConfig):
        return obj
    return RuntimeConfig()


def _emit(ctx: typer.Context, payload: dict[str, Any], *, err: bool = False) -> None:
    emit(payload, pretty=_cfg(ctx).pretty, err=err)


def _fail(ctx: typer.Context, code: str, message: str, *, status: int = 1) -> None:
    _emit(ctx, {"ok": False, "error": {"code": code, "message": message}}, err=True)
    raise typer.Exit(status)


def _client(ctx: typer.Context) -> WowProgressClient:
    try:
        return WowProgressClient()
    except ValueError as exc:
        _fail(ctx, "invalid_cache_config", str(exc))
        raise AssertionError("unreachable")


def _handle_client_error(ctx: typer.Context, exc: WowProgressClientError) -> None:
    _fail(ctx, exc.code, exc.message)


def _shell(value: str) -> str:
    return shlex.quote(value)


def _structured_search_hint(query: str) -> dict[str, Any]:
    return {
        "provider": "wowprogress",
        "query": query,
        "search_query": query,
        "count": 0,
        "results": [],
        "truncated": False,
        "message": "WowProgress search expects structured queries like 'us illidan Liquid', 'guild us illidan Liquid', or 'character us illidan Imonthegcd'.",
        "suggested_queries": [
            "us illidan Liquid",
            "guild us illidan Liquid",
            "character us illidan Imonthegcd",
        ],
    }


def _query_tokens(query: str) -> list[str]:
    return [token for token in query.strip().split() if token]


def _strip_excluded_terms(tokens: list[str]) -> tuple[list[str], list[str]]:
    kept = list(tokens)
    excluded: list[str] = []
    while kept and kept[-1].lower() in EXCLUDED_QUERY_TERMS:
        excluded.insert(0, kept.pop())
    return kept, excluded


def _normalize_realm_candidate(value: str) -> str:
    return value.strip().replace(" ", "-")


def _structured_candidates(tokens: list[str]) -> list[tuple[str, str]]:
    if len(tokens) < 3:
        return []
    trailing = tokens[1:]
    candidates: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for split_index in range(len(trailing) - 1, 0, -1):
        realm = _normalize_realm_candidate(" ".join(trailing[:split_index]))
        name = " ".join(trailing[split_index:]).strip()
        candidate = (realm, name)
        if realm and name and candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)
    return candidates


def _normalize_structured_query(query: str) -> tuple[str, str | None, str | None, list[tuple[str, str]], list[str]]:
    tokens = _query_tokens(query)
    kind: str | None = None
    kept: list[str] = []
    for token in tokens:
        lower = token.lower()
        if kind is None and lower in {"guild", "guilds"}:
            kind = "guild"
            continue
        if kind is None and lower in {"character", "characters", "char"}:
            kind = "character"
            continue
        kept.append(token)
    kept, excluded_terms = _strip_excluded_terms(kept)
    if len(kept) < 3:
        normalized = " ".join(kept).strip() or query.strip()
        return normalized, kind, None, [], excluded_terms
    region = kept[0].lower()
    candidates = _structured_candidates(kept)
    if not candidates:
        normalized = " ".join(kept).strip()
        return normalized, kind, region, [], excluded_terms
    primary_realm, primary_name = candidates[0]
    normalized = " ".join(part for part in ([kind] if kind else []) + [region, primary_realm, primary_name]).strip()
    return normalized, kind, region, candidates, excluded_terms


def _normalized_token_text(value: str) -> str:
    lowered = value.strip().lower()
    parts = [part for part in re.split(r"[^a-z0-9]+", lowered) if part]
    return " ".join(parts)


def _normalized_realm_matches(query_realm: str, resolved_realm: str) -> bool:
    if not query_realm or not resolved_realm:
        return False
    if query_realm == resolved_realm:
        return True
    return resolved_realm.endswith(f" {query_realm}") or query_realm.endswith(f" {resolved_realm}")


def _score_match(
    *,
    query: str,
    kind_hint: str | None,
    kind: str,
    name: str,
    region: str,
    realm: str,
    query_name: str,
    query_realm: str,
) -> tuple[int, list[str]]:
    lowered_query = query.lower()
    name_lower = name.lower()
    combined = " ".join((name, realm, region)).lower()
    normalized_name = _normalized_token_text(name)
    normalized_query_name = _normalized_token_text(query_name)
    normalized_realm = _normalized_token_text(realm)
    normalized_query_realm = _normalized_token_text(query_realm)
    score = 0
    reasons: list[str] = ["route_resolved"]
    if normalized_query_name and normalized_query_name == normalized_name:
        score += 35
        reasons.append("exact_target_name")
    if lowered_query == name_lower:
        score += 50
        reasons.append("exact_name")
    elif lowered_query in name_lower:
        score += 20
        reasons.append("name_contains_query")
    if _normalized_realm_matches(normalized_query_realm, normalized_realm):
        score += 15
        reasons.append("exact_target_realm")
    terms = [part for part in lowered_query.split() if part]
    if terms and all(term in combined for term in terms):
        score += 20
        reasons.append("all_terms_match")
    if any(term == region.lower() for term in terms):
        score += 10
        reasons.append("region_match")
    if any(term == realm.lower() for term in terms):
        score += 10
        reasons.append("realm_match")
    if kind_hint and kind_hint == kind:
        score += 15
        reasons.append("type_hint")
    score += 10
    return score, reasons


def _follow_up(kind: str, region: str, realm: str, name: str) -> dict[str, Any]:
    command = f"wowprogress {kind} {_shell(region)} {_shell(realm)} {_shell(name)}"
    return {
        "provider": "wowprogress",
        "kind": kind,
        "surface": kind,
        "command": command,
    }


def _count_map(values: list[str]) -> list[dict[str, Any]]:
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


def _progress_snapshot(value: str | None) -> dict[str, Any]:
    text = str(value or "").strip()
    match = re.match(r"(?P<killed>\d+)/(?P<total>\d+)(?:\s*\((?P<difficulty>[^)]+)\))?$", text)
    if match is None:
        return {
            "summary": text or None,
            "bosses_killed": None,
            "boss_count": None,
            "difficulty": None,
        }
    return {
        "summary": text,
        "bosses_killed": int(match.group("killed")),
        "boss_count": int(match.group("total")),
        "difficulty": match.group("difficulty"),
    }


def _leaderboard_entry_snapshot(entry: dict[str, Any]) -> dict[str, Any]:
    progress = _progress_snapshot(entry.get("progress"))
    return {
        "rank": entry.get("rank"),
        "guild_name": entry.get("guild_name"),
        "guild_url": entry.get("guild_url"),
        "realm": entry.get("realm"),
        "realm_url": entry.get("realm_url"),
        "progress": progress["summary"],
        "bosses_killed": progress["bosses_killed"],
        "boss_count": progress["boss_count"],
        "difficulty": progress["difficulty"],
    }


def _sample_pve_leaderboard(
    client: WowProgressClient,
    *,
    region: str,
    realm: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    payload = client.fetch_pve_leaderboard(region=region, realm=realm, limit=limit)
    entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []
    snapshots = [_leaderboard_entry_snapshot(entry) for entry in entries if isinstance(entry, dict)]
    leaderboard = payload.get("leaderboard") if isinstance(payload.get("leaderboard"), dict) else {}
    meta = {
        "sampled_at": datetime.now(timezone.utc).isoformat(),
        "cache_ttl_seconds": client.pve_leaderboard_ttl_seconds,
        "page_url": str((payload.get("citations") or {}).get("page") or leaderboard.get("page_url") or ""),
        "active_raid": leaderboard.get("active_raid"),
        "region": leaderboard.get("region") or region.lower(),
        "realm": leaderboard.get("realm"),
        "title": leaderboard.get("title"),
        "requested_limit": limit,
        "leaderboard_entry_count": len(snapshots),
    }
    return snapshots, meta, leaderboard


def _guild_profile_snapshot(*, leaderboard_entry: dict[str, Any], guild_payload: dict[str, Any]) -> dict[str, Any]:
    guild = guild_payload.get("guild") if isinstance(guild_payload.get("guild"), dict) else {}
    progress = guild_payload.get("progress") if isinstance(guild_payload.get("progress"), dict) else {}
    item_level = guild_payload.get("item_level") if isinstance(guild_payload.get("item_level"), dict) else {}
    encounters = guild_payload.get("encounters") if isinstance(guild_payload.get("encounters"), dict) else {}
    items = encounters.get("items") if isinstance(encounters.get("items"), list) else []
    return {
        "leaderboard_rank": leaderboard_entry.get("rank"),
        "guild_name": guild.get("name") or leaderboard_entry.get("guild_name"),
        "region": guild.get("region"),
        "realm": guild.get("realm") or leaderboard_entry.get("realm"),
        "faction": guild.get("faction"),
        "profile_url": guild.get("page_url") or leaderboard_entry.get("guild_url"),
        "armory_url": guild.get("armory_url"),
        "progress": progress.get("summary"),
        "bosses_killed": _progress_snapshot(progress.get("summary")).get("bosses_killed"),
        "boss_count": _progress_snapshot(progress.get("summary")).get("boss_count"),
        "difficulty": _progress_snapshot(progress.get("summary")).get("difficulty"),
        "progress_ranks": progress.get("ranks"),
        "item_level_average": item_level.get("average"),
        "item_level_group_size": item_level.get("group_size"),
        "item_level_ranks": item_level.get("ranks"),
        "encounter_count": encounters.get("count"),
        "encounters": [
            {
                "encounter": item.get("encounter"),
                "difficulty": item.get("difficulty"),
                "world_rank": item.get("world_rank"),
                "region_rank": item.get("region_rank"),
                "realm_rank": item.get("realm_rank"),
                "first_kill_at": item.get("first_kill_at"),
            }
            for item in items[:10]
            if isinstance(item, dict)
        ],
    }


def _sampled_pve_guild_profiles(
    client: WowProgressClient,
    *,
    region: str,
    realm: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    entries, meta, leaderboard = _sample_pve_leaderboard(client, region=region, realm=realm, limit=limit)
    guild_profiles: list[dict[str, Any]] = []
    skipped_missing_profile_url = 0
    for entry in entries:
        guild_url = str(entry.get("guild_url") or "").strip()
        if not guild_url:
            skipped_missing_profile_url += 1
            continue
        payload = client.fetch_guild_page_url(guild_url)
        guild_profiles.append(_guild_profile_snapshot(leaderboard_entry=entry, guild_payload=payload))
    meta = {
        **meta,
        "guild_profile_count": len(guild_profiles),
        "skipped_missing_profile_url": skipped_missing_profile_url,
    }
    return guild_profiles, meta, leaderboard


def _sample_summary(entries: list[dict[str, Any]], *, meta: dict[str, Any]) -> dict[str, Any]:
    rank_values = [int(entry["rank"]) for entry in entries if isinstance(entry.get("rank"), int)]
    killed_values = [int(entry["bosses_killed"]) for entry in entries if isinstance(entry.get("bosses_killed"), int)]
    rank_stats: dict[str, Any] | None = None
    if rank_values:
        sorted_ranks = sorted(rank_values)
        rank_stats = {
            "min": sorted_ranks[0],
            "max": sorted_ranks[-1],
            "average": round(sum(sorted_ranks) / len(sorted_ranks), 2),
            "median": median(sorted_ranks),
        }
    progress_stats: dict[str, Any] | None = None
    if killed_values:
        sorted_kills = sorted(killed_values)
        progress_stats = {
            "min": sorted_kills[0],
            "max": sorted_kills[-1],
            "average": round(sum(sorted_kills) / len(sorted_kills), 2),
            "median": median(sorted_kills),
        }
    return {
        "sampled_at": meta["sampled_at"],
        "entry_count": len(entries),
        "sampling": {
            "requested_limit": meta.get("requested_limit"),
            "returned_entry_count": len(entries),
            "source_scope": "top leaderboard rows fetched from the requested WowProgress leaderboard page",
        },
        "active_raid": meta.get("active_raid"),
        "unique_realms": sorted({str(entry.get("realm") or "") for entry in entries if str(entry.get("realm") or "").strip()}),
        "difficulty_counts": _count_map([str(entry.get("difficulty") or "unknown") for entry in entries]),
        "rank": rank_stats,
        "bosses_killed": progress_stats,
    }


def _guild_profile_sample_summary(entries: list[dict[str, Any]], *, meta: dict[str, Any], filtering: dict[str, Any] | None = None) -> dict[str, Any]:
    item_levels = [float(entry["item_level_average"]) for entry in entries if isinstance(entry.get("item_level_average"), (int, float))]
    world_ranks = [
        int(str((entry.get("progress_ranks") or {}).get("world")).replace(",", ""))
        for entry in entries
        if isinstance(entry.get("progress_ranks"), dict)
        and str((entry.get("progress_ranks") or {}).get("world") or "").replace(",", "").isdigit()
    ]
    return {
        "sampled_at": meta["sampled_at"],
        "guild_profile_count": len(entries),
        "sampling": {
            "requested_limit": meta.get("requested_limit"),
            "source_leaderboard_entry_count": meta.get("leaderboard_entry_count"),
            "returned_guild_profile_count": len(entries),
            "skipped_missing_profile_url": meta.get("skipped_missing_profile_url", 0),
            "source_scope": "top leaderboard rows enriched with direct WowProgress guild pages when a profile URL is present",
        },
        "filtering": filtering,
        "active_raid": meta.get("active_raid"),
        "faction_counts": _count_map([str(entry.get("faction") or "unknown") for entry in entries]),
        "progress_counts": _count_map([str(entry.get("progress") or "unknown") for entry in entries]),
        "difficulty_counts": _count_map([str(entry.get("difficulty") or "unknown") for entry in entries]),
        "item_level_average": _numeric_summary(item_levels),
        "world_progress_rank": _numeric_summary(world_ranks),
    }


def _normalize_slug_filters(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        parts = [part for part in re.split(r"[^a-z0-9]+", value.strip().lower()) if part]
        cleaned = "-".join(parts)
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _metric_within_bounds(value: Any, *, minimum: float | None, maximum: float | None) -> bool:
    if not isinstance(value, (int, float)):
        return True
    numeric_value = float(value)
    if minimum is not None and numeric_value < minimum:
        return False
    if maximum is not None and numeric_value > maximum:
        return False
    return True


def _normalized_encounter_values(entry: dict[str, Any]) -> set[str]:
    return {
        "-".join(part for part in re.split(r"[^a-z0-9]+", str(row.get("encounter") or "").strip().lower()) if part)
        for row in (entry.get("encounters") if isinstance(entry.get("encounters"), list) else [])
        if isinstance(row, dict)
    }


def _categorical_distribution(values: list[str], *, unit: str) -> dict[str, Any]:
    return {
        "unit": unit,
        "rows": _count_map(values),
        "statistics": None,
    }


def _numeric_distribution(values: list[int | float], *, unit: str) -> dict[str, Any]:
    rows = _count_map([str(value) for value in values])
    return {
        "unit": unit,
        "rows": rows,
        "statistics": _numeric_summary(values),
    }


def _numeric_summary(values: list[int | float]) -> dict[str, Any] | None:
    if not values:
        return None
    sorted_values = sorted(values)
    return {
        "min": sorted_values[0],
        "max": sorted_values[-1],
        "average": round(sum(sorted_values) / len(sorted_values), 2),
        "median": median(sorted_values),
    }


def _freshness_payload(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "sampled_at": meta["sampled_at"],
        "cache_ttl_seconds": meta["cache_ttl_seconds"],
    }


def _citations_payload(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "leaderboard_page": meta["page_url"],
    }


def _distribution_response(
    *,
    kind: str,
    metric: str,
    query: dict[str, Any],
    sample: dict[str, Any],
    distribution: dict[str, Any],
    meta: dict[str, Any],
) -> dict[str, Any]:
    return {
        "provider": "wowprogress",
        "kind": kind,
        "metric": metric,
        "query": query,
        "sample": sample,
        "distribution": distribution,
        "freshness": _freshness_payload(meta),
        "citations": _citations_payload(meta),
    }


def _world_rank_value(entry: dict[str, Any]) -> int | None:
    progress_ranks = entry.get("progress_ranks") if isinstance(entry.get("progress_ranks"), dict) else {}
    raw = progress_ranks.get("world")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        cleaned = raw.replace(",", "")
        if cleaned.isdigit():
            return int(cleaned)
    return None


def _guild_profile_matches_filters(
    entry: dict[str, Any],
    *,
    faction: list[str],
    difficulty: list[str],
    world_rank_min: int | None,
    world_rank_max: int | None,
    item_level_min: float | None,
    item_level_max: float | None,
    encounter: list[str],
) -> bool:
    faction_value = str(entry.get("faction") or "").strip().lower().replace(" ", "-")
    if faction and faction_value not in faction:
        return False

    difficulty_value = str(entry.get("difficulty") or "").strip().lower().replace(" ", "-")
    if difficulty and difficulty_value not in difficulty:
        return False

    world_rank = _world_rank_value(entry)
    if not _metric_within_bounds(world_rank, minimum=world_rank_min, maximum=world_rank_max):
        return False

    if not _metric_within_bounds(entry.get("item_level_average"), minimum=item_level_min, maximum=item_level_max):
        return False

    if encounter and not any(value in _normalized_encounter_values(entry) for value in encounter):
        return False
    return True


def _filter_guild_profiles(
    entries: list[dict[str, Any]],
    *,
    faction: list[str] | None,
    difficulty: list[str] | None,
    world_rank_min: int | None,
    world_rank_max: int | None,
    item_level_min: float | None,
    item_level_max: float | None,
    encounter: list[str] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized_faction = _normalize_slug_filters(faction)
    normalized_difficulty = _normalize_slug_filters(difficulty)
    normalized_encounter = _normalize_slug_filters(encounter)
    filtered = [
        entry
        for entry in entries
        if _guild_profile_matches_filters(
            entry,
            faction=normalized_faction,
            difficulty=normalized_difficulty,
            world_rank_min=world_rank_min,
            world_rank_max=world_rank_max,
            item_level_min=item_level_min,
            item_level_max=item_level_max,
            encounter=normalized_encounter,
        )
    ]
    return filtered, {
        "faction": normalized_faction,
        "difficulty": normalized_difficulty,
        "world_rank_min": world_rank_min,
        "world_rank_max": world_rank_max,
        "item_level_min": item_level_min,
        "item_level_max": item_level_max,
        "encounter": normalized_encounter,
        "source_profile_count": len(entries),
        "returned_profile_count": len(filtered),
        "excluded_profile_count": len(entries) - len(filtered),
    }


def _distribution_payload(metric: str, entries: list[dict[str, Any]], *, meta: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    sample = _sample_summary(entries, meta=meta)
    if metric == "rank":
        values = [int(entry["rank"]) for entry in entries if isinstance(entry.get("rank"), int)]
        distribution = _numeric_distribution(values, unit="entries")
    else:
        if metric == "realm":
            values = [str(entry.get("realm") or "unknown") for entry in entries]
        elif metric == "difficulty":
            values = [str(entry.get("difficulty") or "unknown") for entry in entries]
        elif metric == "bosses_killed":
            values = [str(entry.get("bosses_killed")) for entry in entries if isinstance(entry.get("bosses_killed"), int)]
        else:
            values = [str(entry.get("progress") or "unknown") for entry in entries]
        distribution = _categorical_distribution(values, unit="entries")
    return _distribution_response(
        kind="pve_leaderboard_distribution",
        metric=metric,
        query=query,
        sample=sample,
        distribution=distribution,
        meta=meta,
    )


def _guild_profile_categorical_distribution_values(metric: str, entries: list[dict[str, Any]]) -> tuple[list[str], str] | None:
    if metric == "faction":
        return [str(entry.get("faction") or "unknown") for entry in entries], "guild_profiles"
    if metric == "progress":
        return [str(entry.get("progress") or "unknown") for entry in entries], "guild_profiles"
    if metric == "encounter":
        return [
            str(encounter.get("encounter") or "unknown")
            for entry in entries
            for encounter in (entry.get("encounters") if isinstance(entry.get("encounters"), list) else [])
            if isinstance(encounter, dict)
        ], "encounters"
    return None


def _guild_profile_numeric_distribution_values(metric: str, entries: list[dict[str, Any]]) -> tuple[list[int] | list[float], str] | None:
    if metric == "world_rank":
        return [
            int(str((entry.get("progress_ranks") or {}).get("world")).replace(",", ""))
            for entry in entries
            if isinstance(entry.get("progress_ranks"), dict)
            and (entry.get("progress_ranks") or {}).get("world") is not None
            and str((entry.get("progress_ranks") or {}).get("world")).replace(",", "").isdigit()
        ], "guild_profiles"
    return [
        float(entry["item_level_average"])
        for entry in entries
        if isinstance(entry.get("item_level_average"), (int, float))
    ], "guild_profiles"


def _guild_profile_distribution_values(metric: str, entries: list[dict[str, Any]]) -> tuple[list[str] | list[int] | list[float], str, bool]:
    categorical = _guild_profile_categorical_distribution_values(metric, entries)
    if categorical is not None:
        values, unit = categorical
        return values, unit, False
    numeric = _guild_profile_numeric_distribution_values(metric, entries)
    values, unit = numeric if numeric is not None else ([], "guild_profiles")
    return values, unit, True


def _guild_profile_distribution_payload(metric: str, entries: list[dict[str, Any]], *, meta: dict[str, Any], query: dict[str, Any], filtering: dict[str, Any] | None = None) -> dict[str, Any]:
    sample = _guild_profile_sample_summary(entries, meta=meta, filtering=filtering)
    values, unit, numeric = _guild_profile_distribution_values(metric, entries)
    distribution = (
        _numeric_distribution(values, unit=unit)  # type: ignore[arg-type]
        if numeric
        else _categorical_distribution(values, unit=unit)  # type: ignore[arg-type]
    )
    return _distribution_response(
        kind="pve_guild_profiles_distribution",
        metric=metric,
        query=query,
        sample=sample,
        distribution=distribution,
        meta=meta,
    )


def _nearest_guild_profile_rows(metric: str, target: float, entries: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        if metric == "item_level_average":
            raw_value = entry.get("item_level_average")
        else:
            raw_value = (entry.get("progress_ranks") or {}).get("world") if isinstance(entry.get("progress_ranks"), dict) else None
            if isinstance(raw_value, str):
                raw_value = int(raw_value.replace(",", "")) if raw_value.replace(",", "").isdigit() else None
        if not isinstance(raw_value, (int, float)):
            continue
        rows.append(
            {
                "value": float(raw_value),
                "distance": round(abs(float(raw_value) - target), 3),
                "entry": entry,
            }
        )
    rows.sort(key=lambda row: (float(row["distance"]), str((row["entry"] or {}).get("guild_name") or "")))
    return rows[:limit]


def _guild_profile_threshold_estimate(metric: str, nearest: list[dict[str, Any]]) -> tuple[str, list[int] | list[float], str]:
    if metric == "item_level_average":
        return (
            "world_rank",
            [
                int(str((row["entry"].get("progress_ranks") or {}).get("world")).replace(",", ""))
                for row in nearest
                if isinstance(row["entry"].get("progress_ranks"), dict)
                and str((row["entry"].get("progress_ranks") or {}).get("world") or "").replace(",", "").isdigit()
            ],
            "This estimates sampled world-progress ranks near a target item-level average for leaderboard guilds in the active raid.",
        )
    return (
        "item_level_average",
        [float(row["entry"]["item_level_average"]) for row in nearest if isinstance(row["entry"].get("item_level_average"), (int, float))],
        "This estimates sampled guild item-level averages near a target world-progress rank for the active raid.",
    )


def _guild_profile_threshold_payload(
    metric: str,
    target: float,
    entries: list[dict[str, Any]],
    *,
    meta: dict[str, Any],
    query: dict[str, Any],
    nearest_limit: int,
    filtering: dict[str, Any] | None = None,
) -> dict[str, Any]:
    nearest = _nearest_guild_profile_rows(metric, target, entries, limit=nearest_limit)
    estimate_metric, estimate_values, caveat = _guild_profile_threshold_estimate(metric, nearest)
    estimate = None
    if estimate_values:
        sorted_values = sorted(estimate_values)
        estimate = {
            "metric": estimate_metric,
            "count": len(sorted_values),
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "average": round(sum(sorted_values) / len(sorted_values), 2),
            "median": median(sorted_values),
        }
    return {
        "provider": "wowprogress",
        "kind": "pve_guild_profiles_threshold",
        "metric": metric,
        "target": target,
        "query": query,
        "sample": _guild_profile_sample_summary(entries, meta=meta, filtering=filtering),
        "threshold": {
            "nearest_match_count": len(nearest),
            "nearest_matches": [
                {
                    "value": row["value"],
                    "distance": row["distance"],
                    "entry": row["entry"],
                }
                for row in nearest
            ],
            "estimate": estimate,
            "caveat": caveat,
        },
        "freshness": _freshness_payload(meta),
        "citations": _citations_payload(meta),
    }


def _nearest_threshold_rows(metric: str, target: float, entries: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        if metric == "rank":
            raw_value = entry.get("rank")
        else:
            raw_value = entry.get("bosses_killed")
        if not isinstance(raw_value, (int, float)):
            continue
        rows.append(
            {
                "value": float(raw_value),
                "distance": round(abs(float(raw_value) - target), 3),
                "entry": entry,
            }
        )
    rows.sort(
        key=lambda row: (
            float(row["distance"]),
            float(row["value"]),
            str((row["entry"] or {}).get("guild_name") or ""),
        )
    )
    return rows[:limit]


def _threshold_payload(metric: str, target: float, entries: list[dict[str, Any]], *, meta: dict[str, Any], query: dict[str, Any], nearest_limit: int) -> dict[str, Any]:
    nearest = _nearest_threshold_rows(metric, target, entries, limit=nearest_limit)
    if metric == "rank":
        estimate_metric = "bosses_killed"
        estimate_values = [int(row["entry"]["bosses_killed"]) for row in nearest if isinstance(row["entry"].get("bosses_killed"), int)]
        caveat = "This estimates raid-progression states near a sampled WowProgress leaderboard rank, not a universal guild-performance threshold."
    else:
        estimate_metric = "rank"
        estimate_values = [int(row["entry"]["rank"]) for row in nearest if isinstance(row["entry"].get("rank"), int)]
        caveat = "This estimates leaderboard-rank ranges near a sampled boss-kill count for the active raid."
    estimate = None
    if estimate_values:
        sorted_values = sorted(estimate_values)
        estimate = {
            "metric": estimate_metric,
            "count": len(sorted_values),
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "average": round(sum(sorted_values) / len(sorted_values), 2),
            "median": median(sorted_values),
        }
    return {
        "provider": "wowprogress",
        "kind": "pve_leaderboard_threshold",
        "metric": metric,
        "target": target,
        "query": query,
        "sample": _sample_summary(entries, meta=meta),
        "threshold": {
            "nearest_match_count": len(nearest),
            "nearest_matches": [
                {
                    "value": row["value"],
                    "distance": row["distance"],
                    "entry": row["entry"],
                }
                for row in nearest
            ],
            "estimate": estimate,
            "caveat": caveat,
        },
        "freshness": _freshness_payload(meta),
        "citations": _citations_payload(meta),
    }


def _load_pve_leaderboard_sample(
    client: WowProgressClient,
    *,
    region: str,
    realm: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    entries, meta, leaderboard = _sample_pve_leaderboard(client, region=region, realm=realm, limit=limit)
    query = {
        "region": region.lower(),
        "realm": realm.lower() if realm else None,
        "limit": limit,
    }
    return entries, meta, leaderboard, query


def _load_pve_guild_profile_sample(
    client: WowProgressClient,
    *,
    region: str,
    realm: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    entries, meta, leaderboard = _sampled_pve_guild_profiles(client, region=region, realm=realm, limit=limit)
    query = {
        "region": region.lower(),
        "realm": realm.lower() if realm else None,
        "limit": limit,
    }
    return entries, meta, leaderboard, query


def _candidate_from_probe(
    query: str,
    *,
    kind_hint: str | None,
    payload: dict[str, Any],
    query_region: str,
    query_realm: str,
    query_name: str,
) -> dict[str, Any]:
    search_kind = str(payload.get("_search_kind") or "").strip().lower()
    if search_kind == "character":
        return _character_candidate_from_probe(
            query=query,
            kind_hint=kind_hint,
            payload=payload,
            query_region=query_region,
            query_realm=query_realm,
            query_name=query_name,
        )
    return _guild_candidate_from_probe(
        query=query,
        kind_hint=kind_hint,
        payload=payload,
        query_region=query_region,
        query_realm=query_realm,
        query_name=query_name,
    )


def _character_candidate_from_probe(
    *,
    query: str,
    kind_hint: str | None,
    payload: dict[str, Any],
    query_region: str,
    query_realm: str,
    query_name: str,
) -> dict[str, Any]:
    character = payload.get("character") if isinstance(payload.get("character"), dict) else {}
    name = str(character.get("name") or "").strip()
    region = str(character.get("region") or "").strip()
    realm = str(character.get("realm") or "").strip()
    page_url = character.get("page_url")
    score, reasons = _score_match(
        query=query,
        kind_hint=kind_hint,
        kind="character",
        name=name,
        region=region,
        realm=realm,
        query_name=query_name,
        query_realm=query_realm,
    )
    return {
        "provider": "wowprogress",
        "kind": "character",
        "id": page_url or f"character:{region}:{realm}:{name}",
        "name": name,
        "region": region,
        "realm": realm,
        "guild_name": character.get("guild_name"),
        "class_name": character.get("class_name"),
        "race": character.get("race"),
        "level": character.get("level"),
        "profile_url": page_url,
        "ranking": {"score": score, "match_reasons": reasons},
        "follow_up": _follow_up("character", query_region, query_realm, query_name),
    }


def _guild_candidate_from_probe(
    *,
    query: str,
    kind_hint: str | None,
    payload: dict[str, Any],
    query_region: str,
    query_realm: str,
    query_name: str,
) -> dict[str, Any]:
    guild = payload.get("guild") if isinstance(payload.get("guild"), dict) else {}
    name = str(guild.get("name") or "").strip()
    region = str(guild.get("region") or "").strip()
    realm = str(guild.get("realm") or "").strip()
    page_url = guild.get("page_url")
    score, reasons = _score_match(
        query=query,
        kind_hint=kind_hint,
        kind="guild",
        name=name,
        region=region,
        realm=realm,
        query_name=query_name,
        query_realm=query_realm,
    )
    return {
        "provider": "wowprogress",
        "kind": "guild",
        "id": page_url or f"guild:{region}:{realm}:{name}",
        "name": name,
        "region": region,
        "realm": realm,
        "faction": guild.get("faction"),
        "profile_url": page_url,
        "ranking": {"score": score, "match_reasons": reasons},
        "follow_up": _follow_up("guild", query_region, query_realm, query_name),
    }


def _search_payload(
    *,
    query: str,
    normalized_query: str,
    kind_hint: str | None,
    candidates: list[dict[str, Any]],
    limit: int,
    message: str | None = None,
) -> dict[str, Any]:
    sorted_rows = _sorted_search_candidates(candidates)
    return {
        "provider": "wowprogress",
        "query": query,
        "search_query": normalized_query,
        "query_kind": kind_hint,
        "count": len(sorted_rows),
        "results": sorted_rows[:limit],
        "truncated": len(sorted_rows) > limit,
        "message": message,
    }


def _candidate_score(candidate: dict[str, Any]) -> int:
    return int((((candidate.get("ranking") or {}).get("score")) or 0))


def _sorted_search_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        candidates,
        key=lambda item: (-_candidate_score(item), str(item.get("kind") or ""), str(item.get("name") or "")),
    )


def _distinct_result_kinds(results: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(item.get("kind") or "").strip().lower()
            for item in results
            if isinstance(item, dict) and str(item.get("kind") or "").strip()
        }
    )


def _resolve_is_confident(
    *,
    best: dict[str, Any] | None,
    second: dict[str, Any] | None,
    query_kind: str | None,
    distinct_kinds: list[str],
) -> bool:
    if best is None:
        return False
    if not _has_follow_up_command(best):
        return False
    best_score = _candidate_score(best)
    second_score = _candidate_score(second) if second is not None else 0
    if not _meets_score_confidence(best_score, second_score=second_score, has_second=second is not None):
        return False
    return not _is_ambiguous_untyped_result(query_kind, distinct_kinds)


def _resolve_confidence_label(best: dict[str, Any] | None, *, resolved: bool) -> str:
    if best is None:
        return "none"
    if resolved:
        return "high"
    if _candidate_score(best) >= 40:
        return "medium"
    return "low"


def _has_follow_up_command(candidate: dict[str, Any]) -> bool:
    follow_up = candidate.get("follow_up") if isinstance(candidate.get("follow_up"), dict) else {}
    return bool(follow_up.get("command"))


def _meets_score_confidence(best_score: int, *, second_score: int, has_second: bool) -> bool:
    return best_score >= 55 and (not has_second or best_score - second_score >= 15)


def _is_ambiguous_untyped_result(query_kind: str | None, distinct_kinds: list[str]) -> bool:
    return query_kind is None and len(distinct_kinds) > 1


def _resolve_payload(search_payload: dict[str, Any]) -> dict[str, Any]:
    results = search_payload.get("results")
    if not isinstance(results, list):
        results = []
    best = results[0] if results else None
    second = results[1] if len(results) > 1 else None
    query_kind = search_payload.get("query_kind")
    distinct_kinds = _distinct_result_kinds(results)
    follow_up = best.get("follow_up") if isinstance((best or {}).get("follow_up"), dict) else {}
    resolved = _resolve_is_confident(best=best, second=second, query_kind=query_kind, distinct_kinds=distinct_kinds)
    confidence = _resolve_confidence_label(best, resolved=resolved)
    return {
        "provider": "wowprogress",
        "query": search_payload.get("query"),
        "search_query": search_payload.get("search_query"),
        "query_kind": query_kind,
        "resolved": resolved,
        "confidence": confidence,
        "match": best,
        "next_command": follow_up.get("command") if resolved else None,
        "fallback_search_command": None if resolved else f'wowprogress search "{search_payload.get("search_query")}"',
        "candidates": results,
        "message": search_payload.get("message"),
    }


def _probe_search_candidates(
    *,
    client: WowProgressClient,
    kind_hint: str | None,
    region: str,
    query_candidates: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    probe_types = ["char", "guild"]
    if kind_hint == "character":
        probe_types = ["char"]
    elif kind_hint == "guild":
        probe_types = ["guild"]
    candidates: list[dict[str, Any]] = []
    for realm, name in query_candidates:
        match_query = " ".join(part for part in (region, realm, name) if part)
        split_results: list[dict[str, Any]] = []
        for probe_type in probe_types:
            payload = client.probe_search_route(region=region, realm=realm, name=name, obj_type=probe_type)
            if payload is None:
                continue
            split_results.append(
                _candidate_from_probe(
                    match_query,
                    kind_hint=kind_hint,
                    payload=payload,
                    query_region=region,
                    query_realm=realm,
                    query_name=name,
                )
            )
            if kind_hint is not None:
                break
        if split_results:
            candidates.extend(split_results)
            break
    return candidates


def _search_candidates(ctx: typer.Context, query: str, *, limit: int) -> dict[str, Any]:
    normalized_query, kind_hint, region, query_candidates, excluded_terms = _normalize_structured_query(query)
    if region is None or not query_candidates:
        payload = _structured_search_hint(query)
        if excluded_terms:
            payload["excluded_terms"] = excluded_terms
        return payload
    candidates: list[dict[str, Any]] = []
    try:
        with _client(ctx) as client:
            candidates = _probe_search_candidates(
                client=client,
                kind_hint=kind_hint,
                region=region,
                query_candidates=query_candidates,
            )
    except WowProgressClientError as exc:
        _handle_client_error(ctx, exc)
        raise AssertionError("unreachable")
    message = None if candidates else "WowProgress did not resolve that structured guild or character query."
    payload = _search_payload(
        query=query,
        normalized_query=normalized_query,
        kind_hint=kind_hint,
        candidates=candidates,
        limit=limit,
        message=message,
    )
    if excluded_terms:
        payload["excluded_terms"] = excluded_terms
        payload["normalization_hint"] = {
            "code": "excluded_query_terms",
            "message": "Trailing query terms were excluded to keep the WowProgress lookup on a supported structured guild or character route.",
        }
    if query_candidates:
        payload["normalized_candidates"] = [
            {
                "region": region,
                "realm": realm,
                "name": name,
            }
            for realm, name in query_candidates
        ]
    return payload


@app.callback()
def main_callback(
    ctx: typer.Context,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    ctx.obj = RuntimeConfig(pretty=pretty)


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    try:
        settings, guild_ttl, character_ttl, leaderboard_ttl = load_wowprogress_cache_settings_from_env()
    except ValueError as exc:
        _fail(ctx, "invalid_cache_config", str(exc))
        return
    _emit(
        ctx,
        {
            "provider": "wowprogress",
            "status": "ready",
            "command": "doctor",
            "installed": True,
            "language": "python",
            "auth": {
                "required": False,
                "deferred": True,
            },
            "transport": {
                "mode": "browser_fingerprint_http",
                "impersonate": DEFAULT_IMPERSONATE,
            },
            "capabilities": {
                "search": "ready",
                "resolve": "ready",
                "guild": "ready",
                "character": "ready",
                "leaderboard": "ready",
                "sample_pve_leaderboard": "ready",
                "distribution_pve_leaderboard": "ready",
                "threshold_pve_leaderboard": "ready",
                "sample_pve_guild_profiles": "ready",
                "distribution_pve_guild_profiles": "ready",
                "threshold_pve_guild_profiles": "ready",
            },
            "cache": {
                "enabled": settings.enabled,
                "backend": settings.backend,
                "cache_dir": str(settings.cache_dir),
                "redis_url": settings.redis_url,
                "prefix": settings.prefix,
                "ttls": {
                    "guild_page": guild_ttl,
                    "character_page": character_ttl,
                    "leaderboard_page": leaderboard_ttl,
                },
            },
        },
    )


@app.command("search")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Structured query like 'us illidan Liquid' or 'character us illidan Imonthegcd'."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum results to return."),
) -> None:
    _emit(ctx, _search_candidates(ctx, query, limit=limit))


@app.command("resolve")
def resolve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Structured query like 'guild us illidan Liquid' or 'us illidan Imonthegcd'."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum candidates to inspect."),
) -> None:
    _emit(ctx, _resolve_payload(_search_candidates(ctx, query, limit=limit)))


@app.command("guild")
def guild(
    ctx: typer.Context,
    region: str = typer.Argument(..., help="Region slug such as us or eu."),
    realm: str = typer.Argument(..., help="Realm slug or title."),
    name: str = typer.Argument(..., help="Guild name."),
) -> None:
    try:
        with _client(ctx) as client:
            payload = client.fetch_guild_page(region=region, realm=realm, name=name)
    except WowProgressClientError as exc:
        _handle_client_error(ctx, exc)
        return
    _emit(ctx, payload)


@app.command("character")
def character(
    ctx: typer.Context,
    region: str = typer.Argument(..., help="Region slug such as us or eu."),
    realm: str = typer.Argument(..., help="Realm slug or title."),
    name: str = typer.Argument(..., help="Character name."),
) -> None:
    try:
        with _client(ctx) as client:
            payload = client.fetch_character_page(region=region, realm=realm, name=name)
    except WowProgressClientError as exc:
        _handle_client_error(ctx, exc)
        return
    _emit(ctx, payload)


@app.command("leaderboard")
def leaderboard(
    ctx: typer.Context,
    kind: str = typer.Argument(..., help="Leaderboard kind. Phase 1 supports only 'pve'."),
    region: str = typer.Argument(..., help="Region slug such as world, us, or eu."),
    realm: str | None = typer.Option(None, "--realm", help="Optional realm slug to narrow the PvE leaderboard."),
    limit: int = typer.Option(25, "--limit", min=1, max=100, help="Maximum leaderboard rows to return."),
) -> None:
    if kind.lower() != "pve":
        _fail(ctx, "invalid_query", "WowProgress phase 1 supports only the 'pve' leaderboard.")
        return
    try:
        with _client(ctx) as client:
            payload = client.fetch_pve_leaderboard(region=region, realm=realm, limit=limit)
    except WowProgressClientError as exc:
        _handle_client_error(ctx, exc)
        return
    _emit(ctx, payload)


@sample_app.command("pve-leaderboard")
def sample_pve_leaderboard(
    ctx: typer.Context,
    region: str = typer.Option(..., "--region", help="Region slug such as world, us, or eu."),
    realm: str | None = typer.Option(None, "--realm", help="Optional realm slug to narrow the PvE leaderboard."),
    limit: int = typer.Option(25, "--limit", min=1, max=100, help="Maximum leaderboard rows to sample."),
) -> None:
    try:
        with _client(ctx) as client:
            entries, meta, leaderboard, query = _load_pve_leaderboard_sample(client, region=region, realm=realm, limit=limit)
    except WowProgressClientError as exc:
        _handle_client_error(ctx, exc)
        return
    _emit(
        ctx,
        {
            "provider": "wowprogress",
            "kind": "pve_leaderboard_sample",
            "query": query,
            "leaderboard": leaderboard,
            "sample": _sample_summary(entries, meta=meta),
            "entries": entries,
            "freshness": {
                "sampled_at": meta["sampled_at"],
                "cache_ttl_seconds": meta["cache_ttl_seconds"],
            },
            "citations": {
                "leaderboard_page": meta["page_url"],
            },
        },
    )


@distribution_app.command("pve-leaderboard")
def distribution_pve_leaderboard(
    ctx: typer.Context,
    metric: str = typer.Option("progress", "--metric", help="Distribution metric: progress, difficulty, realm, bosses_killed, rank."),
    region: str = typer.Option(..., "--region", help="Region slug such as world, us, or eu."),
    realm: str | None = typer.Option(None, "--realm", help="Optional realm slug to narrow the PvE leaderboard."),
    limit: int = typer.Option(50, "--limit", min=1, max=100, help="Maximum leaderboard rows to sample."),
) -> None:
    if metric not in {"progress", "difficulty", "realm", "bosses_killed", "rank"}:
        _fail(ctx, "invalid_query", "--metric must be one of: progress, difficulty, realm, bosses_killed, rank")
        return
    try:
        with _client(ctx) as client:
            entries, meta, _leaderboard, query = _load_pve_leaderboard_sample(client, region=region, realm=realm, limit=limit)
    except WowProgressClientError as exc:
        _handle_client_error(ctx, exc)
        return
    _emit(
        ctx,
        _distribution_payload(
            metric,
            entries,
            meta=meta,
            query=query,
        ),
    )


@threshold_app.command("pve-leaderboard")
def threshold_pve_leaderboard(
    ctx: typer.Context,
    metric: str = typer.Option("rank", "--metric", help="Threshold metric: rank or bosses_killed."),
    value: float = typer.Option(..., "--value", help="Target metric value to estimate against the sampled leaderboard."),
    region: str = typer.Option(..., "--region", help="Region slug such as world, us, or eu."),
    realm: str | None = typer.Option(None, "--realm", help="Optional realm slug to narrow the PvE leaderboard."),
    limit: int = typer.Option(50, "--limit", min=1, max=100, help="Maximum leaderboard rows to sample."),
    nearest: int = typer.Option(10, "--nearest", min=1, max=50, help="Maximum nearby rows to include in the threshold estimate."),
) -> None:
    if metric not in {"rank", "bosses_killed"}:
        _fail(ctx, "invalid_query", "--metric must be one of: rank, bosses_killed")
        return
    try:
        with _client(ctx) as client:
            entries, meta, _leaderboard, query = _load_pve_leaderboard_sample(client, region=region, realm=realm, limit=limit)
    except WowProgressClientError as exc:
        _handle_client_error(ctx, exc)
        return
    _emit(
        ctx,
        _threshold_payload(
            metric,
            value,
            entries,
            meta=meta,
            query=query,
            nearest_limit=nearest,
        ),
    )


@sample_app.command("pve-guild-profiles")
def sample_pve_guild_profiles(
    ctx: typer.Context,
    region: str = typer.Option(..., "--region", help="Region slug such as world, us, or eu."),
    realm: str | None = typer.Option(None, "--realm", help="Optional realm slug to narrow the PvE leaderboard."),
    limit: int = typer.Option(10, "--limit", min=1, max=25, help="Maximum top leaderboard guild profiles to fetch."),
    faction: list[str] | None = typer.Option(None, "--faction", help="Retain only guild profiles matching the given faction. Repeatable."),
    difficulty: list[str] | None = typer.Option(None, "--difficulty", help="Retain only guild profiles matching the given progression difficulty. Repeatable."),
    world_rank_min: int | None = typer.Option(None, "--world-rank-min", min=1, help="Retain only guild profiles at or above this world rank."),
    world_rank_max: int | None = typer.Option(None, "--world-rank-max", min=1, help="Retain only guild profiles at or below this world rank."),
    item_level_min: float | None = typer.Option(None, "--item-level-min", help="Retain only guild profiles at or above this average item level."),
    item_level_max: float | None = typer.Option(None, "--item-level-max", help="Retain only guild profiles at or below this average item level."),
    encounter: list[str] | None = typer.Option(None, "--encounter", help="Retain only guild profiles containing the given encounter name. Repeatable."),
) -> None:
    try:
        with _client(ctx) as client:
            entries, meta, leaderboard, query = _load_pve_guild_profile_sample(client, region=region, realm=realm, limit=limit)
    except WowProgressClientError as exc:
        _handle_client_error(ctx, exc)
        return
    entries, filtering = _filter_guild_profiles(
        entries,
        faction=faction,
        difficulty=difficulty,
        world_rank_min=world_rank_min,
        world_rank_max=world_rank_max,
        item_level_min=item_level_min,
        item_level_max=item_level_max,
        encounter=encounter,
    )
    _emit(
        ctx,
        {
            "provider": "wowprogress",
            "kind": "pve_guild_profiles_sample",
            "query": {
                **query,
                "filters": {
                    "faction": filtering["faction"],
                    "difficulty": filtering["difficulty"],
                    "world_rank_min": filtering["world_rank_min"],
                    "world_rank_max": filtering["world_rank_max"],
                    "item_level_min": filtering["item_level_min"],
                    "item_level_max": filtering["item_level_max"],
                    "encounter": filtering["encounter"],
                },
            },
            "leaderboard": leaderboard,
            "sample": _guild_profile_sample_summary(entries, meta=meta, filtering=filtering),
            "guild_profiles": entries,
            "freshness": {
                "sampled_at": meta["sampled_at"],
                "cache_ttl_seconds": meta["cache_ttl_seconds"],
            },
            "citations": {
                "leaderboard_page": meta["page_url"],
            },
        },
    )


@distribution_app.command("pve-guild-profiles")
def distribution_pve_guild_profiles(
    ctx: typer.Context,
    metric: str = typer.Option("progress", "--metric", help="Distribution metric: progress, faction, item_level_average, world_rank, encounter."),
    region: str = typer.Option(..., "--region", help="Region slug such as world, us, or eu."),
    realm: str | None = typer.Option(None, "--realm", help="Optional realm slug to narrow the PvE leaderboard."),
    limit: int = typer.Option(10, "--limit", min=1, max=25, help="Maximum top leaderboard guild profiles to fetch."),
    faction: list[str] | None = typer.Option(None, "--faction", help="Retain only guild profiles matching the given faction. Repeatable."),
    difficulty: list[str] | None = typer.Option(None, "--difficulty", help="Retain only guild profiles matching the given progression difficulty. Repeatable."),
    world_rank_min: int | None = typer.Option(None, "--world-rank-min", min=1, help="Retain only guild profiles at or above this world rank."),
    world_rank_max: int | None = typer.Option(None, "--world-rank-max", min=1, help="Retain only guild profiles at or below this world rank."),
    item_level_min: float | None = typer.Option(None, "--item-level-min", help="Retain only guild profiles at or above this average item level."),
    item_level_max: float | None = typer.Option(None, "--item-level-max", help="Retain only guild profiles at or below this average item level."),
    encounter: list[str] | None = typer.Option(None, "--encounter", help="Retain only guild profiles containing the given encounter name. Repeatable."),
) -> None:
    if metric not in {"progress", "faction", "item_level_average", "world_rank", "encounter"}:
        _fail(ctx, "invalid_query", "--metric must be one of: progress, faction, item_level_average, world_rank, encounter")
        return
    try:
        with _client(ctx) as client:
            entries, meta, _leaderboard, query = _load_pve_guild_profile_sample(client, region=region, realm=realm, limit=limit)
    except WowProgressClientError as exc:
        _handle_client_error(ctx, exc)
        return
    entries, filtering = _filter_guild_profiles(
        entries,
        faction=faction,
        difficulty=difficulty,
        world_rank_min=world_rank_min,
        world_rank_max=world_rank_max,
        item_level_min=item_level_min,
        item_level_max=item_level_max,
        encounter=encounter,
    )
    _emit(
        ctx,
        _guild_profile_distribution_payload(
            metric,
            entries,
            meta=meta,
            query={
                **query,
                "filters": {
                    "faction": filtering["faction"],
                    "difficulty": filtering["difficulty"],
                    "world_rank_min": filtering["world_rank_min"],
                    "world_rank_max": filtering["world_rank_max"],
                    "item_level_min": filtering["item_level_min"],
                    "item_level_max": filtering["item_level_max"],
                    "encounter": filtering["encounter"],
                },
            },
            filtering=filtering,
        ),
    )


@threshold_app.command("pve-guild-profiles")
def threshold_pve_guild_profiles(
    ctx: typer.Context,
    metric: str = typer.Option("world_rank", "--metric", help="Threshold metric: world_rank or item_level_average."),
    value: float = typer.Option(..., "--value", help="Target metric value to estimate against the sampled guild profiles."),
    region: str = typer.Option(..., "--region", help="Region slug such as world, us, or eu."),
    realm: str | None = typer.Option(None, "--realm", help="Optional realm slug to narrow the PvE leaderboard."),
    limit: int = typer.Option(10, "--limit", min=1, max=25, help="Maximum top leaderboard guild profiles to fetch."),
    nearest: int = typer.Option(5, "--nearest", min=1, max=25, help="Maximum nearby guild profiles to include in the threshold estimate."),
    faction: list[str] | None = typer.Option(None, "--faction", help="Retain only guild profiles matching the given faction. Repeatable."),
    difficulty: list[str] | None = typer.Option(None, "--difficulty", help="Retain only guild profiles matching the given progression difficulty. Repeatable."),
    world_rank_min: int | None = typer.Option(None, "--world-rank-min", min=1, help="Retain only guild profiles at or above this world rank."),
    world_rank_max: int | None = typer.Option(None, "--world-rank-max", min=1, help="Retain only guild profiles at or below this world rank."),
    item_level_min: float | None = typer.Option(None, "--item-level-min", help="Retain only guild profiles at or above this average item level."),
    item_level_max: float | None = typer.Option(None, "--item-level-max", help="Retain only guild profiles at or below this average item level."),
    encounter: list[str] | None = typer.Option(None, "--encounter", help="Retain only guild profiles containing the given encounter name. Repeatable."),
) -> None:
    if metric not in {"world_rank", "item_level_average"}:
        _fail(ctx, "invalid_query", "--metric must be one of: world_rank, item_level_average")
        return
    try:
        with _client(ctx) as client:
            entries, meta, _leaderboard, query = _load_pve_guild_profile_sample(client, region=region, realm=realm, limit=limit)
    except WowProgressClientError as exc:
        _handle_client_error(ctx, exc)
        return
    entries, filtering = _filter_guild_profiles(
        entries,
        faction=faction,
        difficulty=difficulty,
        world_rank_min=world_rank_min,
        world_rank_max=world_rank_max,
        item_level_min=item_level_min,
        item_level_max=item_level_max,
        encounter=encounter,
    )
    _emit(
        ctx,
        _guild_profile_threshold_payload(
            metric,
            value,
            entries,
            meta=meta,
            query={
                **query,
                "filters": {
                    "faction": filtering["faction"],
                    "difficulty": filtering["difficulty"],
                    "world_rank_min": filtering["world_rank_min"],
                    "world_rank_max": filtering["world_rank_max"],
                    "item_level_min": filtering["item_level_min"],
                    "item_level_max": filtering["item_level_max"],
                    "encounter": filtering["encounter"],
                },
            },
            nearest_limit=nearest,
            filtering=filtering,
        ),
    )


def run() -> None:
    app()


if __name__ == "__main__":
    run()
