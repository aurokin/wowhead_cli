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
- Guide category listing: `wowhead guides <category> [query]`
- News timeline search: `wowhead news [query] [--page <n>] [--pages <n>] [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD]`
- News article fetch: `wowhead news-post <url-or-path>`
- Blue tracker timeline search: `wowhead blue-tracker [query] [--page <n>] [--pages <n>] [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD]`
- Blue tracker topic fetch: `wowhead blue-topic <url-or-path>`
- Talent calculator state decode: `wowhead talent-calc <url-or-ref>`
- Profession tree state decode: `wowhead profession-tree <url-or-ref>`
- Dressing room state inspect: `wowhead dressing-room <url-or-hash>`
- Profiler state inspect: `wowhead profiler <url-or-list-ref>`
- Full guide payload: `wowhead guide-full <guide_id_or_url>`
- Export local guide assets: `wowhead guide-export <guide_id_or_url> --out <dir>`
- Export local guide assets plus bounded linked-entity hydration: `wowhead guide-export <guide_id_or_url> --out <dir> --hydrate-linked-entities [--hydrate-type spell,item,npc]`
- List exported guide bundles: `wowhead guide-bundle-list [--root <dir>] [--max-age-hours <n>]`
- Search exported bundle metadata: `wowhead guide-bundle-search "<query>" [--root <dir>]`
- Query exported bundle content across a root: `wowhead guide-bundle-query "<query>" [--root <dir>]`
- Inspect one exported guide bundle: `wowhead guide-bundle-inspect <bundle-or-selector> [--root <dir>]`
- Rebuild a root bundle index explicitly: `wowhead guide-bundle-index-rebuild [--root <dir>]`
- Inspect the active cache backend: `wowhead cache-inspect`
- Resolve a query to the best next command: `wowhead resolve "<query>" [--entity-type guide|quest|item|spell]`
- Clear cache entries: `wowhead cache-clear [--namespace entity_response] [--expired-only]`
- Refresh an exported guide bundle in place: `wowhead guide-bundle-refresh <bundle-or-selector> [--root <dir>]`
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
17. Cache behavior is now configurable by env vars. Default caching uses file storage with longer TTLs for stable entity/page fetches, plus a normalized `entity` response cache for repeated `entity` lookups with the same flags. For shared environments, optional Redis support uses a required key prefix such as `WOWHEAD_REDIS_PREFIX=wowhead_cli` so this CLI can coexist cleanly with other apps on the same Redis.
18. `guide-export --hydrate-linked-entities` writes compact normalized entity payloads for selected linked entities under `entities/<type>/<id>.json`, plus `entities/manifest.json`. Default hydrated types are `spell,item,npc`; use `--hydrate-type` and `--hydrate-limit` to keep exports bounded. Hydration checks the normalized entity cache before live fetches, and the entity manifest also tracks per-entity `stored_at` timestamps plus `storage_source` for later selective refresh and traceability.
19. `guide-bundle-list` now includes per-bundle `freshness` and `hydration` summaries so agents can see stale or fresh status, hydration settings, hydrated entity counts, and hydration provenance directly from discovery. It uses a default `24` hour threshold unless `--max-age-hours` is supplied, and it prefers a root-level `index.json` when available instead of rescanning bundle directories.
20. `guide-bundle-search` searches indexed bundle metadata across a root and returns ranked matches, compact match reasons, and a suggested `guide-query` command for each hit.
21. `guide-bundle-query` searches content across all bundles under a root and returns both matching bundles and a flattened cross-bundle `top` list. It reuses the same kinds, section-title filter, and linked-source filter behavior as `guide-query`, so agents can broaden from one bundle to many without changing query semantics.
22. `guide-bundle-inspect` is the trust-check command for one bundle. It compares manifest counts to observed local files, reports freshness and hydration state, and tells you whether the root `index.json` is valid and contains that bundle.
23. `guide-bundle-index-rebuild` is the explicit repair path for root discovery. Use it when `index.json` is missing, broken, or out of sync with the actual bundle directories.
24. `guide-bundle-refresh` infers refresh settings from the stored bundle manifest. If `--max-age-hours` is omitted, the default freshness window is 24 hours, so agents can safely refresh without passing a threshold in the common case. For hydrated bundles, refresh reuses entity payloads whose `stored_at` timestamp is still fresh and only re-fetches stale ones unless `--force` is used.
25. `cache-inspect` reports the active cache settings and namespace-level cache stats, so agents can check whether transport and normalized entity caches are populated, expired, or empty before assuming anything about freshness. For shared Redis deployments, `cache-inspect --show-redis-prefixes` also exposes bounded prefix-level visibility so agents can confirm the configured `WOWHEAD_REDIS_PREFIX` is isolated before trusting or clearing anything. Use `cache-inspect --summary --hide-zero` when the raw namespace listing is too noisy for an agent prompt; file-backed summary mode also includes `age_summary` so agents can see oldest/newest cache entry ages quickly.
26. `cache-clear` is the repair command for the cache layer. It can clear everything or just a selected namespace such as `entity_response`, and for file-backed caches it supports `--expired-only` to prune stale entries without blowing away fresh ones. `cache-repair` is the safer cleanup path for legacy unscoped file-cache entries left behind by older layouts, and `cache-repair --expired-only` keeps that cleanup bounded to expired legacy entries.
27. `search` no longer trusts upstream ordering blindly. It reranks suggestions locally using exact-name matches, full-term matches, type hints from the query, and popularity. Each result includes both a compact `ranking` object and `follow_up` guidance, so agents can inspect multiple candidates and still see whether `entity`, `entity-page`, `guide`, `guide-full`, or `comments` is the better next step for each one. If the natural-language query includes follow-up words like `comments`, `links`, or `full`, the CLI strips those from the upstream Wowhead lookup and exposes the actual request text as `search_query`.
28. `resolve` is the conservative counterpart to `search`. It reuses the same reranked candidates and follow-up guidance, optionally narrows by `--entity-type`, and only emits a direct `next_command` when confidence is high. If confidence is not high, it keeps the best candidate plus fallbacks and tells the agent to use `search` instead of overcommitting.

