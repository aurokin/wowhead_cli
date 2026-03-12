# Usage

This document is the command-oriented reference for the local Warcraft CLI workspace.

The goal is to keep the README short and keep detailed usage notes close to actual CLI behavior.

## Wrapper Commands

```bash
warcraft doctor
warcraft search "defias"
warcraft resolve "fairbreeze favors"
warcraft wowhead search "defias"
warcraft wowhead guide 3143
warcraft method search "mistweaver monk"
warcraft method guide mistweaver-monk
warcraft icy-veins search "mistweaver monk guide"
warcraft icy-veins guide mistweaver-monk-pve-healing-guide
warcraft raiderio character us illidan Roguecane
warcraft raiderio guild us illidan Liquid
warcraft warcraft-wiki search "world of warcraft api"
warcraft warcraft-wiki article "World of Warcraft API"
warcraft wowprogress guild us illidan Liquid
warcraft wowprogress leaderboard pve us --limit 10
warcraft simc doctor
warcraft simc version
warcraft simc spec-files mistweaver
warcraft simc apl-lists /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc
```

## Wrapper Conventions

- Use `warcraft` when the provider is unclear.
- Use `warcraft resolve` for a conservative next-command recommendation across providers.
- Use `warcraft search` when you want to inspect candidates across providers.
- Use `warcraft <provider> ...` when you already know which service you need.
- `method` is now a real guide provider with sitemap-backed search, resolve, export, and local query.
- `icy-veins` is now a real guide provider with sitemap-backed search, resolve, export, and local query.
- `raiderio` is now a real phase-1 API provider for direct character, guild, and Mythic+ runs lookups.
- `raiderio` search and resolve currently return structured `coming_soon` payloads in phase 1.
- `warcraft-wiki` is now a real reference provider with MediaWiki-backed search, resolve, article export, and local query.
- `wowprogress` is now a real phase-1 rankings provider for direct guild, character, and PvE leaderboard lookups.
- `wowprogress` search and resolve currently return structured `coming_soon` payloads in phase 1.
- `simc` is now a real phase-1 local-tool provider for local repo inspection, build decoding, and binary execution.
- `simc` now also includes its first readonly analysis commands for APL list inspection, graphing, talent gates, and action tracing.
- `simc` search and resolve currently return structured `coming_soon` payloads in phase 1.
- the flattened `warcraft search` result list is globally sorted by provider-reported ranking score
- `warcraft resolve` prefers the strongest resolved provider result instead of whichever provider happens to be registered first

`warcraft doctor` reports:
- wrapper health
- shared XDG-style config/data/cache roots
- registered provider readiness

## Wowhead Commands

```bash
wowhead search "defias"
wowhead resolve "fairbreeze favors"
wowhead --expansion wotlk search "thunderfury"
wowhead guide 3143
wowhead guide-full 3143
wowhead guide-export 3143 --out ./tmp/frost-dk-guide
wowhead guide-export 3143 --out ./tmp/frost-dk-guide --hydrate-linked-entities --hydrate-type spell,item --hydrate-limit 100
wowhead guide-bundle-list
wowhead guide-bundle-list --max-age-hours 72
wowhead guide-bundle-search "frost death knight"
wowhead guide-bundle-query "obliterate"
wowhead guide-bundle-inspect 3143
wowhead guide-bundle-index-rebuild
wowhead cache-inspect
wowhead cache-inspect --show-redis-prefixes
wowhead cache-inspect --summary --hide-zero
wowhead cache-repair --expired-only
wowhead guide-bundle-inspect 3143 --summary
wowhead cache-clear --namespace entity_response --expired-only
wowhead guide-bundle-refresh ./tmp/frost-dk-guide
wowhead guide-bundle-refresh 3143 --root ./wowhead_exports --max-age-hours 6
wowhead guide-query ./tmp/frost-dk-guide "bellamy"
wowhead guide-query 3143 "obliterate" --root ./wowhead_exports
wowhead guide-query ./tmp/frost-dk-guide "welcome" --kind sections --section-title overview
wowhead guide-query 3143 "bellamy" --root ./wowhead_exports --kind linked_entities --linked-source multi
wowhead --pretty search "defias"
wowhead --fields query,count,results search "defias"
wowhead entity item 19019
wowhead entity item 19019 --no-include-comments
wowhead entity item 19019 --include-all-comments
wowhead entity faction 529 --no-include-comments
wowhead entity recipe 2549 --no-include-comments
wowhead entity mount 460 --no-include-comments
wowhead entity battle-pet 39 --no-include-comments
wowhead --compact entity item 19019
wowhead --expansion classic entity item 19019
wowhead --fields entity.name,entity.page_url,tooltip.summary,linked_entities entity quest 86739
wowhead --expansion ptr --normalize-canonical-to-expansion entity-page item 19019
wowhead entity-page item 19019 --max-links 100
wowhead comments item 19019 --limit 30 --sort rating
wowhead compare item:19019 item:19351 --comment-sample 2
wowhead expansions
```

