from __future__ import annotations

from typing import Any

import typer
from icy_veins_cli.main import app as icy_veins_app
from raiderio_cli.main import app as raiderio_app
from typer.main import get_command
from warcraft_wiki_cli.main import app as warcraft_wiki_app

from method_cli.main import app as method_app
from warcraft_core.output import emit
from warcraft_core.provider_contract import resolve_payload_sort_key, search_result_sort_key
from warcraft_cli.providers import global_doctor_payload, list_providers, provider_resolve, provider_search
from wowhead_cli.main import app as wowhead_app

app = typer.Typer(add_completion=False, help="Warcraft wrapper CLI for routing to service-specific Warcraft CLIs.")


def _emit(payload: Any, *, pretty: bool) -> None:
    emit(payload, pretty=pretty)


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
) -> None:
    ctx.obj = {"pretty": pretty}


def _pretty(ctx: typer.Context) -> bool:
    obj = ctx.obj
    if isinstance(obj, dict):
        return bool(obj.get("pretty"))
    return False


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    _emit(global_doctor_payload(), pretty=_pretty(ctx))


@app.command("search")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search across available providers."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum provider-local results to request."),
) -> None:
    providers: list[dict[str, Any]] = []
    flattened: list[dict[str, Any]] = []
    for registration in list_providers():
        result = provider_search(registration.name, query, limit=limit)
        payload = result.get("payload")
        provider_row = {
            "provider": registration.name,
            "status": registration.status,
            "payload": payload,
        }
        providers.append(provider_row)
        if isinstance(payload, dict):
            for row in payload.get("results", []) or []:
                if isinstance(row, dict):
                    flattened.append({"provider": registration.name, **row})
    flattened.sort(key=search_result_sort_key)
    _emit(
        {
            "query": query,
            "provider_count": len(providers),
            "providers": providers,
            "count": len(flattened),
            "results": flattened,
        },
        pretty=_pretty(ctx),
    )


@app.command("resolve")
def resolve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Resolve a query across available providers."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Maximum provider-local candidates to request."),
) -> None:
    providers: list[dict[str, Any]] = []
    resolved_candidates: list[tuple[str, dict[str, Any]]] = []
    for registration in list_providers():
        result = provider_resolve(registration.name, query, limit=limit)
        payload = result.get("payload")
        providers.append(
            {
                "provider": registration.name,
                "status": registration.status,
                "payload": payload,
            }
        )
        if isinstance(payload, dict) and payload.get("resolved"):
            resolved_candidates.append((registration.name, payload))
    resolved_candidates.sort(key=lambda row: resolve_payload_sort_key(row[0], row[1]))
    best_provider = resolved_candidates[0][0] if resolved_candidates else None
    best_payload = resolved_candidates[0][1] if resolved_candidates else None
    _emit(
        {
            "query": query,
            "provider_count": len(providers),
            "resolved": best_payload is not None,
            "provider": best_provider,
            "match": best_payload.get("match") if isinstance(best_payload, dict) else None,
            "next_command": best_payload.get("next_command") if isinstance(best_payload, dict) else None,
            "confidence": best_payload.get("confidence") if isinstance(best_payload, dict) else None,
            "providers": providers,
        },
        pretty=_pretty(ctx),
    )


@app.command(
    "wowhead",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def wowhead_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(wowhead_app, args=list(ctx.args), prog_name="wowhead")


@app.command(
    "icy-veins",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def icy_veins_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(icy_veins_app, args=list(ctx.args), prog_name="icy-veins")


@app.command(
    "method",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def method_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(method_app, args=list(ctx.args), prog_name="method")


@app.command(
    "raiderio",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def raiderio_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(raiderio_app, args=list(ctx.args), prog_name="raiderio")


@app.command(
    "warcraft-wiki",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def warcraft_wiki_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(warcraft_wiki_app, args=list(ctx.args), prog_name="warcraft-wiki")


def run() -> None:
    app()


if __name__ == "__main__":
    run()
