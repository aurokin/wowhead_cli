from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
import typer

from raiderio_cli.client import RaiderIOClient, load_raiderio_cache_settings_from_env
from warcraft_core.output import emit

app = typer.Typer(add_completion=False, help="Raider.IO profile and leaderboard CLI.")


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


def _client(ctx: typer.Context) -> RaiderIOClient:
    try:
        return RaiderIOClient()
    except ValueError as exc:
        _fail(ctx, "invalid_cache_config", str(exc))
        raise AssertionError("unreachable")


def _handle_http_error(ctx: typer.Context, exc: httpx.HTTPStatusError) -> None:
    status_code = exc.response.status_code
    code = "upstream_error"
    if status_code == 400:
        code = "invalid_query"
    elif status_code == 404:
        code = "not_found"
    elif status_code == 429:
        code = "rate_limited"
    message = f"Raider.IO request failed with HTTP {status_code}."
    try:
        payload = exc.response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        detail = payload.get("message") or payload.get("error")
        if isinstance(detail, str) and detail.strip():
            message = detail.strip()
    _fail(ctx, code, message, status=1)


def _normalize_search_query(query: str) -> tuple[str, str | None]:
    tokens = [token for token in query.strip().split() if token]
    type_hint: str | None = None
    kept: list[str] = []
    for token in tokens:
        lower = token.lower()
        if lower in {"guild", "guilds"}:
            type_hint = "guild"
            continue
        if lower in {"character", "characters", "char"}:
            type_hint = "character"
            continue
        kept.append(token)
    normalized = " ".join(kept).strip() or query.strip()
    return normalized, type_hint


def _match_reasons(
    *,
    query: str,
    type_hint: str | None,
    kind: str,
    name: str,
    region: str | None,
    realm: str | None,
) -> tuple[int, list[str]]:
    lowered_query = query.lower()
    name_lower = name.lower()
    combined = " ".join(part for part in (name, realm or "", region or "") if part).lower()
    score = 0
    reasons: list[str] = []
    if lowered_query == name_lower:
        score += 50
        reasons.append("exact_name")
    elif lowered_query in name_lower:
        score += 25
        reasons.append("name_contains_query")
    query_terms = [part for part in lowered_query.split() if part]
    if query_terms and all(term in combined for term in query_terms):
        score += 20
        reasons.append("all_terms_match")
    if realm and any(term == realm.lower() for term in query_terms):
        score += 10
        reasons.append("realm_match")
    if region and any(term == region.lower() for term in query_terms):
        score += 8
        reasons.append("region_match")
    if type_hint and type_hint == kind:
        score += 15
        reasons.append("type_hint")
    return score, reasons


def _follow_up_for_match(kind: str, region: str | None, realm: str | None, name: str) -> dict[str, Any]:
    base = {
        "provider": "raiderio",
        "kind": kind,
    }
    if kind == "character" and region and realm:
        return {
            **base,
            "surface": "character",
            "command": f"raiderio character {region} {realm} {name}",
        }
    if kind == "guild" and region and realm:
        return {
            **base,
            "surface": "guild",
            "command": f"raiderio guild {region} {realm} {name}",
        }
    return {
        **base,
        "surface": None,
        "command": None,
    }


def _search_results_payload(query: str, raw_matches: list[dict[str, Any]], *, type_hint: str | None, limit: int) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for row in raw_matches:
        kind = str(row.get("type") or "").strip().lower()
        if kind not in {"character", "guild"}:
            continue
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        region_row = data.get("region") if isinstance(data.get("region"), dict) else {}
        realm_row = data.get("realm") if isinstance(data.get("realm"), dict) else {}
        class_row = data.get("class") if isinstance(data.get("class"), dict) else {}
        name = str(data.get("displayName") or data.get("name") or row.get("name") or "").strip()
        region = str(region_row.get("slug") or "").strip() or None
        realm = str(realm_row.get("slug") or "").strip() or None
        score, reasons = _match_reasons(
            query=query,
            type_hint=type_hint,
            kind=kind,
            name=name,
            region=region,
            realm=realm,
        )
        path = data.get("path")
        profile_url = f"https://raider.io{path}" if isinstance(path, str) and path.startswith("/") else None
        results.append(
            {
                "provider": "raiderio",
                "kind": kind,
                "id": data.get("id"),
                "name": name,
                "region": region,
                "region_name": region_row.get("name"),
                "realm": realm,
                "realm_name": realm_row.get("name"),
                "faction": data.get("faction"),
                "class_name": class_row.get("name"),
                "class_slug": class_row.get("slug"),
                "profile_url": profile_url,
                "path": path,
                "ranking": {
                    "score": score,
                    "match_reasons": reasons,
                },
                "follow_up": _follow_up_for_match(kind, region, realm, name),
            }
        )
    results.sort(key=lambda item: (-int(((item.get("ranking") or {}).get("score")) or 0), str(item.get("kind") or ""), str(item.get("name") or "")))
    top = results[:limit]
    return {
        "provider": "raiderio",
        "query": query,
        "search_query": query,
        "count": len(results),
        "results": top,
        "truncated": len(results) > limit,
    }


