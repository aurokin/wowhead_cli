# wowhead-cli

Agent-first CLI for querying Wowhead endpoints without browser automation.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# optional: install Redis cache support
pip install -e '.[dev,redis]'
```

## Local Dev Deploy

```bash
# setup/update editable install and link ~/.local/bin/wowhead
make dev-deploy
wowhead search "defias"

# optional: update venv only (no ~/.local/bin changes)
make dev-deploy-no-link
```

This project uses editable install mode (`pip install -e`), so code changes are immediately reflected without rebuilding.
If `wowhead` is not found, add `~/.local/bin` to your `PATH`.

## Usage

```bash
wowhead search "defias"
wowhead --expansion wotlk search "thunderfury"
wowhead guide 3143
wowhead guide-full 3143
wowhead guide-export 3143 --out ./tmp/frost-dk-guide
wowhead guide-export 3143 --out ./tmp/frost-dk-guide --hydrate-linked-entities --hydrate-type spell,item --hydrate-limit 100
wowhead guide-bundle-list
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

Default output is compact JSON for machine consumption. Use `--pretty` for human-readable JSON.
Successful responses omit `ok`; structured failures return `ok: false` with an `error` object.
Use global `--expansion` to target a version profile; default is `retail`.
Use `guide` to resolve Wowhead guide IDs/URLs and retrieve metadata plus sampled comments.
Use `guide-full` to retrieve the full embedded guide payload in one response, including body markup, nav links, linked entities, gatherer entities, author data, and all parsed comments.
Use `guide-export` to materialize that payload as local assets (`guide.json`, `page.html`, JSONL slices, and `manifest.json`) for repeated agent exploration.
Use `--hydrate-linked-entities` to also write bounded local entity payloads under `entities/<type>/<id>.json` plus `entities/manifest.json`. Hydration reuses the normalized `entity` contract and defaults to `spell,item,npc` when enabled; use `--hydrate-type` and `--hydrate-limit` to narrow it.
Use `guide-bundle-list` to discover exported bundles under `./wowhead_exports/` or another root.
Use `guide-query` to search a previously exported guide bundle locally across section content, navigation links, entities, and comments. It accepts either a direct bundle path or a selector such as guide ID under `--root`. Use `--kind` to narrow categories, `--section-title` to scope section searches, and `--linked-source href|gatherer|multi` to filter merged linked-entity matches by provenance. The flattened `top` list now prefers the merged linked-entity row over duplicate raw gatherer rows when both match the same entity.
Regular `entity`, `guide`, and `comments` responses now include a lightweight `linked_entities` preview with basic records plus a `fetch_more_command` hint; the regular `entity` preview is trimmed to `type`, `id`, `name`, and `url`, and also includes `counts_by_type` so agents can decide quickly whether to escalate. Guide previews expose the merged deduped guide relation set and include `source_counts` so agents can see how href and gatherer sources contributed. Lightweight previews now suppress low-signal names and prefer more actionable relation types before item-heavy noise. Use `--linked-entity-preview-limit 0` on `entity` or `comments` if you want to skip that preview.
Gatherer-derived linked entities now use the linked entity page itself as both `url` and `citation_url`, while still preserving the source page under `source_url`.
Rich linked-entity rows now preserve normalized multi-source attribution under `sources` and `source_kind`, so merged href/gatherer records carry deterministic provenance without changing the lightweight preview shape.
Lightweight previews now also use that merged provenance as a ranking signal, so multi-source relations win tie-breaks over similar single-source rows.
Guide responses use `guide.page_url` as the canonical guide page source; use `citations.comments` for the guide comment thread instead of a duplicate `guide.comments_url` field.
Use `entity` to include comments in the same lookup, skip them with `--no-include-comments`, or return full comment sets with `--include-all-comments`; entity responses expose the primary name at `entity.name`, the canonical page at `entity.page_url`, and normalized tooltip fields at `tooltip.summary`, `tooltip.text`, and `tooltip.html`. `entity-page`, `comments`, and embedded compare entity summaries now use the same `entity.page_url` field instead of older `entity.url` / `entity.comments_url` duplicates. When comments are included, `citations.comments` provides the comment thread source URL. Use `comments.needs_raw_fetch` to decide if raw comments fetching is still needed.
Page-metadata tooltip fallbacks such as `faction` and `pet` now expose `tooltip.summary` as well, not just `tooltip.text`.
For noisier item- and mount-style tooltips, `tooltip.summary` now prefers effect/use text such as `Chance on hit:` or `Use:` over boilerplate item metadata, while `tooltip.text` still preserves the cleaned full text.
That cleaned `tooltip.text` now also normalizes item-style money amounts like `Sell Price: 4g 2s 63c`, removes long quoted flavor-text lines, and fixes noisy spacing such as `(90)` or `+4 Parry`.
Spell-style `tooltip.summary` now also prefers the descriptive effect clause over cast metadata when both are present, so summaries lead with what the spell actually does instead of `Talent`, `Range`, or `Requires` boilerplate.
`compare` now keeps page/comment URLs only on each entity record and removes duplicated top-level citation arrays; generated overlap/unique linked-entity rows expose a single canonical `url` instead of repeating it under `citation_url`.
Some advertised entity types are resolved through type-specific routing under the hood: `faction` and `pet` use page-metadata tooltip fallbacks, `recipe` resolves through spell pages, `mount` resolves through underlying item pages, and `battle-pet` resolves through underlying NPC pages.
Use `--normalize-canonical-to-expansion` if you want canonical page URLs forced into the selected expansion path.
Use `--compact` to truncate long string fields (for example, tooltip HTML blobs).
Use `--fields` to project only selected dot-paths from the JSON payload.
Transport caching is now configurable through env vars. Useful defaults:

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

Optional Redis support uses namespaced keys so it can share an existing Redis safely:

```bash
WOWHEAD_CACHE_BACKEND=redis
WOWHEAD_REDIS_URL=redis://host:6379/3
WOWHEAD_REDIS_PREFIX=wowhead_cli
```

The cache now has two active layers:

- transport cache for raw tooltip/page/search/comment responses
- normalized `entity` response cache for repeated `entity` lookups with the same flags

See `ROADMAP.md` for deferred multi-expansion/subdomain support planning.
See `WOWHEAD_EXPANSION_RESEARCH.md` for routing/dataEnv findings used by the profile model.

## Testing

```bash
# fast local suite (fixture + unit tests)
pytest -q

# live contract checks against real Wowhead endpoints
WOWHEAD_LIVE_TESTS=1 pytest -q -m live
```

Live checks can be run manually in GitHub Actions via `.github/workflows/live-wowhead-contracts.yml` (`workflow_dispatch`).
Live coverage includes mixed entity-type (`item`, `quest`, `npc`, `spell`) contracts and cross-entity compare checks.
