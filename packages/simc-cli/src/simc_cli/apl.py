from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

ACTION_RE = re.compile(r"^actions(?:\.([A-Za-z0-9_]+))?(\+?=)(.+)$")
CALL_RE = re.compile(r"^(call_action_list|run_action_list),name=([A-Za-z0-9_]+)")
TALENT_RE = re.compile(r"talent\.([A-Za-z0-9_]+)")


@dataclass(slots=True)
class AplEntry:
    line_no: int
    list_name: str
    op: str
    action: str
    raw_args: str
    condition: str | None
    raw: str
    target_list: str | None
    kind: str


def _strip_comment(line: str) -> str:
    comment = line.find("#")
    if comment != -1:
        line = line[:comment]
    return line.strip()


def parse_apl(path: str | Path) -> list[AplEntry]:
    entries: list[AplEntry] = []
    apl_path = Path(path)
    for line_no, raw_line in enumerate(apl_path.read_text().splitlines(), start=1):
        line = _strip_comment(raw_line)
        if not line:
            continue
        match = ACTION_RE.match(line)
        if not match:
            continue
        list_name = match.group(1) or "default"
        op = match.group(2)
        body = match.group(3).strip()
        normalized_body = body[1:] if body.startswith("/") else body
        action, _, raw_args = normalized_body.partition(",")
        action = action.strip()
        raw_args = raw_args.strip()
        condition = None
        for part in raw_args.split(","):
            if part.startswith("if="):
                condition = part[3:]
                break
        target_list = None
        kind = "action"
        call_match = CALL_RE.match(normalized_body)
        if call_match:
            kind = call_match.group(1)
            target_list = call_match.group(2)
            action = call_match.group(1)
        entries.append(
            AplEntry(
                line_no=line_no,
                list_name=list_name,
                op=op,
                action=action,
                raw_args=raw_args,
                condition=condition,
                raw=line,
                target_list=target_list,
                kind=kind,
            )
        )
    return entries


def group_entries(entries: list[AplEntry]) -> dict[str, list[AplEntry]]:
    grouped: dict[str, list[AplEntry]] = defaultdict(list)
    for entry in entries:
        grouped[entry.list_name].append(entry)
    return dict(grouped)


def talent_refs(entries: list[AplEntry]) -> dict[str, list[int]]:
    refs: dict[str, set[int]] = defaultdict(set)
    for entry in entries:
        for talent in TALENT_RE.findall(entry.raw):
            refs[talent].add(entry.line_no)
    return {talent: sorted(lines) for talent, lines in sorted(refs.items())}


def action_counts(entries: list[AplEntry]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for entry in entries:
        key = entry.target_list if entry.target_list else entry.action
        counter[key] += 1
    return counter


def mermaid_graph(entries: list[AplEntry]) -> str:
    grouped = group_entries(entries)
    lines = ["flowchart TD"]
    seen_edges: set[tuple[str, str, str]] = set()
    for list_name, list_entries in grouped.items():
        node_name = "default" if list_name == "default" else list_name
        lines.append(f"  {node_name}[{list_name}]")
        for entry in list_entries:
            if not entry.target_list:
                continue
            edge = (list_name, entry.target_list, entry.kind)
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            label = "call" if entry.kind == "call_action_list" else "run"
            lines.append(f"  {node_name} -->|{label}| {entry.target_list}")
    return "\n".join(lines)


def trace_action_entries(entries: list[AplEntry], action: str) -> list[AplEntry]:
    return [entry for entry in entries if entry.action == action]
