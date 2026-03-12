from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from icy_veins_cli.main import app as icy_veins_app
from raiderio_cli.main import app as raiderio_app
from simc_cli.main import app as simc_app
from warcraft_wiki_cli.main import app as warcraft_wiki_app
from wowprogress_cli.main import app as wowprogress_app
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
    app: Any
    doctor_args: tuple[str, ...]


PROVIDERS: tuple[ProviderRegistration, ...] = (
    ProviderRegistration(
        name="wowhead",
        command="wowhead",
        language="python",
        status="ready",
        description="Structured Wowhead provider with live search, resolve, and retrieval commands.",
        app=wowhead_app,
        doctor_args=("cache-inspect", "--summary", "--hide-zero"),
    ),
    ProviderRegistration(
        name="method",
        command="method",
        language="python",
        status="ready",
        description="Method.gg article provider with sitemap-backed search and guide bundle export/query.",
        app=method_app,
        doctor_args=("doctor",),
    ),
    ProviderRegistration(
        name="icy-veins",
        command="icy-veins",
        language="python",
        status="ready",
        description="Icy Veins article provider with sitemap-backed search, resolve, and guide bundle export/query.",
        app=icy_veins_app,
        doctor_args=("doctor",),
    ),
    ProviderRegistration(
        name="raiderio",
        command="raiderio",
        language="python",
        status="partial",
        description="Raider.IO API provider with direct character, guild, and mythic-plus runs lookups.",
        app=raiderio_app,
        doctor_args=("doctor",),
    ),
    ProviderRegistration(
        name="warcraft-wiki",
        command="warcraft-wiki",
        language="python",
        status="ready",
        description="Warcraft Wiki reference provider with MediaWiki-backed search, resolve, article export, and local query.",
        app=warcraft_wiki_app,
        doctor_args=("doctor",),
    ),
    ProviderRegistration(
        name="wowprogress",
        command="wowprogress",
        language="python",
        status="partial",
        description="WowProgress rankings provider with direct guild, character, and PvE leaderboard lookups.",
        app=wowprogress_app,
        doctor_args=("doctor",),
    ),
    ProviderRegistration(
        name="simc",
        command="simc",
        language="python",
        status="partial",
        description="SimulationCraft local provider with repo inspection, build decoding, and local run workflows.",
        app=simc_app,
        doctor_args=("doctor",),
    ),
)


def list_providers() -> tuple[ProviderRegistration, ...]:
    return PROVIDERS


def get_provider(provider: str) -> ProviderRegistration:
    for registration in PROVIDERS:
        if registration.name == provider:
            return registration
    raise ValueError(f"Unknown provider: {provider}")


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
    registration = get_provider(provider)
    code, payload, _stdout = _invoke_provider_app(registration.app, ["search", query, "--limit", str(limit)])
    return {
        "provider": provider,
        "exit_code": code,
        "payload": payload,
    }


def provider_resolve(provider: str, query: str, *, limit: int = 5) -> dict[str, Any]:
    registration = get_provider(provider)
    code, payload, _stdout = _invoke_provider_app(registration.app, ["resolve", query, "--limit", str(limit)])
    return {
        "provider": provider,
        "exit_code": code,
        "payload": payload,
    }


def provider_doctor(provider: str) -> dict[str, Any]:
    registration = get_provider(provider)
    code, payload, _stdout = _invoke_provider_app(registration.app, list(registration.doctor_args))
    return {
        "provider": registration.name,
        "status": "ready" if code == 0 else "error",
        "command": registration.command,
        "language": registration.language,
        "installed": True,
        "details": payload,
    }


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
