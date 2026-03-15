from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import typer
from warcraft_core.output import emit
from warcraft_core.wow_normalization import normalize_region

from warcraftlogs_cli.client import (
    RETAIL_PROFILE,
    ReportFilterOptions,
    ReportPlayerDetailsOptions,
    ReportRankingsOptions,
    WarcraftLogsClient,
    WarcraftLogsClientError,
    load_warcraftlogs_auth_config,
    warcraftlogs_provider_env_path,
)

app = typer.Typer(add_completion=False, help="Warcraft Logs official API CLI.")

FIGHT_ID_OPTION = typer.Option(None, "--fight-id", help="Optional fight ID filter. Repeat as needed.")


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


def _normalize_graphql_enum(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if any(sep in text for sep in ("-", "_", " ")):
        parts = [part for part in re.split(r"[-_\s]+", text) if part]
        return "".join(part[:1].upper() + part[1:] for part in parts)
    if text.islower():
        return text[:1].upper() + text[1:]
    return text


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
            "report_events": "ready",
            "report_table": "ready",
            "report_graph": "ready",
            "report_master_data": "ready",
            "report_player_details": "ready",
            "report_rankings": "ready",
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


def _report_brief_payload(report: dict[str, Any]) -> dict[str, Any]:
    zone = report.get("zone") if isinstance(report.get("zone"), dict) else {}
    return {
        "code": report.get("code"),
        "title": report.get("title"),
        "zone": {"id": zone.get("id"), "name": zone.get("name")} if zone else None,
    }


def _report_filter_query_payload(
    *,
    ability_id: float | None,
    data_type: str | None,
    difficulty: int | None,
    encounter_id: int | None,
    end_time: float | None,
    fight_ids: list[int] | None,
    filter_expression: str | None,
    hostility_type: str | None,
    kill_type: str | None,
    limit: int | None,
    source_id: int | None,
    start_time: float | None,
    target_id: int | None,
    translate: bool | None,
    view_by: str | None,
    wipe_cutoff: int | None,
) -> dict[str, Any]:
    return {
        "ability_id": ability_id,
        "data_type": data_type,
        "difficulty": difficulty,
        "encounter_id": encounter_id,
        "end_time": end_time,
        "fight_ids": fight_ids,
        "filter_expression": filter_expression,
        "hostility_type": hostility_type,
        "kill_type": kill_type,
        "limit": limit,
        "source_id": source_id,
        "start_time": start_time,
        "target_id": target_id,
        "translate": translate,
        "view_by": view_by,
        "wipe_cutoff": wipe_cutoff,
    }


def _report_filter_options(
    *,
    ability_id: float | None,
    data_type: str | None,
    difficulty: int | None,
    encounter_id: int | None,
    end_time: float | None,
    fight_ids: list[int] | None,
    filter_expression: str | None,
    hostility_type: str | None,
    kill_type: str | None,
    limit: int | None,
    source_id: int | None,
    start_time: float | None,
    target_id: int | None,
    translate: bool | None,
    view_by: str | None,
    wipe_cutoff: int | None,
) -> ReportFilterOptions:
    return ReportFilterOptions(
        ability_id=ability_id,
        data_type=data_type,
        difficulty=difficulty,
        encounter_id=encounter_id,
        end_time=end_time,
        fight_ids=fight_ids or None,
        filter_expression=filter_expression,
        hostility_type=hostility_type,
        kill_type=kill_type,
        limit=limit,
        source_id=source_id,
        start_time=start_time,
        target_id=target_id,
        translate=translate,
        view_by=view_by,
        wipe_cutoff=wipe_cutoff,
    )


def _report_events_payload(report: dict[str, Any]) -> dict[str, Any]:
    paginator = report.get("events") if isinstance(report.get("events"), dict) else {}
    return {
        "report": _report_brief_payload(report),
        "next_page_timestamp": paginator.get("nextPageTimestamp"),
        "events": paginator.get("data"),
    }


def _report_json_payload(report: dict[str, Any], *, field: str) -> dict[str, Any]:
    return {
        "report": _report_brief_payload(report),
        field: report.get(field),
    }


def _report_master_data_payload(report: dict[str, Any]) -> dict[str, Any]:
    master_data = report.get("masterData") if isinstance(report.get("masterData"), dict) else {}
    abilities = master_data.get("abilities") if isinstance(master_data.get("abilities"), list) else []
    actors = master_data.get("actors") if isinstance(master_data.get("actors"), list) else []
    return {
        "report": _report_brief_payload(report),
        "master_data": {
            "log_version": master_data.get("logVersion"),
            "game_version": master_data.get("gameVersion"),
            "lang": master_data.get("lang"),
            "ability_count": len([row for row in abilities if isinstance(row, dict)]),
            "actor_count": len([row for row in actors if isinstance(row, dict)]),
            "abilities": [
                {
                    "game_id": row.get("gameID"),
                    "icon": row.get("icon"),
                    "name": row.get("name"),
                    "type": row.get("type"),
                }
                for row in abilities
                if isinstance(row, dict)
            ],
            "actors": [
                {
                    "game_id": row.get("gameID"),
                    "icon": row.get("icon"),
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "pet_owner": row.get("petOwner"),
                    "server": row.get("server"),
                    "sub_type": row.get("subType"),
                    "type": row.get("type"),
                }
                for row in actors
                if isinstance(row, dict)
            ],
        },
    }


def _player_detail_actor_payload(actor: dict[str, Any]) -> dict[str, Any]:
    specs = actor.get("specs") if isinstance(actor.get("specs"), list) else []
    return {
        "name": actor.get("name"),
        "id": actor.get("id"),
        "guid": actor.get("guid"),
        "type": actor.get("type"),
        "server": actor.get("server"),
        "region": actor.get("region"),
        "icon": actor.get("icon"),
        "specs": [
            {"spec": spec.get("spec"), "count": spec.get("count")}
            for spec in specs
            if isinstance(spec, dict)
        ],
        "min_item_level": actor.get("minItemLevel"),
        "max_item_level": actor.get("maxItemLevel"),
        "potion_use": actor.get("potionUse"),
        "healthstone_use": actor.get("healthstoneUse"),
        "combatant_info": actor.get("combatantInfo"),
    }


def _report_player_details_payload(report: dict[str, Any]) -> dict[str, Any]:
    details = report.get("playerDetails") if isinstance(report.get("playerDetails"), dict) else {}
    data = details.get("data") if isinstance(details.get("data"), dict) else {}
    role_data = data.get("playerDetails") if isinstance(data.get("playerDetails"), dict) else data
    roles: dict[str, list[dict[str, Any]]] = {}
    counts: dict[str, int] = {}
    for role in ("tanks", "healers", "dps"):
        rows = role_data.get(role) if isinstance(role_data.get(role), list) else []
        normalized_rows = [_player_detail_actor_payload(row) for row in rows if isinstance(row, dict)]
        roles[role] = normalized_rows
        counts[role] = len(normalized_rows)
    counts["total"] = counts["tanks"] + counts["healers"] + counts["dps"]
    return {
        "report": _report_brief_payload(report),
        "player_details": {
            "counts": counts,
            "roles": roles,
        },
    }


def _report_rankings_payload(report: dict[str, Any]) -> dict[str, Any]:
    rankings = report.get("rankings")
    rows = rankings.get("data") if isinstance(rankings, dict) else []
    normalized_rows = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    return {
        "report": _report_brief_payload(report),
        "rankings": {
            "count": len(normalized_rows),
            "rows": normalized_rows,
        },
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
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "report": _report_brief_payload(payload),
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


@app.command("report-events")
def report_events(
    ctx: typer.Context,
    code: str,
    ability_id: float | None = typer.Option(None, "--ability-id", help="Optional ability game ID filter."),
    data_type: str | None = typer.Option(None, "--data-type", help="Optional event data type."),
    difficulty: int | None = typer.Option(None, "--difficulty", help="Optional difficulty ID filter."),
    encounter_id: int | None = typer.Option(None, "--encounter-id", help="Optional encounter ID filter."),
    end_time: float | None = typer.Option(None, "--end-time", help="Optional event-range end timestamp."),
    fight_id: list[int] | None = FIGHT_ID_OPTION,
    filter_expression: str | None = typer.Option(None, "--filter-expression", help="Optional Warcraft Logs filter expression."),
    hostility_type: str | None = typer.Option(None, "--hostility-type", help="Optional hostility filter."),
    kill_type: str | None = typer.Option(None, "--kill-type", help="Optional kill filter."),
    limit: int | None = typer.Option(None, "--limit", min=1, max=10000, help="Optional page event limit."),
    source_id: int | None = typer.Option(None, "--source-id", help="Optional source actor ID filter."),
    start_time: float | None = typer.Option(None, "--start-time", help="Optional event-range start timestamp."),
    target_id: int | None = typer.Option(None, "--target-id", help="Optional target actor ID filter."),
    translate: bool | None = typer.Option(None, "--translate/--no-translate", help="Optional translation toggle."),
    allow_unlisted: bool = typer.Option(False, "--allow-unlisted", help="Allow lookup of unlisted reports."),
) -> None:
    normalized_data_type = _normalize_graphql_enum(data_type)
    normalized_hostility_type = _normalize_graphql_enum(hostility_type)
    normalized_kill_type = _normalize_graphql_enum(kill_type)
    if not any(value is not None for value in (fight_id, encounter_id, start_time, end_time)):
        _fail(
            ctx,
            "missing_scope",
            "report-events requires a narrowed slice. Provide --fight-id, --encounter-id, --start-time, or --end-time.",
        )
        return
    options = _report_filter_options(
        ability_id=ability_id,
        data_type=normalized_data_type,
        difficulty=difficulty,
        encounter_id=encounter_id,
        end_time=end_time,
        fight_ids=fight_id,
        filter_expression=filter_expression,
        hostility_type=normalized_hostility_type,
        kill_type=normalized_kill_type,
        limit=limit,
        source_id=source_id,
        start_time=start_time,
        target_id=target_id,
        translate=translate,
        view_by=None,
        wipe_cutoff=None,
    )
    client = _client(ctx)
    try:
        payload = client.report_events(code=code, allow_unlisted=allow_unlisted, options=options)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    result_payload = _report_events_payload(payload)
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "query": _report_filter_query_payload(
                ability_id=ability_id,
                data_type=normalized_data_type,
                difficulty=difficulty,
                encounter_id=encounter_id,
                end_time=end_time,
                fight_ids=fight_id,
                filter_expression=filter_expression,
                hostility_type=normalized_hostility_type,
                kill_type=normalized_kill_type,
                limit=limit,
                source_id=source_id,
                start_time=start_time,
                target_id=target_id,
                translate=translate,
                view_by=None,
                wipe_cutoff=None,
            ),
            **result_payload,
        },
    )


