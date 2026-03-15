from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from simc_cli.main import app as simc_app

runner = CliRunner()


def test_simc_doctor_reports_phase_one_capabilities(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "simc"
    repo_root.mkdir()

    def fake_repo_payload(paths):  # noqa: ANN001
        return {
            "root": str(paths.root),
            "exists": True,
            "repo_ready": True,
            "build_ready": True,
            "repo_issues": [],
            "build_issues": [],
            "git": {"git": True, "dirty": False, "branch": "main", "head": "abc", "dirty_entries": []},
            "binary": {"path": str(paths.build_simc), "exists": True, "version_line": "SimulationCraft 1201", "available": True},
        }

    monkeypatch.setattr("simc_cli.main._repo_payload", fake_repo_payload)
    result = runner.invoke(simc_app, ["--repo-root", str(repo_root), "doctor"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["provider"] == "simc"
    assert payload["status"] == "ready"
    assert payload["capabilities"]["version"] == "ready"
    assert payload["capabilities"]["search"] == "coming_soon"
    assert payload["capabilities"]["repo"] == "ready"
    assert payload["capabilities"]["checkout"] == "ready"
    assert payload["capabilities"]["apl_lists"] == "ready"
    assert payload["capabilities"]["apl_prune"] == "ready"
    assert payload["capabilities"]["priority"] == "ready"
    assert payload["capabilities"]["inactive_actions"] == "ready"
    assert payload["capabilities"]["opener"] == "ready"
    assert payload["capabilities"]["analysis_packet"] == "ready"
    assert payload["capabilities"]["first_cast"] == "ready"
    assert payload["capabilities"]["log_actions"] == "ready"


def test_simc_search_is_structured_coming_soon() -> None:
    result = runner.invoke(simc_app, ["search", "mistweaver"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["coming_soon"] is True
    assert payload["count"] == 0


def test_simc_repo_reports_and_updates_resolution(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "simc"
    target.mkdir()

    monkeypatch.setattr(
        "simc_cli.main._repo_resolution",
        lambda ctx: type(
            "Resolution",
            (),
            {
                "root": target.resolve(),
                "source": "config",
                "config_path": tmp_path / "repo.json",
                "configured_root": target.resolve(),
                "managed_root": tmp_path / "managed",
                "managed_exists": False,
                "legacy_root": Path("/tmp/legacy"),
            },
        )(),
    )
    monkeypatch.setattr("simc_cli.main.save_configured_repo_root", lambda root: target.resolve())

    result = runner.invoke(simc_app, ["repo", "--set-root", str(target)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["action"] == "set_root"
    assert payload["changed"] is True
    assert payload["resolution"]["source"] == "config"


def test_simc_checkout_reports_managed_checkout(monkeypatch, tmp_path: Path) -> None:
    managed = tmp_path / "managed"

    monkeypatch.setattr(
        "simc_cli.main.checkout_managed_repo",
        lambda: type("Checkout", (), {"status": "cloned", "root": managed, "repo_url": "https://github.com/simulationcraft/simc.git", "commands": [["git", "clone"]]})(),
    )
    monkeypatch.setattr(
        "simc_cli.main._repo_resolution",
        lambda ctx: type(
            "Resolution",
            (),
            {
                "root": managed,
                "source": "managed",
                "config_path": tmp_path / "repo.json",
                "configured_root": None,
                "managed_root": managed,
                "managed_exists": True,
                "legacy_root": Path("/tmp/legacy"),
            },
        )(),
    )

    result = runner.invoke(simc_app, ["checkout"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "cloned"
    assert payload["active_resolution"]["source"] == "managed"


def test_simc_version_uses_binary_probe(monkeypatch) -> None:
    monkeypatch.setattr(
        "simc_cli.main.binary_version",
        lambda paths: type("VersionInfo", (), {"binary_path": Path("/tmp/simc"), "available": True, "version_line": "SimulationCraft 1201", "returncode": 1})(),
    )
    result = runner.invoke(simc_app, ["version"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["version"] == "SimulationCraft 1201"


def test_simc_spec_files_returns_grouped_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "simc_cli.main.spec_file_search",
        lambda paths, query: {
            "default_apl": [Path("/tmp/simc/ActionPriorityLists/default/monk_mistweaver.simc")],
            "assisted_apl": [],
            "cpp": [],
            "hpp": [],
            "spell_dump": [],
        },
    )
    result = runner.invoke(simc_app, ["spec-files", "mistweaver"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["categories"]["default_apl"]["items"][0]["stem"] == "monk_mistweaver"


def test_simc_decode_build_outputs_decoded_talents(monkeypatch) -> None:
    monkeypatch.setattr(
        "simc_cli.main.load_build_spec",
        lambda **kwargs: type("BuildSpec", (), {
            "actor_class": "monk",
            "spec": "mistweaver",
            "talents": "ABC123",
            "class_talents": None,
            "spec_talents": None,
            "hero_talents": None,
            "source_notes": ["command-line build options"],
        })(),
    )
    monkeypatch.setattr(
        "simc_cli.main.decode_build",
        lambda paths, build_spec: type("Resolution", (), {
            "actor_class": "monk",
            "spec": "mistweaver",
            "enabled_talents": {"ancient_teachings", "jadefire_stomp"},
            "talents_by_tree": {
                "class": [],
                "spec": [type("Talent", (), {"name": "Ancient Teachings", "token": "ancient_teachings", "rank": 1, "max_rank": 1})()],
                "hero": [type("Talent", (), {"name": "Jadefire Stomp", "token": "jadefire_stomp", "rank": 1, "max_rank": 1})()],
                "selection": [],
            },
            "source_notes": ["decoded via /tmp/simc"],
        })(),
    )
    result = runner.invoke(simc_app, ["decode-build", "--actor-class", "monk", "--spec", "mistweaver", "--talents", "ABC123"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["decoded"]["actor_class"] == "monk"
    assert payload["decoded"]["enabled_talents"] == ["ancient_teachings", "jadefire_stomp"]


def test_simc_build_harness_compare_report_and_verify_clean(monkeypatch, tmp_path: Path) -> None:
    harness_path = tmp_path / "demo_harness.simc"

    monkeypatch.setattr(
        "simc_cli.main.load_build_spec",
        lambda **kwargs: type(
            "BuildSpec",
            (),
            {
                "actor_class": "warlock",
                "spec": "demonology",
                "talents": "ABC123",
                "class_talents": None,
                "spec_talents": None,
                "hero_talents": None,
                "source_notes": ["command-line build options"],
            },
        )(),
    )
    build_result = runner.invoke(
        simc_app,
        ["build-harness", "--actor-class", "warlock", "--spec", "demonology", "--talents", "ABC123", "--out", str(harness_path), "--line", "hero_talents=2"],
    )
    assert build_result.exit_code == 0
    build_payload = json.loads(build_result.stdout)
    assert build_payload["kind"] == "build_harness"
    assert build_payload["path"] == str(harness_path)
    assert harness_path.exists()

    apl = tmp_path / "variant.simc"
    apl.write_text("actions=shadow_bolt\n")
    profile = tmp_path / "variant_profile.simc"
    profile.write_text("warlock=\"probe\"\nactions=shadow_bolt\n")
    monkeypatch.setattr("simc_cli.main.build_variant_profile", lambda harness_path, apl_path, label, out_dir=None: profile)
    monkeypatch.setattr(
        "simc_cli.main.validate_profile_file",
        lambda paths, profile_path: type(
            "Validation",
            (),
            {
                "result": type("Result", (), {"returncode": 0, "stdout": "ok\n", "stderr": ""})(),
            },
        )(),
    )
    validate_result = runner.invoke(simc_app, ["validate-apl", str(harness_path), str(apl), "--label", "wowhead"])
    assert validate_result.exit_code == 0
    validate_payload = json.loads(validate_result.stdout)
    assert validate_payload["valid"] is True
    assert validate_payload["label"] == "wowhead"

    compare_payload = {
        "kind": "apl_comparison",
        "compare_dir": str(tmp_path),
        "harness_path": str(harness_path),
        "iterations": 250,
        "threads": 1,
        "validations": [],
        "base": {"label": "base", "dps": 100.0},
        "ranking": [{"label": "base", "dps": 100.0}, {"label": "wowhead", "dps": 99.0}],
        "comparisons": [{"label": "wowhead", "base_label": "base", "dps_delta": -1.0, "percent_delta": -1.0, "top_action_deltas": []}],
    }
    monkeypatch.setattr("simc_cli.main.compare_apl_variants", lambda *args, **kwargs: compare_payload)
    compare_result = runner.invoke(
        simc_app,
        ["compare-apls", str(harness_path), "--base-apl", str(apl), "--variant", f"wowhead={apl}", "--report-out", str(tmp_path / "report.json")],
    )
    assert compare_result.exit_code == 0
    compare_stdout = json.loads(compare_result.stdout)
    assert compare_stdout["kind"] == "apl_comparison"
    assert compare_stdout["report_path"] == str((tmp_path / "report.json").resolve())

    report_result = runner.invoke(simc_app, ["variant-report", str(tmp_path / "report.json")])
    assert report_result.exit_code == 0
    report_payload = json.loads(report_result.stdout)
    assert report_payload["kind"] == "apl_variant_report"
    assert report_payload["best_label"] == "base"

    monkeypatch.setattr(
        "simc_cli.main.verify_clean_payload",
        lambda paths, hash_binary: {"kind": "verify_clean", "repo_root": "/tmp/simc", "git": {"dirty": False}, "binary": {"exists": True}},
    )
    clean_result = runner.invoke(simc_app, ["verify-clean"])
    assert clean_result.exit_code == 0
    clean_payload = json.loads(clean_result.stdout)
    assert clean_payload["kind"] == "verify_clean"
    assert clean_payload["git"]["dirty"] is False


def test_simc_apl_lists_graph_talents_and_trace(monkeypatch, tmp_path: Path) -> None:
    apl = tmp_path / "monk_mistweaver.simc"
    apl.write_text(
        "\n".join(
            [
                "actions=auto_attack",
                "actions+=/run_action_list,name=aoe,if=active_enemies>2",
                "actions+=/rising_sun_kick,if=talent.rising_mist.enabled",
                "actions.aoe=spinning_crane_kick",
            ]
        )
        + "\n"
    )

    result_lists = runner.invoke(simc_app, ["apl-lists", str(apl)])
    assert result_lists.exit_code == 0
    payload_lists = json.loads(result_lists.stdout)
    assert payload_lists["apl"]["list_count"] == 2
    assert payload_lists["lists"][0]["count"] >= 1

    result_graph = runner.invoke(simc_app, ["apl-graph", str(apl)])
    assert result_graph.exit_code == 0
    payload_graph = json.loads(result_graph.stdout)
    assert payload_graph["graph"]["format"] == "mermaid"
    assert "flowchart TD" in payload_graph["graph"]["text"]

    result_talents = runner.invoke(simc_app, ["apl-talents", str(apl)])
    assert result_talents.exit_code == 0
    payload_talents = json.loads(result_talents.stdout)
    assert payload_talents["count"] == 1
    assert payload_talents["talents"][0]["token"] == "rising_mist"

    monkeypatch.setattr(
        "simc_cli.main.find_action",
        lambda paths, action, wow_class: {"apl_default": [], "apl_assisted": [], "class_modules": [], "spell_dump": []},
    )
    result_trace = runner.invoke(simc_app, ["trace-action", str(apl), "rising_sun_kick"])
    assert result_trace.exit_code == 0
    payload_trace = json.loads(result_trace.stdout)
    assert payload_trace["apl_hits"]["count"] == 1
    assert payload_trace["apl_hits"]["items"][0]["list_name"] == "default"


def test_simc_find_action_groups_hits(monkeypatch) -> None:
    monkeypatch.setattr(
        "simc_cli.main.find_action",
        lambda paths, action, wow_class: {
            "apl_default": [],
            "apl_assisted": [],
            "class_modules": [type("Hit", (), {"path": Path("/tmp/sc_monk.cpp"), "line_no": 42, "text": "if ( action == rising_sun_kick )"})()],
            "spell_dump": [],
        },
    )
    result = runner.invoke(simc_app, ["find-action", "rising_sun_kick"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["buckets"]["class_modules"]["items"][0]["line_no"] == 42


def test_simc_apl_prune_branch_trace_and_intent(monkeypatch, tmp_path: Path) -> None:
    apl = tmp_path / "evoker_devastation.simc"
    apl.write_text(
        "\n".join(
            [
                "actions+=/run_action_list,name=aoe,if=active_enemies>=3",
                "actions+=/run_action_list,name=st,if=active_enemies<3",
                "actions.aoe+=/fire_breath",
                "actions.st+=/disintegrate,if=talent.mass_disintegrate",
            ]
        )
        + "\n"
    )
    monkeypatch.setattr(
        "simc_cli.main._resolve_prune_context",
        lambda paths, apl_path, option_values, targets: (
            type("Context", (), {"enabled_talents": {"mass_disintegrate"}, "disabled_talents": set(), "targets": targets, "talent_sources": {"mass_disintegrate": "spec"}})(),
            type("Resolution", (), {"actor_class": "evoker", "spec": "devastation", "source_notes": ["decoded via /tmp/simc"]})(),
        ),
    )

    prune_result = runner.invoke(simc_app, ["apl-prune", str(apl), "--targets", "3"])
    assert prune_result.exit_code == 0
    prune_payload = json.loads(prune_result.stdout)
    assert prune_payload["lists"][0]["items"][0]["state"] == "eligible"

    trace_result = runner.invoke(simc_app, ["apl-branch-trace", str(apl), "--targets", "3"])
    assert trace_result.exit_code == 0
    trace_payload = json.loads(trace_result.stdout)
    assert trace_payload["summary"]["guaranteed_dispatch"] == "aoe"
    assert trace_payload["trace"][0]["text"] == "[default]"

    intent_result = runner.invoke(simc_app, ["apl-intent", str(apl), "--targets", "1"])
    assert intent_result.exit_code == 0
    intent_payload = json.loads(intent_result.stdout)
    assert intent_payload["focus_list"] == "st"
    assert intent_payload["intent"]


def test_simc_priority_inactive_actions_and_opener(monkeypatch, tmp_path: Path) -> None:
    apl = tmp_path / "demonhunter_devourer.simc"
    apl.write_text(
        "\n".join(
            [
                "actions+=/run_action_list,name=aoe,if=active_enemies>=5",
                "actions+=/reapers_toll",
                "actions.aoe+=/void_ray,if=talent.void_ray",
                "actions.aoe+=/collapsing_star,if=talent.collapsing_star",
                "actions.aoe+=/reapers_toll",
                "actions.aoe+=/predators_wake",
            ]
        )
        + "\n"
    )
    monkeypatch.setattr(
        "simc_cli.main._resolve_prune_context",
        lambda paths, apl_path, option_values, targets: (
            type(
                "Context",
                (),
                {
                    "enabled_talents": {"void_ray", "predators_wake"},
                    "disabled_talents": set(),
                    "targets": targets,
                    "talent_sources": {"void_ray": "spec", "predators_wake": "spec"},
                },
            )(),
            type("Resolution", (), {"actor_class": "demonhunter", "spec": "devourer", "source_notes": ["decoded via /tmp/simc"]})(),
        ),
    )

    priority_result = runner.invoke(simc_app, ["priority", str(apl), "--targets", "5"])
    assert priority_result.exit_code == 0
    priority_payload = json.loads(priority_result.stdout)
    assert priority_payload["priority"]["focus_list"] == "aoe"
    assert [row["action"] for row in priority_payload["priority"]["items"][:2]] == ["void_ray", "reapers_toll"]
    assert priority_payload["priority"]["inactive_talent_branches"][0]["action"] == "collapsing_star"

    inactive_result = runner.invoke(simc_app, ["inactive-actions", str(apl), "--targets", "5"])
    assert inactive_result.exit_code == 0
    inactive_payload = json.loads(inactive_result.stdout)
    assert inactive_payload["inactive_actions"]["count"] == 1
    assert inactive_payload["inactive_actions"]["items"][0]["action"] == "collapsing_star"

    opener_result = runner.invoke(simc_app, ["opener", str(apl), "--targets", "5", "--limit", "3"])
    assert opener_result.exit_code == 0
    opener_payload = json.loads(opener_result.stdout)
    assert opener_payload["opener"]["kind"] == "static_priority_preview"
    assert opener_payload["opener"]["items"][0]["action"] == "void_ray"
    assert "static exact-build opener preview" in opener_payload["opener"]["caveat"]


def test_simc_intent_explain_branch_compare_and_analysis_packet(monkeypatch, tmp_path: Path) -> None:
    apl = tmp_path / "evoker_devastation.simc"
    apl.write_text(
        "\n".join(
            [
                "actions+=/run_action_list,name=aoe,if=active_enemies>=3",
                "actions+=/run_action_list,name=st,if=active_enemies<3",
                "actions.aoe+=/fire_breath",
                "actions.st+=/disintegrate,if=talent.mass_disintegrate",
            ]
        )
        + "\n"
    )

    def fake_context(paths, apl_path, option_values, targets):  # noqa: ANN001
        return (
            type(
                "Context",
                (),
                {
                    "enabled_talents": {"mass_disintegrate"} if targets == 1 else set(),
                    "disabled_talents": set(),
                    "targets": targets,
                    "talent_sources": {"mass_disintegrate": "spec"},
                },
            )(),
            type("Resolution", (), {"actor_class": "evoker", "spec": "devastation", "source_notes": ["decoded via /tmp/simc"]})(),
        )

    monkeypatch.setattr("simc_cli.main._resolve_prune_context", fake_context)

    explain_result = runner.invoke(simc_app, ["apl-intent-explain", str(apl), "--targets", "1"])
    assert explain_result.exit_code == 0
    explain_payload = json.loads(explain_result.stdout)
    assert explain_payload["explained_intent"]["priorities"]

    compare_result = runner.invoke(simc_app, ["apl-branch-compare", str(apl), "--left-targets", "3", "--right-targets", "1"])
    assert compare_result.exit_code == 0
    compare_payload = json.loads(compare_result.stdout)
    assert compare_payload["comparison"]["dispatch_changed"] is True
    assert compare_payload["comparison"]["left_focus_intent"]

    packet_result = runner.invoke(simc_app, ["analysis-packet", str(apl), "--targets", "1"])
    assert packet_result.exit_code == 0
    packet_payload = json.loads(packet_result.stdout)
    assert packet_payload["packet"]["focus_list"] == "st"
    assert packet_payload["packet"]["explained_intent"]["priorities"]


def test_simc_first_cast_and_log_actions(monkeypatch, tmp_path: Path) -> None:
    profile = tmp_path / "example.simc"
    profile.write_text('monk="example"\n')
    log_path = tmp_path / "combat.log"
    log_path.write_text(
        "\n".join(
            [
                "0.100 schedules execute for Action 'rising_sun_kick'",
                "0.250 performs Action 'rising_sun_kick'",
            ]
        )
        + "\n"
    )

    monkeypatch.setattr(
        "simc_cli.main.run_first_casts",
        lambda paths, profile_path, action, seeds, max_time, targets, fight_style: [
            type("Result", (), {"seed": 1, "time": 0.2, "log_path": tmp_path / "seed_1.log"})(),
            type("Result", (), {"seed": 2, "time": 0.3, "log_path": tmp_path / "seed_2.log"})(),
        ],
    )
    monkeypatch.setattr(
        "simc_cli.main.summarize_first_casts",
        lambda results: {"samples": 2, "found": 2, "min": 0.2, "avg": 0.25, "max": 0.3},
    )

    first_cast_result = runner.invoke(simc_app, ["first-cast", str(profile), "rising_sun_kick"])
    assert first_cast_result.exit_code == 0
    first_cast_payload = json.loads(first_cast_result.stdout)
    assert first_cast_payload["summary"]["avg"] == 0.25
    assert first_cast_payload["results"][0]["seed"] == 1

    log_result = runner.invoke(simc_app, ["log-actions", str(log_path), "rising_sun_kick"])
    assert log_result.exit_code == 0
    log_payload = json.loads(log_result.stdout)
    assert log_payload["count"] == 1
    assert log_payload["hits"][0]["performed_at"] == 0.25


def test_simc_analysis_packet_surfaces_runtime_timing_failures(monkeypatch, tmp_path: Path) -> None:
    apl = tmp_path / "evoker_devastation.simc"
    apl.write_text("actions.st+=/disintegrate\n")

    monkeypatch.setattr(
        "simc_cli.main._resolve_prune_context",
        lambda paths, apl_path, option_values, targets: (
            type("Context", (), {"enabled_talents": set(), "disabled_talents": set(), "targets": targets, "talent_sources": {}})(),
            type("Resolution", (), {"actor_class": "evoker", "spec": "devastation", "source_notes": ["decoded via /tmp/simc"]})(),
        ),
    )
    monkeypatch.setattr("simc_cli.main.build_analysis_packet", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("timing failed")))

    result = runner.invoke(
        simc_app,
        [
            "analysis-packet",
            str(apl),
            "--targets",
            "1",
            "--sim-profile",
            str(tmp_path / "profile.simc"),
            "--first-cast-action",
            "disintegrate",
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "analysis_packet_failed"
    assert payload["error"]["message"] == "timing failed"


def test_simc_sync_skips_dirty_repo(monkeypatch) -> None:
    monkeypatch.setattr("simc_cli.main.repo_git_status", lambda paths: {"git": True, "dirty": True, "branch": "main", "head": "abc", "dirty_entries": [" M engine/file.cpp"]})
    monkeypatch.setattr("simc_cli.main.sync_repo", lambda paths, allow_dirty: None)
    result = runner.invoke(simc_app, ["sync"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "skipped"
    assert payload["reason"] == "dirty_worktree"


def test_simc_build_surfaces_success(monkeypatch) -> None:
    monkeypatch.setattr(
        "simc_cli.main.build_repo",
        lambda paths, target: type("Result", (), {"command": ["cmake", "--build", str(paths.build_dir)], "returncode": 0, "stdout": "Built target simc\n", "stderr": ""})(),
    )
    result = runner.invoke(simc_app, ["build"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "built"


def test_simc_run_surfaces_failure_with_preview(monkeypatch, tmp_path: Path) -> None:
    profile = tmp_path / "example.simc"
    profile.write_text('monk="example"\n')
    monkeypatch.setattr(
        "simc_cli.main.run_profile",
        lambda paths, profile_path, simc_args: type("Result", (), {"command": [str(paths.build_simc), str(profile_path)], "returncode": 1, "stdout": "", "stderr": "bad profile\n"})(),
    )
    monkeypatch.setattr(
        "simc_cli.main.binary_version",
        lambda paths: type("VersionInfo", (), {"binary_path": paths.build_simc, "available": True, "version_line": "SimulationCraft 1201", "returncode": 1})(),
    )
    result = runner.invoke(simc_app, ["run", str(profile)])
    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "run_failed"


def test_simc_sim_uses_quick_preset_and_surfaces_run_metadata(monkeypatch, tmp_path: Path) -> None:
    profile = tmp_path / "example.simc"
    profile.write_text('paladin="example"\n')

    def _run(paths, profile_path, simc_args):
        args = {item.split("=", 1)[0]: item.split("=", 1)[1] for item in simc_args if "=" in item}
        json_path = Path(args["json2"])
        json_path.write_text(
            json.dumps(
                {
                    "version": "SimulationCraft 1201-01",
                    "sim": {
                        "options": {
                            "iterations": 1000,
                            "target_error": 0,
                            "threads": 12,
                            "fight_style": "Patchwerk",
                            "desired_targets": 1,
                            "max_time": 300,
                            "vary_combat_length": 0.2,
                            "seed": 12345,
                            "dbc": {
                                "version_used": "Live",
                                "Live": {"wow_version": "12.0.1.66263"},
                            },
                        },
                        "statistics": {
                            "elapsed_time_seconds": 4.33,
                            "elapsed_cpu_seconds": 100.4,
                            "init_time_seconds": 0.12,
                            "merge_time_seconds": 0.03,
                            "analyze_time_seconds": 0.01,
                            "simulation_length": {"count": 1003},
                        },
                        "players": [
                            {
                                "name": "example",
                                "specialization": "protection",
                                "role": "tank",
                                "collected_data": {
                                    "fight_length": {"mean": 299.37, "count": 1003},
                                    "dps": {"mean": 18834.4},
                                    "dpse": {"mean": 37.2},
                                    "dtps": {"mean": 75769.2},
                                    "hps": {"mean": 2210.9},
                                    "deaths": {"mean": 0.0},
                                    "absorb": {"mean": 795348.3},
                                    "heal": {"mean": 661816.8},
                                },
                            }
                        ],
                    },
                }
            )
        )
        return type(
            "Result",
            (),
            {"command": [str(paths.build_simc), str(profile_path), *simc_args], "returncode": 0, "stdout": "ok\n", "stderr": ""},
        )()

    monkeypatch.setattr("simc_cli.main.run_profile", _run)
    result = runner.invoke(simc_app, ["sim", str(profile)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["preset"] == "quick"
    assert payload["input_source"] == "file"
    assert payload["run_settings"]["iterations_requested"] == 1000
    assert payload["run_settings"]["iterations_completed"] == 1003
    assert payload["run_settings"]["stop_reason"] == "fixed_iterations_completed"
    assert payload["runtime"]["elapsed_time_seconds"] == 4.33
    assert payload["metrics"]["dps"] == 18834.4
    assert payload["metrics"]["dtps"] == 75769.2
    assert payload["metrics"]["fight_length"] == 299.37
    assert payload["simc_version"] == "SimulationCraft 1201-01"
    assert payload["game_version"] == "12.0.1.66263"
    assert payload["json_report_path"] is None


def test_simc_sim_reads_stdin_and_respects_overrides(monkeypatch, tmp_path: Path) -> None:
    def _run(paths, profile_path, simc_args):
        args = {item.split("=", 1)[0]: item.split("=", 1)[1] for item in simc_args if "=" in item}
        json_path = Path(args["json2"])
        json_path.write_text(
            json.dumps(
                {
                    "version": "SimulationCraft 1201-01",
                    "sim": {
                        "options": {
                            "iterations": 6000,
                            "target_error": 0,
                            "threads": 4,
                            "fight_style": "HecticAddCleave",
                            "desired_targets": 5,
                            "max_time": 180,
                            "vary_combat_length": 0.1,
                            "seed": 222,
                            "dbc": {"version_used": "Live", "Live": {"wow_version": "12.0.1.66263"}},
                        },
                        "statistics": {"elapsed_time_seconds": 8.6, "simulation_length": {"count": 6003}},
                        "players": [
                            {
                                "name": "stdin-example",
                                "specialization": "protection",
                                "role": "tank",
                                "collected_data": {
                                    "fight_length": {"mean": 180.0, "count": 6003},
                                    "dps": {"mean": 21000.0},
                                    "dpse": {"mean": 50.0},
                                    "dtps": {"mean": 80000.0},
                                    "hps": {"mean": 2500.0},
                                    "deaths": {"mean": 0.0},
                                    "absorb": {"mean": 1.0},
                                    "heal": {"mean": 2.0},
                                },
                            }
                        ],
                    },
                }
            )
        )
        return type(
            "Result",
            (),
            {"command": [str(paths.build_simc), str(profile_path), *simc_args], "returncode": 0, "stdout": "", "stderr": ""},
        )()

    monkeypatch.setattr("simc_cli.main.run_profile", _run)
    result = runner.invoke(
        simc_app,
        ["sim", "-", "--preset", "high-accuracy", "--iterations", "6000", "--max-time", "180", "--fight-style", "HecticAddCleave", "--targets", "5", "--threads", "4", "--vary-combat-length", "0.1"],
        input='paladin="stdin-example"\n',
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["preset"] == "high-accuracy"
    assert payload["input_source"] == "stdin"
    assert payload["profile_path"] is None
    assert payload["run_settings"]["iterations_requested"] == 6000
    assert payload["run_settings"]["threads"] == 4
    assert payload["run_settings"]["fight_style"] == "HecticAddCleave"
    assert payload["run_settings"]["desired_targets"] == 5
    assert payload["run_settings"]["max_time"] == 180


@pytest.mark.skipif(not Path("/home/auro/code/simc/build/simc").exists(), reason="local simc binary not available")
def test_simc_version_reads_local_binary() -> None:
    result = runner.invoke(simc_app, ["version"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert str(payload["version"]).startswith("SimulationCraft")
