from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

from simc_cli.apl import action_counts, group_entries, mermaid_graph, parse_apl, talent_refs, trace_action_entries
from simc_cli.branch import attach_focus_comparison, compare_branch_summaries, explain_intent, summarize_branches, summarize_intent, trace_apl
from simc_cli.build_input import decode_build, extract_build_spec_from_text, infer_actor_and_spec_from_apl, load_build_spec
from simc_cli.packet import build_analysis_packet
from simc_cli.prune import PruneContext, TruthValue, prune_entries, split_csv_values
from simc_cli.repo import RepoPaths, discover_repo, validate_build, validate_repo
from simc_cli.run import binary_version, build_repo, repo_git_status, run_profile, sync_repo
from simc_cli.search import find_action, spec_file_search
from warcraft_core.output import emit

app = typer.Typer(add_completion=False, help="SimulationCraft local workflow CLI.")


@dataclass(slots=True)
class RuntimeConfig:
    pretty: bool = False
    repo_root: str | None = None


def _cfg(ctx: typer.Context) -> RuntimeConfig:
    obj = ctx.obj
    if isinstance(obj, RuntimeConfig):
        return obj
    return RuntimeConfig()


def _emit(ctx: typer.Context, payload: dict[str, Any], *, err: bool = False) -> None:
    emit(payload, pretty=_cfg(ctx).pretty, err=err)


def _fail(ctx: typer.Context, code: str, message: str, *, status: int = 1, extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"ok": False, "error": {"code": code, "message": message}}
    if extra:
        payload.update(extra)
    _emit(ctx, payload, err=True)
    raise typer.Exit(status)


def _repo_paths(ctx: typer.Context) -> RepoPaths:
    return discover_repo(_cfg(ctx).repo_root)


def _preview_text(text: str, *, max_lines: int = 20) -> tuple[list[str], bool]:
    lines = text.splitlines()
    return lines[:max_lines], len(lines) > max_lines


def _repo_payload(paths: RepoPaths) -> dict[str, Any]:
    repo_issues = validate_repo(paths)
    build_issues = validate_build(paths)
    git_status = repo_git_status(paths)
    version = binary_version(paths)
    return {
        "root": str(paths.root),
        "exists": paths.root.exists(),
        "repo_ready": not repo_issues,
        "build_ready": not build_issues,
        "repo_issues": repo_issues,
        "build_issues": build_issues,
        "git": git_status,
        "binary": {
            "path": str(paths.build_simc),
            "exists": paths.build_simc.exists(),
            "version_line": version.version_line,
            "available": version.available,
        },
    }


def _coming_soon_payload(*, query: str, suggested_command: str) -> dict[str, Any]:
    return {
        "provider": "simc",
        "query": query,
        "search_query": query,
        "count": 0,
        "results": [],
        "candidates": [],
        "resolved": False,
        "confidence": "none",
        "match": None,
        "next_command": None,
        "fallback_search_command": None,
        "coming_soon": True,
        "message": "Free-text discovery is not implemented yet for simc phase 1. Use direct repo, spec-files, decode-build, or run commands.",
        "suggested_command": suggested_command,
    }


def _serialize_build_spec(spec: Any) -> dict[str, Any]:
    return {
        "actor_class": spec.actor_class,
        "spec": spec.spec,
        "talents": spec.talents,
        "class_talents": spec.class_talents,
        "spec_talents": spec.spec_talents,
        "hero_talents": spec.hero_talents,
        "source_notes": spec.source_notes,
    }


def _resolve_path(paths: RepoPaths, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = paths.root / path
    return path.resolve()


def _build_option_values(
    *,
    profile_path: str | None,
    build_file: str | None,
    build_text: str | None,
    talents: str | None,
    class_talents: str | None,
    spec_talents: str | None,
    hero_talents: str | None,
    actor_class: str | None,
    spec_name: str | None,
    enable: list[str],
    disable: list[str],
) -> dict[str, Any]:
    return {
        "profile_path": profile_path,
        "build_file": build_file,
        "build_text": build_text,
        "talents": talents,
        "class_talents": class_talents,
        "spec_talents": spec_talents,
        "hero_talents": hero_talents,
        "actor_class": actor_class,
        "spec_name": spec_name,
        "enable": enable,
        "disable": disable,
    }


def _resolve_prune_context(paths: RepoPaths, apl_path: Path, option_values: dict[str, Any], targets: int) -> tuple[PruneContext, Any]:
    build_spec = load_build_spec(
        apl_path=apl_path,
        profile_path=option_values["profile_path"],
        build_file=option_values["build_file"],
        build_text=option_values["build_text"],
        talents=option_values["talents"],
        class_talents=option_values["class_talents"],
        spec_talents=option_values["spec_talents"],
        hero_talents=option_values["hero_talents"],
        actor_class=option_values["actor_class"],
        spec_name=option_values["spec_name"],
    )
    resolution = decode_build(paths, build_spec)
    enabled = set(resolution.enabled_talents)
    enabled.update(split_csv_values(option_values["enable"]))
    disabled = split_csv_values(option_values["disable"])
    talent_sources = {
        talent.token: talent.tree
        for tree in ("class", "spec", "hero")
        for talent in resolution.talents_by_tree.get(tree, [])
    }
    for token in split_csv_values(option_values["enable"]):
        talent_sources[token] = "manual"
    context = PruneContext(
        enabled_talents=enabled,
        disabled_talents=disabled,
        targets=targets,
        talent_sources=talent_sources,
    )
    return context, resolution


@app.callback()
def main_callback(
    ctx: typer.Context,
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON output."),
    repo_root: str | None = typer.Option(None, "--repo-root", help="Override the local SimulationCraft checkout path."),
) -> None:
    ctx.obj = RuntimeConfig(pretty=pretty, repo_root=repo_root)


@app.command("doctor")
def doctor(ctx: typer.Context) -> None:
    paths = _repo_paths(ctx)
    repo = _repo_payload(paths)
    status = "ready" if repo["repo_ready"] and repo["build_ready"] else "degraded"
    _emit(
        ctx,
        {
            "provider": "simc",
            "status": status,
            "command": "doctor",
            "installed": True,
            "language": "python",
            "auth": {
                "required": False,
                "deferred": False,
            },
            "capabilities": {
                "search": "coming_soon",
                "resolve": "coming_soon",
                "doctor": "ready",
                "version": "ready",
                "sync": "ready",
                "build": "ready",
                "run": "ready",
                "inspect": "ready",
                "spec_files": "ready",
                "decode_build": "ready",
                "apl_lists": "ready",
                "apl_graph": "ready",
                "apl_talents": "ready",
                "find_action": "ready",
                "trace_action": "ready",
                "apl_prune": "ready",
                "apl_branch_trace": "ready",
                "apl_intent": "ready",
                "apl_intent_explain": "ready",
                "apl_branch_compare": "ready",
                "analysis_packet": "ready",
            },
            "repo": repo,
        },
    )


@app.command("search")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Free-text query. Structured discovery is deferred for simc phase 1."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Unused in phase 1."),
) -> None:
    del limit
    _emit(ctx, _coming_soon_payload(query=query, suggested_command="simc spec-files monk"))


