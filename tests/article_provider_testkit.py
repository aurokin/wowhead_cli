from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

LIVE_ENABLED = os.getenv("WOWHEAD_LIVE_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}


def require_live(provider_name: str) -> None:
    if not LIVE_ENABLED:
        pytest.skip(f"Set WOWHEAD_LIVE_TESTS=1 to run live {provider_name} tests.")


def invoke_live(runner: CliRunner, app: Any, args: list[str], *, provider_name: str, attempts: int = 3):
    last_result = None
    for attempt in range(1, attempts + 1):
        result = runner.invoke(app, args)
        if result.exit_code == 0:
            return result
        last_result = result
        if attempt < attempts:
            time.sleep(float(attempt))
    assert last_result is not None
    pytest.fail(
        f"Live {provider_name} command failed after {attempts} attempts.\n"
        f"args={args}\n"
        f"exit_code={last_result.exit_code}\n"
        f"output={last_result.output[:2000]}"
    )


def payload_for_live(runner: CliRunner, app: Any, args: list[str], *, provider_name: str) -> dict[str, Any]:
    result = invoke_live(runner, app, args, provider_name=provider_name)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Command did not produce JSON.\nargs={args}\nstdout={result.stdout[:2000]}\n{exc}")
    assert payload.get("ok") is not False
    return payload


def error_payload(result: Any) -> dict[str, Any]:
    return json.loads(result.stderr or result.output)


def load_fixture_text(fixture_dir: Path, name: str) -> str:
    return (fixture_dir / name).read_text(encoding="utf-8")
