from __future__ import annotations

from typing import Any

import typer

from warcraft_core.output import emit

app = typer.Typer(add_completion=False, help="Method.gg CLI. Milestone 1 exposes stubbed provider commands.")


def _coming_soon_payload(command: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "provider": "method",
        "status": "coming_soon",
        "command": command,
        "message": "Method.gg provider commands are stubbed in milestone 1.",
    }
    payload.update(extra)
    return payload


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


def _emit(ctx: typer.Context, payload: dict[str, Any]) -> None:
    emit(payload, pretty=_pretty(ctx))


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    _emit(
        ctx,
        _coming_soon_payload(
            "doctor",
            installed=True,
            language="python",
            capabilities={
                "search": "coming_soon",
                "resolve": "coming_soon",
                "guide": "coming_soon",
                "guide_full": "coming_soon",
                "guide_export": "coming_soon",
                "guide_query": "coming_soon",
            },
        ),
    )


@app.command("search")
def search(ctx: typer.Context, query: str = typer.Argument(...), limit: int = typer.Option(5, "--limit", min=1, max=50)) -> None:
    _emit(ctx, _coming_soon_payload("search", query=query, limit=limit, count=0, results=[]))


@app.command("resolve")
def resolve(ctx: typer.Context, query: str = typer.Argument(...), limit: int = typer.Option(5, "--limit", min=1, max=50)) -> None:
    _emit(
        ctx,
        _coming_soon_payload(
            "resolve",
            query=query,
            limit=limit,
            resolved=False,
            confidence="none",
            match=None,
            next_command=None,
            candidates=[],
        ),
    )


@app.command("guide")
def guide(ctx: typer.Context, guide_ref: str = typer.Argument(...)) -> None:
    _emit(ctx, _coming_soon_payload("guide", guide_ref=guide_ref))


@app.command("guide-full")
def guide_full(ctx: typer.Context, guide_ref: str = typer.Argument(...)) -> None:
    _emit(ctx, _coming_soon_payload("guide-full", guide_ref=guide_ref))


@app.command("guide-export")
def guide_export(ctx: typer.Context, guide_ref: str = typer.Argument(...)) -> None:
    _emit(ctx, _coming_soon_payload("guide-export", guide_ref=guide_ref))


@app.command("guide-query")
def guide_query(ctx: typer.Context, bundle_ref: str = typer.Argument(...), query: str = typer.Argument(...)) -> None:
    _emit(ctx, _coming_soon_payload("guide-query", bundle_ref=bundle_ref, query=query))


def run() -> None:
    app()


if __name__ == "__main__":
    run()
