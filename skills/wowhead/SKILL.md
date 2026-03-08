---
name: wowhead
description: Query World of Warcraft data through the local `wowhead` CLI. Use when users need Wowhead lookups, entity resolution, quest/NPC/item/spell details, guide lookups, comments, or citation links. Trigger on requests like "look this up on wowhead", "find quest/npc/item/spell", "show comments", "compare entities", or troubleshooting quest progression with Wowhead evidence.
---

# Wowhead

Use the local `wowhead` command to fetch structured WoW data and citations.

Successful responses omit `ok`; only structured failures return `ok: false` with an `error` object.

## Command Routing

- Unknown ID or ambiguous request: `wowhead search "<query>" --limit 5`
- Known entity type + ID: `wowhead entity <type> <id>`
- Full page metadata + linked entities: `wowhead entity-page <type> <id>`
- Comments only / larger comment pull: `wowhead comments <type> <id> --limit <n> --sort newest|rating`
- Guide lookup: `wowhead guide <guide_id_or_url>`
- Full guide payload: `wowhead guide-full <guide_id_or_url>`
- Export local guide assets: `wowhead guide-export <guide_id_or_url> --out <dir>`
- List exported guide bundles: `wowhead guide-bundle-list [--root <dir>]`
- Query exported guide assets: `wowhead guide-query <dir> "<query>"`
- Multi-entity compare: `wowhead compare <type:id> <type:id> ...`

## Standard Workflow

1. Resolve candidate with `search` if ID is unknown.
2. Fetch main object with `entity`.
3. Inspect comment completeness from `entity` output:
- `comments.all_comments_included` indicates whether returned comments are complete.
- `comments.needs_raw_fetch` indicates whether to call `wowhead comments ...` for full coverage.
4. For `entity`, prefer `entity.name` and `entity.page_url` over older tooltip-derived naming; use `tooltip.summary` for fast scanning, `tooltip.text` for the cleaned full text, and `tooltip.html` only when markup matters. Page-metadata tooltip fallbacks such as `faction` and `pet` also expose `tooltip.summary`, not just `tooltip.text`. For noisy item- and mount-style tooltips, `tooltip.summary` now prefers effect/use text such as `Chance on hit:` or `Use:` over boilerplate item metadata, and `tooltip.text` now normalizes common artifacts like broken money amounts, long quoted flavor-text lines, and stray spacing around parentheticals or stat bonuses. Spell-style `tooltip.summary` also prefers the descriptive effect clause over cast metadata when both are present.
5. Inspect `linked_entities.counts_by_type` and the lightweight preview items on regular responses to decide whether to escalate to `entity-page` or `guide-full`.
6. For `entity`, `entity-page`, `comments`, and embedded compare entity summaries, use `entity.page_url` as the canonical page source and `citations.comments` for the comment thread source instead of older duplicated URL fields.
7. Some entity types use special routing under the hood:
- `faction` and `pet` derive tooltip text from page metadata.
- `recipe` resolves through spell pages.
- `mount` resolves through underlying item pages.
- `battle-pet` resolves through underlying NPC pages.
8. `guide` and `guide-full` now use the same merged `linked_entities` semantics; use `linked_entities.source_counts` when you need to understand how href and gatherer sources contributed.
9. Lightweight linked-entity previews are intentionally ranked and filtered for decision-making; they are not DOM-order dumps, and low-signal labels may be omitted from preview names even though the full relation data is still available via `entity-page` or `guide-full`.
10. For guide responses, prefer `guide.page_url` as the canonical guide source and `citations.comments` for the comment thread source.
11. For `compare`, use each entity record's `entity.page_url` and `citations.comments`; generated shared/unique linked-entity rows expose only `url`, not a duplicate `citation_url`.
12. Gatherer-derived linked entities use the linked entity page as both `url` and `citation_url`; `source_url` remains the original page where the relation was found.
13. Rich linked-entity payloads preserve normalized multi-source attribution under `sources` and `source_kind`; lightweight preview rows stay slim and do not expose that provenance.
14. Lightweight preview ranking prefers merged multi-source relations over similar single-source peers when other signals are otherwise comparable.
15. For exported guide bundles, prefer merged `linked_entities` plus `guide-query --linked-source href|gatherer|multi` over treating `linked_entities` and `gatherer_entities` as separate query buckets unless you explicitly need the raw source-specific rows.
16. In `guide-query`, the flattened `top` list prefers the merged linked-entity row over a duplicate raw gatherer row for the same entity; use `matches.gatherer_entities` if you explicitly need the raw source-specific result too.
17. Cache behavior is now configurable by env vars. Default transport caching uses file storage with longer TTLs for stable entity/page fetches. For shared environments, optional Redis support uses a required key prefix such as `WOWHEAD_REDIS_PREFIX=wowhead_cli` so this CLI can coexist cleanly with other apps on the same Redis.

## Required Usage Rules

- Use `wowhead` (not `wowhead-cli`) in commands and examples.
- Place global flags before the subcommand:
- `wowhead --expansion wotlk entity item 19019`
- Use `--fields` when you only need specific keys.
- Use `--pretty` for user-facing JSON output.
- If comments are not needed, use `--no-include-comments` for faster lookups.
- If full comment set is required in one call, use `--include-all-comments`.
- Use `--linked-entity-preview-limit 0` if you need the faster `entity`/`comments` path without relation previews.

## Examples

```bash
wowhead search "Watch the Den" --limit 5
wowhead entity quest 86864
wowhead entity quest 86864 --no-include-comments
wowhead entity quest 86864 --include-all-comments
wowhead entity faction 529 --no-include-comments
wowhead entity recipe 2549 --no-include-comments
wowhead entity mount 460 --no-include-comments
wowhead entity battle-pet 39 --no-include-comments
wowhead comments quest 86864 --limit 50 --sort rating
wowhead guide 3143
wowhead guide-full 3143
wowhead guide-export 3143 --out ./tmp/frost-dk-guide
wowhead guide-bundle-list
wowhead guide-query ./tmp/frost-dk-guide "bellamy"
wowhead guide-query 3143 "obliterate" --root ./wowhead_exports
wowhead guide-query ./tmp/frost-dk-guide "welcome" --kind sections --section-title overview
wowhead guide-query 3143 "bellamy" --root ./wowhead_exports --kind linked_entities --linked-source multi
wowhead --expansion classic entity npc 91331
wowhead --fields entity.name,entity.page_url,tooltip.summary,linked_entities entity quest 86682
```
