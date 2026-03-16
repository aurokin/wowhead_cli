---
name: warcraft
description: Use the local `warcraft` CLI as the root Warcraft data entrypoint when the source is unclear or the user may need more than one provider. Best for wrapper `search`, `resolve`, `doctor`, expansion-aware routing, and handing off to the right provider CLI.
---

# Warcraft

Use `warcraft` first when the caller does not already know which provider they need.

## Start Here

- Source unclear:
  - `warcraft resolve "<query>"`
  - if unresolved: `warcraft search "<query>"`
- Source known:
  - `warcraft <provider> ...`
- Version-specific request:
  - `warcraft --expansion <profile> ...`
- Trust check:
  - `warcraft doctor`
- Cross-provider guide evidence:
  - `warcraft guide-compare <bundle-a> <bundle-b>`
  - `warcraft guide-compare-query "<guide query>"`
  - `warcraft guide-compare-query "<guide query>" --simc-build-handoff --simc-apl-path <apl>`
  - `warcraft guide-builds-simc <bundle-or-orchestration-root>`
  - `warcraft guide-builds-simc <bundle-or-orchestration-root> --apl-path <apl>`

## Provider Synopsis

| Provider | Best for | First commands |
| --- | --- | --- |
| `wowhead` | entities, guides, comments, timelines, tool-state refs | `warcraft wowhead search ...`, `warcraft wowhead entity ...`, `warcraft wowhead guide ...` |
| `method` | supported article/guide families with simple article structure | `warcraft method search ...`, `warcraft method guide ...` |
| `icy-veins` | spec guides, hubs, and guide subpages | `warcraft icy-veins search ...`, `warcraft icy-veins guide ...` |
| `raiderio` | character/guild profiles, Mythic+, sampled run analytics | `warcraft raiderio character ...`, `warcraft raiderio sample ...` |
| `warcraft-wiki` | API docs, events, systems, lore, reference pages | `warcraft warcraft-wiki api ...`, `warcraft warcraft-wiki article ...` |
| `wowprogress` | progression, rankings, guild/profile analytics | `warcraft guild ...`, `warcraft wowprogress guild ...`, `warcraft wowprogress sample ...` |
| `warcraftlogs` | official raid-log API, world metadata, guild/character/report lookups | `warcraftlogs doctor`, `warcraftlogs guild ...`, `warcraftlogs report-fights ...` |
| `simc` | local SimulationCraft inspection, exact-build priority analysis, APL comparison, and runs | `warcraft simc doctor`, `warcraft simc priority ...`, `warcraft simc compare-apls ...` |

## Routing Rules

- Prefer `resolve` when you want one conservative next command.
- Prefer `search` when you want to inspect candidates across providers.
- Prefer `warcraft guild ...` when the user wants a guild snapshot and you want normalized input plus explicit source disagreement reporting.
- Preserve provider provenance. `warcraft` is a router, not a source.
- Use `warcraft guide-compare` when you already have exported guide bundles and want additive cross-provider evidence instead of a synthesized summary.
- Use `warcraft guide-compare-query` when you want the wrapper to resolve, export, and compare guide candidates conservatively across supported guide providers.
- `guide-compare-query` may use a provider search fallback only when the top guide result is clearly decisive; it should not guess across weak or ambiguous guide candidates.
- `guide-compare-query` should reuse prior orchestrated bundles only through explicit freshness rules like `--max-age-hours` and `--force-refresh`, not through invisible cache-like behavior.
- Add `--simc-build-handoff` when you want the orchestration packet to include explicit guide build refs handed into `simc`; add `--simc-apl-path` when you also want exact-build `describe-build` output.
- Use `warcraft guide-builds-simc` when you want explicit guide build refs handed into `simc` without inferring claims from guide prose.
- Add `--apl-path` when you want the wrapper to include exact-build `simc describe-build` output for those same explicit guide build refs.
- When `--expansion` matters, trust only the providers the wrapper says are included.
- Once the provider is known, switch to the provider CLI or the provider reference below.

## Read Next

- `wowhead`: see `references/wowhead.md`
- `method`: see `references/method.md`
- `icy-veins`: see `references/icy-veins.md`
- `raiderio`: see `references/raiderio.md`
- `warcraft-wiki`: see `references/warcraft-wiki.md`
- `wowprogress`: see `references/wowprogress.md`
- `warcraftlogs`: see `references/warcraftlogs.md`
- `simc`: see `references/simc.md`

## Notes

- This skill is the umbrella consumer skill.
- Keep provider details in the reference files so they can become standalone skills later without rewriting the root skill.
- Keep reference links portable: use relative paths like `references/simc.md`, not machine-specific absolute paths.
