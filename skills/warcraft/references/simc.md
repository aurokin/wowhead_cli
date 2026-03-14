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
- source inspection: `simc spec-files ...`, `simc apl-lists ...`, `simc apl-talents ...`
- reasoning: `simc priority ...`, `simc inactive-actions ...`, `simc opener ...`, `simc analysis-packet ...`
- APL comparison: `simc build-harness ...`, `simc validate-apl ...`, `simc compare-apls ...`
- execution: `simc run ...`

## Effective Use

- prefer readonly APL inspection before jumping to a real sim run
- if the user provides a talent string or import string, assume they want the exact build only; use `priority` or `inactive-actions` so inactive talent branches are excluded before you summarize the rotation
- use `apl-prune`, `apl-branch-trace`, and `apl-intent` for conservative flow reasoning
- use `priority` as the default build-scoped priority view
- use `inactive-actions` when you need to prove a shared APL branch is not active for the current build
- use `opener` for a static early-action preview, then escalate to `first-cast` if runtime confirmation matters
- use `analysis-packet` when you want an agent-facing summary instead of assembling outputs manually
- use `first-cast` and `log-actions` when static analysis is not enough and you need runtime confirmation
- if the user wants to compare guide-derived or custom APLs, build a harness and use `compare-apls`; do not edit upstream SimC files
- use `verify-clean` before and after local comparison work when upstream cleanliness matters
- iteration guidance should be purpose-based:
  - quick sanity check: around `1000`
  - compare variants: around `5000-10000`
  - higher-confidence final run: around `20000-30000`
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

## Boundaries

- `simc` is a local-tool provider, not a web-data provider
- current `search` / `resolve` remain limited compared with the other providers
