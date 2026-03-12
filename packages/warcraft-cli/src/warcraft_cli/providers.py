from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from typer.testing import CliRunner

from method_cli.main import app as method_app
from warcraft_content.paths import cache_root, config_root, data_root
from wowhead_cli.main import app as wowhead_app

runner = CliRunner()


@dataclass(frozen=True, slots=True)
class ProviderRegistration:
    name: str
    command: str
    language: str
    status: str
    description: str


PROVIDERS: tuple[ProviderRegistration, ...] = (
    ProviderRegistration(
        name="wowhead",
        command="wowhead",
        language="python",
        status="ready",
        description="Structured Wowhead provider with live search, resolve, and retrieval commands.",
    ),
    ProviderRegistration(
        name="method",
        command="method",
        language="python",
        status="ready",
        description="Method.gg article provider with sitemap-backed search and guide bundle export/query.",
    ),
)


def list_providers() -> tuple[ProviderRegistration, ...]:
    return PROVIDERS


def _invoke_provider_app(app: Any, args: list[str]) -> tuple[int, dict[str, Any] | None, str]:
    result = runner.invoke(app, args)
    payload: dict[str, Any] | None = None
    stdout = result.stdout.strip()
    if stdout:
        try:
            maybe_payload = json.loads(stdout)
        except json.JSONDecodeError:
            maybe_payload = None
        if isinstance(maybe_payload, dict):
            payload = maybe_payload
    return result.exit_code, payload, result.stdout


def provider_search(provider: str, query: str, *, limit: int = 5) -> dict[str, Any]:
    if provider == "wowhead":
        code, payload, _stdout = _invoke_provider_app(wowhead_app, ["search", query, "--limit", str(limit)])
    elif provider == "method":
        code, payload, _stdout = _invoke_provider_app(method_app, ["search", query, "--limit", str(limit)])
    else:
        raise ValueError(f"Unknown provider: {provider}")
    return {
        "provider": provider,
        "exit_code": code,
        "payload": payload,
    }


def provider_resolve(provider: str, query: str, *, limit: int = 5) -> dict[str, Any]:
    if provider == "wowhead":
        code, payload, _stdout = _invoke_provider_app(wowhead_app, ["resolve", query, "--limit", str(limit)])
    elif provider == "method":
        code, payload, _stdout = _invoke_provider_app(method_app, ["resolve", query, "--limit", str(limit)])
    else:
        raise ValueError(f"Unknown provider: {provider}")
    return {
        "provider": provider,
        "exit_code": code,
        "payload": payload,
    }


def provider_doctor(provider: str) -> dict[str, Any]:
    if provider == "wowhead":
        code, payload, _stdout = _invoke_provider_app(wowhead_app, ["cache-inspect", "--summary", "--hide-zero"])
        return {
            "provider": provider,
            "status": "ready" if code == 0 else "error",
            "command": "wowhead",
            "language": "python",
            "installed": True,
            "details": payload,
        }
    if provider == "method":
        code, payload, _stdout = _invoke_provider_app(method_app, ["doctor"])
        return {
            "provider": provider,
            "status": "ready" if code == 0 else "error",
            "command": "method",
            "language": "python",
            "installed": True,
            "details": payload,
        }
    raise ValueError(f"Unknown provider: {provider}")


def global_doctor_payload() -> dict[str, Any]:
    return {
        "wrapper": {
            "provider_count": len(PROVIDERS),
            "python_first": True,
            "shell_fallback": True,
        },
        "paths": {
            "config_root": str(config_root()),
            "data_root": str(data_root()),
            "cache_root": str(cache_root()),
        },
        "providers": [provider_doctor(provider.name) for provider in PROVIDERS],
    }
