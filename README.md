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
wowhead resolve "fairbreeze favors"

# optional: update venv only (no ~/.local/bin changes)
make dev-deploy-no-link
```

This project uses editable install mode (`pip install -e`), so code changes are immediately reflected without rebuilding.
If `wowhead` is not found, add `~/.local/bin` to your `PATH`.

## Quick Start

```bash
wowhead search "defias"
wowhead guide 3143
wowhead guide-export 3143 --out ./tmp/frost-dk-guide
wowhead guide-bundle-list
wowhead guide-bundle-search "frost"
wowhead guide-bundle-query "obliterate"
wowhead guide-bundle-inspect 3143
wowhead guide-bundle-index-rebuild
wowhead cache-inspect
wowhead cache-clear --namespace entity_response --expired-only
wowhead entity item 19019
wowhead comments item 19019 --limit 30 --sort rating
wowhead compare item:19019 item:19351 --comment-sample 2
```

The CLI defaults to compact JSON for machine use. Use `--pretty` for readable output and `--fields` when you only want selected paths from the response. Use `search` when you want to inspect multiple candidates, and `resolve` when you want the CLI to recommend one next command conservatively.

## Docs

Detailed usage lives in [docs/USAGE.md](/home/auro/code/wowhead_cli/docs/USAGE.md).

Other useful docs:
- [docs/ROADMAP.md](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
- [docs/WOWHEAD_ACCESS_METHODS.md](/home/auro/code/wowhead_cli/docs/WOWHEAD_ACCESS_METHODS.md)
- [docs/WOWHEAD_EXPANSION_RESEARCH.md](/home/auro/code/wowhead_cli/docs/WOWHEAD_EXPANSION_RESEARCH.md)

The preferred pattern is to keep docs driven by actual code behavior. The README should stay short, while command details and behavior notes live under `docs/`.

## Testing

```bash
# fast local suite (fixture + unit tests)
pytest -q

# live contract checks against real Wowhead endpoints
WOWHEAD_LIVE_TESTS=1 pytest -q -m live
```

Live checks can be run manually in GitHub Actions via `.github/workflows/live-wowhead-contracts.yml` (`workflow_dispatch`).
Live coverage includes mixed entity-type (`item`, `quest`, `npc`, `spell`) contracts and cross-entity compare checks.
