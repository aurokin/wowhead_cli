# Warcraft Logs Encounter Rankings Plan

## Goal

Add a first-class `warcraftlogs encounter-rankings` command backed by the official Warcraft Logs encounter rankings API so boss/class/spec ranking queries map to real ranking data instead of sampled kill analytics.

## Problem

Current boss-level Warcraft Logs commands such as `boss-kills` and `top-kills` accept `--spec-name`, but that filter currently means "keep sampled boss kills that include a matching player spec". It does not mean "return spec-filtered parse rankings".

That mismatch is especially confusing for queries like:

- "top 10 Balance Druid parses on Mythic Vanguard"

Users typically expect a ranking leaderboard, not sampled kill rows that merely contain a Balance player.

## Proposed Fix

Ship a new `warcraftlogs encounter-rankings` command that uses `Encounter.characterRankings(...)` and exposes encounter ranking filters directly:

- `--zone-id`
- `--boss-id` or `--boss-name`
- `--difficulty`
- `--class-name`
- `--spec-name`
- `--metric`
- `--page`
- `--partition`
- `--size`
- `--server-region`
- `--server-slug`
- `--leaderboard`
- `--hard-mode-level`
- `--filter`
- `--include-combatant-info`
- `--include-other-players`
- `--top`

Keep the existing sampled boss analytics commands, but make their semantics more explicit in both help text and output.

## Work Items

- [x] Add encounter rankings client query and options dataclass
- [x] Add `warcraftlogs encounter-rankings` CLI command
- [x] Normalize encounter rankings payload for agent-friendly output
- [x] Add explicit ambiguity note for sampled boss commands when `--spec-name` is used
- [x] Update Warcraft Logs docs and skill examples
- [x] Add tests for the new command and sampled-command cleanup
- [x] Run targeted verification

## Progress

### 2026-04-14

- [x] Researched the official Warcraft Logs encounter docs and confirmed `Encounter.characterRankings(...)` supports `className` and `specName`.
- [x] Confirmed the current `top-kills`/`boss-kills` implementation uses sampled report discovery plus participant spec matching, not ranking queries.
- [x] Added `EncounterRankingsOptions`, `ENCOUNTER_RANKINGS_QUERY`, and `WarcraftLogsClient.encounter_rankings(...)`.
- [x] Added `warcraftlogs encounter-rankings` with `--boss-id` or `--boss-name` resolution inside `--zone-id`.
- [x] Normalized encounter ranking output into an explicit `encounter_rankings` payload with stable row summaries and preserved raw provider data.
- [x] Added sampled-command notes clarifying that `--spec-name` on sampled boss analytics is participant filtering, not a spec leaderboard.
- [x] Updated Warcraft Logs docs and skill references to route boss/class/spec leaderboard questions to `encounter-rankings`.
- [x] Added unit coverage for the new command and the new sampled-command note behavior.
- [x] Verification completed:
  - `.venv/bin/pytest -q tests/test_warcraftlogs_cli.py`
  - `.venv/bin/ruff check --select I,B009,B904,UP017 packages/warcraftlogs-cli/src/warcraftlogs_cli/main.py tests/test_warcraftlogs_cli.py`
  - `.venv/bin/warcraftlogs encounter-rankings --help`

## Notes

- The preferred fix is additive. Do not reinterpret `top-kills` as rankings.
- Sampled analytics remain useful, but they must stay clearly labeled as sampled analytics.
- The docs example URL pattern to align with is:
  - `https://www.warcraftlogs.com/zone/rankings/46?boss=3180&class=Druid&spec=Balance`
