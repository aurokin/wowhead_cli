# SimulationCraft CLI Plan

## Status

`simc` phase 1 is implemented.

Current commands:
- `simc doctor`
- `simc version`
- `simc inspect`
- `simc spec-files`
- `simc decode-build`
- `simc sync`
- `simc build`
- `simc run`
- `simc search` and `simc resolve` as structured `coming_soon` stubs for wrapper stability

The design for later phases is still informed by the existing exploration work in `/home/auro/code/simc_exp`.

That matters because `simc_exp` already proves a substantial second-layer command family on top of a local SimulationCraft checkout:
- repo and binary health checks
- build-input decoding
- APL parsing and graphing
- branch and priority analysis
- short-run sim timing helpers
- combat-log inspection
- agent-facing analysis packets

## Why SimC Is Structurally Important

`simc` is not just another web integration. It is a local-tool and local-repository integration, and the monorepo should be designed with that in mind.

If the shared abstractions only work for HTTP services, the structure is too narrow.

## Research Summary

Observed from the official repository and README:
- SimulationCraft is a local simulator written in C++
- the command-line binary is `simc`
- the graphical interface is explicitly described as largely unmaintained
- the project expects local builds on Linux rather than packaged Linux releases
- parameter-file and command-line driven execution are first-class workflows

Observed from the existing `simc_exp` tool:
- a readonly local checkout is enough for a lot of useful analysis work
- many high-value questions do not require mutating the repo or running a full sim immediately
- APL structure, build decoding, and search/trace workflows are agent-useful on their own
- short local sims are still useful as an escalation path for timing and runtime validation

## Access Model

This should be a local-tool service:
- readonly local repo inspection
- optional local repo sync
- local build management
- local binary execution
- profile, log, and analysis helpers

The important planning change is that `simc` should not be thought of as only:
- sync repo
- build binary
- run sim

It should also support a readonly analysis mode against a local SimulationCraft source tree.

## Recommended Phase Shape

### Phase 1: Local Tool Foundation

Implemented:

- `simc doctor`
- `simc sync`
- `simc build`
- `simc version`
- `simc run <profile-or-file>`
- `simc inspect <profile-or-result>`
- `simc spec-files`
- `simc decode-build`

This is the minimal operational layer.

### Phase 2: Readonly Source Analysis

This is where `simc_exp` is directly relevant next.

- `simc apl-lists`
- `simc apl-graph`
- `simc apl-talents`
- `simc find-action`
- `simc trace-action`

These commands should work against a local checkout without requiring a full sim run.

### Phase 3: Runtime-Aware Reasoning

- `simc apl-prune`
- `simc apl-branch-trace`
- `simc apl-intent`
- `simc apl-intent-explain`
- `simc apl-branch-compare`
- `simc analysis-packet`
- `simc first-cast`
- `simc log-actions`

This is the agent-analysis layer proven by `simc_exp`.

## What Can Reuse Shared Code

- output shaping
- local cache/state directories
- bundle/report indexing if result storage becomes useful
- wrapper routing from `warcraft`
- shared environment/config path handling

## What This Service Should Validate

`simc` is the test for whether the monorepo abstractions work for local tools as well as network services.

If a shared layer assumes HTTP everywhere, it is the wrong layer.

It should also validate that the repo can support:
- readonly source-tree analysis
- optional escalation into binary-backed execution
- agent-facing reasoning packets that are not tied to HTTP responses or article pages

## What Should Stay SimC-Specific

- local source-tree parsing and APL reasoning
- git sync policy
- build orchestration
- binary invocation
- result/report parsing
- environment validation
- talent/build decoding logic that depends on the local SimC binary

## What To Adopt From `simc_exp`

Strong candidates to migrate into `simc`:
- build-input normalization and decode helpers
- repo discovery and validation
- APL parsing, graphing, and talent-reference extraction
- action search and trace helpers
- branch/prune analysis
- analysis-packet generation
- short-run `first-cast` timing helpers
- combat-log action summaries

What should not be copied blindly:
- hardcoded repo paths
- the exact command names if the service-wide CLI surface needs to be simplified
- assumptions that every analysis path must exist in phase 1

## First Useful Slice

1. `doctor` against a local readonly checkout
2. `version` and binary detection
3. `spec-files` and `decode-build`
4. one controlled `run` path

That would give agents immediate value without requiring the full advanced analysis surface on day one.

## Risks

- local build requirements will vary by platform
- this integration needs strong environment diagnostics
- result parsing should not be over-generalized too early
- readonly source analysis can sprawl if we do not keep phase boundaries clear
- the analysis layer should not assume one spec or one APL family

## Why `simc_exp` Matters

`simc_exp` is effectively a design probe for the higher-level `simc` CLI.

It shows that a readonly local SimulationCraft source tree can support:
- structural APL understanding
- build decoding
- branch reasoning
- runtime escalation when needed

That is a strong use case for the monorepo because it is a different kind of provider than every site-backed CLI in this repo.

## Source Links

- `https://github.com/simulationcraft/simc`
- `/home/auro/code/simc_exp`
- [SimulationCraft migration inventory](/home/auro/code/wowhead_cli/docs/SIMC_MIGRATION_INVENTORY.md)
- [SimulationCraft implementation plan](/home/auro/code/wowhead_cli/docs/SIMC_IMPLEMENTATION_PLAN.md)
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
