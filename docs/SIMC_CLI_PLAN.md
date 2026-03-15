# SimulationCraft CLI Plan

## Status

`simc` phase 1 is implemented.

Current commands:
- `simc doctor`
- `simc repo`
- `simc checkout`
- `simc version`
- `simc sim`
- `simc inspect`
- `simc spec-files`
- `simc decode-build`
- `simc build-harness`
- `simc validate-apl`
- `simc compare-apls`
- `simc variant-report`
- `simc verify-clean`
- `simc apl-lists`
- `simc apl-graph`
- `simc apl-talents`
- `simc find-action`
- `simc trace-action`
- `simc apl-prune`
- `simc apl-branch-trace`
- `simc apl-intent`
- `simc apl-intent-explain`
- `simc priority`
- `simc inactive-actions`
- `simc opener`
- `simc apl-branch-compare`
- `simc analysis-packet`
- `simc first-cast`
- `simc log-actions`
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
- optional managed local checkout/update for users who want the CLI to own the repo lifecycle
- local build management
- local binary execution
- profile, log, and analysis helpers
- local comparison workflows for guide-derived or user-derived APL variants without touching upstream

The important planning change is that `simc` should not be thought of as only:
- sync repo
- build binary
- run sim

It should also support a readonly analysis mode against a local SimulationCraft source tree.

Longer term, the repo strategy should support both:
- explicit repo-path/config driven usage
- an optional CLI-managed checkout and update workflow

## Recommended Phase Shape

### Phase 1: Local Tool Foundation

Implemented:

- `simc doctor`
- `simc sync`
- `simc build`
- `simc version`
- `simc sim`
- `simc run <profile-or-file>`
- `simc inspect <profile-or-result>`
- `simc spec-files`
- `simc decode-build`

This is the minimal operational layer.

Recent usability improvement:
- `simc sim` is now the preferred consumer run path
- it uses explicit fixed presets instead of leaving iteration counts implicit
- it always returns:
  - run settings
  - runtime timing
  - core metrics
- default presets:
  - `quick` -> `1000` iterations
  - `high-accuracy` -> `5000` iterations
- `decode-build` now distinguishes between:
  - bare WoW talent export strings
  - SimC-native build/profile text
  and reports both `source_kind` and the normalized generated SimC profile used for decode/debug flows

### Phase 2: Readonly Source Analysis

The first readonly-analysis slice is now implemented.

- `simc apl-lists`
- `simc apl-graph`
- `simc apl-talents`
- `simc find-action`
- `simc trace-action`

These commands should work against a local checkout without requiring a full sim run.

### Phase 3: Runtime-Aware Reasoning

Phase 3 is now implemented:
- `simc apl-prune`
- `simc apl-branch-trace`
- `simc apl-intent`
- `simc apl-intent-explain`
- `simc priority`
- `simc inactive-actions`
- `simc opener`
- `simc apl-branch-compare`
- `simc analysis-packet`
- `simc first-cast`
- `simc log-actions`

This is the agent-analysis layer proven by `simc_exp`.

### Comparison Workflow

The next important `simc` layer is now implemented as a local comparison workflow:
- `simc build-harness`
- `simc validate-apl`
- `simc compare-apls`
- `simc variant-report`
- `simc verify-clean`

This is the correct answer to conversations where the user wants to draft guide-shaped APL variants, compare them objectively, and keep the upstream SimulationCraft repo untouched.

Consumer guidance boundary:
- default to `1000` iterations for most consumer-facing work
- only suggest `5000+` when the user explicitly wants higher accuracy
- thread recommendations should not be hard-coded in consumer guidance
- if thread tuning matters, the CLI or agent should inspect the current machine before recommending a value

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

## Analysis Boundary

The `simc` analysis layer should stay grounded in observable local evidence.

That means:
- `analysis-packet` and intent helpers can summarize structure, branches, and runtime samples
- exact-build views like `priority`, `inactive-actions`, and `opener` should strip inactive talent branches instead of summarizing from shared APL text blindly
- they can recommend next commands or follow-up investigations
- they should not drift into authoritative "smart answers" that go beyond what the local source tree or runtime sample actually proves

This is an important boundary for agent trust:
- analysis metadata is good
- evidence-backed recommendations are good
- unsupported synthesis is not

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

Agent-experience boundary:
- exact-build workflows should make the input handoff explicit
- a user may paste either a WoW talent export or SimC-native build text
- the CLI should identify which one it received before downstream APL reasoning begins
- decode failures should carry enough metadata to debug the generated profile quickly

That is a strong use case for the monorepo because it is a different kind of provider than every site-backed CLI in this repo.

## Source Links

- `https://github.com/simulationcraft/simc`
- `/home/auro/code/simc_exp`
- [SimulationCraft migration inventory](/home/auro/code/wowhead_cli/docs/SIMC_MIGRATION_INVENTORY.md)
- [SimulationCraft implementation plan](/home/auro/code/wowhead_cli/docs/SIMC_IMPLEMENTATION_PLAN.md)
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