## Method Commands

```bash
method doctor
method search "mistweaver monk"
method resolve "mistweaver monk guide"
method guide "mistweaver-monk"
method guide-full "mistweaver-monk"
method guide-export "mistweaver-monk" --out ./tmp/method-mistweaver
method guide-query ./tmp/method-mistweaver "tea serenity"
```

Method guide behavior:
- `search` and `resolve` work against the Method guide sitemap
- `guide` returns the requested page summary with navigation and linked-entity preview
- `guide-full` walks the guide navigation and returns all discovered guide pages
- `guide-export` writes a local guide bundle under `./method_exports/` by default
- `guide-query` searches exported Method bundles across sections, navigation links, and linked entities

## Icy Veins Commands

```bash
icy-veins doctor
icy-veins search "mistweaver monk guide"
icy-veins resolve "mistweaver monk guide"
icy-veins guide "mistweaver-monk-pve-healing-guide"
icy-veins guide-full "mistweaver-monk-pve-healing-guide"
icy-veins guide-export "mistweaver-monk-pve-healing-guide" --out ./tmp/icy-mistweaver
icy-veins guide-query ./tmp/icy-mistweaver "vivify"
```

Icy Veins guide behavior:
- `search` and `resolve` work against the Icy Veins sitemap for WoW guide-like pages
- `guide` returns the requested page summary with guide-family navigation, page TOC, and linked-entity preview
- `guide-full` walks the guide-family navigation and returns all discovered guide pages
- `guide-export` writes a local guide bundle under `./icy-veins_exports/` by default
- `guide-query` searches exported Icy Veins bundles across sections, navigation links, and linked entities

## Raider.IO Commands

```bash
raiderio doctor
raiderio search "liquid"
raiderio resolve "liquid"
raiderio character us illidan Roguecane
raiderio guild us illidan Liquid
raiderio mythic-plus-runs --region world --dungeon all --page 0
```

Raider.IO phase-1 behavior:
- `doctor` reports cache config and phase-1 capability state
- `character` returns a compact profile summary with guild, Mythic+, and raid progression context
- `guild` returns a compact guild profile with raid progression, raid rankings, and roster preview
- `mythic-plus-runs` returns ranked Mythic+ run summaries from the documented API endpoint
- `search` and `resolve` exist for wrapper-contract stability, but return structured `coming_soon` payloads until Raider.IO discovery is implemented

## Warcraft Wiki Commands

```bash
warcraft-wiki doctor
warcraft-wiki search "world of warcraft api"
warcraft-wiki resolve "world of warcraft api"
warcraft-wiki article "World of Warcraft API"
warcraft-wiki article-full "World of Warcraft API"
warcraft-wiki article-export "World of Warcraft API" --out ./tmp/wiki-api
warcraft-wiki article-query ./tmp/wiki-api "framexml"
```

Warcraft Wiki behavior:
- `search` and `resolve` use the MediaWiki search API
- `article` returns a compact article summary with section navigation and linked wiki-article preview
- `article-full` returns the parsed article payload used for local export
- `article-export` writes a local article bundle under `./warcraft-wiki_exports/` by default
- `article-query` searches exported wiki bundles across sections, navigation links, and linked entities

## WowProgress Commands

```bash
wowprogress doctor
wowprogress search "liquid"
wowprogress resolve "liquid"
wowprogress guild us illidan Liquid
wowprogress character us illidan Imonthegcd
wowprogress leaderboard pve us --limit 10
wowprogress leaderboard pve us --realm illidan --limit 10
```

WowProgress phase-1 behavior:
- `doctor` reports cache config and the browser-fingerprint HTTP transport used for live fetches
- `guild` returns a compact guild profile with progression, item-level rank context, and encounter history
- `character` returns a compact character profile with item-level, SimDPS, and PvE raid-history context
- `leaderboard pve` returns the current PvE progression leaderboard for a region, optionally narrowed to a realm
- `search` and `resolve` exist for wrapper-contract stability, but return structured `coming_soon` payloads until WowProgress discovery is implemented

## SimulationCraft Commands

```bash
simc doctor
simc version
simc inspect
simc inspect /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc
simc spec-files mistweaver
simc decode-build --apl-path /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --talents ABC123 --actor-class monk --spec mistweaver
simc apl-lists /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc
simc apl-graph /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc
simc apl-talents /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc
simc find-action rising_sun_kick --class monk
simc trace-action /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc rising_sun_kick --class monk
simc run ./profile.simc --arg iterations=1 --arg desired_targets=1
simc sync
simc build
```