@app.command("report-table")
def report_table(
    ctx: typer.Context,
    code: str,
    ability_id: float | None = typer.Option(None, "--ability-id", help="Optional ability game ID filter."),
    data_type: str | None = typer.Option(None, "--data-type", help="Optional table data type."),
    difficulty: int | None = typer.Option(None, "--difficulty", help="Optional difficulty ID filter."),
    encounter_id: int | None = typer.Option(None, "--encounter-id", help="Optional encounter ID filter."),
    end_time: float | None = typer.Option(None, "--end-time", help="Optional event-range end timestamp."),
    fight_id: list[int] | None = FIGHT_ID_OPTION,
    filter_expression: str | None = typer.Option(None, "--filter-expression", help="Optional Warcraft Logs filter expression."),
    hostility_type: str | None = typer.Option(None, "--hostility-type", help="Optional hostility filter."),
    kill_type: str | None = typer.Option(None, "--kill-type", help="Optional kill filter."),
    source_id: int | None = typer.Option(None, "--source-id", help="Optional source actor ID filter."),
    start_time: float | None = typer.Option(None, "--start-time", help="Optional event-range start timestamp."),
    target_id: int | None = typer.Option(None, "--target-id", help="Optional target actor ID filter."),
    translate: bool | None = typer.Option(None, "--translate/--no-translate", help="Optional translation toggle."),
    view_by: str | None = typer.Option(None, "--view-by", help="Optional view grouping."),
    wipe_cutoff: int | None = typer.Option(None, "--wipe-cutoff", help="Optional wipe cutoff."),
    allow_unlisted: bool = typer.Option(False, "--allow-unlisted", help="Allow lookup of unlisted reports."),
) -> None:
    normalized_data_type = _normalize_graphql_enum(data_type)
    normalized_hostility_type = _normalize_graphql_enum(hostility_type)
    normalized_kill_type = _normalize_graphql_enum(kill_type)
    normalized_view_by = _normalize_graphql_enum(view_by)
    options = _report_filter_options(
        ability_id=ability_id,
        data_type=normalized_data_type,
        difficulty=difficulty,
        encounter_id=encounter_id,
        end_time=end_time,
        fight_ids=fight_id,
        filter_expression=filter_expression,
        hostility_type=normalized_hostility_type,
        kill_type=normalized_kill_type,
        limit=None,
        source_id=source_id,
        start_time=start_time,
        target_id=target_id,
        translate=translate,
        view_by=normalized_view_by,
        wipe_cutoff=wipe_cutoff,
    )
    client = _client(ctx)
    try:
        payload = client.report_table(code=code, allow_unlisted=allow_unlisted, options=options)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    result_payload = _report_json_payload(payload, field="table")
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "query": _report_filter_query_payload(
                ability_id=ability_id,
                data_type=normalized_data_type,
                difficulty=difficulty,
                encounter_id=encounter_id,
                end_time=end_time,
                fight_ids=fight_id,
                filter_expression=filter_expression,
                hostility_type=normalized_hostility_type,
                kill_type=normalized_kill_type,
                limit=None,
                source_id=source_id,
                start_time=start_time,
                target_id=target_id,
                translate=translate,
                view_by=normalized_view_by,
                wipe_cutoff=wipe_cutoff,
            ),
            **result_payload,
        },
    )