def _resolve_payload(search_payload: dict[str, Any], *, limit: int) -> dict[str, Any]:
    results = search_payload.get("results")
    if not isinstance(results, list):
        results = []
    top = results[:limit]
    if not top:
        return {
            "provider": "raiderio",
            "query": search_payload.get("query"),
            "search_query": search_payload.get("search_query"),
            "resolved": False,
            "confidence": "none",
            "match": None,
            "next_command": None,
            "fallback_search_command": f'raiderio search "{search_payload.get("search_query")}"',
            "candidates": [],
        }
    best = top[0]
    best_score = int((((best.get("ranking") or {}).get("score")) or 0))
    second_score = int(((((top[1].get("ranking") or {}).get("score")) if len(top) > 1 else 0) or 0))
    follow_up = best.get("follow_up") if isinstance(best.get("follow_up"), dict) else {}
    resolved = bool(follow_up.get("command")) and (best_score >= 45 and (len(top) == 1 or best_score - second_score >= 15))
    confidence = "high" if resolved else ("medium" if best_score >= 30 else "low")
    return {
        "provider": "raiderio",
        "query": search_payload.get("query"),
        "search_query": search_payload.get("search_query"),
        "resolved": resolved,
        "confidence": confidence if top else "none",
        "match": best,
        "next_command": follow_up.get("command") if resolved else None,
        "fallback_search_command": None if resolved else f'raiderio search "{search_payload.get("search_query")}"',
        "candidates": top,
    }


def _raid_progression_summary(progress: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raid_slug, row in sorted(progress.items()):
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "raid_slug": raid_slug,
                "summary": row.get("summary") or "",
                "total_bosses": row.get("total_bosses"),
                "normal_bosses_killed": row.get("normal_bosses_killed"),
                "heroic_bosses_killed": row.get("heroic_bosses_killed"),
                "mythic_bosses_killed": row.get("mythic_bosses_killed"),
            }
        )
    return rows


def _guild_rankings_summary(rankings: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raid_slug, row in sorted(rankings.items()):
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "raid_slug": raid_slug,
                "normal": row.get("normal"),
                "heroic": row.get("heroic"),
                "mythic": row.get("mythic"),
            }
        )
    return rows


def _recent_run_summary(row: dict[str, Any]) -> dict[str, Any]:
    dungeon = row.get("dungeon") if isinstance(row.get("dungeon"), dict) else {}
    return {
        "mythic_level": row.get("mythic_level"),
        "dungeon": dungeon.get("name"),
        "dungeon_slug": dungeon.get("slug"),
        "completed_at": row.get("completed_at"),
        "num_chests": row.get("num_chests"),
        "clear_time_ms": row.get("clear_time_ms"),
        "keystone_time_ms": row.get("keystone_time_ms"),
    }


def _ranking_run_summary(row: dict[str, Any]) -> dict[str, Any]:
    run = row.get("run") if isinstance(row.get("run"), dict) else {}
    dungeon = run.get("dungeon") if isinstance(run.get("dungeon"), dict) else {}
    roster = run.get("roster") if isinstance(run.get("roster"), list) else []
    return {
        "rank": row.get("rank"),
        "score": row.get("score"),
        "mythic_level": run.get("mythic_level"),
        "dungeon": dungeon.get("name"),
        "dungeon_slug": dungeon.get("slug"),
        "completed_at": run.get("completed_at"),
        "affixes": [affix.get("slug") for affix in run.get("weekly_modifiers", []) if isinstance(affix, dict)],
        "roster": [
            {
                "name": ((entry.get("character") or {}).get("name") if isinstance(entry, dict) else None),
                "realm": ((((entry.get("character") or {}).get("realm") or {}).get("slug")) if isinstance(entry, dict) else None),
                "region": ((((entry.get("character") or {}).get("region") or {}).get("slug")) if isinstance(entry, dict) else None),
                "role": entry.get("role") if isinstance(entry, dict) else None,
            }
            for entry in roster[:5]
            if isinstance(entry, dict)
        ],
    }