SimulationCraft phase-1 behavior:
- `doctor` reports repo path, git status, binary presence, and phase-1 capability state
- `version` probes the local `simc` binary and extracts the printed SimulationCraft version line
- `inspect` returns either repo state or file-level inspection data, including inferred actor/spec and extracted build lines for `.simc` files
- `spec-files` searches the local checkout across APL files and, when queried, matching class modules and spell dumps
- `decode-build` uses the local `simc` binary to decode talent strings into enabled talents and tree-grouped talent rows
- `apl-lists` returns parsed action lists and their entries from a local `.simc` file
- `apl-graph` emits a Mermaid action-list call graph from a local `.simc` file
- `apl-talents` returns talent gate references and a compact action frequency summary for a local `.simc` file
- `find-action` searches local APLs, class modules, and spell dumps for an action token
- `trace-action` combines local APL hits with broader repo search hits for one action token
- `run` executes the local `simc` binary against a profile and returns bounded stdout/stderr previews
- `sync` and `build` are conservative local repo helpers; `sync` skips dirty worktrees unless `--allow-dirty` is set
- `search` and `resolve` exist for wrapper-contract stability, but return structured `coming_soon` payloads until SimC discovery is implemented

## Output Conventions

- Default output is compact JSON for machine consumption.
- Use `--pretty` for human-readable JSON.
- Successful responses omit `ok`.
- Structured failures return `ok: false` with an `error` object.
- Use `--fields` to project only selected dot-paths from the JSON payload.
- Use `--compact` to truncate long string fields such as tooltip HTML blobs.
- Wrapper responses preserve provider provenance instead of flattening everything into a fake universal schema.

## Expansion And Routing

- Use global `--expansion` to target a version profile; default is `retail`.
- Use `--normalize-canonical-to-expansion` if you want canonical entity page URLs forced into the selected expansion path.
- Some entity types use special routing under the hood:
  - `faction` and `pet` use page-metadata tooltip fallbacks
  - `recipe` resolves through spell pages
  - `mount` resolves through underlying item pages
  - `battle-pet` resolves through underlying NPC pages

See [WOWHEAD_EXPANSION_RESEARCH.md](/home/auro/code/wowhead_cli/docs/WOWHEAD_EXPANSION_RESEARCH.md) for the routing and `dataEnv` findings behind this behavior.

## Entity Retrieval

- `entity` is the compact main retrieval command.
- `entity-page` is the richer page exploration command.
- `comments` is the comment-focused command.

Regular `entity`, `guide`, and `comments` responses include a lightweight `linked_entities` preview with:
- basic records
- `counts_by_type`
- `fetch_more_command`

Use `--linked-entity-preview-limit 0` on `entity` or `comments` if you want to skip that preview.

`entity` responses expose:
- `entity.name`
- `entity.page_url`
- `tooltip.summary`
- `tooltip.text`
- `tooltip.html`

When comments are included:
- `citations.comments` is the comment-thread source URL
- `comments.needs_raw_fetch` indicates whether a larger raw comments fetch is still useful

Tooltip cleanup behavior:
- item and mount summaries prefer actionable effect or use text over boilerplate
- spell summaries prefer the descriptive effect clause over cast metadata
- cleaned tooltip text normalizes noisy spacing, money strings, and long flavor-text noise

## Guides And Bundles

- `guide` resolves guide IDs or URLs and returns metadata plus sampled comments.
- `guide-full` returns the rich embedded guide payload in one response.
- `guide-export` writes local guide assets for repeated agent exploration.

`guide-export` writes files such as:
- `guide.json`
- `page.html`
- `sections.jsonl`
- `linked-entities.jsonl`
- `comments.jsonl`
- `manifest.json`

Optional hydration:
- `--hydrate-linked-entities` writes compact local entity payloads under `entities/<type>/<id>.json`
- default hydrated types are `spell,item,npc`
- use `--hydrate-type` and `--hydrate-limit` to narrow the hydration set

Hydration behavior:
- it reuses the normalized `entity` contract
- it checks the normalized entity cache before live fetches
- hydrated entity manifests track `stored_at` and `storage_source`
- bundle manifests expose `hydration.source_counts`

Search and resolve:
- use `search` when you want to browse candidates or the query is likely ambiguous
- `search` results now include `ranking` plus `follow_up`, so each candidate carries a suggested next command such as `entity`, `entity-page`, `guide`, `guide-full`, or `comments`
- when the query contains follow-up words like `comments`, `links`, or `full`, the CLI strips those from the upstream Wowhead lookup and exposes the actual request text as `search_query`
- use `resolve` when you want the CLI to choose the best next command conservatively
- `resolve` reuses the same follow-up guidance, but only emits `next_command` when confidence is high
- `resolve --entity-type guide` or similar can safely narrow ambiguous queries when the caller already knows the target class of thing

