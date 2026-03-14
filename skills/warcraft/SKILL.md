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

## Provider Synopsis

| Provider | Best for | First commands |
| --- | --- | --- |
| `wowhead` | entities, guides, comments, timelines, tool-state refs | `warcraft wowhead search ...`, `warcraft wowhead entity ...`, `warcraft wowhead guide ...` |
| `method` | supported article/guide families with simple article structure | `warcraft method search ...`, `warcraft method guide ...` |
| `icy-veins` | spec guides, hubs, and guide subpages | `warcraft icy-veins search ...`, `warcraft icy-veins guide ...` |
| `raiderio` | character/guild profiles, Mythic+, sampled run analytics | `warcraft raiderio character ...`, `warcraft raiderio sample ...` |
| `warcraft-wiki` | API docs, events, systems, lore, reference pages | `warcraft warcraft-wiki api ...`, `warcraft warcraft-wiki article ...` |
| `wowprogress` | progression, rankings, guild/profile analytics | `warcraft guild ...`, `warcraft wowprogress guild ...`, `warcraft wowprogress sample ...` |
| `simc` | local SimulationCraft inspection, exact-build priority analysis, APL comparison, and runs | `warcraft simc doctor`, `warcraft simc priority ...`, `warcraft simc compare-apls ...` |

## Routing Rules

- Prefer `resolve` when you want one conservative next command.
- Prefer `search` when you want to inspect candidates across providers.
- Prefer `warcraft guild ...` when the user wants a guild snapshot and you want normalized input plus explicit source disagreement reporting.
- Preserve provider provenance. `warcraft` is a router, not a source.
- When `--expansion` matters, trust only the providers the wrapper says are included.
- Once the provider is known, switch to the provider CLI or the provider reference below.

## Read Next

- `wowhead`: see [references/wowhead.md](/home/auro/code/wowhead_cli/skills/warcraft/references/wowhead.md)
- `method`: see [references/method.md](/home/auro/code/wowhead_cli/skills/warcraft/references/method.md)
- `icy-veins`: see [references/icy-veins.md](/home/auro/code/wowhead_cli/skills/warcraft/references/icy-veins.md)
- `raiderio`: see [references/raiderio.md](/home/auro/code/wowhead_cli/skills/warcraft/references/raiderio.md)
- `warcraft-wiki`: see [references/warcraft-wiki.md](/home/auro/code/wowhead_cli/skills/warcraft/references/warcraft-wiki.md)
- `wowprogress`: see [references/wowprogress.md](/home/auro/code/wowhead_cli/skills/warcraft/references/wowprogress.md)
- `simc`: see [references/simc.md](/home/auro/code/wowhead_cli/skills/warcraft/references/simc.md)

## Notes

- This skill is the umbrella consumer skill.
- Keep provider details in the reference files so they can become standalone skills later without rewriting the root skill.
