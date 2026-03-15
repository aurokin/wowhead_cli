from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import typer
from warcraft_core.output import emit
from warcraft_core.wow_normalization import normalize_region

from warcraftlogs_cli.client import (
    RETAIL_PROFILE,
    WarcraftLogsClient,
    WarcraftLogsClientError,
    load_warcraftlogs_auth_config,
    warcraftlogs_provider_env_path,
)

app = typer.Typer(add_completion=False, help="Warcraft Logs official API CLI.")


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


def _client(ctx: typer.Context) -> WarcraftLogsClient:
    try:
        return WarcraftLogsClient()
    except ValueError as exc:
        _fail(ctx, "missing_auth", str(exc))
        raise AssertionError("unreachable") from exc


def _handle_client_error(ctx: typer.Context, exc: WarcraftLogsClientError) -> None:
    _fail(ctx, exc.code, exc.message)


def _doctor_payload() -> dict[str, Any]:
    auth = load_warcraftlogs_auth_config()
    credential_source = auth.env_file if auth.env_file is not None else ("environment" if auth.configured else None)
    return {
        "ok": True,
        "provider": "warcraftlogs",
        "status": "ready",
        "site_profile": {
            "key": RETAIL_PROFILE.key,
            "label": RETAIL_PROFILE.label,
            "root_url": RETAIL_PROFILE.root_url,
            "api_url": RETAIL_PROFILE.api_url,
        },
        "auth": {
            "required": True,
            "configured": auth.configured,
            "flow": "oauth_client_credentials",
            "credential_source": credential_source,
            "lookup_order": [".env.local", warcraftlogs_provider_env_path(), "environment"],
            "redirect_flow_deferred": True,
        },
        "capabilities": {
            "doctor": "ready",
            "rate_limit": "ready",
            "regions": "ready",
            "expansions": "ready",
            "server": "ready",
            "zone": "ready",
            "zones": "ready",
            "encounter": "ready",
            "guild": "ready",
            "guild_rankings": "ready",
            "character": "ready",
            "character_rankings": "ready",
            "report": "ready",
            "reports": "ready",
            "report_fights": "ready",
            "user_auth": "planned",
        },
    }


def _region_payload(region: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": region.get("id"),
        "name": region.get("name"),
        "compact_name": region.get("compactName"),
        "slug": normalize_region(str(region.get("slug", ""))),
    }


def _server_payload(server: dict[str, Any]) -> dict[str, Any]:
    region = server.get("region") if isinstance(server.get("region"), dict) else {}
    subregion = server.get("subregion") if isinstance(server.get("subregion"), dict) else {}
    return {
        "id": server.get("id"),
        "name": server.get("name"),
        "normalized_name": server.get("normalizedName"),
        "slug": server.get("slug"),
        "region": _region_payload(region) if region else None,
        "subregion": {
            "id": subregion.get("id"),
            "name": subregion.get("name"),
        }
        if subregion
        else None,
        "connected_realm_id": server.get("connectedRealmID"),
        "season_id": server.get("seasonID"),
    }


def _zone_payload(zone: dict[str, Any]) -> dict[str, Any]:
    expansion = zone.get("expansion") if isinstance(zone.get("expansion"), dict) else {}
    difficulties = zone.get("difficulties")
    encounters = zone.get("encounters")
    return {
        "id": zone.get("id"),
        "name": zone.get("name"),
        "frozen": zone.get("frozen"),
        "expansion": {
            "id": expansion.get("id"),
            "name": expansion.get("name"),
        }
        if expansion
        else None,
        "difficulties": [
            {"id": difficulty.get("id"), "name": difficulty.get("name"), "sizes": difficulty.get("sizes", [])}
            for difficulty in difficulties
            if isinstance(difficulty, dict)
        ]
        if isinstance(difficulties, list)
        else [],
        "encounters": [
            {"id": encounter.get("id"), "name": encounter.get("name"), "journal_id": encounter.get("journalID")}
            for encounter in encounters
            if isinstance(encounter, dict)
        ]
        if isinstance(encounters, list)
        else [],
        "partitions": [
            {
                "id": partition.get("id"),
                "name": partition.get("name"),
                "compact_name": partition.get("compactName"),
                "default": partition.get("default"),
            }
            for partition in (zone.get("partitions") if isinstance(zone.get("partitions"), list) else [])
            if isinstance(partition, dict)
        ],
    }