Bundle discovery and refresh:
- bundle freshness summaries now include reason fields such as `bundle_reasons` and `hydration_reasons`, so stale bundles can be triaged without opening the manifest
- `guide-bundle-list`, `guide-bundle-search`, and `guide-bundle-query` now expose root-level `stale_reason_counts` rollups
- `guide-bundle-inspect --summary` returns a compact trust-check payload focused on freshness and issues
- `guide-bundle-list` discovers bundles under `./wowhead_exports/` or another root
- `guide-bundle-search` searches indexed bundle metadata across a root
- `guide-bundle-query` searches exported bundle content across a root using the same match kinds and linked-source filters as `guide-query`
- `guide-bundle-inspect` checks one bundle for freshness, file presence, observed counts, and root index membership
- `guide-bundle-index-rebuild` rescans a root and rewrites `index.json` explicitly for repair cases
- it includes `freshness` and `hydration` summaries
- `--max-age-hours` changes the freshness threshold used by those summaries
- bundle exports and refreshes maintain a root-level `index.json`
- `guide-bundle-list`, `guide-bundle-search`, and `guide-bundle-query` prefer that index when it is present and valid
- `guide-bundle-refresh` refreshes an existing bundle in place
- `cache-inspect` shows current cache config plus namespace-level stats for the active file or Redis backend
- `cache-clear` clears cache entries across all namespaces or selected namespaces, with `--expired-only` support for file-backed caches
- `search` now reranks upstream suggestions locally and includes lightweight `ranking.score` plus `ranking.match_reasons` per result
- `resolve` is the conservative one-shot discovery path: it picks a best match and returns a runnable `next_command` only when confidence is high, otherwise it falls back to `search`
- if `--max-age-hours` is omitted on refresh, the default freshness window is `24`
- refresh selectively rehydrates stale hydrated entity payloads unless `--force` is used

## Guide Querying

`guide-query` searches one exported guide bundle locally across:
- section content
- navigation links
- linked entities
- gatherer entities
- comments

It accepts either:
- a direct bundle path
- a selector such as guide ID under `--root`

Useful filters:
- `--kind`
- `--section-title`
- `--linked-source href|gatherer|multi`

The flattened `top` list prefers merged linked-entity rows over duplicate raw gatherer rows for the same entity.

## Compare

`compare` performs multi-entity analysis with:
- normalized summary fields
- linked-entity overlap and unique sets
- comment context
- canonical citation links

Generated overlap and unique linked-entity rows use a single canonical `url`.

## Cache

Transport caching is configurable through env vars. Useful defaults:

```bash
WOWHEAD_CACHE_BACKEND=file
WOWHEAD_CACHE_DIR=~/.cache/wowhead_cli/http
WOWHEAD_SEARCH_CACHE_TTL_SECONDS=900
WOWHEAD_TOOLTIP_CACHE_TTL_SECONDS=3600
WOWHEAD_ENTITY_PAGE_CACHE_TTL_SECONDS=3600
WOWHEAD_GUIDE_PAGE_CACHE_TTL_SECONDS=3600
WOWHEAD_COMMENT_REPLIES_CACHE_TTL_SECONDS=1800
WOWHEAD_ENTITY_CACHE_TTL_SECONDS=3600
```

Optional Redis support:

```bash
WOWHEAD_CACHE_BACKEND=redis
WOWHEAD_REDIS_URL=redis://host:6379/3
WOWHEAD_REDIS_PREFIX=wowhead_cli
```

Current active cache layers:
- transport cache for raw tooltip, page, search, and comment responses
- normalized `entity` response cache for repeated `entity` lookups with the same flags

The normalized entity cache is expansion-scoped.

Redis visibility:
- `cache-inspect --show-redis-prefixes` adds a bounded `prefix_visibility` summary for shared Redis deployments
- it shows whether the configured prefix appears isolated, how many keys live under other prefixes, and a capped list of visible prefixes in the same Redis

Cache cleanup and compact inspection:
- `cache-inspect --summary` returns a compact top-namespace view instead of the full namespace listing
- `cache-inspect --hide-zero` removes zero-valued count fields from cache stats
- summary-mode file cache inspection now includes `age_summary` with oldest/newest entry timestamps and ages
- `cache-repair` reports legacy unscoped file-cache entries; `cache-repair --apply` prunes them
- `cache-repair --expired-only` limits that repair to expired legacy entries

## Related Docs

- [ROADMAP.md](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
- [WOWHEAD_ACCESS_METHODS.md](/home/auro/code/wowhead_cli/docs/WOWHEAD_ACCESS_METHODS.md)
- [WOWHEAD_EXPANSION_RESEARCH.md](/home/auro/code/wowhead_cli/docs/WOWHEAD_EXPANSION_RESEARCH.md)
