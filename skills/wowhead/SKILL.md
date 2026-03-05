---
name: wowhead
description: Query World of Warcraft data through the local `wowhead` CLI. Use when users need Wowhead lookups, entity resolution, quest/NPC/item/spell details, guide lookups, comments, or citation links. Trigger on requests like "look this up on wowhead", "find quest/npc/item/spell", "show comments", "compare entities", or troubleshooting quest progression with Wowhead evidence.
---

# Wowhead

Use the local `wowhead` command to fetch structured WoW data and citations.

## Command Routing

- Unknown ID or ambiguous request: `wowhead search "<query>" --limit 5`
- Known entity type + ID: `wowhead entity <type> <id>`
- Full page metadata + linked entities: `wowhead entity-page <type> <id>`
- Comments only / larger comment pull: `wowhead comments <type> <id> --limit <n> --sort newest|rating`
- Guide lookup: `wowhead guide <guide_id_or_url>`
- Multi-entity compare: `wowhead compare <type:id> <type:id> ...`

## Standard Workflow

1. Resolve candidate with `search` if ID is unknown.
2. Fetch main object with `entity`.
3. Inspect comment completeness from `entity` output:
- `comments_included` indicates whether comments were requested.
- `comments.all_comments_included` indicates whether returned comments are complete.
- `comments.needs_raw_fetch` indicates whether to call `wowhead comments ...` for full coverage.
4. Use `citations.page` and `citations.comments` in responses.

## Required Usage Rules

- Use `wowhead` (not `wowhead-cli`) in commands and examples.
- Place global flags before the subcommand:
- `wowhead --expansion wotlk entity item 19019`
- Use `--fields` when you only need specific keys.
- Use `--pretty` for user-facing JSON output.
- If comments are not needed, use `--no-include-comments` for faster lookups.
- If full comment set is required in one call, use `--include-all-comments`.

## Examples

```bash
wowhead search "Watch the Den" --limit 5
wowhead entity quest 86864
wowhead entity quest 86864 --no-include-comments
wowhead entity quest 86864 --include-all-comments
wowhead comments quest 86864 --limit 50 --sort rating
wowhead guide 3143
wowhead --expansion classic entity npc 91331
wowhead --fields entity,tooltip.name,citations entity quest 86682
```
