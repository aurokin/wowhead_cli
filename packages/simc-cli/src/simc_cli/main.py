from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

from simc_cli.build_input import decode_build, extract_build_spec_from_text, infer_actor_and_spec_from_apl, load_build_spec
from simc_cli.repo import RepoPaths, discover_repo, validate_build, validate_repo
from simc_cli.run import binary_version, build_repo, repo_git_status, run_profile, sync_repo
from simc_cli.search import spec_file_search
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
