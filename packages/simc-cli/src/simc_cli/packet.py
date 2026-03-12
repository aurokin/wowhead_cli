from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from simc_cli.branch import IntentExplanation, explain_intent, is_helper_decision, summarize_branches, summarize_intent, summarize_list_decisions
from simc_cli.prune import PruneContext


@dataclass(slots=True)
class AnalysisPacket:
    apl_path: Path
    start_list: str
    focus_list: str
    dispatch_certainty: str
    top_level_runtime_unresolved: bool
    runtime_sensitive_priorities: list[str]
    escalation_reasons: list[str]
    next_steps: list[str]
    intent_lines: list[str]
    explained_intent: IntentExplanation
    branch_summary: object


def build_analysis_packet(
    apl_path: str | Path,
    context: PruneContext,
    *,
    start_list: str = "default",
    intent_limit: int = 6,
    explain_limit: int = 8,
    runtime_scan_limit: int = 8,
) -> AnalysisPacket:
    normalized_path = Path(apl_path).expanduser().resolve()
    summary = summarize_branches(normalized_path, context, start_list=start_list)
    focus_list = summary.guaranteed_dispatch or start_list
    intent_lines = summarize_intent(normalized_path, context, focus_list, limit=intent_limit)
    explained = explain_intent(normalized_path, context, focus_list, limit=explain_limit)

    early_decisions = summarize_list_decisions(normalized_path, context, focus_list)
    runtime_sensitive = [
        f"L{decision.line_no} {decision.action_label}"
        for decision in early_decisions
        if decision.status == "possible"
        and decision.reason == "depends on runtime-only state"
        and not is_helper_decision(decision)
    ][:runtime_scan_limit]

    escalation_reasons: list[str] = []
    if summary.unresolved_branches:
        escalation_reasons.append("top-level dispatch still has unresolved branch candidates")
    if summary.branch_decisions and not summary.guaranteed_dispatch:
        escalation_reasons.append("no guaranteed run_action_list dispatch from the starting list")
    if runtime_sensitive:
        escalation_reasons.append(f"early priorities in {focus_list} depend on runtime-only state")

    return AnalysisPacket(
        apl_path=normalized_path,
        start_list=start_list,
        focus_list=focus_list,
        dispatch_certainty="guaranteed" if summary.guaranteed_dispatch else "unresolved",
        top_level_runtime_unresolved=bool(summary.unresolved_branches),
        runtime_sensitive_priorities=runtime_sensitive,
        escalation_reasons=escalation_reasons,
        next_steps=recommended_next_steps(start_list, focus_list, bool(summary.unresolved_branches), bool(runtime_sensitive)),
        intent_lines=intent_lines,
        explained_intent=explained,
        branch_summary=summary,
    )


def recommended_next_steps(start_list: str, focus_list: str, has_unresolved_branches: bool, has_runtime_sensitive_priorities: bool) -> list[str]:
    steps: list[str] = []
    if has_unresolved_branches:
        steps.append(f"run apl-branch-trace from `{start_list}` to inspect unresolved branch paths")
    if has_runtime_sensitive_priorities:
        steps.append(f"use trace-action on early `{focus_list}` actions before making runtime claims")
    if not steps:
        steps.append("use trace-action for any action-specific implementation questions")
    return steps