@app.command("resolve")
def resolve(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Free-text query. Structured resolution is deferred for simc phase 1."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Unused in phase 1."),
) -> None:
    del limit
    _emit(ctx, _coming_soon_payload(query=query, suggested_command="simc decode-build --apl-path /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc"))


@app.command("version")
def version(ctx: typer.Context) -> None:
    version_info = binary_version(_repo_paths(ctx))
    if not version_info.available:
        _fail(ctx, "missing_binary", f"SimC binary not found: {version_info.binary_path}")
        return
    _emit(
        ctx,
        {
            "provider": "simc",
            "binary": {
                "path": str(version_info.binary_path),
                "available": version_info.available,
                "returncode": version_info.returncode,
            },
            "version": version_info.version_line,
        },
    )


@app.command("inspect")
def inspect(
    ctx: typer.Context,
    target: str | None = typer.Argument(None, help="Optional file path to inspect. If omitted, inspect the repo."),
) -> None:
    paths = _repo_paths(ctx)
    if target is None:
        _emit(ctx, {"provider": "simc", "inspect": "repo", "repo": _repo_payload(paths)})
        return
    resolved = Path(target).expanduser().resolve()
    if not resolved.exists():
        _fail(ctx, "not_found", f"Inspect target not found: {resolved}")
        return
    payload: dict[str, Any] = {
        "provider": "simc",
        "inspect": "path",
        "target": {
            "path": str(resolved),
            "relative_to_repo": str(resolved.relative_to(paths.root)) if resolved.is_relative_to(paths.root) else None,
            "kind": "directory" if resolved.is_dir() else "file",
        },
    }
    if resolved.is_file():
        text = resolved.read_text()
        inferred_class, inferred_spec = infer_actor_and_spec_from_apl(resolved)
        payload["target"].update(
            {
                "suffix": resolved.suffix,
                "line_count": len(text.splitlines()),
                "inferred_actor_class": inferred_class,
                "inferred_spec": inferred_spec,
                "build_spec": _serialize_build_spec(extract_build_spec_from_text(text)),
            }
        )
    _emit(ctx, payload)


@app.command("spec-files")
def spec_files(
    ctx: typer.Context,
    query: str | None = typer.Argument(None, help="Optional substring to narrow APL and class-module files."),
    limit: int = typer.Option(25, "--limit", min=1, max=200, help="Maximum file rows to return per category."),
) -> None:
    paths = _repo_paths(ctx)
    matches = spec_file_search(paths, query)
    categories: dict[str, Any] = {}
    total = 0
    for category, rows in matches.items():
        items = [
            {
                "path": str(path),
                "relative_path": str(path.relative_to(paths.root)) if path.is_relative_to(paths.root) else str(path),
                "stem": path.stem,
            }
            for path in rows[:limit]
        ]
        categories[category] = {
            "count": len(rows),
            "items": items,
            "truncated": len(rows) > limit,
        }
        total += len(rows)
    _emit(ctx, {"provider": "simc", "query": query, "count": total, "categories": categories})


@app.command("decode-build")
def decode_build_command(
    ctx: typer.Context,
    apl_path: str | None = typer.Option(None, "--apl-path", help="Optional APL path used to infer actor class and spec."),
    profile_path: str | None = typer.Option(None, "--profile-path", help="Optional profile path containing build lines."),
    build_file: str | None = typer.Option(None, "--build-file", help="Optional plain text file with talents/spec lines."),
    build_text: str | None = typer.Option(None, "--build-text", help="Inline build text or talent hash."),
    talents: str | None = typer.Option(None, "--talents", help="SimC talents string or talents=... line."),
    class_talents: str | None = typer.Option(None, "--class-talents", help="Split class talents string."),
    spec_talents: str | None = typer.Option(None, "--spec-talents", help="Split spec talents string."),
    hero_talents: str | None = typer.Option(None, "--hero-talents", help="Split hero talents string."),
    actor_class: str | None = typer.Option(None, "--actor-class", help="Actor class such as monk or evoker."),
    spec_name: str | None = typer.Option(None, "--spec", help="Spec name such as mistweaver."),
) -> None:
    paths = _repo_paths(ctx)
    build_spec = load_build_spec(
        apl_path=apl_path,
        profile_path=profile_path,
        build_file=build_file,
        build_text=build_text,
        talents=talents,
        class_talents=class_talents,
        spec_talents=spec_talents,
        hero_talents=hero_talents,
        actor_class=actor_class,
        spec_name=spec_name,
    )
    if not build_spec.actor_class or not build_spec.spec:
        _fail(ctx, "invalid_query", "Could not determine actor class and spec for build decoding.")
        return
    try:
        resolution = decode_build(paths, build_spec)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        _fail(ctx, "decode_failed", str(exc))
        return
    _emit(
        ctx,
        {
            "provider": "simc",
            "build_spec": _serialize_build_spec(build_spec),
            "decoded": {
                "actor_class": resolution.actor_class,
                "spec": resolution.spec,
                "enabled_talents": sorted(resolution.enabled_talents),
                "talents_by_tree": {
                    tree: [
                        {
                            "name": talent.name,
                            "token": talent.token,
                            "rank": talent.rank,
                            "max_rank": talent.max_rank,
                        }
                        for talent in talents
                    ]
                    for tree, talents in resolution.talents_by_tree.items()
                },
                "source_notes": resolution.source_notes,
            },
        },
    )


