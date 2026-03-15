from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import httpx
import typer
from icy_veins_cli.main import app as icy_veins_app
from method_cli.main import app as method_app
from raiderio_cli.client import RaiderIOClient
from raiderio_cli.main import app as raiderio_app
from simc_cli.main import app as simc_app
from typer.main import get_command
from warcraft_content.article_bundle import compare_article_bundles, load_article_bundle
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
from warcraft_core.wow_normalization import normalize_name, normalize_region, primary_realm_slug
from warcraft_wiki_cli.main import app as warcraft_wiki_app
from warcraftlogs_cli.main import app as warcraftlogs_app
from wowhead_cli.expansion_profiles import resolve_expansion
from wowhead_cli.main import app as wowhead_app
from wowprogress_cli.client import WowProgressClient, WowProgressClientError
from wowprogress_cli.main import app as wowprogress_app

from warcraft_cli.providers import (
    expansion_filtered_providers,
    expansion_support_snapshot,
    get_provider,
    global_doctor_payload,
    list_providers,
    provider_expansion_exclusion_reason,
    provider_expansion_support,
    provider_invoke,
    provider_resolve,
    provider_search,
)

app = typer.Typer(add_completion=False, help="Warcraft wrapper CLI for routing to service-specific Warcraft CLIs.")
GUIDE_COMPARE_BUNDLES_ARGUMENT = typer.Argument(
    ...,
    help="Two or more exported guide bundle directories from wowhead, method, or icy-veins.",
)
GUIDE_COMPARE_QUERY_PROVIDERS = ("wowhead", "method", "icy-veins")


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


def _slugify_path_fragment(value: str) -> str:
    parts = [
        part
        for part in "".join(
            character.lower() if character.isalnum() else " "
            for character in value.strip()
        ).split()
        if part
    ]
    if not parts:
        return "query"
    return "-".join(parts[:12])


def _default_guide_compare_query_root(query: str) -> Path:
    return Path.cwd() / "warcraft_guide_compare" / _slugify_path_fragment(query)


def _guide_compare_manifest_path(root: Path) -> Path:
    return root / "manifest.json"


def _iso_now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso8601_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _guide_compare_freshness(exported_at: Any, *, max_age_hours: int) -> dict[str, Any]:
    parsed = _parse_iso8601_utc(exported_at)
    if parsed is None:
        return {"status": "stale", "reason": "missing_exported_at", "age_hours": None, "max_age_hours": max_age_hours}
    age_hours = round((datetime.now(timezone.utc) - parsed).total_seconds() / 3600, 2)
    if age_hours > max_age_hours:
        return {"status": "stale", "reason": "max_age_exceeded", "age_hours": age_hours, "max_age_hours": max_age_hours}
    return {"status": "fresh", "reason": "within_max_age", "age_hours": age_hours, "max_age_hours": max_age_hours}


def _load_guide_compare_manifest(root: Path) -> dict[str, Any] | None:
    path = _guide_compare_manifest_path(root)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_guide_compare_manifest(
    *,
    root: Path,
    query: str,
    requested_expansion: str | None,
    max_age_hours: int,
    provider_results: list[dict[str, Any]],
) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for row in provider_results:
        if row.get("status") not in {"exported", "reused"}:
            continue
        candidate = row.get("candidate") if isinstance(row.get("candidate"), dict) else {}
        freshness = row.get("freshness") if isinstance(row.get("freshness"), dict) else {}
        providers.append(
            {
                "provider": row.get("provider"),
                "bundle_path": row.get("bundle_path"),
                "candidate_ref": candidate.get("ref"),
                "candidate_name": candidate.get("name"),
                "selection_source": candidate.get("selection_source"),
                "exported_at": row.get("exported_at"),
                "freshness": freshness,
            }
        )
    payload = {
        "kind": "guide_compare_orchestration_manifest",
        "updated_at": _iso_now_utc(),
        "query": query,
        "requested_expansion": requested_expansion,
        "max_age_hours": max_age_hours,
        "providers": providers,
    }
    root.mkdir(parents=True, exist_ok=True)
    _guide_compare_manifest_path(root).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def _load_guide_build_source(source_path: Path) -> tuple[str, list[tuple[Path, dict[str, Any]]], dict[str, Any] | None]:
    manifest_path = source_path / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Missing manifest file under {source_path}.")
    try:
        raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid manifest under {source_path}: {exc}") from exc
    if not isinstance(raw_manifest, dict):
        raise ValueError(f"Manifest under {source_path} is not a JSON object.")
    if raw_manifest.get("kind") == "guide_compare_orchestration_manifest":
        bundle_inputs: list[tuple[Path, dict[str, Any]]] = []
        providers = raw_manifest.get("providers")
        if not isinstance(providers, list):
            raise ValueError(f"Orchestration manifest under {source_path} is missing providers.")
        for row in providers:
            if not isinstance(row, dict):
                continue
            bundle_path_raw = row.get("bundle_path")
            if not isinstance(bundle_path_raw, str) or not bundle_path_raw.strip():
                continue
            bundle_path = Path(bundle_path_raw).expanduser()
            bundle_inputs.append((bundle_path, load_article_bundle(bundle_path)))
        return "orchestration_root", bundle_inputs, raw_manifest
    return "bundle", [(source_path, load_article_bundle(source_path))], raw_manifest


