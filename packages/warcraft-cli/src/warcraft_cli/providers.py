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
from wowhead_cli.expansion_profiles import list_profiles
from wowhead_cli.main import app as wowhead_app

runner = CliRunner()


@dataclass(frozen=True, slots=True)
class ProviderRegistration:
    name: str
    command: str
    language: str
    status: str
    description: str
    expansion_mode: str
    supported_expansions: tuple[str, ...]
    app: Any
    doctor_args: tuple[str, ...]


PROVIDERS: tuple[ProviderRegistration, ...] = (
    ProviderRegistration(
        name="wowhead",
        command="wowhead",
        language="python",
        status="ready",
        description="Structured Wowhead provider with live search, resolve, and retrieval commands.",
        expansion_mode="profiled",
        supported_expansions=tuple(profile.key for profile in list_profiles()),
        app=wowhead_app,
        doctor_args=("cache-inspect", "--summary", "--hide-zero"),
    ),
    ProviderRegistration(
        name="method",
        command="method",
        language="python",
        status="ready",
        description="Method.gg article provider with sitemap-backed search and guide bundle export/query.",
        expansion_mode="fixed",
        supported_expansions=("retail",),
        app=method_app,
        doctor_args=("doctor",),
    ),
    ProviderRegistration(
        name="icy-veins",
        command="icy-veins",
        language="python",
        status="ready",
        description="Icy Veins article provider with sitemap-backed search, resolve, and guide bundle export/query.",
        expansion_mode="fixed",
        supported_expansions=("retail",),
        app=icy_veins_app,
        doctor_args=("doctor",),
    ),
    ProviderRegistration(
        name="raiderio",
        command="raiderio",
        language="python",
        status="partial",
        description="Raider.IO API provider with search, resolve, character, guild, and mythic-plus runs lookups.",
        expansion_mode="fixed",
        supported_expansions=("retail",),
        app=raiderio_app,
        doctor_args=("doctor",),
    ),
    ProviderRegistration(
        name="warcraft-wiki",
        command="warcraft-wiki",
        language="python",
        status="ready",
        description="Warcraft Wiki reference provider with MediaWiki-backed search, resolve, article export, and local query.",
        expansion_mode="none",
        supported_expansions=(),
        app=warcraft_wiki_app,
        doctor_args=("doctor",),
    ),
    ProviderRegistration(
        name="wowprogress",
        command="wowprogress",
        language="python",
        status="partial",
        description="WowProgress rankings provider with structured search, conservative resolve, guild, character, and PvE leaderboard lookups.",
        expansion_mode="fixed",
        supported_expansions=("retail",),
        app=wowprogress_app,
        doctor_args=("doctor",),
    ),
    ProviderRegistration(
        name="simc",
        command="simc",
        language="python",
        status="partial",
        description="SimulationCraft local provider with repo inspection, build decoding, and local run workflows.",
        expansion_mode="none",
        supported_expansions=(),
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


def provider_expansion_support(registration: ProviderRegistration, *, requested_expansion: str | None = None) -> dict[str, Any]:
    allowed = provider_supports_expansion(registration, requested_expansion=requested_expansion)
    payload: dict[str, Any] = {
        "mode": registration.expansion_mode,
        "supported_expansions": list(registration.supported_expansions),
        "requested_expansion": requested_expansion,
        "allowed": allowed,
    }
    reason = provider_expansion_exclusion_reason(registration, requested_expansion=requested_expansion)
    if reason is not None:
        payload["exclusion_reason"] = reason
    return payload


def provider_supports_expansion(registration: ProviderRegistration, *, requested_expansion: str | None) -> bool:
    if requested_expansion is None:
        return True
    if registration.expansion_mode in {"profiled", "fixed"}:
        return requested_expansion in registration.supported_expansions
    return False


def provider_expansion_exclusion_reason(
    registration: ProviderRegistration,
    *,
    requested_expansion: str | None,
) -> str | None:
    if requested_expansion is None or provider_supports_expansion(registration, requested_expansion=requested_expansion):
        return None
    if registration.expansion_mode == "fixed":
        return "provider_fixed_to_other_expansion"
    if registration.expansion_mode == "profiled":
        return "provider_does_not_support_requested_expansion"
    return "provider_has_no_expansion_support"


def expansion_filtered_providers(
    *,
    requested_expansion: str | None,
) -> tuple[list[ProviderRegistration], list[dict[str, Any]]]:
    included: list[ProviderRegistration] = []
    excluded: list[dict[str, Any]] = []
    for registration in PROVIDERS:
        if provider_supports_expansion(registration, requested_expansion=requested_expansion):
            included.append(registration)
            continue
        excluded.append(
            {
                "provider": registration.name,
                "command": registration.command,
                "expansion_support": provider_expansion_support(
                    registration,
                    requested_expansion=requested_expansion,
                ),
            }
        )
    return included, excluded


def expansion_support_snapshot(*, requested_expansion: str | None) -> list[dict[str, Any]]:
    return [
        {
            "provider": registration.name,
            "command": registration.command,
            "expansion_support": provider_expansion_support(
                registration,
                requested_expansion=requested_expansion,
            ),
        }
        for registration in PROVIDERS
    ]


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


def provider_search(provider: str, query: str, *, limit: int = 5, expansion: str | None = None) -> dict[str, Any]:
    registration = get_provider(provider)
    args = ["search", query, "--limit", str(limit)]
    if expansion is not None and registration.name == "wowhead":
        args = ["--expansion", expansion, *args]
    code, payload, _stdout = _invoke_provider_app(registration.app, args)
    return {
        "provider": provider,
        "exit_code": code,
        "payload": payload,
    }


def provider_resolve(provider: str, query: str, *, limit: int = 5, expansion: str | None = None) -> dict[str, Any]:
    registration = get_provider(provider)
    args = ["resolve", query, "--limit", str(limit)]
    if expansion is not None and registration.name == "wowhead":
        args = ["--expansion", expansion, *args]
    code, payload, _stdout = _invoke_provider_app(registration.app, args)
    return {
        "provider": provider,
        "exit_code": code,
        "payload": payload,
    }


def provider_doctor(provider: str, *, requested_expansion: str | None = None) -> dict[str, Any]:
    registration = get_provider(provider)
    code, payload, _stdout = _invoke_provider_app(registration.app, list(registration.doctor_args))
    return {
        "provider": registration.name,
        "status": "ready" if code == 0 else "error",
        "command": registration.command,
        "language": registration.language,
        "installed": True,
        "expansion_support": provider_expansion_support(registration, requested_expansion=requested_expansion),
        "details": payload,
    }


def global_doctor_payload(*, requested_expansion: str | None = None) -> dict[str, Any]:
    included, excluded = expansion_filtered_providers(requested_expansion=requested_expansion)
    return {
        "wrapper": {
            "provider_count": len(PROVIDERS),
            "python_first": True,
            "shell_fallback": True,
            "requested_expansion": requested_expansion,
            "expansion_filter_active": requested_expansion is not None,
            "included_provider_count": len(included),
            "excluded_provider_count": len(excluded),
        },
        "paths": {
            "config_root": str(config_root()),
            "data_root": str(data_root()),
            "cache_root": str(cache_root()),
        },
        "providers": [provider_doctor(provider.name, requested_expansion=requested_expansion) for provider in PROVIDERS],
        "included_providers": [provider.name for provider in included],
        "excluded_providers": excluded,
    }
