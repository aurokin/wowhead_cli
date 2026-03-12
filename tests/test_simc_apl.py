from __future__ import annotations

from pathlib import Path

from simc_cli.apl import action_counts, group_entries, mermaid_graph, parse_apl, talent_refs, trace_action_entries


def _sample_apl(tmp_path: Path) -> Path:
    apl = tmp_path / "monk_mistweaver.simc"
    apl.write_text(
        "\n".join(
            [
                "actions.precombat=flask",
                "actions=auto_attack",
                "actions+=/run_action_list,name=aoe,if=active_enemies>2",
                "actions+=/rising_sun_kick,if=talent.rising_mist.enabled",
                "actions.aoe=spinning_crane_kick",
                "actions.aoe+=/call_action_list,name=cds",
                "actions.cds=invoke_chiji,if=talent.invoke_chiji_the_red_crane.enabled",
            ]
        )
        + "\n"
    )
    return apl


def test_parse_apl_and_group_entries(tmp_path: Path) -> None:
    apl = _sample_apl(tmp_path)
    entries = parse_apl(apl)
    grouped = group_entries(entries)
    assert len(entries) == 7
    assert sorted(grouped) == ["aoe", "cds", "default", "precombat"]
    assert grouped["default"][1].target_list == "aoe"


def test_talent_refs_and_action_counts(tmp_path: Path) -> None:
    apl = _sample_apl(tmp_path)
    entries = parse_apl(apl)
    refs = talent_refs(entries)
    counts = action_counts(entries)
    assert refs["invoke_chiji_the_red_crane"] == [7]
    assert refs["rising_mist"] == [4]
    assert counts["aoe"] == 1
    assert counts["rising_sun_kick"] == 1


def test_mermaid_graph_and_trace_action(tmp_path: Path) -> None:
    apl = _sample_apl(tmp_path)
    entries = parse_apl(apl)
    graph = mermaid_graph(entries)
    traced = trace_action_entries(entries, "rising_sun_kick")
    assert "default -->|run| aoe" in graph
    assert "aoe -->|call| cds" in graph
    assert len(traced) == 1
    assert traced[0].line_no == 4
