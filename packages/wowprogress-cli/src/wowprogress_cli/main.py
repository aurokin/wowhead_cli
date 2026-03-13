from __future__ import annotations

from dataclasses import dataclass
import shlex
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


def _normalize_structured_query(query: str) -> tuple[str, str | None, str | None, str | None, str | None]:
    tokens = [token for token in query.strip().split() if token]
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
    if len(kept) < 3:
        return " ".join(kept).strip() or query.strip(), kind, None, None, None
    region = kept[0].lower()
    realm = kept[1]
    name = " ".join(kept[2:]).strip()
    normalized = " ".join(part for part in ([kind] if kind else []) + [region, realm, name]).strip()
    return normalized, kind, region, realm, name


def _score_match(*, query: str, kind_hint: str | None, kind: str, name: str, region: str, realm: str) -> tuple[int, list[str]]:
    lowered_query = query.lower()
    name_lower = name.lower()
    combined = " ".join((name, realm, region)).lower()
    score = 0
    reasons: list[str] = ["route_resolved"]
    if lowered_query == name_lower:
        score += 50
        reasons.append("exact_name")
    elif lowered_query in name_lower:
        score += 20
        reasons.append("name_contains_query")
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
        character = payload.get("character") if isinstance(payload.get("character"), dict) else {}
        name = str(character.get("name") or "").strip()
        region = str(character.get("region") or "").strip()
        realm = str(character.get("realm") or "").strip()
        page_url = character.get("page_url")
        score, reasons = _score_match(query=query, kind_hint=kind_hint, kind="character", name=name, region=region, realm=realm)
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
    guild = payload.get("guild") if isinstance(payload.get("guild"), dict) else {}
    name = str(guild.get("name") or "").strip()
    region = str(guild.get("region") or "").strip()
    realm = str(guild.get("realm") or "").strip()
    page_url = guild.get("page_url")
    score, reasons = _score_match(query=query, kind_hint=kind_hint, kind="guild", name=name, region=region, realm=realm)
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


def _search_payload(*, query: str, normalized_query: str, candidates: list[dict[str, Any]], limit: int, message: str | None = None) -> dict[str, Any]:
    sorted_rows = sorted(
        candidates,
        key=lambda item: (-int(((item.get("ranking") or {}).get("score")) or 0), str(item.get("kind") or ""), str(item.get("name") or "")),
    )
    return {
        "provider": "wowprogress",
        "query": query,
        "search_query": normalized_query,
        "count": len(sorted_rows),
        "results": sorted_rows[:limit],
        "truncated": len(sorted_rows) > limit,
        "message": message,
    }


def _resolve_payload(search_payload: dict[str, Any]) -> dict[str, Any]:
    results = search_payload.get("results")
    if not isinstance(results, list):
        results = []
    best = results[0] if results else None
    second = results[1] if len(results) > 1 else None
    best_score = int((((best or {}).get("ranking") or {}).get("score")) or 0)
    second_score = int((((second or {}).get("ranking") or {}).get("score")) or 0)
    follow_up = best.get("follow_up") if isinstance((best or {}).get("follow_up"), dict) else {}
    resolved = best is not None and bool(follow_up.get("command")) and (best_score >= 55 and (second is None or best_score - second_score >= 15))
    confidence = "high" if resolved else ("medium" if best_score >= 40 else ("low" if best is not None else "none"))
    return {
        "provider": "wowprogress",
        "query": search_payload.get("query"),
        "search_query": search_payload.get("search_query"),
        "resolved": resolved,
        "confidence": confidence,
        "match": best,
        "next_command": follow_up.get("command") if resolved else None,
        "fallback_search_command": None if resolved else f'wowprogress search "{search_payload.get("search_query")}"',
        "candidates": results,
        "message": search_payload.get("message"),
    }


def _search_candidates(ctx: typer.Context, query: str, *, limit: int) -> dict[str, Any]:
    normalized_query, kind_hint, region, realm, name = _normalize_structured_query(query)
    if region is None or realm is None or name is None:
        return _structured_search_hint(query)
    match_query = " ".join(part for part in (region, realm, name) if part)
    probe_types = ["char", "guild"]
    if kind_hint == "character":
        probe_types = ["char"]
    elif kind_hint == "guild":
        probe_types = ["guild"]
    candidates: list[dict[str, Any]] = []
    try:
        with _client(ctx) as client:
            for probe_type in probe_types:
                payload = client.probe_search_route(region=region, realm=realm, name=name, obj_type=probe_type)
                if payload is None:
                    continue
                candidates.append(
                    _candidate_from_probe(
                        match_query,
                        kind_hint=kind_hint,
                        payload=payload,
                        query_region=region,
                        query_realm=realm,
                        query_name=name,
                    )
                )
    except WowProgressClientError as exc:
        _handle_client_error(ctx, exc)
        raise AssertionError("unreachable")
    message = None if candidates else "WowProgress did not resolve that structured guild or character query."
    return _search_payload(query=query, normalized_query=normalized_query, candidates=candidates, limit=limit, message=message)


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


def run() -> None:
    app()


if __name__ == "__main__":
    run()