def _expansion_payload(expansion: dict[str, Any]) -> dict[str, Any]:
    zones = expansion.get("zones")
    zone_rows = [zone for zone in zones if isinstance(zone, dict)] if isinstance(zones, list) else []
    return {
        "id": expansion.get("id"),
        "name": expansion.get("name"),
        "zone_count": len(zone_rows),
        "zones": [
            {
                "id": zone.get("id"),
                "name": zone.get("name"),
                "frozen": zone.get("frozen"),
            }
            for zone in zone_rows
        ],
    }


def _rank_payload(rank: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(rank, dict):
        return None
    return {
        "number": rank.get("number"),
        "color": rank.get("color"),
        "percentile": rank.get("percentile"),
    }


def _guild_payload(guild: dict[str, Any]) -> dict[str, Any]:
    faction = guild.get("faction") if isinstance(guild.get("faction"), dict) else {}
    server = guild.get("server") if isinstance(guild.get("server"), dict) else {}
    zone_ranking = guild.get("zoneRanking") if isinstance(guild.get("zoneRanking"), dict) else {}
    progress = zone_ranking.get("progress") if isinstance(zone_ranking.get("progress"), dict) else {}
    tags = guild.get("tags")
    return {
        "id": guild.get("id"),
        "name": guild.get("name"),
        "description": guild.get("description"),
        "competition_mode": guild.get("competitionMode"),
        "stealth_mode": guild.get("stealthMode"),
        "tags": [
            {"id": tag.get("id"), "name": tag.get("name")}
            for tag in tags
            if isinstance(tag, dict)
        ]
        if isinstance(tags, list)
        else [],
        "faction": {
            "id": faction.get("id"),
            "name": faction.get("name"),
        }
        if faction
        else None,
        "server": _server_payload(server) if server else None,
        "zone_ranking": {
            "progress": {
                "world": _rank_payload(progress.get("worldRank")),
                "region": _rank_payload(progress.get("regionRank")),
                "server": _rank_payload(progress.get("serverRank")),
            }
        }
        if zone_ranking
        else None,
    }


def _rank_positions_payload(positions: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(positions, dict):
        return None
    return {
        "world": _rank_payload(positions.get("worldRank")),
        "region": _rank_payload(positions.get("regionRank")),
        "server": _rank_payload(positions.get("serverRank")),
    }


def _guild_rankings_payload(guild: dict[str, Any]) -> dict[str, Any]:
    server = guild.get("server") if isinstance(guild.get("server"), dict) else {}
    zone_ranking = guild.get("zoneRanking") if isinstance(guild.get("zoneRanking"), dict) else {}
    return {
        "id": guild.get("id"),
        "name": guild.get("name"),
        "server": _server_payload(server) if server else None,
        "zone_ranking": {
            "progress": _rank_positions_payload(zone_ranking.get("progress")),
            "speed": _rank_positions_payload(zone_ranking.get("speed")),
            "complete_raid_speed": _rank_positions_payload(zone_ranking.get("completeRaidSpeed")),
        }
        if zone_ranking
        else None,
    }


def _archive_status_payload(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "is_archived": value.get("isArchived"),
        "is_accessible": value.get("isAccessible"),
        "archive_date": value.get("archiveDate"),
    }


def _character_payload(character: dict[str, Any]) -> dict[str, Any]:
    faction = character.get("faction") if isinstance(character.get("faction"), dict) else {}
    server = character.get("server") if isinstance(character.get("server"), dict) else {}
    guilds = character.get("guilds")
    normalized_guilds: list[dict[str, Any]] = []
    if isinstance(guilds, list):
        for guild in guilds:
            if not isinstance(guild, dict):
                continue
            normalized_guilds.append(
                {
                    "id": guild.get("id"),
                    "name": guild.get("name"),
                    "server": _server_payload(guild.get("server")) if isinstance(guild.get("server"), dict) else None,
                }
            )
    return {
        "id": character.get("id"),
        "canonical_id": character.get("canonicalID"),
        "name": character.get("name"),
        "level": character.get("level"),
        "class_id": character.get("classID"),
        "hidden": character.get("hidden"),
        "server": _server_payload(server) if server else None,
        "guild_rank": character.get("guildRank"),
        "faction": {"id": faction.get("id"), "name": faction.get("name")} if faction else None,
        "guilds": normalized_guilds,
    }


def _report_payload(report: dict[str, Any]) -> dict[str, Any]:
    zone = report.get("zone") if isinstance(report.get("zone"), dict) else {}
    guild = report.get("guild") if isinstance(report.get("guild"), dict) else {}
    return {
        "code": report.get("code"),
        "title": report.get("title"),
        "start_time": report.get("startTime"),
        "end_time": report.get("endTime"),
        "visibility": report.get("visibility"),
        "archive_status": _archive_status_payload(report.get("archiveStatus")),
        "segments": report.get("segments"),
        "exported_segments": report.get("exportedSegments"),
        "zone": {"id": zone.get("id"), "name": zone.get("name")} if zone else None,
        "guild": {
            "id": guild.get("id"),
            "name": guild.get("name"),
            "server": _server_payload(guild.get("server")) if isinstance(guild.get("server"), dict) else None,
        }
        if guild
        else None,
    }


def _character_rankings_payload(character: dict[str, Any], *, top: int) -> dict[str, Any]:
    server = character.get("server") if isinstance(character.get("server"), dict) else {}
    faction = character.get("faction") if isinstance(character.get("faction"), dict) else {}
    rankings = character.get("zoneRankings") if isinstance(character.get("zoneRankings"), dict) else {}
    rankings_error = rankings.get("error") if isinstance(rankings.get("error"), str) else None
    all_stars = rankings.get("allStars") if isinstance(rankings.get("allStars"), list) else []
    ranking_rows = rankings.get("rankings") if isinstance(rankings.get("rankings"), list) else []
    return {
        "id": character.get("id"),
        "canonical_id": character.get("canonicalID"),
        "name": character.get("name"),
        "level": character.get("level"),
        "class_id": character.get("classID"),
        "server": _server_payload(server) if server else None,
        "faction": {"id": faction.get("id"), "name": faction.get("name")} if faction else None,
        "summary": {
            "zone": rankings.get("zone"),
            "difficulty": rankings.get("difficulty"),
            "metric": rankings.get("metric"),
            "partition": rankings.get("partition"),
            "size": rankings.get("size"),
            "best_performance_average": rankings.get("bestPerformanceAverage"),
            "median_performance_average": rankings.get("medianPerformanceAverage"),
        }
        if not rankings_error
        else None,
        "error": rankings_error,
        "all_stars": [
            {
                "spec": row.get("spec"),
                "points": row.get("points"),
                "possible_points": row.get("possiblePoints"),
                "rank": row.get("rank"),
                "rank_percent": row.get("rankPercent"),
                "region_rank": row.get("regionRank"),
                "server_rank": row.get("serverRank"),
                "total": row.get("total"),
            }
            for row in all_stars[:top]
            if isinstance(row, dict)
        ],
        "rankings": [
            {
                "encounter": row.get("encounter"),
                "spec": row.get("spec"),
                "best_spec": row.get("bestSpec"),
                "rank_percent": row.get("rankPercent"),
                "median_percent": row.get("medianPercent"),
                "total_kills": row.get("totalKills"),
                "all_stars": row.get("allStars"),
                "best_rank": row.get("bestRank"),
                "best_amount": row.get("bestAmount"),
                "fastest_kill": row.get("fastestKill"),
            }
            for row in ranking_rows[:top]
            if isinstance(row, dict)
        ],
        "raw": rankings,
    }


def _reports_payload(pagination: dict[str, Any]) -> dict[str, Any]:
    rows = pagination.get("data") if isinstance(pagination.get("data"), list) else []
    return {
        "pagination": {
            "total": pagination.get("total"),
            "per_page": pagination.get("per_page"),
            "current_page": pagination.get("current_page"),
            "from": pagination.get("from"),
            "to": pagination.get("to"),
            "last_page": pagination.get("last_page"),
            "has_more_pages": pagination.get("has_more_pages"),
        },
        "reports": [_report_payload(report) for report in rows if isinstance(report, dict)],
    }


@app.callback()
def main(
    ctx: typer.Context,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
) -> None:
    ctx.obj = RuntimeConfig(pretty=pretty)


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    _emit(ctx, _doctor_payload())


@app.command("rate-limit")
def rate_limit(ctx: typer.Context) -> None:
    client = _client(ctx)
    try:
        payload = client.rate_limit()
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "rate_limit": {
                "limit_per_hour": payload.get("limitPerHour"),
                "points_spent_this_hour": payload.get("pointsSpentThisHour"),
                "points_reset_in": payload.get("pointsResetIn"),
            },
        },
    )