@app.command("apl-lists")
def apl_lists(
    ctx: typer.Context,
    apl_path: str = typer.Argument(..., help="Path to a .simc APL file."),
    list_name: str | None = typer.Option(None, "--list", help="Only return one action list."),
) -> None:
    paths = _repo_paths(ctx)
    resolved = _resolve_path(paths, apl_path)
    if not resolved.exists():
        _fail(ctx, "not_found", f"APL file not found: {resolved}")
        return
    entries = parse_apl(resolved)
    grouped = group_entries(entries)
    selected_names = [list_name] if list_name else sorted(grouped)
    lists_payload: list[dict[str, Any]] = []
    for current in selected_names:
        current_entries = grouped.get(current, [])
        lists_payload.append(
            {
                "list_name": current,
                "count": len(current_entries),
                "entries": [
                    {
                        "line_no": entry.line_no,
                        "action": entry.action,
                        "kind": entry.kind,
                        "target_list": entry.target_list,
                        "condition": entry.condition,
                        "raw": entry.raw,
                    }
                    for entry in current_entries
                ],
            }
        )
    _emit(
        ctx,
        {
            "provider": "simc",
            "apl": {
                "path": str(resolved),
                "relative_to_repo": str(resolved.relative_to(paths.root)) if resolved.is_relative_to(paths.root) else None,
                "entry_count": len(entries),
                "list_count": len(grouped),
            },
            "lists": lists_payload,
        },
    )


@app.command("apl-graph")
def apl_graph_command(
    ctx: typer.Context,
    apl_path: str = typer.Argument(..., help="Path to a .simc APL file."),
) -> None:
    paths = _repo_paths(ctx)
    resolved = _resolve_path(paths, apl_path)
    if not resolved.exists():
        _fail(ctx, "not_found", f"APL file not found: {resolved}")
        return
    entries = parse_apl(resolved)
    grouped = group_entries(entries)
    _emit(
        ctx,
        {
            "provider": "simc",
            "apl": {
                "path": str(resolved),
                "relative_to_repo": str(resolved.relative_to(paths.root)) if resolved.is_relative_to(paths.root) else None,
                "list_count": len(grouped),
            },
            "graph": {
                "format": "mermaid",
                "text": mermaid_graph(entries),
            },
        },
    )


@app.command("apl-talents")
def apl_talents_command(
    ctx: typer.Context,
    apl_path: str = typer.Argument(..., help="Path to a .simc APL file."),
) -> None:
    paths = _repo_paths(ctx)
    resolved = _resolve_path(paths, apl_path)
    if not resolved.exists():
        _fail(ctx, "not_found", f"APL file not found: {resolved}")
        return
    entries = parse_apl(resolved)
    refs = talent_refs(entries)
    counts = action_counts(entries)
    _emit(
        ctx,
        {
            "provider": "simc",
            "apl": {
                "path": str(resolved),
                "relative_to_repo": str(resolved.relative_to(paths.root)) if resolved.is_relative_to(paths.root) else None,
            },
            "count": len(refs),
            "talents": [{"token": token, "lines": lines} for token, lines in refs.items()],
            "action_counts": [{"name": name, "count": count} for name, count in counts.most_common(25)],
        },
    )


@app.command("find-action")
def find_action_command(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action, buff, or token to search for."),
    wow_class: str | None = typer.Option(None, "--class", help="Optional class name to narrow code and spell dumps."),
    limit: int = typer.Option(25, "--limit", min=1, max=200, help="Maximum hits to return per bucket."),
) -> None:
    paths = _repo_paths(ctx)
    results = find_action(paths, action, wow_class)
    buckets: dict[str, Any] = {}
    total = 0
    for bucket, hits in results.items():
        items = [
            {
                "path": str(hit.path),
                "relative_to_repo": str(hit.path.relative_to(paths.root)) if hit.path.is_relative_to(paths.root) else str(hit.path),
                "line_no": hit.line_no,
                "text": hit.text,
            }
            for hit in hits[:limit]
        ]
        buckets[bucket] = {
            "count": len(hits),
            "items": items,
            "truncated": len(hits) > limit,
        }
        total += len(hits)
    _emit(ctx, {"provider": "simc", "action": action, "class_filter": wow_class, "count": total, "buckets": buckets})


@app.command("trace-action")
def trace_action_command(
    ctx: typer.Context,
    apl_path: str = typer.Argument(..., help="Path to a .simc APL file."),
    action: str = typer.Argument(..., help="Action name to trace."),
    wow_class: str | None = typer.Option(None, "--class", help="Optional class name to narrow code and spell dumps."),
    limit: int = typer.Option(25, "--limit", min=1, max=200, help="Maximum non-APL hits to return per bucket."),
) -> None:
    paths = _repo_paths(ctx)
    resolved = _resolve_path(paths, apl_path)
    if not resolved.exists():
        _fail(ctx, "not_found", f"APL file not found: {resolved}")
        return
    entries = trace_action_entries(parse_apl(resolved), action)
    search_hits = find_action(paths, action, wow_class)
    buckets: dict[str, Any] = {}
    total = 0
    for bucket, hits in search_hits.items():
        items = [
            {
                "path": str(hit.path),
                "relative_to_repo": str(hit.path.relative_to(paths.root)) if hit.path.is_relative_to(paths.root) else str(hit.path),
                "line_no": hit.line_no,
                "text": hit.text,
            }
            for hit in hits[:limit]
        ]
        buckets[bucket] = {
            "count": len(hits),
            "items": items,
            "truncated": len(hits) > limit,
        }
        total += len(hits)
    _emit(
        ctx,
        {
            "provider": "simc",
            "action": action,
            "class_filter": wow_class,
            "apl": {
                "path": str(resolved),
                "relative_to_repo": str(resolved.relative_to(paths.root)) if resolved.is_relative_to(paths.root) else None,
            },
            "apl_hits": {
                "count": len(entries),
                "items": [
                    {
                        "line_no": entry.line_no,
                        "list_name": entry.list_name,
                        "action": entry.action,
                        "kind": entry.kind,
                        "target_list": entry.target_list,
                        "condition": entry.condition,
                        "raw": entry.raw,
                    }
                    for entry in entries
                ],
            },
            "external_hit_count": total,
            "buckets": buckets,
        },
    )


