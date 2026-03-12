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


def _coming_soon_payload(*, provider: str, query: str, command_hint: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "query": query,
        "search_query": query,
        "count": 0,
        "results": [],
        "candidates": [],
        "resolved": False,
        "confidence": "none",
        "match": None,
        "next_command": None,
        "fallback_search_command": None,
        "coming_soon": True,
        "message": "Free-text discovery is not implemented yet for Raider.IO phase 1. Use direct character or guild commands.",
        "suggested_command": command_hint,
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
                "search": "coming_soon",
                "resolve": "coming_soon",
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
    query: str = typer.Argument(..., help="Free-text query. Structured discovery is deferred for Raider.IO phase 1."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Unused in phase 1."),
) -> None:
    _emit(ctx, _coming_soon_payload(provider="raiderio", query=query, command_hint="raiderio character us illidan Roguecane"))


@app.command("resolve")
def resolve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Free-text query. Structured resolution is deferred for Raider.IO phase 1."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Unused in phase 1."),
) -> None:
    _emit(ctx, _coming_soon_payload(provider="raiderio", query=query, command_hint="raiderio guild us illidan Liquid"))


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
