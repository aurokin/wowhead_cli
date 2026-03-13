# Usage

This document is the command-oriented reference for the local Warcraft CLI workspace.

The goal is to keep the README short and keep detailed usage notes close to actual CLI behavior.

## Wrapper Commands

```bash
warcraft doctor
warcraft --expansion wotlk doctor
warcraft search "defias"
warcraft --expansion wotlk search "thunderfury"
warcraft --expansion wotlk search "thunderfury" --compact --expansion-debug
warcraft search "guild us illidan Liquid" --compact --ranking-debug
warcraft resolve "fairbreeze favors"
warcraft --expansion wotlk resolve "thunderfury"
warcraft --expansion wotlk resolve "guild us illidan Liquid" --compact --expansion-debug
warcraft resolve "character us illidan Roguecane" --compact --ranking-debug
warcraft --expansion wotlk wowhead search "thunderfury"
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
warcraft warcraft-wiki api "CreateFrame"
warcraft warcraft-wiki event "OnKeyDown"
warcraft wowprogress guild us illidan Liquid
warcraft wowprogress leaderboard pve us --limit 10
warcraft simc doctor
warcraft simc version
warcraft simc spec-files mistweaver
warcraft simc apl-lists /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc
warcraft simc apl-intent /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
warcraft simc analysis-packet /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
warcraft simc first-cast /home/auro/code/simc/profiles/MID1/MID1_Monk_Windwalker.simc tiger_palm --seeds 1 --max-time 20
```

## Wrapper Conventions

- Use `warcraft` when the provider is unclear.
- Use `warcraft resolve` for a conservative next-command recommendation across providers.
- Use `warcraft search` when you want to inspect candidates across providers.
- Use `warcraft <provider> ...` when you already know which service you need.
- Use `warcraft --expansion <profile>` when the game version matters and you do not want silent cross-version mixing.
- `method` is now a real guide provider with sitemap-backed search, resolve, export, and local query.
- `icy-veins` is now a real guide provider with sitemap-backed search, resolve, export, and local query.
- `raiderio` is now a real phase-1 API provider for direct character, guild, and Mythic+ runs lookups.
- `raiderio` now includes real search and conservative resolve on top of the live site search surface.
- `warcraft-wiki` is now a real reference provider with MediaWiki-backed search, resolve, typed `api` / `event` lookups, article export, and local query.
- `wowprogress` is now a real phase-1 rankings provider with structured search, conservative resolve, and direct guild, character, and PvE leaderboard lookups.
- `simc` is now a real phase-1 local-tool provider for local repo inspection, build decoding, and binary execution.
- `simc` now also includes its first readonly analysis commands for APL list inspection, graphing, talent gates, and action tracing.
- `simc` now includes an early phase-3 slice for conservative prune, branch-trace, and intent analysis.
- `simc` now includes comparison, packet, first-cast, and log-actions commands built on the same conservative reasoning layer.
- `simc` search and resolve currently return structured `coming_soon` payloads in phase 1.
- the flattened `warcraft search` result list is globally sorted by a tunable wrapper ranking layer that combines provider score, query intent, provider family, and result kind
- flattened wrapper results now include `wrapper_ranking` so agents can inspect why a provider/result surfaced first
- `warcraft resolve` uses the same wrapper ranking layer on top of provider confidence instead of trusting provider registration order
- use `--compact` on `warcraft search` or `warcraft resolve` when you want the wrapper decision without the full per-provider payloads
- use `--ranking-debug` when you want compact ranking summaries for the top wrapper candidates
- use `--expansion-debug` when you want a compact per-provider expansion eligibility snapshot
- wrapper ranking policy can be overridden with `~/.config/warcraft/wrapper_ranking.json`
- the wrapper may synthesize a direct provider route when a provider has a strong direct command but no native search surface for that query family, such as `wowprogress leaderboard pve ...`
- wrapper expansion filtering is conservative:
  - `wowhead` is currently the only profiled expansion-aware provider
  - `method`, `icy-veins`, `raiderio`, and `wowprogress` are currently treated as retail-only when wrapper expansion filtering is active
  - `warcraft-wiki` and `simc` are currently excluded from wrapper expansion-filtered `search` and `resolve`
  - wrapper `search`, `resolve`, and `doctor` now report included and excluded providers when expansion filtering is active
  - `--expansion-debug` exposes the full provider eligibility snapshot even in compact mode
  - direct passthrough commands reject unsupported provider/expansion combinations instead of silently ignoring the expansion request

