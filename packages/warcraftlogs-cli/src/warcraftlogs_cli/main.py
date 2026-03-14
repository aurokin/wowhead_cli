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
            "server": "ready",
            "zones": "ready",
            "encounter": "ready",
            "guild": "ready",
            "character": "ready",
            "report": "ready",
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
        "archive_status": report.get("archiveStatus"),
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