29. Bundle freshness summaries now include `bundle_reasons` and `hydration_reasons`, so agents can tell whether a bundle is stale because of age, missing timestamps, disabled hydration, or bundle-level staleness without opening manifest files. Root-level bundle discovery commands now also expose `stale_reason_counts`, and `guide-bundle-inspect --summary` provides a compact trust-check view when the full inspection payload is more detail than an agent needs.
30. `news` and `blue-tracker` are timeline-native surfaces, not generic search aliases. Use them when the user needs topic history, bounded date windows, page-window scans across posts, or stable listing-field filters instead of a single latest result.
31. `news-post` and `blue-topic` are the detail-fetch companions for those timeline commands. Prefer those over generic page scraping when you already have a specific news or blue-tracker URL.
32. `news-post` can also expose related/recent-post buckets that Wowhead embeds on article pages, and `blue-topic` exposes participant and blue-author summaries. Use those instead of building your own thread/article context heuristics.
33. `guides <category>` is the right surface for browsable guide families like `classes`, `professions`, and `raids`; use it when the user knows the guide family but not the exact guide slug or ID.
34. `guides <category>` also supports stable guide-list metadata filters such as author, updated window, patch range, and explicit sort controls. Prefer those over manually scanning long guide lists.
35. `talent-calc` and `profession-tree` are the first Wowhead tool decoders. They normalize the cited state URL and extract reliable route state like class/spec/build code or profession/loadout code.
36. `dressing-room` and `profiler` are currently state inspectors, not full decoders. Use them for normalized share refs and citations, but do not claim they fully decode appearance payloads or profile contents yet.
37. Treat deeper `dressing-room` / `profiler` decoding as a maintainability boundary. Do not drift into client-state reverse-engineering without an explicit product decision and a concrete workflow that justifies the complexity.

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
wowhead news "hotfixes" --pages 2 --date-from 2026-03-01
wowhead news "hotfixes" --type live --author Jaydaa --pages 2
wowhead news-post /news/midnight-hotfixes-for-march-13th-marl-decor-cost-reduction-class-bugfixes-and-380785
wowhead blue-tracker "class tuning" --pages 2 --date-from 2026-03-01
wowhead blue-tracker "class tuning" --region eu --forum "General Discussion"
wowhead blue-topic /blue-tracker/topic/eu/class-tuning-incoming-18-march-610948
wowhead guides classes "death knight"
wowhead guides classes --author Khazakdk --patch-min 120001 --updated-after 2026-02-01
wowhead guides classes --sort updated --limit 10
wowhead talent-calc druid/balance/DAQBBBBQQRUFURYVBEANVVRUVFVVVQCVQhEUEBUEBhVQ
wowhead profession-tree alchemy/BCuA
wowhead dressing-room "#fz8zz0zb89c8mM8YB8mN8X18mO8ub8mP8uD"
wowhead profiler 97060220/us/illidan/Roguecane
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
wowhead guide-export 3143 --out ./tmp/frost-dk-guide --hydrate-linked-entities --hydrate-type spell,item
wowhead guide-bundle-list
wowhead guide-bundle-refresh ./tmp/frost-dk-guide
wowhead guide-query ./tmp/frost-dk-guide "bellamy"
wowhead guide-query 3143 "obliterate" --root ./wowhead_exports
wowhead guide-query ./tmp/frost-dk-guide "welcome" --kind sections --section-title overview
wowhead guide-query 3143 "bellamy" --root ./wowhead_exports --kind linked_entities --linked-source multi
wowhead --expansion classic entity npc 91331
wowhead --fields entity.name,entity.page_url,tooltip.summary,linked_entities entity quest 86682
```