@app.command("report-graph")
def report_graph(
    ctx: typer.Context,
    code: str,
    ability_id: float | None = typer.Option(None, "--ability-id", help="Optional ability game ID filter."),
    data_type: str | None = typer.Option(None, "--data-type", help="Optional graph data type."),
    difficulty: int | None = typer.Option(None, "--difficulty", help="Optional difficulty ID filter."),
    encounter_id: int | None = typer.Option(None, "--encounter-id", help="Optional encounter ID filter."),
    end_time: float | None = typer.Option(None, "--end-time", help="Optional event-range end timestamp."),
    fight_id: list[int] | None = FIGHT_ID_OPTION,
    filter_expression: str | None = typer.Option(None, "--filter-expression", help="Optional Warcraft Logs filter expression."),
    hostility_type: str | None = typer.Option(None, "--hostility-type", help="Optional hostility filter."),
    kill_type: str | None = typer.Option(None, "--kill-type", help="Optional kill filter."),
    source_id: int | None = typer.Option(None, "--source-id", help="Optional source actor ID filter."),
    start_time: float | None = typer.Option(None, "--start-time", help="Optional event-range start timestamp."),
    target_id: int | None = typer.Option(None, "--target-id", help="Optional target actor ID filter."),
    translate: bool | None = typer.Option(None, "--translate/--no-translate", help="Optional translation toggle."),
    view_by: str | None = typer.Option(None, "--view-by", help="Optional view grouping."),
    wipe_cutoff: int | None = typer.Option(None, "--wipe-cutoff", help="Optional wipe cutoff."),
    allow_unlisted: bool = typer.Option(False, "--allow-unlisted", help="Allow lookup of unlisted reports."),
) -> None:
    normalized_data_type = _normalize_graphql_enum(data_type)
    normalized_hostility_type = _normalize_graphql_enum(hostility_type)
    normalized_kill_type = _normalize_graphql_enum(kill_type)
    normalized_view_by = _normalize_graphql_enum(view_by)
    options = _report_filter_options(
        ability_id=ability_id,
        data_type=normalized_data_type,
        difficulty=difficulty,
        encounter_id=encounter_id,
        end_time=end_time,
        fight_ids=fight_id,
        filter_expression=filter_expression,
        hostility_type=normalized_hostility_type,
        kill_type=normalized_kill_type,
        limit=None,
        source_id=source_id,
        start_time=start_time,
        target_id=target_id,
        translate=translate,
        view_by=normalized_view_by,
        wipe_cutoff=wipe_cutoff,
    )
    client = _client(ctx)
    try:
        payload = client.report_graph(code=code, allow_unlisted=allow_unlisted, options=options)
    except WarcraftLogsClientError as exc:
        _handle_client_error(ctx, exc)
        return
    finally:
        client.close()
    result_payload = _report_json_payload(payload, field="graph")
    _emit(
        ctx,
        {
            "ok": True,
            "provider": "warcraftlogs",
            "query": _report_filter_query_payload(
                ability_id=ability_id,
                data_type=normalized_data_type,
                difficulty=difficulty,
                encounter_id=encounter_id,
                end_time=end_time,
                fight_ids=fight_id,
                filter_expression=filter_expression,
                hostility_type=normalized_hostility_type,
                kill_type=normalized_kill_type,
                limit=None,
                source_id=source_id,
                start_time=start_time,
                target_id=target_id,
                translate=translate,
                view_by=normalized_view_by,
                wipe_cutoff=wipe_cutoff,
            ),
            **result_payload,
        },
    )


