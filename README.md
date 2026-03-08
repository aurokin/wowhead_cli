# wowhead-cli

Agent-first CLI for querying Wowhead endpoints without browser automation.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
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
wowhead guide-bundle-list
wowhead guide-query ./tmp/frost-dk-guide "bellamy"
wowhead guide-query 3143 "obliterate" --root ./wowhead_exports
wowhead guide-query ./tmp/frost-dk-guide "welcome" --kind sections --section-title overview
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
wowhead --fields entity.name,entity.page_url,tooltip.text,linked_entities entity quest 86739
wowhead --expansion ptr --normalize-canonical-to-expansion entity-page item 19019
wowhead entity-page item 19019 --max-links 100
wowhead comments item 19019 --limit 30 --sort rating
wowhead compare item:19019 item:19351 --comment-sample 2
wowhead expansions
```

Default output is compact JSON for machine consumption. Use `--pretty` for human-readable JSON.
Use global `--expansion` to target a version profile; default is `retail`.
Use `guide` to resolve Wowhead guide IDs/URLs and retrieve metadata plus sampled comments.
Use `guide-full` to retrieve the full embedded guide payload in one response, including body markup, nav links, linked entities, gatherer entities, author data, and all parsed comments.
Use `guide-export` to materialize that payload as local assets (`guide.json`, `page.html`, JSONL slices, and `manifest.json`) for repeated agent exploration.
Use `guide-bundle-list` to discover exported bundles under `./wowhead_exports/` or another root.
Use `guide-query` to search a previously exported guide bundle locally across section content, navigation links, entities, and comments. It accepts either a direct bundle path or a selector such as guide ID under `--root`. Use `--kind` to narrow categories and `--section-title` to scope section searches.
Regular `entity`, `guide`, and `comments` responses now include a lightweight `linked_entities` preview with basic records plus a `fetch_more_command` hint; the regular `entity` preview is trimmed to `type`, `id`, `name`, and `url`, and also includes `counts_by_type` so agents can decide quickly whether to escalate. Guide previews expose the merged deduped guide relation set and include `source_counts` so agents can see how href and gatherer sources contributed. Use `--linked-entity-preview-limit 0` on `entity` or `comments` if you want to skip that preview.
Use `entity` to include comments in the same lookup, skip them with `--no-include-comments`, or return full comment sets with `--include-all-comments`; entity responses expose the primary name at `entity.name`, the canonical page at `entity.page_url`, and normalized tooltip fields at `tooltip.text` and `tooltip.html`. When comments are included, `citations.comments` provides the comment thread source URL. Use `comments.needs_raw_fetch` to decide if raw comments fetching is still needed.
Some advertised entity types are resolved through type-specific routing under the hood: `faction` and `pet` use page-metadata tooltip fallbacks, `recipe` resolves through spell pages, `mount` resolves through underlying item pages, and `battle-pet` resolves through underlying NPC pages.
Use `--normalize-canonical-to-expansion` if you want canonical page URLs forced into the selected expansion path.
Use `--compact` to truncate long string fields (for example, tooltip HTML blobs).
Use `--fields` to project only selected dot-paths from the JSON payload.

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