@app.command("apl-prune")
def apl_prune_command(
    ctx: typer.Context,
    apl_path: str = typer.Argument(..., help="Path to a .simc APL file."),
    targets: int = typer.Option(1, "--targets", min=1, help="Active target count."),
    list_name: str | None = typer.Option(None, "--list", help="Only return one action list."),
    show: str = typer.Option("all", "--show", help="One of all, eligible, dead, or unknown."),
    profile_path: str | None = typer.Option(None, "--profile-path", help="Optional profile path containing build lines."),
    build_file: str | None = typer.Option(None, "--build-file", help="Optional plain text file with talents/spec lines."),
    build_text: str | None = typer.Option(None, "--build-text", help="Inline build text or talent hash."),
    talents: str | None = typer.Option(None, "--talents", help="SimC talents string or talents=... line."),
    class_talents: str | None = typer.Option(None, "--class-talents", help="Split class talents string."),
    spec_talents: str | None = typer.Option(None, "--spec-talents", help="Split spec talents string."),
    hero_talents: str | None = typer.Option(None, "--hero-talents", help="Split hero talents string."),
    actor_class: str | None = typer.Option(None, "--actor-class", help="Actor class such as monk or evoker."),
    spec_name: str | None = typer.Option(None, "--spec", help="Spec name such as mistweaver."),
    enable: list[str] = typer.Option([], "--enable", help="Enabled talent names. Repeat or pass comma-separated values."),
    disable: list[str] = typer.Option([], "--disable", help="Disabled talent names. Repeat or pass comma-separated values."),
) -> None:
    if show not in {"all", "eligible", "dead", "unknown"}:
        _fail(ctx, "invalid_query", "--show must be one of: all, eligible, dead, unknown")
        return
    paths = _repo_paths(ctx)
    resolved = _resolve_path(paths, apl_path)
    if not resolved.exists():
        _fail(ctx, "not_found", f"APL file not found: {resolved}")
        return
    option_values = _build_option_values(
        profile_path=profile_path,
        build_file=build_file,
        build_text=build_text,
        talents=talents,
        class_talents=class_talents,
        spec_talents=spec_talents,
        hero_talents=hero_talents,
        actor_class=actor_class,
        spec_name=spec_name,
        enable=enable,
        disable=disable,
    )
    try:
        context, resolution = _resolve_prune_context(paths, resolved, option_values, targets)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        _fail(ctx, "prune_context_failed", str(exc))
        return
    grouped: dict[str, list[Any]] = {}
    for pruned in prune_entries(parse_apl(resolved), context):
        grouped.setdefault(pruned.entry.list_name, []).append(pruned)
    selected_names = [list_name] if list_name else sorted(grouped)
    lists_payload: list[dict[str, Any]] = []
    for current in selected_names:
        current_entries = grouped.get(current, [])
        items = []
        for pruned in current_entries:
            if show != "all" and pruned.state.value != show:
                continue
            items.append(
                {
                    "line_no": pruned.entry.line_no,
                    "action": pruned.entry.action,
                    "target_list": pruned.entry.target_list,
                    "condition": pruned.entry.condition,
                    "state": pruned.state.value,
                    "reason": pruned.reason,
                    "raw": pruned.entry.raw,
                }
            )
        lists_payload.append({"list_name": current, "count": len(items), "items": items})
    _emit(
        ctx,
        {
            "provider": "simc",
            "apl": {
                "path": str(resolved),
                "relative_to_repo": str(resolved.relative_to(paths.root)) if resolved.is_relative_to(paths.root) else None,
            },
            "build": {
                "actor_class": resolution.actor_class,
                "spec": resolution.spec,
                "targets": context.targets,
                "enabled_talents": len(context.enabled_talents),
                "source_notes": resolution.source_notes,
            },
            "show": show,
            "lists": lists_payload,
        },
    )


