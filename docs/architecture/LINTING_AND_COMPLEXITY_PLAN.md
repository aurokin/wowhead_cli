# Linting And Complexity Plan

## Goal

Add static quality checks that help us:
- find refactor opportunities early
- surface complexity hotspots before they become harder to test
- improve confidence in shared-package boundaries
- identify code that should move into shared helpers instead of staying duplicated in provider packages

This work is meant to support maintainability, testing quality, and better code sharing. It is not just style enforcement.

## Current State

The repo currently relies mainly on:
- `pytest`
- live contract tests
- `compileall` in `make fmt-check`

That means we have very little automated signal for:
- complexity
- dead code
- import drift
- type regressions
- repeated patterns that should be extracted

## Recommended Tooling

### Ruff

Use `ruff` as the primary linting tool.

Add:
- core pyflakes / pycodestyle checks
- import sorting
- bugbear
- pyupgrade
- simplification rules
- cyclomatic complexity reporting
- selected refactor-oriented rules

Suggested rule families:
- `F`
- `E`
- `W`
- `I`
- `B`
- `UP`
- `SIM`
- `C90`
- selected `PLR`

Why first:
- fast
- low friction
- immediately useful across the whole repo

Phase-1 rollout note:
- make the default `make lint` gate cover shared packages first
- keep a broader `make lint-all` report for the whole repo backlog
- do not block day-to-day work on the existing full-repo style backlog before the first refactor passes land

### Mypy

Add `mypy`, but roll it out in phases.

Start with:
- `warcraft-core`
- `warcraft-api`
- `warcraft-content`

Then expand to:
- `warcraft-cli`
- provider packages one by one

Why:
- shared packages are the highest-leverage place for type safety
- provider packages can adopt stricter typing gradually

### Radon / Xenon

Add complexity reporting with `radon` or `xenon`.

Use this initially as a reporting gate, not a hard blocker.

Primary uses:
- identify oversized functions
- identify branch-heavy logic
- prioritize refactors that will improve testability

### Vulture

Add `vulture` for dead code detection.

Use it conservatively:
- report first
- review before deleting anything

Why:
- provider iteration often leaves behind dead helpers, stale fallback logic, and unused compatibility paths

### Pytest Coverage

Add `pytest-cov`.

Focus first on:
- shared packages
- analytics helpers
- provider normalization/filtering helpers

Prefer branch coverage in critical shared logic where practical.

Environment note:
- prefer `pytest-cov` when `sqlite3` support is available
- on machines where the active Python build is missing `_sqlite3`, `make coverage` should fall back to a stdlib `trace` summary for the shared packages instead of failing outright

### Import-Linter

Add `import-linter` to protect package boundaries.

Primary contracts to enforce:
- provider packages must not import each other
- shared packages may not depend on provider packages
- wrapper may depend on shared packages and provider CLI interfaces, but providers should stay isolated

This is especially valuable in a monorepo where “just one import” can quietly erode the architecture.

## Expected Refactor Signal

These tools are likely to point at real hotspots, not just style issues.

Examples already visible from a quick scan:
- large Wowhead command handlers and payload builders
- large SimC command handlers
- Raider.IO analytics helpers with multiple branching paths
- WowProgress guild-profile analytics helpers
- Icy Veins family scoring logic

Likely outcomes:
- split oversized command handlers into smaller payload/query helpers
- extract repeated filter/query-normalization utilities
- tighten analytics summary helpers
- remove stale compatibility or fallback branches
- expose new shared utilities where multiple providers repeat the same pattern

## Rollout Order

1. Add `ruff`.
2. Add `radon` / `xenon` in report-only mode.
3. Add `mypy` for shared packages.
4. Add `import-linter` for package boundaries.
5. Add `pytest-cov` for shared packages and analytics helpers.
6. Add `vulture` as a review-oriented report.

## Execution Strategy

### Phase 1

Add tooling and commands only:
- `make lint`
- `make lint-all`
- `make complexity`
- `make typecheck`
- `make coverage`

Do not try to clean the whole repo in the same change.

Practical phase-1 behavior:
- `make lint` should be clean for shared packages
- `make lint-all` can remain an exploratory full-repo report and should not block local work on the existing backlog
- `make complexity` should use module invocation so stale console-script wrappers do not break the report
- `make coverage` should prefer `pytest-cov`, but fall back to stdlib `trace` coverage when `sqlite3` support is unavailable

### Phase 2

Run the tools and create a concrete refactor backlog:
- highest-complexity functions
- duplicated filter/sampling code
- dead code candidates
- import-boundary violations

### Phase 3

Refactor in small slices:
- one provider family at a time
- shared code only when repetition is actually proven
- tests strengthened alongside refactors

## Path And Local Install

For this machine, the efficient way to get all CLIs on `PATH` is already built into the repo.

Use:

```bash
make dev-deploy
```

That script:
- creates `.venv` if needed
- installs `-e '.[dev]'`
- writes wrapper scripts into `~/.local/bin` for:
  - `warcraft`
  - `wowhead`
  - `method`
  - `icy-veins`
  - `raiderio`
  - `warcraft-wiki`
  - `wowprogress`
  - `simc`

If this machine does not already have `~/.local/bin` on `PATH`, add:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

to the shell profile, for example `~/.zshrc`.

This is the preferred local setup because it:
- keeps the repo editable
- avoids manual symlink work
- keeps one consistent install path for all CLIs

## Success Criteria

This plan is successful when:
- linting is fast enough to run regularly
- complexity reports identify clear refactor targets
- shared packages have meaningful type coverage
- package boundaries are enforced automatically
- refactors become easier to justify with tool output
- new shared utilities are extracted based on repeated patterns, not guesses
