# wowhead-cli

Agent-first CLI for querying Wowhead endpoints without browser automation.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Usage

```bash
wowhead search "defias"
wowhead --expansion wotlk search "thunderfury"
wowhead guide 3143
wowhead --pretty search "defias"
wowhead --fields query,count,results search "defias"
wowhead entity item 19019
wowhead entity item 19019 --no-include-comments
wowhead entity item 19019 --include-all-comments
wowhead --compact entity item 19019
wowhead --expansion classic entity item 19019
wowhead --expansion ptr --normalize-canonical-to-expansion entity-page item 19019
wowhead entity-page item 19019 --max-links 100
wowhead comments item 19019 --limit 30 --sort rating
wowhead compare item:19019 item:19351 --comment-sample 2
wowhead expansions
```

Default output is compact JSON for machine consumption. Use `--pretty` for human-readable JSON.
Use global `--expansion` to target a version profile; default is `retail`.
Use `guide` to resolve Wowhead guide IDs/URLs and retrieve metadata plus sampled comments.
Use `entity` to include comments in the same lookup, skip them with `--no-include-comments`, or return full comment sets with `--include-all-comments`; check `all_comments_included` in output for completeness.
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
