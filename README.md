# warcraft

Warcraft data CLI monorepo.

Milestone 1 includes:
- `warcraft` as the root wrapper
- `wowhead` as the working provider CLI
- `method` as a registered stub provider

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
# setup/update editable install and link ~/.local/bin/{warcraft,wowhead,method}
make dev-deploy
warcraft doctor
warcraft search "defias"
wowhead search "defias"

# optional: update venv only (no ~/.local/bin changes)
make dev-deploy-no-link
```

This project uses editable install mode (`pip install -e`), so code changes are immediately reflected without rebuilding.
If `wowhead` is not found, add `~/.local/bin` to your `PATH`.

## Quick Start

```bash
warcraft doctor
warcraft search "defias"
warcraft resolve "fairbreeze favors"
warcraft wowhead guide 3143
warcraft method search "mistweaver monk"
wowhead search "defias"
wowhead guide 3143
```

Use `warcraft` when the source is unclear. Use `wowhead` directly once you know you need Wowhead behavior. `method` is intentionally stubbed in milestone 1.

## Docs

Detailed usage lives in [docs/USAGE.md](/home/auro/code/wowhead_cli/docs/USAGE.md).

Other useful docs:
- [docs/ROADMAP.md](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
- [docs/MIGRATION_CHECKLIST.md](/home/auro/code/wowhead_cli/docs/MIGRATION_CHECKLIST.md)
- [docs/WOWHEAD_ACCESS_METHODS.md](/home/auro/code/wowhead_cli/docs/WOWHEAD_ACCESS_METHODS.md)
- [docs/WOWHEAD_EXPANSION_RESEARCH.md](/home/auro/code/wowhead_cli/docs/WOWHEAD_EXPANSION_RESEARCH.md)
- [docs/WRAPPER_PROVIDER_CONTRACT.md](/home/auro/code/wowhead_cli/docs/WRAPPER_PROVIDER_CONTRACT.md)

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
