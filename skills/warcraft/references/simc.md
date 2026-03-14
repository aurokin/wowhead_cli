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
- source inspection: `simc spec-files ...`, `simc apl-lists ...`, `simc apl-talents ...`
- reasoning: `simc apl-intent ...`, `simc analysis-packet ...`
- execution: `simc run ...`

## Effective Use

- prefer readonly APL inspection before jumping to a real sim run
- use `apl-prune`, `apl-branch-trace`, and `apl-intent` for conservative flow reasoning
- use `analysis-packet` when you want an agent-facing summary instead of assembling outputs manually
- use `first-cast` and `log-actions` when static analysis is not enough and you need runtime confirmation

## Boundaries

- `simc` is a local-tool provider, not a web-data provider
- current `search` / `resolve` remain limited compared with the other providers