`warcraft doctor` reports:
- wrapper health
- shared XDG-style config/data/cache roots
- registered provider readiness
- provider expansion-support mode and active expansion eligibility when `--expansion` is set

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
- the currently supported Method surface is supported guide/article content under `/guides/<slug>` and `/guides/<slug>/<section>`
- currently validated supported families include class guides, profession guides, delve guides, reputation guides, and article guides
- `guide` returns the requested page summary with navigation and linked-entity preview
- `guide-full` walks the guide navigation and returns all discovered guide pages
- `guide-export` writes a local guide bundle under `./method_exports/` by default
- `guide-query` searches exported Method bundles across sections, navigation links, and linked entities
- unsupported Method query families such as `tier list` return a `scope_hint` and no search candidates
- unsupported Method URLs such as premium or account pages return structured `invalid_guide_ref` errors
- unsupported index-style roots such as `tier-list` return structured `unsupported_guide_surface` errors

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
- `search` and `resolve` work against the Icy Veins WoW sitemap for supported guide families
- broad class and role queries now prefer the corresponding class hub or role guide, while specialized queries like easy mode or leveling penalize those broad hubs
- supported families now include:
  - class hubs
  - role guides
  - spec guides
  - easy mode pages
  - leveling guides
  - PvP guides
  - spec subpages such as builds, rotation, stat priority, gems, gear, spell summary, resources, Mythic+ tips, macros/addons, and simulations
  - raid guides
  - expansion guides
  - special-event guides such as Remix and Torghast pages
- `guide` returns the requested page summary with family metadata, page TOC, and linked-entity preview
- `guide-full` is family-aware:
  - class hubs and role guides stay on the current page
  - spec-family pages walk the related family navigation only
- unsupported or bad WoW refs fail with a structured `invalid_guide_ref`
- unsupported Icy Veins query families such as `patch notes` or `latest class changes` now return a `scope_hint` and no search candidates
- representative real-page fixtures now cover supported and intentionally unsupported Icy Veins WoW page shapes
- PvP and stat-priority pages are now part of the validated supported family set
- resources, macros/addons, Mythic+ tips, and simulations are now also part of the validated supported family set
- leveling, builds/talents, rotation, gems/enchants/consumables, and spell-summary pages are now also part of the validated supported family set
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
- `search` returns ranked character and guild matches with follow-up commands
- structured queries like `guild us illidan Liquid` or `character us illidan Roguecane` now probe the direct profile surfaces before falling back to the weaker site search route
- `resolve` picks a next command conservatively and falls back to `search` when the match set is ambiguous
- `character` returns a compact profile summary with guild, Mythic+, and raid progression context
- `guild` returns a compact guild profile with raid progression, raid rankings, and roster preview
- `mythic-plus-runs` returns ranked Mythic+ run summaries from the documented API endpoint

## Warcraft Wiki Commands

```bash
warcraft-wiki doctor
warcraft-wiki search "world of warcraft api"
warcraft-wiki resolve "world of warcraft api"
warcraft-wiki article "World of Warcraft API"
warcraft-wiki article-full "World of Warcraft API"
warcraft-wiki api "CreateFrame"
warcraft-wiki api-full "XML schema"
warcraft-wiki event "OnKeyDown"
warcraft-wiki event-full "Events"
warcraft-wiki article-export "World of Warcraft API" --out ./tmp/wiki-api
warcraft-wiki article-query ./tmp/wiki-api "framexml"
```

Warcraft Wiki behavior:
- `search` and `resolve` use the MediaWiki search API
- `search` and `resolve` now apply family-aware ranking for programming pages like `API_CreateFrame`, `UIHANDLER_OnKeyDown`, and framework/system reference pages like `World of Warcraft API`, `Expansion`, and `Renown`
- `search` and `resolve` now also clean out low-value leading family hint terms like `faction`, `lore`, `guide`, `zone`, `profession`, `class`, and `expansion` when there is a stronger article target underneath, and report the cleanup in `excluded_terms`
- `api` and `api-full` are the preferred typed programming surfaces for API functions, framework pages, XML schema pages, console-variable reference pages, and API-change pages
- `event` and `event-full` are the preferred typed programming surfaces for UI handler pages and event/framework pages
- `article` returns a compact article summary with section navigation, linked wiki-article preview, and extracted `reference` metadata
- `article-full` returns the parsed article payload used for local export, including top-level and per-page `reference` metadata
- `article-export` writes a local article bundle under `./warcraft-wiki_exports/` by default
- `article-query` searches exported wiki bundles across sections, navigation links, and linked entities
- programming pages now strip low-value wiki chrome more aggressively and filter edit-action links from linked-entity output
- `reference` metadata is now useful beyond API pages: programming howtos, API-change pages, class pages, profession pages, faction pages, zone pages, expansion pages, systems pages, guide pages, and lore pages all expose at least a family-aware summary, and some pages also expose `patch_changes`, `see_also`, and `references`
- redirect-backed article lookups now follow MediaWiki redirects, so short refs like `Legion` resolve to canonical pages like `World of Warcraft: Legion`

