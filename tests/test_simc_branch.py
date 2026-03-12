from __future__ import annotations

from pathlib import Path

from simc_cli.branch import attach_focus_comparison, compare_branch_summaries, explain_intent, summarize_branches, summarize_intent
from simc_cli.prune import PruneContext


def _sample_apl(tmp_path: Path) -> Path:
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
    return apl


def test_summarize_branches_and_intent(tmp_path: Path) -> None:
    apl = _sample_apl(tmp_path)
    summary = summarize_branches(apl, PruneContext(enabled_talents={"mass_disintegrate"}, disabled_talents=set(), targets=3))
    intent = summarize_intent(apl, PruneContext(enabled_talents={"mass_disintegrate"}, disabled_talents=set(), targets=1), "st")
    explained = explain_intent(apl, PruneContext(enabled_talents={"mass_disintegrate"}, disabled_talents=set(), targets=1), "st")
    assert summary.guaranteed_dispatch == "aoe"
    assert "always: disintegrate [talent.mass_disintegrate=true]" in intent
    assert explained.priorities


def test_compare_branch_summaries_and_focus_comparison(tmp_path: Path) -> None:
    apl = _sample_apl(tmp_path)
    left_context = PruneContext(enabled_talents={"mass_disintegrate"}, disabled_talents=set(), targets=3)
    right_context = PruneContext(enabled_talents=set(), disabled_talents=set(), targets=1)
    comparison = compare_branch_summaries(
        summarize_branches(apl, left_context),
        summarize_branches(apl, right_context),
    )
    comparison = attach_focus_comparison(comparison, apl, left_context, right_context)
    assert comparison.dispatch_changed is True
    assert comparison.left_focus_intent
    assert comparison.right_focus_intent == []
