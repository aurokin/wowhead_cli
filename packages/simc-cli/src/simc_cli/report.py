from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SimReportSummary:
    version: str | None
    game_version: str | None
    player_name: str | None
    player_spec: str | None
    player_role: str | None
    iterations_completed: int | None
    run_settings: dict[str, Any]
    runtime: dict[str, Any]
    metrics: dict[str, Any]


def load_sim_report(path: str | Path) -> dict[str, Any]:
    resolved = Path(path).expanduser().resolve()
    return json.loads(resolved.read_text())


def summarize_sim_report(report: dict[str, Any]) -> SimReportSummary:
    sim = report.get("sim") if isinstance(report, dict) else None
    if not isinstance(sim, dict):
        raise RuntimeError("SimC JSON report did not contain sim metadata.")
    options = sim.get("options") if isinstance(sim.get("options"), dict) else {}
    statistics = sim.get("statistics") if isinstance(sim.get("statistics"), dict) else {}
    players = sim.get("players") if isinstance(sim.get("players"), list) else []
    if not players or not isinstance(players[0], dict):
        raise RuntimeError("SimC JSON report did not contain players.")
    player = players[0]
    collected = player.get("collected_data") if isinstance(player.get("collected_data"), dict) else {}
    iterations_completed = _metric_count(collected.get("fight_length")) or _metric_count(statistics.get("simulation_length"))

    dps = _metric_mean(collected.get("dps"))
    dps_error = _metric_mean(collected.get("dpse"))
    target_error_percent = (
        round(dps_error / dps * 100.0, 3)
        if dps and dps_error is not None and isinstance(iterations_completed, int) and iterations_completed > 1
        else None
    )

    dbc = options.get("dbc") if isinstance(options.get("dbc"), dict) else {}
    version_used = dbc.get("version_used")
    live_info = dbc.get(version_used) if isinstance(version_used, str) and isinstance(dbc.get(version_used), dict) else {}

    run_settings = {
        "iterations_requested": options.get("iterations"),
        "iterations_completed": iterations_completed,
        "target_error_requested": options.get("target_error"),
        "target_error_percent": target_error_percent,
        "threads": options.get("threads"),
        "fight_style": options.get("fight_style"),
        "desired_targets": options.get("desired_targets"),
        "max_time": options.get("max_time"),
        "vary_combat_length": options.get("vary_combat_length"),
        "seed": options.get("seed"),
        "stop_reason": _stop_reason(options=options, iterations_completed=iterations_completed),
    }
    runtime = {
        "elapsed_time_seconds": statistics.get("elapsed_time_seconds"),
        "elapsed_cpu_seconds": statistics.get("elapsed_cpu_seconds"),
        "init_time_seconds": statistics.get("init_time_seconds"),
        "merge_time_seconds": statistics.get("merge_time_seconds"),
        "analyze_time_seconds": statistics.get("analyze_time_seconds"),
    }
    metrics = {
        "dps": dps,
        "dps_error": dps_error,
        "dtps": _metric_mean(collected.get("dtps")),
        "hps": _metric_mean(collected.get("hps")),
        "deaths": _metric_mean(collected.get("deaths")),
        "fight_length": _metric_mean(collected.get("fight_length")),
        "absorb": _metric_mean(collected.get("absorb")),
        "heal": _metric_mean(collected.get("heal")),
    }
    return SimReportSummary(
        version=str(report.get("version")) if report.get("version") is not None else None,
        game_version=live_info.get("wow_version") if isinstance(live_info, dict) else None,
        player_name=str(player.get("name")) if player.get("name") is not None else None,
        player_spec=str(player.get("specialization")) if player.get("specialization") is not None else None,
        player_role=str(player.get("role")) if player.get("role") is not None else None,
        iterations_completed=iterations_completed,
        run_settings=run_settings,
        runtime=runtime,
        metrics=metrics,
    )


def sim_report_payload(
    summary: SimReportSummary,
    *,
    profile_path: str | None,
    preset: str,
    input_source: str,
    json_report_path: str | None,
    command: list[str],
) -> dict[str, Any]:
    return {
        "provider": "simc",
        "status": "completed",
        "preset": preset,
        "input_source": input_source,
        "profile_path": profile_path,
        "json_report_path": json_report_path,
        "command": command,
        "simc_version": summary.version,
        "game_version": summary.game_version,
        "player": {
            "name": summary.player_name,
            "spec": summary.player_spec,
            "role": summary.player_role,
        },
        "run_settings": summary.run_settings,
        "runtime": summary.runtime,
        "metrics": summary.metrics,
    }


def _metric_mean(metric: Any) -> float | None:
    if isinstance(metric, dict):
        value = metric.get("mean")
        if isinstance(value, (int, float)):
            return float(value)
    if isinstance(metric, (int, float)):
        return float(metric)
    return None


def _metric_count(metric: Any) -> int | None:
    if isinstance(metric, dict):
        value = metric.get("count")
        if isinstance(value, int):
            return value
    return None


def _stop_reason(*, options: dict[str, Any], iterations_completed: int | None) -> str:
    target_error = options.get("target_error")
    iterations_requested = options.get("iterations")
    if isinstance(target_error, (int, float)) and float(target_error) > 0:
        if isinstance(iterations_requested, int) and isinstance(iterations_completed, int) and iterations_completed < iterations_requested:
            return "target_error_reached"
        return "target_error_requested"
    return "fixed_iterations_completed"