@app.command("report-master-data")
def report_master_data(
    ctx: typer.Context,
    code: str,
    actor_type: str | None = typer.Option(None, "--actor-type", help="Optional actor type filter."),
    actor_sub_type: str | None = typer.Option(None, "--actor-sub-type", help="Optional actor sub-type filter."),
    translate: bool | None = typer.Option(None, "--translate/--no-translate", help="Optional translation toggle."),
    allow_unlisted: bool = typer.Option(False, "--allow-unlisted", help="Allow lookup of unlisted reports."),
) -> None:
    client = _client(ctx)
    try:
        payload = client.report_master_data(
            code=code,
            allow_unlisted=allow_unlisted,
            translate=translate,
            actor_type=actor_type,
            actor_sub_type=actor_sub_type,
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
            "query": {"actor_type": actor_type, "actor_sub_type": actor_sub_type, "translate": translate},
            **_report_master_data_payload(payload),
        },
    )


@app.command("report-player-details")
def report_player_details(
    ctx: typer.Context,
    code: str,
    difficulty: int | None = typer.Option(None, "--difficulty", help="Optional difficulty ID filter."),
    encounter_id: int | None = typer.Option(None, "--encounter-id", help="Optional encounter ID filter."),
    end_time: float | None = typer.Option(None, "--end-time", help="Optional event-range end timestamp."),
    fight_id: list[int] | None = FIGHT_ID_OPTION,
    include_combatant_info: bool | None = typer.Option(
        None,
        "--include-combatant-info/--no-include-combatant-info",
        help="Optional combatant detail toggle.",
    ),
    kill_type: str | None = typer.Option(None, "--kill-type", help="Optional kill filter."),
    start_time: float | None = typer.Option(None, "--start-time", help="Optional event-range start timestamp."),
    translate: bool | None = typer.Option(None, "--translate/--no-translate", help="Optional translation toggle."),
    allow_unlisted: bool = typer.Option(False, "--allow-unlisted", help="Allow lookup of unlisted reports."),
) -> None:
    normalized_kill_type = _normalize_graphql_enum(kill_type)
    options = ReportPlayerDetailsOptions(
        difficulty=difficulty,
        encounter_id=encounter_id,
        end_time=end_time,
        fight_ids=fight_id or None,
        include_combatant_info=include_combatant_info,
        kill_type=normalized_kill_type,
        start_time=start_time,
        translate=translate,
    )
    client = _client(ctx)
    try:
        payload = client.report_player_details(code=code, allow_unlisted=allow_unlisted, options=options)
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
                "difficulty": difficulty,
                "encounter_id": encounter_id,
                "end_time": end_time,
                "fight_ids": fight_id,
                "include_combatant_info": include_combatant_info,
                "kill_type": normalized_kill_type,
                "start_time": start_time,
                "translate": translate,
            },
            **_report_player_details_payload(payload),
        },
    )