@app.callback()
def main_callback(
    ctx: typer.Context,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    ctx.obj = RuntimeConfig(pretty=pretty)


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    try:
        settings, static_ttl, character_ttl, guild_ttl, mplus_runs_ttl = load_raiderio_cache_settings_from_env()
    except ValueError as exc:
        _fail(ctx, "invalid_cache_config", str(exc))
        return
    _emit(
        ctx,
        {
            "provider": "raiderio",
            "status": "ready",
            "command": "doctor",
            "installed": True,
            "language": "python",
            "auth": {
                "required": False,
                "deferred": True,
            },
            "capabilities": {
                "search": "ready",
                "resolve": "ready",
                "character": "ready",
                "guild": "ready",
                "mythic_plus_runs": "ready",
            },
            "cache": {
                "enabled": settings.enabled,
                "backend": settings.backend,
                "cache_dir": str(settings.cache_dir),
                "redis_url": settings.redis_url,
                "prefix": settings.prefix,
                "ttls": {
                    "static_data": static_ttl,
                    "character_profile": character_ttl,
                    "guild_profile": guild_ttl,
                    "mythic_plus_runs": mplus_runs_ttl,
                },
            },
        },
    )


@app.command("search")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Free-text character or guild query."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum results to return."),
    kind: str = typer.Option("all", "--kind", help="Optional result kind: all, character, or guild."),
) -> None:
    if kind not in {"all", "character", "guild"}:
        _fail(ctx, "invalid_query", "--kind must be one of: all, character, guild")
        return
    normalized_query, type_hint = _normalize_search_query(query)
    effective_kind = type_hint or kind
    try:
        with _client(ctx) as client:
            payload = client.search(term=normalized_query, kind=effective_kind)
    except httpx.HTTPStatusError as exc:
        _handle_http_error(ctx, exc)
        return
    raw_matches = payload.get("matches") if isinstance(payload.get("matches"), list) else []
    _emit(ctx, _search_results_payload(normalized_query, raw_matches, type_hint=type_hint, limit=limit))


@app.command("resolve")
def resolve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Free-text character or guild query."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum candidates to return."),
    kind: str = typer.Option("all", "--kind", help="Optional result kind: all, character, or guild."),
) -> None:
    if kind not in {"all", "character", "guild"}:
        _fail(ctx, "invalid_query", "--kind must be one of: all, character, guild")
        return
    normalized_query, type_hint = _normalize_search_query(query)
    effective_kind = type_hint or kind
    try:
        with _client(ctx) as client:
            payload = client.search(term=normalized_query, kind=effective_kind)
    except httpx.HTTPStatusError as exc:
        _handle_http_error(ctx, exc)
        return
    raw_matches = payload.get("matches") if isinstance(payload.get("matches"), list) else []
    search_payload = _search_results_payload(normalized_query, raw_matches, type_hint=type_hint, limit=limit)
    _emit(ctx, _resolve_payload(search_payload, limit=limit))


