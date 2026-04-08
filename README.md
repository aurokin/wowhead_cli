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
# branch-local editable environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# optional: install Redis cache support
pip install -e '.[dev,redis]'
```

## Stable Host Deploy

```bash
# install a stable machine-wide runtime under ~/.local/share/warcraft
make stable-deploy

# roll back the stable runtime to an earlier immutable release
make stable-rollback RELEASE="20260329010101-abc1234"

warcraft doctor
warcraft search "defias"
```

This writes `~/.local/bin/{warcraft,wowhead,method,icy-veins,raiderio,warcraft-wiki,wowprogress,warcraftlogs,simc}` wrappers that point at the stable `~/.local/share/warcraft/install/current/venv`, and it exports stable skills under `~/.local/share/warcraft/skills/`.
By default the stable deploy stages a versioned release under `~/.local/share/warcraft/install/releases/<release-id>/` and then repoints `~/.local/share/warcraft/install/current/` only after the build succeeds.
Because wrappers and exported skills follow `install/current`, rollback is just a repoint of that symlink. `make stable-rollback` is the preferred path, but manual rollback stays simple if you need it urgently.

## Branch-Local Editable Deploy

```bash
# create a sibling worktree from the reserved master checkout
make worktree-add BRANCH="feature-wrapper-routing"

# setup/update the current checkout as an editable branch-local environment
make dev-deploy-no-link

# optional: regenerate the shell env activation file for this worktree
make worktree-env

# optional: add the worktree venv to PATH in this shell
source .warcraft/worktree-env.sh

# deliberate exception: relink ~/.local/bin to this checkout
WARCRAFT_ALLOW_LINK_BIN=1 make dev-deploy
```

This project uses editable install mode (`pip install -e`) for branch-local development, so code changes are immediately reflected without rebuilding.
Use `make dev-deploy-no-link` for branch worktrees so the host keeps pointing at the stable checkout.
That branch-local setup writes `.warcraft/worktree-env.sh`, keeps credentials in the shared host config/state roots, and isolates branch-local data/cache under `.warcraft/runtime/`.
Use `make worktree-env` whenever you want to regenerate or refresh that shell activation file explicitly.
Only the reserved `master/` checkout should drive `make stable-deploy`, and that checkout should be clean before deploying.
Use the same reserved `master/` checkout for `make stable-rollback` when you need to flip `install/current` back to an older release.
Use `make worktree-add BRANCH="<name>"` from `master/` to create sibling worktrees under `~/code/warcraft_cli/`.
This repo pins that stable branch policy to `master` through the Make targets, while the helper scripts still honor `WARCRAFT_STABLE_BRANCH` for repositories that use a different trunk branch.
If a repository carries both local `master` and `main` branches without a usable `origin/HEAD`, set `WARCRAFT_STABLE_BRANCH` explicitly instead of relying on auto-detection.

## Retiring The Old Repo-Local Deploy

```bash
# after stable-deploy has repointed ~/.local/bin away from this checkout
make retire-dev-deploy
```

That command uninstalls the editable `warcraft` package from the repo-local `.venv` and archives the old `.venv` so the host no longer depends on the checkout path.
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
simc analysis-packet <simc-root>/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
```

Use `warcraft` when the source is unclear. Use `wowhead`, `method`, `icy-veins`, `raiderio`, `warcraft-wiki`, `wowprogress`, `warcraftlogs`, or `simc` directly once you know the provider you need.

## Docs

- [docs/README.md](docs/README.md)
- [docs/USAGE.md](docs/USAGE.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/foundation/PRODUCT_PRINCIPLES.md](docs/foundation/PRODUCT_PRINCIPLES.md)
- [docs/foundation/SAFE_ANALYTICS_RULES.md](docs/foundation/SAFE_ANALYTICS_RULES.md)

## Testing

```bash
# fast local suite (fixture + unit tests)
pytest -q

# live contract checks against real Wowhead endpoints
WOWHEAD_LIVE_TESTS=1 pytest -q -m live
```

Live checks can be run manually in GitHub Actions via `.github/workflows/live-wowhead-contracts.yml` (`workflow_dispatch`).
Live coverage includes mixed entity-type (`item`, `quest`, `npc`, `spell`) contracts and cross-entity compare checks.

## Health Checks

```bash
make fmt-check
make lint
make lint-all
make complexity
make typecheck
make coverage
```

Notes:
- `make lint-all` is report-only and keeps the current full-repo Ruff backlog visible without blocking local work.
- `make complexity` runs `radon` via `python -m` so stale console-script wrappers do not break the report.
- `make coverage` prefers `pytest-cov` when available and falls back to stdlib `trace` coverage for the shared packages when the active Python build lacks `sqlite3`.
