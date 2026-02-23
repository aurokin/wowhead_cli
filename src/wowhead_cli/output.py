from __future__ import annotations

from typing import Any

import orjson
import typer


def to_json(payload: Any, *, pretty: bool) -> str:
    option = 0
    if pretty:
        option |= orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS
    return orjson.dumps(payload, option=option).decode("utf-8")


def emit(payload: Any, *, pretty: bool, err: bool = False) -> None:
    typer.echo(to_json(payload, pretty=pretty), err=err)