@app.command("apl-branch-trace")
def apl_branch_trace_command(
    ctx: typer.Context,
    apl_path: str = typer.Argument(..., help="Path to a .simc APL file."),
    targets: int = typer.Option(1, "--targets", min=1, help="Active target count."),
    list_name: str = typer.Option("default", "--list", help="Starting action list."),
    max_depth: int = typer.Option(6, "--max-depth", min=1, max=20, help="Maximum recursive trace depth."),
    profile_path: str | None = typer.Option(None, "--profile-path", help="Optional profile path containing build lines."),
    build_file: str | None = typer.Option(None, "--build-file", help="Optional plain text file with talents/spec lines."),
    build_text: str | None = typer.Option(None, "--build-text", help="Inline build text or talent hash."),
    talents: str | None = typer.Option(None, "--talents", help="SimC talents string or talents=... line."),
    class_talents: str | None = typer.Option(None, "--class-talents", help="Split class talents string."),
    spec_talents: str | None = typer.Option(None, "--spec-talents", help="Split spec talents string."),
    hero_talents: str | None = typer.Option(None, "--hero-talents", help="Split hero talents string."),
    actor_class: str | None = typer.Option(None, "--actor-class", help="Actor class such as monk or evoker."),
    spec_name: str | None = typer.Option(None, "--spec", help="Spec name such as mistweaver."),
    enable: list[str] = typer.Option([], "--enable", help="Enabled talent names. Repeat or pass comma-separated values."),
    disable: list[str] = typer.Option([], "--disable", help="Disabled talent names. Repeat or pass comma-separated values."),
) -> None:
    paths = _repo_paths(ctx)
    resolved = _resolve_path(paths, apl_path)
    if not resolved.exists():
        _fail(ctx, "not_found", f"APL file not found: {resolved}")
        return
    option_values = _build_option_values(
        profile_path=profile_path,
        build_file=build_file,
        build_text=build_text,
        talents=talents,
        class_talents=class_talents,
        spec_talents=spec_talents,
        hero_talents=hero_talents,
        actor_class=actor_class,
        spec_name=spec_name,
        enable=enable,
        disable=disable,
    )
    try:
        context, resolution = _resolve_prune_context(paths, resolved, option_values, targets)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        _fail(ctx, "branch_trace_failed", str(exc))
        return
    summary = summarize_branches(resolved, context, start_list=list_name)
    trace_lines = trace_apl(resolved, context, start_list=list_name, max_depth=max_depth)
    _emit(
        ctx,
        {
            "provider": "simc",
            "apl": {
                "path": str(resolved),
                "relative_to_repo": str(resolved.relative_to(paths.root)) if resolved.is_relative_to(paths.root) else None,
            },
            "build": {
                "actor_class": resolution.actor_class,
                "spec": resolution.spec,
                "targets": context.targets,
                "enabled_talents": len(context.enabled_talents),
                "source_notes": resolution.source_notes,
            },
            "summary": {
                "start_list": summary.start_list,
                "guaranteed_dispatch": summary.guaranteed_dispatch,
                "guaranteed_dispatch_line": summary.guaranteed_dispatch_line,
                "guaranteed_dispatch_reason": summary.guaranteed_dispatch_reason,
                "dead_branches": summary.dead_branches,
                "unresolved_branches": summary.unresolved_branches,
                "shadowed_lines": summary.shadowed_lines,
            },
            "trace": [{"depth": line.depth, "text": line.text} for line in trace_lines],
        },
    )


@app.command("apl-intent")
def apl_intent_command(
    ctx: typer.Context,
    apl_path: str = typer.Argument(..., help="Path to a .simc APL file."),
    targets: int = typer.Option(1, "--targets", min=1, help="Active target count."),
    list_name: str = typer.Option("default", "--list", help="Starting action list."),
    limit: int = typer.Option(6, "--limit", min=1, max=50, help="Number of intent lines to return."),
    profile_path: str | None = typer.Option(None, "--profile-path", help="Optional profile path containing build lines."),
    build_file: str | None = typer.Option(None, "--build-file", help="Optional plain text file with talents/spec lines."),
    build_text: str | None = typer.Option(None, "--build-text", help="Inline build text or talent hash."),
    talents: str | None = typer.Option(None, "--talents", help="SimC talents string or talents=... line."),
    class_talents: str | None = typer.Option(None, "--class-talents", help="Split class talents string."),
    spec_talents: str | None = typer.Option(None, "--spec-talents", help="Split spec talents string."),
    hero_talents: str | None = typer.Option(None, "--hero-talents", help="Split hero talents string."),
    actor_class: str | None = typer.Option(None, "--actor-class", help="Actor class such as monk or evoker."),
    spec_name: str | None = typer.Option(None, "--spec", help="Spec name such as mistweaver."),
    enable: list[str] = typer.Option([], "--enable", help="Enabled talent names. Repeat or pass comma-separated values."),
    disable: list[str] = typer.Option([], "--disable", help="Disabled talent names. Repeat or pass comma-separated values."),
) -> None:
    paths = _repo_paths(ctx)
    resolved = _resolve_path(paths, apl_path)
    if not resolved.exists():
        _fail(ctx, "not_found", f"APL file not found: {resolved}")
        return
    option_values = _build_option_values(
        profile_path=profile_path,
        build_file=build_file,
        build_text=build_text,
        talents=talents,
        class_talents=class_talents,
        spec_talents=spec_talents,
        hero_talents=hero_talents,
        actor_class=actor_class,
        spec_name=spec_name,
        enable=enable,
        disable=disable,
    )
    try:
        context, resolution = _resolve_prune_context(paths, resolved, option_values, targets)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        _fail(ctx, "intent_failed", str(exc))
        return
    summary = summarize_branches(resolved, context, start_list=list_name)
    focus_list = summary.guaranteed_dispatch or list_name
    _emit(
        ctx,
        {
            "provider": "simc",
            "apl": {
                "path": str(resolved),
                "relative_to_repo": str(resolved.relative_to(paths.root)) if resolved.is_relative_to(paths.root) else None,
            },
            "build": {
                "actor_class": resolution.actor_class,
                "spec": resolution.spec,
                "targets": context.targets,
                "enabled_talents": len(context.enabled_talents),
                "source_notes": resolution.source_notes,
            },
            "focus_list": focus_list,
            "summary": {
                "start_list": summary.start_list,
                "guaranteed_dispatch": summary.guaranteed_dispatch,
                "guaranteed_dispatch_line": summary.guaranteed_dispatch_line,
                "guaranteed_dispatch_reason": summary.guaranteed_dispatch_reason,
                "dead_branches": summary.dead_branches,
                "unresolved_branches": summary.unresolved_branches,
                "shadowed_lines": summary.shadowed_lines,
            },
            "intent": summarize_intent(resolved, context, focus_list, limit=limit),
        },
    )


