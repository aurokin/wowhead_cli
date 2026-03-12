from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import typer

from warcraft_core.output import emit
from wowprogress_cli.client import DEFAULT_IMPERSONATE, WowProgressClient, WowProgressClientError, load_wowprogress_cache_settings_from_env

app = typer.Typer(add_completion=False, help="WowProgress rankings and profile CLI.")


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


def _coming_soon_payload(*, query: str, suggested_command: str) -> dict[str, Any]:
    return {
        "provider": "wowprogress",
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
        "message": "Free-text discovery is not implemented yet for WowProgress phase 1. Use direct guild, character, or leaderboard commands.",
        "suggested_command": suggested_command,
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
                "search": "coming_soon",
                "resolve": "coming_soon",
                "guild": "ready",
                "character": "ready",
                "leaderboard": "ready",
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
    query: str = typer.Argument(..., help="Free-text query. Structured discovery is deferred for WowProgress phase 1."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Unused in phase 1."),
) -> None:
    _emit(ctx, _coming_soon_payload(query=query, suggested_command="wowprogress guild us illidan Liquid"))


@app.command("resolve")
def resolve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Free-text query. Structured resolution is deferred for WowProgress phase 1."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Unused in phase 1."),
) -> None:
    _emit(ctx, _coming_soon_payload(query=query, suggested_command="wowprogress character us illidan Imonthegcd"))


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


def run() -> None:
    app()


if __name__ == "__main__":
    run()
