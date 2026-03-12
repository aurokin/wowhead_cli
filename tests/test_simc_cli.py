from __future__ import annotations

import json
import subprocess
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
    assert payload["capabilities"]["apl_lists"] == "ready"
    assert payload["capabilities"]["apl_prune"] == "ready"


def test_simc_search_is_structured_coming_soon() -> None:
    result = runner.invoke(simc_app, ["search", "mistweaver"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["coming_soon"] is True
    assert payload["count"] == 0


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


@pytest.mark.skipif(not Path("/home/auro/code/simc/build/simc").exists(), reason="local simc binary not available")
def test_simc_version_reads_local_binary() -> None:
    result = runner.invoke(simc_app, ["version"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert str(payload["version"]).startswith("SimulationCraft")
