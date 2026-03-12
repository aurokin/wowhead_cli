# SimulationCraft Implementation Plan

## Purpose

This document is the file-level implementation plan for the `simc` provider.

It is the bridge between:
- the high-level [SimulationCraft CLI plan](/home/auro/code/wowhead_cli/docs/SIMC_CLI_PLAN.md)
- the module inventory in [SIMC_MIGRATION_INVENTORY.md](/home/auro/code/wowhead_cli/docs/SIMC_MIGRATION_INVENTORY.md)
- actual code creation under `packages/simc-cli/`

This is intentionally more concrete than the roadmap.

Current status:
- phase 1 package and command surface are implemented
- phase 2 readonly analysis commands are implemented
- most of phase 3 is implemented
- the remaining purpose of this document is to guide the runtime-helper tail of phase 3 work

## Package Shape

Created in phase 1:
- `packages/simc-cli/pyproject.toml`
- `packages/simc-cli/src/simc_cli/__init__.py`
- `packages/simc-cli/src/simc_cli/main.py`

Created provider-local modules:
- `packages/simc-cli/src/simc_cli/repo.py`
- `packages/simc-cli/src/simc_cli/build_input.py`
- `packages/simc-cli/src/simc_cli/search.py`
- `packages/simc-cli/src/simc_cli/run.py`

Phase-2 modules:
- `packages/simc-cli/src/simc_cli/apl.py`

Phase-3 modules:
- `packages/simc-cli/src/simc_cli/prune.py`
- `packages/simc-cli/src/simc_cli/branch.py`
- `packages/simc-cli/src/simc_cli/packet.py`
- `packages/simc-cli/src/simc_cli/logs.py`

## Dependency Direction

Allowed dependencies:
- `simc-cli` -> `warcraft-core`
- `simc-cli` -> `warcraft-content` only if local result/index storage later proves useful

Not needed initially:
- `warcraft-api`

Reason:
- `simc` is not an HTTP-backed provider
- forcing `warcraft-api` into it would create the wrong dependency shape

## Phase 1 Scope

Shipped in phase 1:
- `simc doctor`
- `simc version`
- `simc sync`
- `simc build`
- `simc run`
- `simc inspect`
- `simc spec-files`
- `simc decode-build`

Wrapper integration:
- `warcraft simc ...`
- `warcraft doctor` should report `simc` readiness
- `warcraft search` / `resolve` can return structured `coming_soon` for `simc` in phase 1

## Phase 1 Module Mapping

### `repo.py`

Primary source:
- `/home/auro/code/simc_exp/simc_exp/repo.py`

Responsibilities:
- discover local SimulationCraft checkout
- resolve important repo paths
- validate required directories
- validate binary presence

Needed changes:
- replace hardcoded defaults with XDG-aware config or explicit CLI options
- support readonly repo usage first
- separate repo validation from build validation

### `build_input.py`

Primary source:
- `/home/auro/code/simc_exp/simc_exp/build_input.py`

Phase-1 responsibilities:
- infer actor/spec from APL path when useful
- normalize raw build inputs
- decode builds through local `simc` binary

Needed changes:
- remove assumptions tied to `simc_exp` temp naming
- cleanly separate:
  - raw build spec extraction
  - binary-backed decode
  - command-facing payload shaping

### `search.py`

Primary source:
- `/home/auro/code/simc_exp/simc_exp/search.py`

Phase-1 responsibilities:
- `spec-files`

Keep in phase 1:
- repo-local file discovery
- rg-based text search helpers needed for `spec-files`

Move `find-action` / `trace-action` behavior later unless phase 1 stays small enough to absorb them safely.

### `run.py`

Primary source:
- selected logic from `/home/auro/code/simc_exp/simc_exp/sim.py`

Phase-1 responsibilities:
- `version`
- `run`
- basic `inspect`

Needed changes:
- split one-off first-cast logic from generic binary execution
- make output capture explicit and structured
- keep temporary-output handling safe and predictable

### `main.py`

New Typer CLI surface.

Do not port:
- old argparse code from `/home/auro/code/simc_exp/simc_exp/cli.py`

Do:
- rebuild the command surface in the current monorepo style
- use shared output helpers
- keep error payloads aligned with the rest of the repo

## Readonly Analysis Status

Implemented on top of the phase-1 base:
- `apl.py`
- readonly `find-action` / `trace-action`
- `apl-lists`
- `apl-graph`
- `apl-talents`

Primary source modules:
- `/home/auro/code/simc_exp/simc_exp/apl.py`
- `/home/auro/code/simc_exp/simc_exp/search.py`

Implemented package layout change:
- added `apl.py`
- expanded `search.py`

## Phase 3 Scope

Ship after the base provider is trusted:
- `simc first-cast`
- `simc log-actions`

Primary source modules:
- `/home/auro/code/simc_exp/simc_exp/prune.py`
- `/home/auro/code/simc_exp/simc_exp/branch.py`
- `/home/auro/code/simc_exp/simc_exp/packet.py`
- `/home/auro/code/simc_exp/simc_exp/sim.py`

Suggested package layout change:
- add `prune.py`
- add `branch.py`
- add `packet.py`
- split log parsing into `logs.py` if it improves clarity

## Command Surface Strategy

Keep the surface conservative at first.

Phase 1:
- prioritize repo health and one reliable run path
- add readonly file discovery and build decoding

Phase 2:
- add source analysis that does not require simulation

Phase 3:
- add structural reasoning and runtime escalation

Do not front-load every `simc_exp` command into the first provider milestone.

## Test Plan

### Phase 1 tests

Created in phase 1:
- `tests/test_simc_repo.py`
- `tests/test_simc_build_input.py`
- `tests/test_simc_cli.py`

Port or adapt from:
- `/home/auro/code/simc_exp/tests/test_build_input.py`

Add provider-specific coverage for:
- missing repo
- missing binary
- build decode with mocked subprocess
- `doctor`
- `version`
- `spec-files`

### Phase 2 tests

Create:
- `tests/test_simc_apl.py`
- `tests/test_simc_search.py`

Port or adapt from:
- relevant logic currently covered indirectly in `simc_exp`

### Phase 3 tests

Create:
- `tests/test_simc_prune.py`
- `tests/test_simc_branch.py`
- `tests/test_simc_packet.py`
- `tests/test_simc_runtime.py`

Port or adapt from:
- `/home/auro/code/simc_exp/tests/test_prune.py`
- `/home/auro/code/simc_exp/tests/test_packet.py`
- `/home/auro/code/simc_exp/tests/test_simc_integration.py`

## Live Or Local Verification Expectations

Because `simc` is local-tool backed, verification is different from site-backed providers.

Expected verification gates:
- fast unit tests always
- local integration checks only when a SimulationCraft checkout and binary exist
- explicit smoke commands documented in `docs/USAGE.md` once implemented

## Recommended First Implementation Order

1. package skeleton
2. `repo.py`
3. `doctor`
4. `version`
5. `build_input.py`
6. `decode-build`
7. `search.py` for `spec-files`
8. `run.py` for controlled `run`
9. wrapper registration
10. docs and skill updates

This order gives us a usable provider without prematurely porting the deepest analysis logic.

## Rules

- Port logic modules before command glue.
- Keep readonly analysis first-class.
- Do not make `simc` depend on HTTP-oriented shared packages unless a real need appears.
- Keep `simc`-specific reasoning inside `simc-cli`.
- Update this doc if the file layout or phase boundaries change.
