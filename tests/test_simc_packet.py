from __future__ import annotations

from pathlib import Path

from simc_cli.packet import build_analysis_packet
from simc_cli.prune import PruneContext


def test_build_analysis_packet_reports_guaranteed_dispatch(tmp_path: Path) -> None:
    apl_path = tmp_path / "evoker_devastation.simc"
    apl_path.write_text(
        "\n".join(
            [
                "actions+=/run_action_list,name=aoe,if=active_enemies>=3",
                "actions+=/run_action_list,name=st,if=active_enemies<3",
                "actions.aoe+=/fire_breath",
                "actions.st+=/disintegrate",
            ]
        )
        + "\n"
    )
    packet = build_analysis_packet(apl_path, PruneContext(enabled_talents=set(), disabled_talents=set(), targets=3))
    assert packet.focus_list == "aoe"
    assert packet.dispatch_certainty == "guaranteed"
    assert packet.escalation_reasons == []
    assert "always: fire breath" in packet.intent_lines


def test_build_analysis_packet_flags_runtime_sensitive_priorities(tmp_path: Path) -> None:
    apl_path = tmp_path / "evoker_devastation.simc"
    apl_path.write_text(
        "\n".join(
            [
                "actions+=/run_action_list,name=st,if=active_enemies<3",
                "actions.st+=/disintegrate,if=buff.dragonrage.up",
            ]
        )
        + "\n"
    )
    packet = build_analysis_packet(apl_path, PruneContext(enabled_talents=set(), disabled_talents=set(), targets=1))
    assert packet.focus_list == "st"
    assert "early priorities in st depend on runtime-only state" in packet.escalation_reasons
    assert packet.runtime_sensitive_priorities == ["L2 disintegrate"]
