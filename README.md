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

## Supported Providers

- [`warcraft`](docs/warcraft/README.md): root wrapper and orchestration CLI
- [`wowhead`](docs/wowhead/README.md): entity, guide, comments, and bundle workflows
- [`method`](docs/method/README.md): guide extraction and local guide workflows
- [`icy-veins`](docs/icy-veins/README.md): guide extraction and local guide workflows
- [`raiderio`](docs/raiderio/README.md): API-backed profile and leaderboard workflows
- [`warcraft-wiki`](docs/warcraft-wiki/README.md): reference, lore, and API/article workflows
- [`wowprogress`](docs/wowprogress/README.md): rankings and profile workflows
- [`warcraftlogs`](docs/warcraftlogs/README.md): official log/report workflows
- [`simc`](docs/simc/README.md): local SimulationCraft inspection and analysis workflows

## Quick Start

```bash
warcraft doctor
warcraft search "defias"
warcraft guide-compare-query "mistweaver monk guide"
warcraft warcraftlogs resolve "https://www.warcraftlogs.com/reports/abcd1234#fight=3"
warcraftlogs report-encounter abcd1234 --fight-id 3
simc analysis-packet /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
```

Use `warcraft` when the source is unclear. Use `wowhead`, `method`, `icy-veins`, `raiderio`, `warcraft-wiki`, `wowprogress`, `warcraftlogs`, or `simc` directly once you know the provider you need.

## Docs

- [docs/README.md](/home/auro/code/warcraft_cli/docs/README.md)
- [docs/USAGE.md](/home/auro/code/warcraft_cli/docs/USAGE.md)
- [docs/ROADMAP.md](/home/auro/code/warcraft_cli/docs/ROADMAP.md)
- [docs/foundation/PRODUCT_PRINCIPLES.md](/home/auro/code/warcraft_cli/docs/foundation/PRODUCT_PRINCIPLES.md)
- [docs/foundation/SAFE_ANALYTICS_RULES.md](/home/auro/code/warcraft_cli/docs/foundation/SAFE_ANALYTICS_RULES.md)

## Testing

```bash
# fast local suite (fixture + unit tests)
pytest -q

# live contract checks against real Wowhead endpoints
WOWHEAD_LIVE_TESTS=1 pytest -q -m live
```

Live checks can be run manually in GitHub Actions via `.github/workflows/live-wowhead-contracts.yml` (`workflow_dispatch`).
Live coverage includes mixed entity-type (`item`, `quest`, `npc`, `spell`) contracts and cross-entity compare checks.
