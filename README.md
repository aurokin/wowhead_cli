# warcraft

Warcraft data CLI monorepo.

## Principles

- These CLIs exist to give agents a comprehensive World of Warcraft toolset across guides, reference content, rankings, logs, and local simulation workflows.
- The product goal is to make complex WoW questions easier for agents by returning accurate, structured, well-formatted data with clear provenance.
- When a workflow is not supported, the CLIs should fail clearly instead of pretending to answer it.
- Prefer trustworthy building blocks that agents can compose:
  - normalization
  - sampling
  - aggregation
  - provenance
  - freshness
- Normalization is an additive analysis layer. It should improve routing and comparison without replacing raw source detail.
- Do not bolt on fake universal "smart answers" where the underlying source contract is narrower than the question.

Current state:
- `warcraft` as the root wrapper
- `wowhead` as the working provider CLI
- `method` as a working guide provider
- `icy-veins` as a working guide provider
- `raiderio` as a working phase-1 API provider
- `warcraft-wiki` as a working reference/article provider
- `wowprogress` as a working phase-1 rankings/profile provider
- `warcraftlogs` as a working phase-1 official log provider
- `simc` as a working phase-1 local SimulationCraft provider
  - phase-2 readonly analysis commands are now in place
  - phase-3 reasoning and runtime helpers are now in place

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
# setup/update editable install and link ~/.local/bin/{warcraft,wowhead,method,icy-veins,raiderio,warcraft-wiki,wowprogress,warcraftlogs,simc}
make dev-deploy
warcraft doctor
warcraft search "defias"
warcraft search "mistweaver monk guide"
warcraft resolve "https://www.warcraftlogs.com/reports/abcd1234#fight=3"
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
warcraft guide-compare ./tmp/method-mistweaver ./tmp/icy-mistweaver
warcraft guide-compare-query "mistweaver monk guide"
warcraft wowhead guide 3143
warcraft method search "mistweaver monk"
warcraft icy-veins search "mistweaver monk guide"
warcraft raiderio character us illidan Roguecane
warcraft raiderio search "Roguecane"
warcraft warcraft-wiki article "World of Warcraft API"
warcraft wowprogress search "guild us illidan Liquid"
warcraft wowprogress guild us illidan Liquid
warcraft warcraftlogs resolve "https://www.warcraftlogs.com/reports/abcd1234#fight=3"
warcraft simc doctor
method guide mistweaver-monk
icy-veins guide mistweaver-monk-pve-healing-guide
raiderio guild us illidan Liquid
warcraft-wiki search "world of warcraft api"
wowprogress leaderboard pve us --limit 10
warcraftlogs report-encounter abcd1234 --fight-id 3
simc version
simc repo
simc spec-files mistweaver
simc apl-lists /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc
simc apl-intent /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
simc analysis-packet /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
simc first-cast /home/auro/code/simc/profiles/MID1/MID1_Monk_Windwalker.simc tiger_palm --seeds 1 --max-time 20
method guide-export mistweaver-monk --out ./tmp/method-mistweaver
wowhead search "defias"
wowhead guide 3143
```

Use `warcraft` when the source is unclear. Use `wowhead`, `method`, `icy-veins`, `raiderio`, `warcraft-wiki`, `wowprogress`, `warcraftlogs`, or `simc` directly once you know the provider you need.

## Docs

Detailed usage lives in [docs/USAGE.md](/home/auro/code/warcraft_cli/docs/USAGE.md).

Other useful docs:
- [docs/ROADMAP.md](/home/auro/code/warcraft_cli/docs/ROADMAP.md)
- [docs/IDENTITY_CONTRACT.md](/home/auro/code/warcraft_cli/docs/IDENTITY_CONTRACT.md)
- [docs/MIGRATION_CHECKLIST.md](/home/auro/code/warcraft_cli/docs/MIGRATION_CHECKLIST.md)
- [docs/WOWHEAD_ACCESS_METHODS.md](/home/auro/code/warcraft_cli/docs/WOWHEAD_ACCESS_METHODS.md)
- [docs/WOWHEAD_EXPANSION_RESEARCH.md](/home/auro/code/warcraft_cli/docs/WOWHEAD_EXPANSION_RESEARCH.md)
- [docs/WRAPPER_PROVIDER_CONTRACT.md](/home/auro/code/warcraft_cli/docs/WRAPPER_PROVIDER_CONTRACT.md)

The preferred pattern is to keep docs driven by actual code behavior. The README should stay short, while command details and behavior notes live under `docs/`.
See [docs/ROADMAP.md](/home/auro/code/warcraft_cli/docs/ROADMAP.md) for the longer agent-product principles and representative workflow examples.

## Testing

```bash
# fast local suite (fixture + unit tests)
pytest -q

# live contract checks against real Wowhead endpoints
WOWHEAD_LIVE_TESTS=1 pytest -q -m live
```

Live checks can be run manually in GitHub Actions via `.github/workflows/live-wowhead-contracts.yml` (`workflow_dispatch`).
Live coverage includes mixed entity-type (`item`, `quest`, `npc`, `spell`) contracts and cross-entity compare checks.