@app.command("character")
def character(
    ctx: typer.Context,
    region: str = typer.Argument(..., help="Region slug such as us or eu."),
    realm: str = typer.Argument(..., help="Realm slug or title."),
    name: str = typer.Argument(..., help="Character name."),
) -> None:
    try:
        with _client(ctx) as client:
            payload = client.character_profile(region=region, realm=realm, name=name)
    except httpx.HTTPStatusError as exc:
        _handle_http_error(ctx, exc)
        return
    raid_rows = _raid_progression_summary(payload.get("raid_progression") or {})
    recent_runs = payload.get("mythic_plus_recent_runs") if isinstance(payload.get("mythic_plus_recent_runs"), list) else []
    scores = payload.get("mythic_plus_scores_by_season") if isinstance(payload.get("mythic_plus_scores_by_season"), list) else []
    current_scores = scores[0] if scores else {}
    current_score_value = (((current_scores.get("scores") or {}).get("all")) if isinstance(current_scores, dict) else None)
    current_score_color = (((current_scores.get("segments") or {}).get("all") or {}).get("color")) if isinstance(current_scores, dict) else None
    guild = payload.get("guild") if isinstance(payload.get("guild"), dict) else None
    _emit(
        ctx,
        {
            "character": {
                "name": payload.get("name"),
                "region": payload.get("region"),
                "realm": payload.get("realm"),
                "race": payload.get("race"),
                "class_name": payload.get("class"),
                "active_spec_name": payload.get("active_spec_name"),
                "faction": payload.get("faction"),
                "profile_url": payload.get("profile_url"),
                "thumbnail_url": payload.get("thumbnail_url"),
            },
            "guild": {
                "name": guild.get("name"),
                "realm": guild.get("realm"),
                "region": guild.get("region"),
            } if guild else None,
            "mythic_plus": {
                "season": current_scores.get("season") if isinstance(current_scores, dict) else None,
                "current_score": current_score_value,
                "current_score_color": current_score_color,
                "ranks": payload.get("mythic_plus_ranks"),
                "recent_run_count": len(recent_runs),
                "recent_runs": [_recent_run_summary(row) for row in recent_runs[:5] if isinstance(row, dict)],
            },
            "raiding": {
                "raid_count": len(raid_rows),
                "progression": raid_rows,
            },
            "citations": {
                "profile": payload.get("profile_url"),
            },
        },
    )


@app.command("guild")
def guild(
    ctx: typer.Context,
    region: str = typer.Argument(..., help="Region slug such as us or eu."),
    realm: str = typer.Argument(..., help="Realm slug or title."),
    name: str = typer.Argument(..., help="Guild name."),
) -> None:
    try:
        with _client(ctx) as client:
            payload = client.guild_profile(region=region, realm=realm, name=name)
    except httpx.HTTPStatusError as exc:
        _handle_http_error(ctx, exc)
        return
    members = payload.get("members") if isinstance(payload.get("members"), list) else []
    raid_progression = _raid_progression_summary(payload.get("raid_progression") or {})
    raid_rankings = _guild_rankings_summary(payload.get("raid_rankings") or {})
    _emit(
        ctx,
        {
            "guild": {
                "name": payload.get("name"),
                "region": payload.get("region"),
                "realm": payload.get("realm"),
                "faction": payload.get("faction"),
                "profile_url": payload.get("profile_url"),
                "member_count": len(members),
            },
            "raiding": {
                "raid_count": len(raid_progression),
                "progression": raid_progression,
                "rankings": raid_rankings,
            },
            "roster_preview": [
                {
                    "name": ((row.get("character") or {}).get("name") if isinstance(row, dict) else None),
                    "realm": ((row.get("character") or {}).get("realm") if isinstance(row, dict) else None),
                    "class_name": ((row.get("character") or {}).get("class") if isinstance(row, dict) else None),
                    "active_spec_name": ((row.get("character") or {}).get("active_spec_name") if isinstance(row, dict) else None),
                }
                for row in members[:10]
                if isinstance(row, dict)
            ],
            "citations": {
                "profile": payload.get("profile_url"),
            },
        },
    )


@app.command("mythic-plus-runs")
def mythic_plus_runs(
    ctx: typer.Context,
    season: str = typer.Option("", "--season", help="Season slug. Defaults to Raider.IO current default season."),
    region: str = typer.Option("world", "--region", help="Region slug such as world, us, or eu."),
    dungeon: str = typer.Option("all", "--dungeon", help="Dungeon slug or all."),
    affixes: str = typer.Option("", "--affixes", help="Affix slug, fortified, tyrannical, current, or all."),
    page: int = typer.Option(0, "--page", min=0, help="Page of rankings to request."),
) -> None:
    try:
        with _client(ctx) as client:
            payload = client.mythic_plus_runs(
                season=season or None,
                region=region,
                dungeon=dungeon,
                affixes=affixes or None,
                page=page,
            )
    except httpx.HTTPStatusError as exc:
        _handle_http_error(ctx, exc)
        return
    rankings = payload.get("rankings") if isinstance(payload.get("rankings"), list) else []
    _emit(
        ctx,
        {
            "query": {
                "season": payload.get("season") or season or None,
                "region": payload.get("region") or region,
                "dungeon": payload.get("dungeon") or dungeon,
                "affixes": affixes or None,
                "page": page,
            },
            "count": len(rankings),
            "runs": [_ranking_run_summary(row) for row in rankings],
        },
    )


def run() -> None:
    app()


if __name__ == "__main__":
    run()