@app.command("apl-intent-explain")
def apl_intent_explain_command(
    ctx: typer.Context,
    apl_path: str = typer.Argument(..., help="Path to a .simc APL file."),
    targets: int = typer.Option(1, "--targets", min=1, help="Active target count."),
    list_name: str = typer.Option("default", "--list", help="Starting action list."),
    limit: int = typer.Option(8, "--limit", min=1, max=50, help="Maximum items per bucket."),
    profile_path: str | None = typer.Option(None, "--profile-path", help="Optional profile path containing build lines."),
    build_file: str | None = typer.Option(None, "--build-file", help="Optional plain text file with talents/spec lines."),
    build_text: str | None = typer.Option(None, "--build-text", help="Inline build text or talent hash."),
    talents: str | None = typer.Option(None, "--talents", help="SimC talents string or talents=... line."),
    class_talents: str | None = typer.Option(None, "--class-talents", help="Split class talents string."),
    spec_talents: str | None = typer.Option(None, "--spec-talents", help="Split spec talents string."),
    hero_talents: str | None = typer.Option(None, "--hero-talents", help="Split hero talents string."),
    actor_class: str | None = typer.Option(None, "--actor-class", help="Actor class such as monk or evoker."),
    spec_name: str | None = typer.Option(None, "--spec", help="Spec name such as mistweaver."),
    enable: list[str] = typer.Option([], "--enable", help="Enabled talent names. Repeat or pass comma-separated values."),
    disable: list[str] = typer.Option([], "--disable", help="Disabled talent names. Repeat or pass comma-separated values."),
) -> None:
    paths = _repo_paths(ctx)
    resolved = _resolve_path(paths, apl_path)
    if not resolved.exists():
        _fail(ctx, "not_found", f"APL file not found: {resolved}")
        return
    option_values = _build_option_values(
        profile_path=profile_path,
        build_file=build_file,
        build_text=build_text,
        talents=talents,
        class_talents=class_talents,
        spec_talents=spec_talents,
        hero_talents=hero_talents,
        actor_class=actor_class,
        spec_name=spec_name,
        enable=enable,
        disable=disable,
    )
    try:
        context, resolution = _resolve_prune_context(paths, resolved, option_values, targets)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        _fail(ctx, "intent_explain_failed", str(exc))
        return
    summary = summarize_branches(resolved, context, start_list=list_name)
    focus_list = summary.guaranteed_dispatch or list_name
    explanation = explain_intent(resolved, context, focus_list, limit=limit)
    _emit(
        ctx,
        {
            "provider": "simc",
            "apl": {
                "path": str(resolved),
                "relative_to_repo": str(resolved.relative_to(paths.root)) if resolved.is_relative_to(paths.root) else None,
            },
            "build": {
                "actor_class": resolution.actor_class,
                "spec": resolution.spec,
                "targets": context.targets,
                "enabled_talents": len(context.enabled_talents),
                "source_notes": resolution.source_notes,
            },
            "focus_list": focus_list,
            "summary": {
                "start_list": summary.start_list,
                "guaranteed_dispatch": summary.guaranteed_dispatch,
                "guaranteed_dispatch_line": summary.guaranteed_dispatch_line,
                "guaranteed_dispatch_reason": summary.guaranteed_dispatch_reason,
                "dead_branches": summary.dead_branches,
                "unresolved_branches": summary.unresolved_branches,
                "shadowed_lines": summary.shadowed_lines,
            },
            "explained_intent": {
                "setup": explanation.setup,
                "helpers": explanation.helpers,
                "burst": explanation.burst,
                "priorities": explanation.priorities,
            },
        },
    )