@app.command("regions")
def regions(ctx: typer.Context) -> None:
    client = _client(ctx)
    try:
        rows = client.regions()
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    regions_payload = [_region_payload(region) for region in rows]
    _emit(ctx, {"ok": True, "provider": "warcraftlogs", "count": len(regions_payload), "regions": regions_payload})


@app.command("expansions")
def expansions(ctx: typer.Context) -> None:
    client = _client(ctx)
    try:
        rows = client.expansions()
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    expansions_payload = [_expansion_payload(row) for row in rows]
    _emit(ctx, {"ok": True, "provider": "warcraftlogs", "count": len(expansions_payload), "expansions": expansions_payload})


@app.command("server")
def server(
    ctx: typer.Context,
    region: str,
    slug: str,
) -> None:
    client = _client(ctx)
    try:
        payload = client.server(region=region, slug=slug)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    _emit(ctx, {"ok": True, "provider": "warcraftlogs", "server": _server_payload(payload)})


@app.command("zones")
def zones(
    ctx: typer.Context,
    expansion_id: int | None = typer.Option(None, "--expansion-id", help="Optional Warcraft Logs expansion ID filter."),
) -> None:
    client = _client(ctx)
    try:
        rows = client.zones(expansion_id=expansion_id)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    zones_payload = [_zone_payload(zone) for zone in rows]
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "expansion_id": expansion_id,
            "count": len(zones_payload),
            "zones": zones_payload,
        },
    )