def _collect_build_reference_handoff_rows(
    bundle_inputs: list[tuple[Path, dict[str, Any]]],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for bundle_path, bundle in bundle_inputs:
        manifest = bundle.get("manifest") if isinstance(bundle.get("manifest"), dict) else {}
        provider = manifest.get("provider") if isinstance(manifest.get("provider"), str) else None
        for row in bundle.get("build_references") or []:
            if not isinstance(row, dict):
                continue
            ref_url = row.get("url")
            if not isinstance(ref_url, str) or not ref_url.strip():
                continue
            record = grouped.get(ref_url)
            source_entry = {
                "provider": provider,
                "bundle_path": str(bundle_path),
                "label": row.get("label"),
                "source_urls": list(row.get("source_urls") or []),
                "build_identity": row.get("build_identity"),
            }
            if record is None:
                grouped[ref_url] = {
                    "reference": {
                        "url": ref_url,
                        "reference_type": row.get("reference_type"),
                        "build_code": row.get("build_code"),
                        "label": row.get("label"),
                        "build_identity": row.get("build_identity"),
                    },
                    "sources": [source_entry],
                }
                continue
            record["sources"].append(source_entry)
    return sorted(grouped.values(), key=lambda row: str(((row.get("reference") or {}).get("url")) or ""))


def _normalize_guide_compare_providers(values: list[str]) -> tuple[str, ...]:
    selected = [value.strip() for raw in values for value in raw.split(",") if value.strip()]
    if not selected:
        return GUIDE_COMPARE_QUERY_PROVIDERS
    invalid = sorted(provider for provider in selected if provider not in GUIDE_COMPARE_QUERY_PROVIDERS)
    if invalid:
        supported = ", ".join(GUIDE_COMPARE_QUERY_PROVIDERS)
        raise ValueError(
            f"Unsupported guide comparison providers: {', '.join(invalid)}. Supported providers: {supported}."
        )
    deduped: list[str] = []
    for provider in selected:
        if provider not in deduped:
            deduped.append(provider)
    return tuple(deduped)


def _resolved_guide_match(provider: str, payload: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "missing_payload"
    if not payload.get("resolved"):
        return None, "provider_did_not_resolve_query"
    match = payload.get("match")
    if not isinstance(match, dict):
        return None, "missing_resolved_match"
    entity_type = match.get("entity_type")
    if entity_type != "guide":
        return None, f"resolved_non_guide:{entity_type}"
    raw_ref = match.get("id")
    if raw_ref is None:
        metadata = match.get("metadata")
        if isinstance(metadata, dict):
            raw_ref = metadata.get("slug")
    if raw_ref is None:
        return None, "resolved_guide_missing_ref"
    ref = str(raw_ref)
    return {
        "provider": provider,
        "ref": ref,
        "name": match.get("name"),
        "url": match.get("url"),
        "confidence": payload.get("confidence"),
        "next_command": payload.get("next_command"),
        "selection_source": "resolve",
    }, None


def _search_fallback_guide_match(
    provider: str,
    payload: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "missing_search_payload"
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        return None, "provider_search_returned_no_results"
    top = results[0]
    if not isinstance(top, dict):
        return None, "invalid_search_top_candidate"
    if top.get("entity_type") != "guide":
        return None, f"search_top_non_guide:{top.get('entity_type')}"

    ranking = top.get("ranking")
    top_score = int(ranking.get("score") or 0) if isinstance(ranking, dict) else 0
    second_score = 0
    if len(results) > 1 and isinstance(results[1], dict):
        second_ranking = results[1].get("ranking")
        second_score = int(second_ranking.get("score") or 0) if isinstance(second_ranking, dict) else 0
    if top_score < 30:
        return None, f"search_top_guide_score_too_low:{top_score}"
    if top_score < 50 and top_score < second_score + 15:
        return None, "search_results_not_decisive"

    raw_ref = top.get("id")
    if raw_ref is None:
        metadata = top.get("metadata")
        if isinstance(metadata, dict):
            raw_ref = metadata.get("slug")
    if raw_ref is None:
        return None, "search_guide_missing_ref"

    return {
        "provider": provider,
        "ref": str(raw_ref),
        "name": top.get("name"),
        "url": top.get("url"),
        "confidence": "medium",
        "next_command": (
            top.get("follow_up", {}).get("recommended_command")
            if isinstance(top.get("follow_up"), dict)
            else None
        ),
        "selection_source": "search_fallback",
        "search_ranking": ranking,
    }, None


def _normalized_identity(region: str, realm: str, name: str) -> dict[str, str]:
    return {
        "region": normalize_region(region),
        "realm": primary_realm_slug(realm),
        "name": normalize_name(name),
    }


def _raiderio_source(identity: dict[str, str]) -> dict[str, Any]:
    try:
        with RaiderIOClient() as client:
            payload = client.guild_profile_variants(**identity)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        return {
            "provider": "raiderio",
            "status": "error",
            "error": {
                "code": "not_found" if status_code == 404 else "upstream_error",
                "message": f"Raider.IO request failed with HTTP {status_code}.",
            },
        }
    progression = payload.get("raid_progression") if isinstance(payload.get("raid_progression"), dict) else {}
    rankings = payload.get("raid_rankings") if isinstance(payload.get("raid_rankings"), dict) else {}
    active_key = next(iter(progression), None)
    active_progress = progression.get(active_key) if isinstance(active_key, str) else None
    active_rankings = rankings.get(active_key) if isinstance(active_key, str) else None
    members = payload.get("members") if isinstance(payload.get("members"), list) else []
    roster_preview = [
        {
            "name": ((row.get("character") or {}).get("name") if isinstance(row, dict) else None),
            "class_name": ((row.get("character") or {}).get("class") if isinstance(row, dict) else None),
            "spec_name": ((row.get("character") or {}).get("active_spec_name") if isinstance(row, dict) else None),
            "role": ((row.get("character") or {}).get("active_spec_role") if isinstance(row, dict) else None),
            "profile_url": ((row.get("character") or {}).get("profile_url") if isinstance(row, dict) else None),
        }
        for row in members[:10]
        if isinstance(row, dict) and isinstance(row.get("character"), dict)
    ]
    return {
        "provider": "raiderio",
        "status": "ok",
        "guild": {
            "name": payload.get("name"),
            "region": payload.get("region"),
            "realm": payload.get("realm"),
            "faction": payload.get("faction"),
            "profile_url": payload.get("profile_url"),
        },
        "active_raid": {
            "key": active_key,
            "summary": active_progress.get("summary") if isinstance(active_progress, dict) else None,
            "boss_count": active_progress.get("total_bosses") if isinstance(active_progress, dict) else None,
            "rankings": active_rankings,
        },
        "roster": {
            "member_count": len(members),
            "preview": roster_preview,
        },
        "citations": {
            "profile_url": payload.get("profile_url"),
        },
    }


def _wowprogress_source(identity: dict[str, str]) -> dict[str, Any]:
    try:
        with WowProgressClient() as client:
            payload = client.fetch_guild_page_variants(**identity)
    except WowProgressClientError as exc:
        return {
            "provider": "wowprogress",
            "status": "error",
            "error": {"code": exc.code, "message": exc.message},
        }
    progress = payload.get("progress") if isinstance(payload.get("progress"), dict) else {}
    item_level = payload.get("item_level") if isinstance(payload.get("item_level"), dict) else {}
    encounters = payload.get("encounters") if isinstance(payload.get("encounters"), dict) else {}
    items = encounters.get("items") if isinstance(encounters.get("items"), list) else []
    guild = payload.get("guild") if isinstance(payload.get("guild"), dict) else {}
    return {
        "provider": "wowprogress",
        "status": "ok",
        "guild": guild,
        "active_raid": {
            "name": progress.get("raid"),
            "tier_key": progress.get("tier_key"),
            "summary": progress.get("summary"),
            "boss_count": len(items),
            "rankings": progress.get("ranks"),
        },
        "item_level": item_level,
        "encounters": {
            "count": encounters.get("count"),
            "preview": items[:10],
        },
        "citations": payload.get("citations"),
    }


def _guild_conflicts(raiderio: dict[str, Any] | None, wowprogress: dict[str, Any] | None) -> dict[str, Any]:
    reasons: list[str] = []
    different_window = False
    if raiderio and wowprogress:
        ri_bosses = ((raiderio.get("active_raid") or {}).get("boss_count") if isinstance(raiderio.get("active_raid"), dict) else None)
        wp_bosses = ((wowprogress.get("active_raid") or {}).get("boss_count") if isinstance(wowprogress.get("active_raid"), dict) else None)
        ri_summary = str(((raiderio.get("active_raid") or {}).get("summary")) or "")
        wp_summary = str(((wowprogress.get("active_raid") or {}).get("summary")) or "")
        if ri_bosses != wp_bosses or (ri_summary and wp_summary and ri_summary != wp_summary):
            different_window = True
            reasons.append("providers_report_different_active_raid_windows")
    return {
        "different_tier_window_detected": different_window,
        "reasons": reasons,
    }


def _guild_merge_payload(identity: dict[str, str], *, raiderio: dict[str, Any], wowprogress: dict[str, Any]) -> dict[str, Any]:
    ri_ok = raiderio.get("status") == "ok"
    wp_ok = wowprogress.get("status") == "ok"
    if not ri_ok and not wp_ok:
        return {
            "ok": False,
            "error": {
                "code": "guild_not_found",
                "message": "No guild provider returned a guild snapshot for that query.",
            },
            "query": identity,
            "sources": {
                "raiderio": raiderio,
                "wowprogress": wowprogress,
            },
        }
    preferred_guild = (wowprogress.get("guild") if wp_ok else None) or (raiderio.get("guild") if ri_ok else None) or {}
    return {
        "ok": True,
        "provider": "warcraft",
        "kind": "guild_snapshot",
        "query": identity,
        "guild": {
            "name": preferred_guild.get("name"),
            "region": preferred_guild.get("region") or identity["region"],
            "realm": preferred_guild.get("realm") or identity["realm"],
            "faction": preferred_guild.get("faction"),
        },
        "sources": {
            "raiderio": raiderio,
            "wowprogress": wowprogress,
        },
        "conflicts": _guild_conflicts(
            raiderio if ri_ok else None,
            wowprogress if wp_ok else None,
        ),
    }


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


@app.command("guild")
def guild(
    ctx: typer.Context,
    region: str = typer.Argument(..., help="Region slug such as us or eu."),
    realm: str = typer.Argument(..., help="Realm title or slug."),
    name: str = typer.Argument(..., help="Guild name."),
) -> None:
    identity = _normalized_identity(region, realm, name)
    payload = _guild_merge_payload(
        identity,
        raiderio=_raiderio_source(identity),
        wowprogress=_wowprogress_source(identity),
    )
    _emit(payload, pretty=_pretty(ctx), err=not payload.get("ok"))
    if not payload.get("ok"):
        raise typer.Exit(1)


@app.command("guild-history")
def guild_history(
    ctx: typer.Context,
    region: str = typer.Argument(..., help="Region slug such as us or eu."),
    realm: str = typer.Argument(..., help="Realm title or slug."),
    name: str = typer.Argument(..., help="Guild name."),
) -> None:
    identity = _normalized_identity(region, realm, name)
    try:
        with WowProgressClient() as client:
            payload = client.fetch_guild_history(**identity)
    except WowProgressClientError as exc:
        _emit(
            {
                "ok": False,
                "error": {"code": exc.code, "message": exc.message},
                "query": identity,
                "source": "wowprogress",
            },
            pretty=_pretty(ctx),
            err=True,
        )
        raise typer.Exit(1)
    history = payload.get("history") if isinstance(payload.get("history"), list) else []
    _emit(
        {
            "ok": True,
            "provider": "warcraft",
            "kind": "guild_history",
            "query": identity,
            "source": "wowprogress",
            "guild": payload.get("guild"),
            "count": len(history),
            "tiers": history,
            "citations": payload.get("citations"),
        },
        pretty=_pretty(ctx),
    )


@app.command("guild-ranks")
def guild_ranks(
    ctx: typer.Context,
    region: str = typer.Argument(..., help="Region slug such as us or eu."),
    realm: str = typer.Argument(..., help="Realm title or slug."),
    name: str = typer.Argument(..., help="Guild name."),
) -> None:
    identity = _normalized_identity(region, realm, name)
    try:
        with WowProgressClient() as client:
            payload = client.fetch_guild_history(**identity)
    except WowProgressClientError as exc:
        _emit(
            {
                "ok": False,
                "error": {"code": exc.code, "message": exc.message},
                "query": identity,
                "source": "wowprogress",
            },
            pretty=_pretty(ctx),
            err=True,
        )
        raise typer.Exit(1)
    history = payload.get("history") if isinstance(payload.get("history"), list) else []
    _emit(
        {
            "ok": True,
            "provider": "warcraft",
            "kind": "guild_ranks",
            "query": identity,
            "source": "wowprogress",
            "guild": payload.get("guild"),
            "count": len(history),
            "tiers": [
                {
                    "tier_key": row.get("tier_key"),
                    "raid": row.get("raid"),
                    "current": row.get("current"),
                    "progress": row.get("progress"),
                    "progress_ranks": row.get("progress_ranks"),
                    "item_level_average": row.get("item_level_average"),
                    "item_level_ranks": row.get("item_level_ranks"),
                    "last_kill_at": row.get("last_kill_at"),
                    "page_url": row.get("page_url"),
                }
                for row in history
                if isinstance(row, dict)
            ],
            "citations": payload.get("citations"),
        },
        pretty=_pretty(ctx),
    )


@app.command("guide-compare")
def guide_compare(
    ctx: typer.Context,
    bundles: list[Path] = GUIDE_COMPARE_BUNDLES_ARGUMENT,
) -> None:
    if len(bundles) < 2:
        _emit(
            {
                "ok": False,
                "error": {
                    "code": "invalid_argument",
                    "message": "guide-compare requires at least two exported guide bundles.",
                },
            },
            pretty=_pretty(ctx),
            err=True,
        )
        raise typer.Exit(1)

    bundle_inputs: list[tuple[Path, dict[str, Any]]] = []
    for bundle_path in bundles:
        resolved_path = bundle_path.expanduser()
        if not resolved_path.exists():
            _emit(
                {
                    "ok": False,
                    "error": {
                        "code": "invalid_bundle",
                        "message": f"Bundle directory not found: {resolved_path}",
                    },
                },
                pretty=_pretty(ctx),
                err=True,
            )
            raise typer.Exit(1)
        try:
            bundle_inputs.append((resolved_path, load_article_bundle(resolved_path)))
        except (ValueError, OSError) as exc:
            _emit(
                {
                    "ok": False,
                    "error": {
                        "code": "invalid_bundle",
                        "message": str(exc),
                    },
                    "bundle": str(resolved_path),
                },
                pretty=_pretty(ctx),
                err=True,
            )
            raise typer.Exit(1) from exc

    payload = {
        "provider": "warcraft",
        **compare_article_bundles(bundle_inputs),
    }
    _emit(payload, pretty=_pretty(ctx))


@app.command("guide-compare-query")
def guide_compare_query(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Guide query to resolve across supported guide providers."),
    provider: list[str] = typer.Option(
        [],
        "--provider",
        help="Restrict orchestration to one or more providers from: wowhead, method, icy-veins.",
    ),
    out_root: Path | None = typer.Option(
        None,
        "--out-root",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True,
        help="Directory root where orchestrated guide bundles should be written.",
    ),
    limit: int = typer.Option(
        5,
        "--limit",
        min=1,
        max=20,
        help="Maximum provider-local resolve candidates to request before selecting one guide match.",
    ),
    max_age_hours: int = typer.Option(
        24,
        "--max-age-hours",
        min=1,
        max=24 * 30,
        help="Reuse existing orchestrated guide bundles only when they are newer than this many hours.",
    ),
    force_refresh: bool = typer.Option(
        False,
        "--force-refresh/--no-force-refresh",
        help="Re-export selected guide bundles even when a fresh orchestrated bundle already exists.",
    ),
) -> None:
    requested_expansion = _requested_expansion(ctx)
    try:
        selected_providers = _normalize_guide_compare_providers(provider)
    except ValueError as exc:
        _emit(
            {
                "ok": False,
                "error": {"code": "invalid_argument", "message": str(exc)},
            },
            pretty=_pretty(ctx),
            err=True,
        )
        raise typer.Exit(1) from exc

    orchestration_root = (out_root or _default_guide_compare_query_root(query)).expanduser()
    orchestration_manifest = _load_guide_compare_manifest(orchestration_root) or {}
    manifest_rows = orchestration_manifest.get("providers")
    manifest_by_provider: dict[str, dict[str, Any]] = {}
    if isinstance(manifest_rows, list):
        for row in manifest_rows:
            if not isinstance(row, dict):
                continue
            provider_name = row.get("provider")
            if isinstance(provider_name, str):
                manifest_by_provider[provider_name] = row
    provider_rows: list[dict[str, Any]] = []
    bundle_inputs: list[tuple[Path, dict[str, Any]]] = []

    for provider_name in selected_providers:
        registration = get_provider(provider_name)
        exclusion_reason = provider_expansion_exclusion_reason(
            registration,
            requested_expansion=requested_expansion,
        )
        if exclusion_reason is not None:
            provider_rows.append(
                {
                    "provider": provider_name,
                    "status": "skipped",
                    "reason": exclusion_reason,
                    "expansion_support": provider_expansion_support(
                        registration,
                        requested_expansion=requested_expansion,
                    ),
                }
            )
            continue

        resolved = provider_resolve(
            provider_name,
            query,
            limit=limit,
            expansion=requested_expansion,
        )
        candidate, candidate_reason = _resolved_guide_match(
            provider_name,
            resolved.get("payload") if isinstance(resolved, dict) else None,
        )
        search_payload: dict[str, Any] | None = None
        if candidate is None:
            searched = provider_search(
                provider_name,
                query,
                limit=limit,
                expansion=requested_expansion,
            )
            search_payload = searched.get("payload") if isinstance(searched, dict) else None
            fallback_candidate, fallback_reason = _search_fallback_guide_match(
                provider_name,
                search_payload,
            )
            if fallback_candidate is not None:
                candidate = fallback_candidate
                candidate_reason = None
            else:
                candidate_reason = fallback_reason if fallback_reason is not None else candidate_reason
        if candidate is None:
            provider_rows.append(
                {
                    "provider": provider_name,
                    "status": "skipped",
                    "reason": candidate_reason,
                    "resolve": resolved.get("payload") if isinstance(resolved, dict) else None,
                    "search": search_payload,
                }
            )
            continue

        export_dir = orchestration_root / provider_name
        existing_row = manifest_by_provider.get(provider_name)
        existing_freshness = (
            _guide_compare_freshness(existing_row.get("exported_at"), max_age_hours=max_age_hours)
            if isinstance(existing_row, dict)
            else {"status": "stale", "reason": "missing_manifest_row", "age_hours": None, "max_age_hours": max_age_hours}
        )
        same_candidate = (
            isinstance(existing_row, dict)
            and str(existing_row.get("candidate_ref") or "") == str(candidate["ref"])
            and str(existing_row.get("bundle_path") or "") == str(export_dir)
        )
        can_reuse = (
            not force_refresh
            and same_candidate
            and existing_freshness.get("status") == "fresh"
            and export_dir.exists()
        )
        if can_reuse:
            try:
                bundle_inputs.append((export_dir, load_article_bundle(export_dir)))
            except (ValueError, OSError) as exc:
                provider_rows.append(
                    {
                        "provider": provider_name,
                        "status": "error",
                        "reason": "invalid_exported_bundle",
                        "candidate": candidate,
                        "bundle_path": str(export_dir),
                        "freshness": existing_freshness,
                        "error": str(exc),
                    }
                )
                continue
            provider_rows.append(
                {
                    "provider": provider_name,
                    "status": "reused",
                    "candidate": candidate,
                    "bundle_path": str(export_dir),
                    "freshness": existing_freshness,
                    "exported_at": existing_row.get("exported_at") if isinstance(existing_row, dict) else None,
                }
            )
            continue

        export_result = provider_invoke(
            provider_name,
            ["guide-export", candidate["ref"], "--out", str(export_dir)],
            expansion=requested_expansion,
        )
        if export_result.get("exit_code") != 0:
            provider_rows.append(
                {
                    "provider": provider_name,
                    "status": "error",
                    "reason": "guide_export_failed",
                    "candidate": candidate,
                    "bundle_path": str(export_dir),
                    "freshness": existing_freshness,
                    "export": export_result.get("payload"),
                }
            )
            continue
        try:
            bundle_inputs.append((export_dir, load_article_bundle(export_dir)))
        except (ValueError, OSError) as exc:
            provider_rows.append(
                {
                    "provider": provider_name,
                    "status": "error",
                    "reason": "invalid_exported_bundle",
                    "candidate": candidate,
                    "bundle_path": str(export_dir),
                    "freshness": existing_freshness,
                    "error": str(exc),
                }
            )
            continue

        exported_at = _iso_now_utc()
        provider_rows.append(
            {
                "provider": provider_name,
                "status": "exported",
                "candidate": candidate,
                "bundle_path": str(export_dir),
                "freshness": _guide_compare_freshness(exported_at, max_age_hours=max_age_hours),
                "exported_at": exported_at,
                "export": export_result.get("payload"),
            }
        )

    payload: dict[str, Any] = {
        "provider": "warcraft",
        "kind": "guide_bundle_comparison_orchestration",
        "query": query,
        "requested_expansion": requested_expansion,
        "selected_providers": list(selected_providers),
        "output_root": str(orchestration_root),
        "max_age_hours": max_age_hours,
        "force_refresh": force_refresh,
        "provider_results": provider_rows,
        "exported_bundle_count": len(bundle_inputs),
        "comparison": None,
    }
    payload["manifest"] = _write_guide_compare_manifest(
        root=orchestration_root,
        query=query,
        requested_expansion=requested_expansion,
        max_age_hours=max_age_hours,
        provider_results=provider_rows,
    )
    if len(bundle_inputs) >= 2:
        payload["comparison"] = {
            "provider": "warcraft",
            **compare_article_bundles(bundle_inputs),
        }
        _emit(payload, pretty=_pretty(ctx))
        return

    payload["ok"] = False
    payload["error"] = {
        "code": "insufficient_guides",
        "message": "Need at least two exported guide bundles to compare.",
    }
    _emit(payload, pretty=_pretty(ctx), err=True)
    raise typer.Exit(1)


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
    "warcraftlogs",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def warcraftlogs_passthrough(ctx: typer.Context) -> None:
    _invoke_sub_app(
        warcraftlogs_app,
        args=_passthrough_args(ctx, provider_name="warcraftlogs"),
        prog_name="warcraftlogs",
    )


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