@app.command("apl-branch-compare")
def apl_branch_compare_command(
    ctx: typer.Context,
    apl_path: str = typer.Argument(..., help="Path to a .simc APL file."),
    left_targets: int = typer.Option(1, "--left-targets", min=1, help="Target count for the left context."),
    right_targets: int = typer.Option(1, "--right-targets", min=1, help="Target count for the right context."),
    list_name: str = typer.Option("default", "--list", help="Starting action list."),
    profile_path: str | None = typer.Option(None, "--profile-path", help="Optional left profile path containing build lines."),
    build_file: str | None = typer.Option(None, "--build-file", help="Optional left build file."),
    build_text: str | None = typer.Option(None, "--build-text", help="Inline left build text or talent hash."),
    talents: str | None = typer.Option(None, "--talents", help="Left SimC talents string or talents=... line."),
    class_talents: str | None = typer.Option(None, "--class-talents", help="Left split class talents string."),
    spec_talents: str | None = typer.Option(None, "--spec-talents", help="Left split spec talents string."),
    hero_talents: str | None = typer.Option(None, "--hero-talents", help="Left split hero talents string."),
    actor_class: str | None = typer.Option(None, "--actor-class", help="Left actor class such as monk or evoker."),
    spec_name: str | None = typer.Option(None, "--spec", help="Left spec name such as mistweaver."),
    enable: list[str] = typer.Option([], "--enable", help="Enabled left talent names. Repeat or pass comma-separated values."),
    disable: list[str] = typer.Option([], "--disable", help="Disabled left talent names. Repeat or pass comma-separated values."),
    right_profile_path: str | None = typer.Option(None, "--right-profile-path", help="Optional right profile path containing build lines."),
    right_build_file: str | None = typer.Option(None, "--right-build-file", help="Optional right build file."),
    right_build_text: str | None = typer.Option(None, "--right-build-text", help="Inline right build text or talent hash."),
    right_talents: str | None = typer.Option(None, "--right-talents", help="Right SimC talents string or talents=... line."),
    right_class_talents: str | None = typer.Option(None, "--right-class-talents", help="Right split class talents string."),
    right_spec_talents: str | None = typer.Option(None, "--right-spec-talents", help="Right split spec talents string."),
    right_hero_talents: str | None = typer.Option(None, "--right-hero-talents", help="Right split hero talents string."),
    right_actor_class: str | None = typer.Option(None, "--right-actor-class", help="Right actor class such as monk or evoker."),
    right_spec_name: str | None = typer.Option(None, "--right-spec", help="Right spec name such as mistweaver."),
    right_enable: list[str] = typer.Option([], "--right-enable", help="Enabled right talent names. Repeat or pass comma-separated values."),
    right_disable: list[str] = typer.Option([], "--right-disable", help="Disabled right talent names. Repeat or pass comma-separated values."),
) -> None:
    paths = _repo_paths(ctx)
    resolved = _resolve_path(paths, apl_path)
    if not resolved.exists():
        _fail(ctx, "not_found", f"APL file not found: {resolved}")
        return
    left_values = _build_option_values(
        profile_path=profile_path,
        build_file=build_file,
        build_text=build_text,
        talents=talents,
        class_talents=class_talents,
        spec_talents=spec_talents,
        hero_talents=hero_talents,
        actor_class=actor_class,
        spec_name=spec_name,
        enable=enable,
        disable=disable,
    )
    right_values = _build_option_values(
        profile_path=right_profile_path if right_profile_path is not None else profile_path,
        build_file=right_build_file if right_build_file is not None else build_file,
        build_text=right_build_text if right_build_text is not None else build_text,
        talents=right_talents if right_talents is not None else talents,
        class_talents=right_class_talents if right_class_talents is not None else class_talents,
        spec_talents=right_spec_talents if right_spec_talents is not None else spec_talents,
        hero_talents=right_hero_talents if right_hero_talents is not None else hero_talents,
        actor_class=right_actor_class if right_actor_class is not None else actor_class,
        spec_name=right_spec_name if right_spec_name is not None else spec_name,
        enable=[*enable, *right_enable],
        disable=[*disable, *right_disable],
    )
    try:
        left_context, left_resolution = _resolve_prune_context(paths, resolved, left_values, left_targets)
        right_context, right_resolution = _resolve_prune_context(paths, resolved, right_values, right_targets)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        _fail(ctx, "branch_compare_failed", str(exc))
        return
    comparison = attach_focus_comparison(
        compare_branch_summaries(
            summarize_branches(resolved, left_context, start_list=list_name),
            summarize_branches(resolved, right_context, start_list=list_name),
        ),
        resolved,
        left_context,
        right_context,
    )
    _emit(
        ctx,
        {
            "provider": "simc",
            "apl": {
                "path": str(resolved),
                "relative_to_repo": str(resolved.relative_to(paths.root)) if resolved.is_relative_to(paths.root) else None,
            },
            "left": {
                "actor_class": left_resolution.actor_class,
                "spec": left_resolution.spec,
                "targets": left_context.targets,
                "enabled_talents": len(left_context.enabled_talents),
                "source_notes": left_resolution.source_notes,
            },
            "right": {
                "actor_class": right_resolution.actor_class,
                "spec": right_resolution.spec,
                "targets": right_context.targets,
                "enabled_talents": len(right_context.enabled_talents),
                "source_notes": right_resolution.source_notes,
            },
            "comparison": {
                "start_list": comparison.start_list,
                "left_dispatch": comparison.left_dispatch,
                "right_dispatch": comparison.right_dispatch,
                "dispatch_changed": comparison.dispatch_changed,
                "decision_changes": comparison.decision_changes,
                "left_focus_list": comparison.left_focus_list,
                "right_focus_list": comparison.right_focus_list,
                "focus_list_same": comparison.focus_list_same,
                "focus_changes": comparison.focus_changes,
                "left_focus_preview": comparison.left_focus_preview,
                "right_focus_preview": comparison.right_focus_preview,
                "left_focus_intent": comparison.left_focus_intent,
                "right_focus_intent": comparison.right_focus_intent,
            },
        },
    )


@app.command("analysis-packet")
def analysis_packet_command(
    ctx: typer.Context,
    apl_path: str = typer.Argument(..., help="Path to a .simc APL file."),
    targets: int = typer.Option(1, "--targets", min=1, help="Active target count."),
    list_name: str = typer.Option("default", "--list", help="Starting action list."),
    intent_limit: int = typer.Option(6, "--intent-limit", min=1, max=50, help="Number of intent lines to return."),
    explain_limit: int = typer.Option(8, "--explain-limit", min=1, max=50, help="Maximum items per explanation bucket."),
    runtime_scan_limit: int = typer.Option(8, "--runtime-scan-limit", min=1, max=50, help="How many early runtime-sensitive lines to report."),
    profile_path: str | None = typer.Option(None, "--profile-path", help="Optional profile path containing build lines."),
    build_file: str | None = typer.Option(None, "--build-file", help="Optional plain text file with talents/spec lines."),
    build_text: str | None = typer.Option(None, "--build-text", help="Inline build text or talent hash."),
    talents: str | None = typer.Option(None, "--talents", help="SimC talents string or talents=... line."),
    class_talents: str | None = typer.Option(None, "--class-talents", help="Split class talents string."),
    spec_talents: str | None = typer.Option(None, "--spec-talents", help="Split spec talents string."),
    hero_talents: str | None = typer.Option(None, "--hero-talents", help="Split hero talents string."),
    actor_class: str | None = typer.Option(None, "--actor-class", help="Actor class such as monk or evoker."),
    spec_name: str | None = typer.Option(None, "--spec", help="Spec name such as mistweaver."),
    enable: list[str] = typer.Option([], "--enable", help="Enabled talent names. Repeat or pass comma-separated values."),
    disable: list[str] = typer.Option([], "--disable", help="Disabled talent names. Repeat or pass comma-separated values."),
) -> None:
    paths = _repo_paths(ctx)
    resolved = _resolve_path(paths, apl_path)
    if not resolved.exists():
        _fail(ctx, "not_found", f"APL file not found: {resolved}")
        return
    option_values = _build_option_values(
        profile_path=profile_path,
        build_file=build_file,
        build_text=build_text,
        talents=talents,
        class_talents=class_talents,
        spec_talents=spec_talents,
        hero_talents=hero_talents,
        actor_class=actor_class,
        spec_name=spec_name,
        enable=enable,
        disable=disable,
    )
    try:
        context, resolution = _resolve_prune_context(paths, resolved, option_values, targets)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        _fail(ctx, "analysis_packet_failed", str(exc))
        return
    packet = build_analysis_packet(
        resolved,
        context,
        start_list=list_name,
        intent_limit=intent_limit,
        explain_limit=explain_limit,
        runtime_scan_limit=runtime_scan_limit,
    )
    _emit(
        ctx,
        {
            "provider": "simc",
            "apl": {
                "path": str(packet.apl_path),
                "relative_to_repo": str(packet.apl_path.relative_to(paths.root)) if packet.apl_path.is_relative_to(paths.root) else None,
            },
            "build": {
                "actor_class": resolution.actor_class,
                "spec": resolution.spec,
                "targets": context.targets,
                "enabled_talents": len(context.enabled_talents),
                "source_notes": resolution.source_notes,
            },
            "packet": {
                "start_list": packet.start_list,
                "focus_list": packet.focus_list,
                "dispatch_certainty": packet.dispatch_certainty,
                "top_level_runtime_unresolved": packet.top_level_runtime_unresolved,
                "runtime_sensitive_priorities": packet.runtime_sensitive_priorities,
                "escalation_reasons": packet.escalation_reasons,
                "next_steps": packet.next_steps,
                "intent_lines": packet.intent_lines,
                "explained_intent": {
                    "setup": packet.explained_intent.setup,
                    "helpers": packet.explained_intent.helpers,
                    "burst": packet.explained_intent.burst,
                    "priorities": packet.explained_intent.priorities,
                },
                "branch_summary": {
                    "start_list": packet.branch_summary.start_list,
                    "guaranteed_dispatch": packet.branch_summary.guaranteed_dispatch,
                    "guaranteed_dispatch_line": packet.branch_summary.guaranteed_dispatch_line,
                    "guaranteed_dispatch_reason": packet.branch_summary.guaranteed_dispatch_reason,
                    "dead_branches": packet.branch_summary.dead_branches,
                    "unresolved_branches": packet.branch_summary.unresolved_branches,
                    "shadowed_lines": packet.branch_summary.shadowed_lines,
                },
            },
        },
    )