@app.command("zone")
def zone(ctx: typer.Context, zone_id: int) -> None:
    client = _client(ctx)
    try:
        payload = client.zone(zone_id=zone_id)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    _emit(ctx, {"ok": True, "provider": "warcraftlogs", "zone": _zone_payload(payload)})


@app.command("encounter")
def encounter(ctx: typer.Context, encounter_id: int) -> None:
    client = _client(ctx)
    try:
        payload = client.encounter(encounter_id=encounter_id)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    zone = payload.get("zone") if isinstance(payload.get("zone"), dict) else {}
    expansion = zone.get("expansion") if isinstance(zone.get("expansion"), dict) else {}
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "encounter": {
                "id": payload.get("id"),
                "name": payload.get("name"),
                "journal_id": payload.get("journalID"),
                "zone": {
                    "id": zone.get("id"),
                    "name": zone.get("name"),
                    "expansion": {"id": expansion.get("id"), "name": expansion.get("name")} if expansion else None,
                }
                if zone
                else None,
            },
        },
    )


@app.command("guild")
def guild(
    ctx: typer.Context,
    region: str,
    realm: str,
    name: str,
    zone_id: int | None = typer.Option(None, "--zone-id", help="Optional Warcraft Logs zone ID for current guild ranking context."),
) -> None:
    client = _client(ctx)
    try:
        payload = client.guild(region=region, realm=realm, name=name, zone_id=zone_id)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "query": {"region": region, "realm": realm, "name": name, "zone_id": zone_id},
            "guild": _guild_payload(payload),
        },
    )


@app.command("guild-rankings")
def guild_rankings(
    ctx: typer.Context,
    region: str,
    realm: str,
    name: str,
    zone_id: int | None = typer.Option(None, "--zone-id", help="Optional Warcraft Logs zone ID."),
    size: int | None = typer.Option(None, "--size", help="Optional raid size."),
    difficulty: int | None = typer.Option(None, "--difficulty", help="Optional difficulty ID for speed ranks."),
) -> None:
    client = _client(ctx)
    try:
        payload = client.guild_rankings(region=region, realm=realm, name=name, zone_id=zone_id, size=size, difficulty=difficulty)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "query": {"region": region, "realm": realm, "name": name, "zone_id": zone_id, "size": size, "difficulty": difficulty},
            "guild_rankings": _guild_rankings_payload(payload),
        },
    )


@app.command("character")
def character(ctx: typer.Context, region: str, realm: str, name: str) -> None:
    client = _client(ctx)
    try:
        payload = client.character(region=region, realm=realm, name=name)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "query": {"region": region, "realm": realm, "name": name},
            "character": _character_payload(payload),
        },
    )


