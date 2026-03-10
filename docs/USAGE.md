# Usage

This document is the command-oriented reference for the local `wowhead` CLI.

The goal is to keep the README short and keep detailed usage notes close to actual CLI behavior.

## Common Commands

```bash
wowhead search "defias"
wowhead --expansion wotlk search "thunderfury"
wowhead guide 3143
wowhead guide-full 3143
wowhead guide-export 3143 --out ./tmp/frost-dk-guide
wowhead guide-export 3143 --out ./tmp/frost-dk-guide --hydrate-linked-entities --hydrate-type spell,item --hydrate-limit 100
wowhead guide-bundle-list
wowhead guide-bundle-list --max-age-hours 72
wowhead guide-bundle-search "frost death knight"
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

## Output Conventions

- Default output is compact JSON for machine consumption.
- Use `--pretty` for human-readable JSON.
- Successful responses omit `ok`.
- Structured failures return `ok: false` with an `error` object.
- Use `--fields` to project only selected dot-paths from the JSON payload.
- Use `--compact` to truncate long string fields such as tooltip HTML blobs.

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

Bundle discovery and refresh:
- `guide-bundle-list` discovers bundles under `./wowhead_exports/` or another root
- `guide-bundle-search` searches indexed bundle metadata across a root
- it includes `freshness` and `hydration` summaries
- `--max-age-hours` changes the freshness threshold used by those summaries
- bundle exports and refreshes maintain a root-level `index.json`
- `guide-bundle-list` and `guide-bundle-search` prefer that index when it is present and valid
- `guide-bundle-refresh` refreshes an existing bundle in place
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

## Related Docs

- [ROADMAP.md](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
- [WOWHEAD_ACCESS_METHODS.md](/home/auro/code/wowhead_cli/docs/WOWHEAD_ACCESS_METHODS.md)
- [WOWHEAD_EXPANSION_RESEARCH.md](/home/auro/code/wowhead_cli/docs/WOWHEAD_EXPANSION_RESEARCH.md)