@app.command("sync")
def sync(
    ctx: typer.Context,
    allow_dirty: bool = typer.Option(False, "--allow-dirty", help="Allow git pull even if the repo has local changes."),
) -> None:
    paths = _repo_paths(ctx)
    if not paths.root.exists():
        _fail(ctx, "missing_repo", f"SimulationCraft repo not found: {paths.root}")
        return
    result = sync_repo(paths, allow_dirty=allow_dirty)
    git_status = repo_git_status(paths)
    if result is None:
        _emit(
            ctx,
            {
                "provider": "simc",
                "status": "skipped",
                "reason": "dirty_worktree",
                "repo": str(paths.root),
                "git": git_status,
            },
        )
        return
    stdout_preview, stdout_truncated = _preview_text(result.stdout)
    stderr_preview, stderr_truncated = _preview_text(result.stderr)
    if result.returncode != 0:
        _fail(
            ctx,
            "sync_failed",
            "SimulationCraft git sync failed.",
            extra={
                "command": result.command,
                "stdout_preview": stdout_preview,
                "stdout_truncated": stdout_truncated,
                "stderr_preview": stderr_preview,
                "stderr_truncated": stderr_truncated,
            },
        )
        return
    _emit(
        ctx,
        {
            "provider": "simc",
            "status": "updated",
            "repo": str(paths.root),
            "command": result.command,
            "git": repo_git_status(paths),
            "stdout_preview": stdout_preview,
            "stdout_truncated": stdout_truncated,
            "stderr_preview": stderr_preview,
            "stderr_truncated": stderr_truncated,
        },
    )


@app.command("build")
def build(
    ctx: typer.Context,
    target: str | None = typer.Option(None, "--target", help="Optional build target passed to cmake."),
) -> None:
    paths = _repo_paths(ctx)
    if not paths.build_dir.exists():
        _fail(ctx, "missing_build_dir", f"SimulationCraft build dir not found: {paths.build_dir}")
        return
    result = build_repo(paths, target=target)
    stdout_preview, stdout_truncated = _preview_text(result.stdout)
    stderr_preview, stderr_truncated = _preview_text(result.stderr)
    if result.returncode != 0:
        _fail(
            ctx,
            "build_failed",
            "SimulationCraft build failed.",
            extra={
                "command": result.command,
                "stdout_preview": stdout_preview,
                "stdout_truncated": stdout_truncated,
                "stderr_preview": stderr_preview,
                "stderr_truncated": stderr_truncated,
            },
        )
        return
    _emit(
        ctx,
        {
            "provider": "simc",
            "status": "built",
            "command": result.command,
            "stdout_preview": stdout_preview,
            "stdout_truncated": stdout_truncated,
            "stderr_preview": stderr_preview,
            "stderr_truncated": stderr_truncated,
        },
    )


@app.command("run")
def run_command(
    ctx: typer.Context,
    profile_path: str = typer.Argument(..., help="Path to a SimulationCraft profile to execute."),
    simc_arg: list[str] = typer.Option([], "--arg", help="Additional raw SimulationCraft arg, repeatable."),
) -> None:
    paths = _repo_paths(ctx)
    resolved = Path(profile_path).expanduser().resolve()
    if not resolved.exists():
        _fail(ctx, "not_found", f"Profile not found: {resolved}")
        return
    result = run_profile(paths, resolved, simc_args=list(simc_arg))
    stdout_preview, stdout_truncated = _preview_text(result.stdout)
    stderr_preview, stderr_truncated = _preview_text(result.stderr)
    version_line = binary_version(paths).version_line
    if result.returncode != 0:
        _fail(
            ctx,
            "run_failed",
            "SimulationCraft run failed.",
            extra={
                "command": result.command,
                "stdout_preview": stdout_preview,
                "stdout_truncated": stdout_truncated,
                "stderr_preview": stderr_preview,
                "stderr_truncated": stderr_truncated,
                "version": version_line,
            },
        )
        return
    _emit(
        ctx,
        {
            "provider": "simc",
            "status": "completed",
            "profile_path": str(resolved),
            "command": result.command,
            "version": version_line,
            "stdout_preview": stdout_preview,
            "stdout_truncated": stdout_truncated,
            "stderr_preview": stderr_preview,
            "stderr_truncated": stderr_truncated,
        },
    )


def run() -> None:
    app()


if __name__ == "__main__":
    run()
