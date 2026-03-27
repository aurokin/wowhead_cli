# SimulationCraft

## Best For

- local repo inspection
- readonly APL analysis
- build decoding
- controlled local sim execution

## Start With

- readiness: `simc doctor`
- repo state: `simc repo`
- managed checkout: `simc checkout`
- upstream safety: `simc verify-clean`
- build identification: `simc identify-build`
- build summary: `simc describe-build`
- source inspection: `simc spec-files ...`, `simc apl-lists ...`, `simc apl-talents ...`
- reasoning: `simc priority ...`, `simc inactive-actions ...`, `simc opener ...`, `simc analysis-packet ...`
- direct sim runs: `simc sim ...`
- APL comparison: `simc build-harness ...`, `simc validate-apl ...`, `simc compare-apls ...`
- talent comparison: `simc compare-builds --base ... --other ...`
- talent modification: `simc modify-build --talents ... --swap-class-tree-from ... --add ... --remove ...`
- low-level execution: `simc run ...`

## Effective Use

- prefer readonly APL inspection before jumping to a real sim run
- if the user provides a talent string, import string, or Wowhead talent-calc URL with build code, assume they want the exact build only; use `describe-build` first for “what is this build doing?” requests, then use `priority` or `inactive-actions` when you need finer evidence
- users may paste:
  - a bare WoW talent export string
  - a Wowhead talent-calc URL with build code
  - SimC-native build/profile text
  `identify-build`, `describe-build`, and `decode-build` report `source_kind`, resolved class/spec, and the normalized generated profile so you can verify the handoff before reasoning from it
- for exact-build commands, `--talents` is now safe for the same common consumer inputs as `--build-text`, including bare WoW exports and Wowhead talent-calc URLs with build codes
- do not tell the user they must provide class/spec unless `identify-build` failed first; the CLI now probes the local SimC spec set for bare WoW exports when direct metadata is missing
- prefer `describe-build` over ad hoc prose synthesis when you need to talk about:
  - active hero/spec package
  - skipped capstones or alternate branches
  - ST vs AoE shape changes
  - dispatcher-to-leaf focus changes exposed through `focus_path`
- use `apl-prune`, `apl-branch-trace`, and `apl-intent` for conservative flow reasoning
- use `priority` as the default build-scoped priority view
- use `inactive-actions` when you need to prove a shared APL branch is not active for the current build
- use `opener` for a static early-action preview, then escalate to `first-cast` if runtime confirmation matters
- use `analysis-packet` when you want an agent-facing summary instead of assembling outputs manually
- use `first-cast` and `log-actions` when static analysis is not enough and you need runtime confirmation
- use `sim` as the default consumer run path:
  - `simc sim ./profile.simc`
  - `cat ./profile.simc | simc sim -`
  - it always reports run settings, runtime, and core output metrics
- use `compare-builds` to diff talent selections between two or more builds by tree; this is the right tool when the user asks "what changed between these two builds?"
- use `modify-build` to produce a new talent export string from an existing build:
  - `--swap-class-tree-from` / `--swap-spec-tree-from` / `--swap-hero-tree-from` replace an entire tree from another build
  - `--add name:rank` and `--remove name` adjust individual talents
  - the output includes the new WoW export string, a Wowhead URL, and a diff from the base build
  - this uses SimC's own encoder, not reverse-engineered client-side encoding
- if the user wants to compare guide-derived or custom APLs, build a harness and use `compare-apls`; do not edit upstream SimC files
- use `verify-clean` before and after local comparison work when upstream cleanliness matters
- use `1000` iterations for most work
- use `5000+` iterations only when the user explicitly wants higher accuracy
- `sim --preset quick` is the default `1000`-iteration path
- `sim --preset high-accuracy` is the default `5000`-iteration path
- do not recommend a fixed thread count blindly; either omit `threads` or inspect the current machine first

## Comparison Workflow

- use `build-harness` to create one shared local profile baseline
- use `validate-apl` to catch syntax or setup issues before longer sim runs
- use `compare-apls` to compare base and variant APLs on the same harness
- use `variant-report` to summarize winners, DPS deltas, and action-count deltas
- use `verify-clean` before and after the comparison if the user cares about upstream cleanliness

This is the default safe path for:

- guide-vs-guide APL comparisons
- custom APL experiments
- any workflow where local variants should stay out of the upstream SimC repo

## Talent Modification Workflow

- use `compare-builds` first to understand the per-tree differences between builds
- use `modify-build` with `--swap-*-tree-from` when the user wants to take an entire tree from another build
- use `modify-build` with `--add` / `--remove` when the user wants to adjust specific talents without a full tree swap
- both paths can be combined: swap a tree and then add/remove on top
- talent encoding goes through the local SimC binary, so `doctor` must report a working binary

## Boundaries

- `simc` is a local-tool provider, not a web-data provider
- current `search` / `resolve` remain limited compared with the other providers
