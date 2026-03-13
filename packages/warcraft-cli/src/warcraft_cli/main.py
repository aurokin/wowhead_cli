from __future__ import annotations

from typing import Any

import typer
from icy_veins_cli.main import app as icy_veins_app
from raiderio_cli.main import app as raiderio_app
from simc_cli.main import app as simc_app
from typer.main import get_command
from warcraft_wiki_cli.main import app as warcraft_wiki_app
from wowprogress_cli.main import app as wowprogress_app

from method_cli.main import app as method_app
from warcraft_core.output import emit
from warcraft_core.provider_contract import (
    compact_resolve_match,
    compact_wrapper_candidate,
    decorate_resolve_payload,
    decorate_search_result,
    resolve_payload_sort_key,
    search_result_sort_key,
    synthetic_resolve_payloads,
    synthetic_search_candidates,
)
from warcraft_cli.providers import (
    expansion_filtered_providers,
    expansion_support_snapshot,
    get_provider,
    global_doctor_payload,
    list_providers,
    provider_expansion_exclusion_reason,
    provider_expansion_support,
    provider_resolve,
    provider_search,
)
from wowhead_cli.expansion_profiles import resolve_expansion
from wowhead_cli.main import app as wowhead_app

app = typer.Typer(add_completion=False, help="Warcraft wrapper CLI for routing to service-specific Warcraft CLIs.")


def _emit(payload: Any, *, pretty: bool, err: bool = False) -> None:
    emit(payload, pretty=pretty, err=err)


def _invoke_sub_app(sub_app: typer.Typer, *, args: list[str], prog_name: str) -> None:
    command = get_command(sub_app)
    try:
        command.main(args=args, prog_name=prog_name, standalone_mode=False)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        raise typer.Exit(code) from exc


@app.callback()
def main_callback(
    ctx: typer.Context,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
    expansion: str | None = typer.Option(
        None,
        "--expansion",
        help="Filter wrapper search/resolve to a specific expansion profile. Passed through to expansion-aware providers like wowhead.",
    ),
) -> None:
    requested_expansion: str | None = None
    if expansion is not None:
        try:
            requested_expansion = resolve_expansion(expansion).key
        except ValueError as exc:
            raise typer.BadParameter(str(exc), param_hint="--expansion") from exc
    ctx.obj = {"pretty": pretty, "requested_expansion": requested_expansion}


def _pretty(ctx: typer.Context) -> bool:
    obj = ctx.obj
    if isinstance(obj, dict):
        return bool(obj.get("pretty"))
    return False


def _requested_expansion(ctx: typer.Context) -> str | None:
    obj = ctx.obj
    if isinstance(obj, dict):
        value = obj.get("requested_expansion")
        if isinstance(value, str) and value:
            return value
    return None


def _passthrough_args(ctx: typer.Context, *, provider_name: str) -> list[str]:
    args = list(ctx.args)
    requested_expansion = _requested_expansion(ctx)
    if requested_expansion is None:
        return args
    registration = get_provider(provider_name)
    reason = provider_expansion_exclusion_reason(registration, requested_expansion=requested_expansion)
    if reason is not None:
        _emit(
            {
                "ok": False,
                "error": {
                    "code": "unsupported_provider_expansion",
                    "message": (
                        f"Provider {provider_name!r} does not support wrapper expansion "
                        f"{requested_expansion!r}."
                    ),
                },
                "provider": provider_name,
                "requested_expansion": requested_expansion,
                "expansion_support": provider_expansion_support(
                    registration,
                    requested_expansion=requested_expansion,
                ),
            },
            pretty=_pretty(ctx),
            err=True,
        )
        raise typer.Exit(1)
    if provider_name == "wowhead":
        if "--expansion" in args:
            _emit(
                {
                    "ok": False,
                    "error": {
                        "code": "duplicate_expansion_argument",
                        "message": "Do not pass both warcraft --expansion and wowhead --expansion in the same command.",
                    },
                    "provider": provider_name,
                    "requested_expansion": requested_expansion,
                },
                pretty=_pretty(ctx),
                err=True,
            )
            raise typer.Exit(1)
        return ["--expansion", requested_expansion, *args]
    return args


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    _emit(global_doctor_payload(requested_expansion=_requested_expansion(ctx)), pretty=_pretty(ctx))


@app.command("search")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search across available providers."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum provider-local results to request."),
    compact: bool = typer.Option(False, "--compact", help="Return a smaller wrapper payload with compact candidates."),
    ranking_debug: bool = typer.Option(False, "--ranking-debug", help="Include compact wrapper ranking summaries for the returned candidates."),
    expansion_debug: bool = typer.Option(
        False,
        "--expansion-debug",
        help="Include a compact expansion support snapshot for all providers.",
    ),
) -> None:
    requested_expansion = _requested_expansion(ctx)
    included_registrations, excluded_providers = expansion_filtered_providers(requested_expansion=requested_expansion)
    providers: list[dict[str, Any]] = []
    flattened: list[dict[str, Any]] = []
    for registration in included_registrations:
        result = provider_search(registration.name, query, limit=limit, expansion=requested_expansion)
        payload = result.get("payload")
        provider_row = {
            "provider": registration.name,
            "status": registration.status,
            "expansion_support": provider_expansion_support(
                registration,
                requested_expansion=requested_expansion,
            ),
            "payload": payload,
        }
        providers.append(provider_row)
        if isinstance(payload, dict):
            for row in payload.get("results", []) or []:
                if isinstance(row, dict):
                    flattened.append(
                        decorate_search_result(
                            query,
                            {
                                "provider": registration.name,
                                "provider_expansion": provider_expansion_support(
                                    registration,
                                    requested_expansion=requested_expansion,
                                ),
                                **row,
                            },
                        )
                    )
    for row in synthetic_search_candidates(query):
        registration = get_provider(str(row.get("provider") or ""))
        if provider_expansion_exclusion_reason(registration, requested_expansion=requested_expansion) is not None:
            continue
        flattened.append(
            decorate_search_result(
                query,
                {
                    "provider_expansion": provider_expansion_support(
                        registration,
                        requested_expansion=requested_expansion,
                    ),
                    **row,
                },
            )
        )
    flattened.sort(key=search_result_sort_key)
    top = flattened[:limit]
    if compact:
        top = [compact_wrapper_candidate(row) for row in top]
    payload: dict[str, Any] = {
        "query": query,
        "provider_count": len(list_providers()),
        "requested_expansion": requested_expansion,
        "expansion_filter_active": requested_expansion is not None,
        "included_providers": [registration.name for registration in included_registrations],
        "excluded_providers": excluded_providers,
        "included_provider_count": len(included_registrations),
        "excluded_provider_count": len(excluded_providers),
        "providers": [] if compact else providers,
        "count": len(flattened),
        "results": top,
    }
    if ranking_debug:
        payload["ranking_debug"] = [compact_wrapper_candidate(row) for row in flattened[:limit]]
    if expansion_debug:
        payload["expansion_debug"] = expansion_support_snapshot(requested_expansion=requested_expansion)
    _emit(
        payload,
        pretty=_pretty(ctx),
    )