@app.command("report-rankings")
def report_rankings(
    ctx: typer.Context,
    code: str,
    compare: str | None = typer.Option(None, "--compare", help="Optional compare mode such as rankings or parses."),
    difficulty: int | None = typer.Option(None, "--difficulty", help="Optional difficulty ID filter."),
    encounter_id: int | None = typer.Option(None, "--encounter-id", help="Optional encounter ID filter."),
    fight_id: list[int] | None = FIGHT_ID_OPTION,
    player_metric: str | None = typer.Option(None, "--player-metric", help="Optional player metric such as dps or hps."),
    timeframe: str | None = typer.Option(None, "--timeframe", help="Optional timeframe such as today or historical."),
    allow_unlisted: bool = typer.Option(False, "--allow-unlisted", help="Allow lookup of unlisted reports."),
) -> None:
    normalized_compare = _normalize_graphql_enum(compare)
    normalized_timeframe = _normalize_graphql_enum(timeframe)
    options = ReportRankingsOptions(
        compare=normalized_compare,
        difficulty=difficulty,
        encounter_id=encounter_id,
        fight_ids=fight_id or None,
        player_metric=player_metric,
        timeframe=normalized_timeframe,
    )
    client = _client(ctx)
    try:
        payload = client.report_rankings(code=code, allow_unlisted=allow_unlisted, options=options)
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
                "compare": normalized_compare,
                "difficulty": difficulty,
                "encounter_id": encounter_id,
                "fight_ids": fight_id,
                "player_metric": player_metric,
                "timeframe": normalized_timeframe,
            },
            **_report_rankings_payload(payload),
        },
    )


def run() -> None:
    app()