## WowProgress Commands

```bash
wowprogress doctor
wowprogress search "guild us illidan Liquid"
wowprogress resolve "character us illidan Imonthegcd"
wowprogress guild us illidan Liquid
wowprogress character us illidan Imonthegcd
wowprogress leaderboard pve us --limit 10
wowprogress leaderboard pve us --realm illidan --limit 10
```

WowProgress phase-1 behavior:
- `doctor` reports cache config and the browser-fingerprint HTTP transport used for live fetches
- `search` expects structured queries like `us illidan Liquid`, `guild us illidan Liquid`, or `character us illidan Imonthegcd`
- `search` normalizes some realm forms like `area 52` -> `area-52` and returns `normalized_candidates` so the cleaned structured targets stay visible
- `search` can exclude unsupported trailing terms like `recruit` and reports them in `excluded_terms` with a `normalization_hint`
- `resolve` uses the same structured query shape and only returns a next command when the route probe is unambiguous
- direct route resolution handles canonical WowProgress realm formatting, so queries like `guild us area-52 xD` still resolve correctly even when the site returns `US-Area 52`
- `guild` returns a compact guild profile with progression, item-level rank context, and encounter history
- `character` returns a compact character profile with item-level, SimDPS, and PvE raid-history context
- `leaderboard pve` returns the current PvE progression leaderboard for a region, optionally narrowed to a realm
- WowProgress search is intentionally structured instead of broad free text because the site-native search surface is heavily constrained and less reliable than direct route resolution

## SimulationCraft Commands

```bash
simc doctor
simc repo
simc repo --set-root /home/auro/code/simc
simc checkout
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
simc apl-prune /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
simc apl-branch-trace /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
simc apl-intent /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
simc apl-intent-explain /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
simc apl-branch-compare /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --left-targets 3 --right-targets 1
simc analysis-packet /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
simc first-cast /home/auro/code/simc/profiles/MID1/MID1_Monk_Windwalker.simc tiger_palm --seeds 1 --max-time 20
simc log-actions /tmp/simc-cli-example/seed_1.log tiger_palm rising_sun_kick
simc run ./profile.simc --arg iterations=1 --arg desired_targets=1
simc sync
simc build
```

SimulationCraft behavior:
- `doctor` reports repo path, git status, binary presence, phase capability state, and repo-resolution source
- `repo` shows the active repo-resolution path and can persist or clear an explicit repo root
- `checkout` performs an optional CLI-managed checkout or update under the XDG data root
- `version` probes the local `simc` binary and extracts the printed SimulationCraft version line
- `inspect` returns either repo state or file-level inspection data, including inferred actor/spec and extracted build lines for `.simc` files
- `spec-files` searches the local checkout across APL files and, when queried, matching class modules and spell dumps
- `decode-build` uses the local `simc` binary to decode talent strings into enabled talents and tree-grouped talent rows
- `apl-lists` returns parsed action lists and their entries from a local `.simc` file
- `apl-graph` emits a Mermaid action-list call graph from a local `.simc` file
- `apl-talents` returns talent gate references and a compact action frequency summary for a local `.simc` file
- `find-action` searches local APLs, class modules, and spell dumps for an action token
- `trace-action` combines local APL hits with broader repo search hits for one action token
- `apl-prune` classifies APL lines conservatively as `eligible`, `dead`, or `unknown` using decoded talents plus target count
- `apl-branch-trace` traces likely `run_action_list` and `call_action_list` flow through one APL
- `apl-intent` summarizes the early likely priorities in the selected focus list after branch evaluation
- `apl-intent-explain` groups the early likely priorities into setup, helper, burst, and remaining priority buckets
- `apl-branch-compare` compares branch and focus-list changes between two target/build contexts
- `analysis-packet` emits an agent-facing summary with branch certainty, intent lines, explained intent, escalation reasons, recommended next steps, and optional first-cast timing samples
- `first-cast` runs short one-iteration sims and records the first observed execution time for a named action across one or more seeds
- `log-actions` inspects an existing SimC combat log and extracts the first scheduled and performed timestamps for named actions
- `run` executes the local `simc` binary against a profile and returns bounded stdout/stderr previews
- `sync` and `build` are conservative local repo helpers; `sync` skips dirty worktrees unless `--allow-dirty` is set
- `search` and `resolve` exist for wrapper-contract stability, but return structured `coming_soon` payloads until SimC discovery is implemented
- repo resolution supports both explicit path configuration and a CLI-managed checkout fallback

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