@app.command("resolve")
def resolve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Resolve a query across available providers."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum provider-local candidates to request."),
    compact: bool = typer.Option(False, "--compact", help="Return a smaller wrapper payload with a compact match summary."),
    ranking_debug: bool = typer.Option(False, "--ranking-debug", help="Include compact wrapper ranking summaries for resolved candidates."),
    expansion_debug: bool = typer.Option(
        False,
        "--expansion-debug",
        help="Include a compact expansion support snapshot for all providers.",
    ),
) -> None:
    requested_expansion = _requested_expansion(ctx)
    included_registrations, excluded_providers = expansion_filtered_providers(requested_expansion=requested_expansion)
    providers: list[dict[str, Any]] = []
    resolved_candidates: list[tuple[str, dict[str, Any]]] = []
    for registration in included_registrations:
        result = provider_resolve(registration.name, query, limit=limit, expansion=requested_expansion)
        payload = result.get("payload")
        providers.append(
            {
                "provider": registration.name,
                "status": registration.status,
                "expansion_support": provider_expansion_support(
                    registration,
                    requested_expansion=requested_expansion,
                ),
                "payload": payload,
            }
        )
        if isinstance(payload, dict) and payload.get("resolved"):
            resolved_candidates.append((registration.name, decorate_resolve_payload(query, registration.name, payload)))
    for provider_name, payload in synthetic_resolve_payloads(query):
        registration = get_provider(provider_name)
        if provider_expansion_exclusion_reason(registration, requested_expansion=requested_expansion) is not None:
            continue
        resolved_candidates.append((provider_name, payload))
    resolved_candidates.sort(key=lambda row: resolve_payload_sort_key(row[0], row[1]))
    best_provider = resolved_candidates[0][0] if resolved_candidates else None
    best_payload = resolved_candidates[0][1] if resolved_candidates else None
    match = compact_resolve_match(best_payload) if compact else (best_payload.get("match") if isinstance(best_payload, dict) else None)
    payload: dict[str, Any] = {
        "query": query,
        "provider_count": len(list_providers()),
        "requested_expansion": requested_expansion,
        "expansion_filter_active": requested_expansion is not None,
        "included_providers": [registration.name for registration in included_registrations],
        "excluded_providers": excluded_providers,
        "included_provider_count": len(included_registrations),
        "excluded_provider_count": len(excluded_providers),
        "resolved": best_payload is not None,
        "provider": best_provider,
        "match": match,
        "next_command": best_payload.get("next_command") if isinstance(best_payload, dict) else None,
        "confidence": best_payload.get("confidence") if isinstance(best_payload, dict) else None,
        "providers": [] if compact else providers,
    }
    if ranking_debug:
        payload["ranking_debug"] = [compact_resolve_match(row[1]) for row in resolved_candidates[:limit] if compact_resolve_match(row[1]) is not None]
    if expansion_debug:
        payload["expansion_debug"] = expansion_support_snapshot(requested_expansion=requested_expansion)
    _emit(
        payload,
        pretty=_pretty(ctx),
    )


@app.command(
    "wowhead",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def wowhead_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(wowhead_app, args=_passthrough_args(ctx, provider_name="wowhead"), prog_name="wowhead")


@app.command(
    "icy-veins",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def icy_veins_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(icy_veins_app, args=_passthrough_args(ctx, provider_name="icy-veins"), prog_name="icy-veins")


@app.command(
    "method",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def method_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(method_app, args=_passthrough_args(ctx, provider_name="method"), prog_name="method")


@app.command(
    "raiderio",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def raiderio_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(raiderio_app, args=_passthrough_args(ctx, provider_name="raiderio"), prog_name="raiderio")


@app.command(
    "warcraft-wiki",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def warcraft_wiki_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(
        warcraft_wiki_app,
        args=_passthrough_args(ctx, provider_name="warcraft-wiki"),
        prog_name="warcraft-wiki",
    )


@app.command(
    "wowprogress",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def wowprogress_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(
        wowprogress_app,
        args=_passthrough_args(ctx, provider_name="wowprogress"),
        prog_name="wowprogress",
    )


@app.command(
    "simc",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def simc_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(simc_app, args=_passthrough_args(ctx, provider_name="simc"), prog_name="simc")


def run() -> None:
    app()


if __name__ == "__main__":
    run()