@app.command("character-rankings")
def character_rankings(
    ctx: typer.Context,
    region: str,
    realm: str,
    name: str,
    zone_id: int | None = typer.Option(None, "--zone-id", help="Optional Warcraft Logs zone ID."),
    difficulty: int | None = typer.Option(None, "--difficulty", help="Optional difficulty ID."),
    metric: str | None = typer.Option(None, "--metric", help="Optional ranking metric such as dps, hps, or tankhps."),
    size: int | None = typer.Option(None, "--size", help="Optional raid size."),
    spec_name: str | None = typer.Option(None, "--spec-name", help="Optional spec slug filter."),
    top: int = typer.Option(5, "--top", min=1, max=20, help="Number of top ranking rows to keep in the summary."),
) -> None:
    client = _client(ctx)
    try:
        payload = client.character_rankings(
            region=region,
            realm=realm,
            name=name,
            zone_id=zone_id,
            difficulty=difficulty,
            metric=metric,
            size=size,
            spec_name=spec_name,
        )
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "query": {
                "region": region,
                "realm": realm,
                "name": name,
                "zone_id": zone_id,
                "difficulty": difficulty,
                "metric": metric,
                "size": size,
                "spec_name": spec_name,
                "top": top,
            },
            "character_rankings": _character_rankings_payload(payload, top=top),
        },
    )


@app.command("report")
def report(
    ctx: typer.Context,
    code: str,
    allow_unlisted: bool = typer.Option(False, "--allow-unlisted", help="Allow lookup of unlisted reports."),
) -> None:
    client = _client(ctx)
    try:
        payload = client.report(code=code, allow_unlisted=allow_unlisted)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "report": _report_payload(payload),
        },
    )


@app.command("reports")
def reports(
    ctx: typer.Context,
    guild_region: str | None = typer.Option(None, "--guild-region", help="Optional guild region for guild-scoped report queries."),
    guild_realm: str | None = typer.Option(None, "--guild-realm", help="Optional guild realm for guild-scoped report queries."),
    guild_name: str | None = typer.Option(None, "--guild-name", help="Optional guild name for guild-scoped report queries."),
    limit: int = typer.Option(25, "--limit", min=1, max=100, help="Reports per page."),
    page: int = typer.Option(1, "--page", min=1, help="Page number."),
    start_time: float | None = typer.Option(None, "--start-time", help="Optional report-range start time in milliseconds."),
    end_time: float | None = typer.Option(None, "--end-time", help="Optional report-range end time in milliseconds."),
    zone_id: int | None = typer.Option(None, "--zone-id", help="Optional Warcraft Logs zone filter."),
    game_zone_id: int | None = typer.Option(None, "--game-zone-id", help="Optional game zone filter."),
) -> None:
    client = _client(ctx)
    try:
        payload = client.reports(
            guild_region=guild_region,
            guild_realm=guild_realm,
            guild_name=guild_name,
            limit=limit,
            page=page,
            start_time=start_time,
            end_time=end_time,
            zone_id=zone_id,
            game_zone_id=game_zone_id,
        )
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    report_payload = _reports_payload(payload)
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "query": {
                "guild_region": guild_region,
                "guild_realm": guild_realm,
                "guild_name": guild_name,
                "limit": limit,
                "page": page,
                "start_time": start_time,
                "end_time": end_time,
                "zone_id": zone_id,
                "game_zone_id": game_zone_id,
            },
            "count": len(report_payload["reports"]),
            **report_payload,
        },
    )


@app.command("report-fights")
def report_fights(
    ctx: typer.Context,
    code: str,
    difficulty: int | None = typer.Option(None, "--difficulty", help="Optional difficulty ID filter."),
    allow_unlisted: bool = typer.Option(False, "--allow-unlisted", help="Allow lookup of unlisted reports."),
) -> None:
    client = _client(ctx)
    try:
        payload = client.report_fights(code=code, difficulty=difficulty, allow_unlisted=allow_unlisted)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    fights = payload.get("fights") if isinstance(payload.get("fights"), list) else []
    zone = payload.get("zone") if isinstance(payload.get("zone"), dict) else {}
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "report": {
                "code": payload.get("code"),
                "title": payload.get("title"),
                "zone": {"id": zone.get("id"), "name": zone.get("name")} if zone else None,
            },
            "difficulty": difficulty,
            "count": len(fights),
            "fights": [
                {
                    "id": fight.get("id"),
                    "name": fight.get("name"),
                    "encounter_id": fight.get("encounterID"),
                    "difficulty": fight.get("difficulty"),
                    "kill": fight.get("kill"),
                    "complete_raid": fight.get("completeRaid"),
                    "start_time": fight.get("startTime"),
                    "end_time": fight.get("endTime"),
                    "fight_percentage": fight.get("fightPercentage"),
                    "boss_percentage": fight.get("bossPercentage"),
                    "average_item_level": fight.get("averageItemLevel"),
                    "size": fight.get("size"),
                }
                for fight in fights
                if isinstance(fight, dict)
            ],
        },
    )


def run() -> None:
    app()
