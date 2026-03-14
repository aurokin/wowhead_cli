---
name: wowhead
description: Use the local `wowhead` CLI for structured WoW lookups on Wowhead. Best for entities, guides, comments, timelines, and stable tool-state inspection when the caller already wants the Wowhead source.
---

# Wowhead

Use `wowhead` when the caller already wants the Wowhead source or when the `warcraft` wrapper has already routed you here.

## Start Here

- Unknown object:
  - `wowhead search "<query>"`
- Conservative next step:
  - `wowhead resolve "<query>"`
- Known entity:
  - `wowhead entity <type> <id>`
- Known guide:
  - `wowhead guide <id-or-url>`
- Timeline scan:
  - `wowhead news ...`
  - `wowhead blue-tracker ...`
- Specific article/topic:
  - `wowhead news-post <url-or-path>`
  - `wowhead blue-topic <url-or-path>`

## Main Surfaces

| Surface | Best for | First commands |
| --- | --- | --- |
| entities | item, quest, spell, npc, faction, tooltip lookups | `wowhead search ...`, `wowhead entity ...`, `wowhead entity-page ...` |
| guides | direct guides and guide-family discovery | `wowhead guide ...`, `wowhead guides ...` |
| comments | fuller thread retrieval | `wowhead comments ...` |
| timelines | news and blue-tracker history | `wowhead news ...`, `wowhead blue-tracker ...` |
| tool-state | calculator or share-link inspection | `wowhead talent-calc ...`, `wowhead profession-tree ...`, `wowhead dressing-room ...`, `wowhead profiler ...` |
| local bundles | exported guide bundles and local querying | `wowhead guide-export ...`, `wowhead guide-query ...`, `wowhead guide-bundle-list` |

## Usage Rules

- Use `wowhead`, not `wowhead-cli`, in commands and examples.
- Put global flags before the subcommand.
- Prefer `entity` first, then `entity-page` only when you need fuller linked-entity context.
- Use `comments` when you need more than the default embedded comment slice.
- Use `guides <category>` when the guide family is known but the exact guide is not.
- Use `news-post` and `blue-topic` when you already have a specific URL from a timeline result.
- Treat `dressing-room` and `profiler` as state inspectors, not full decoders.

## Read Next

- entities and comments: see [references/entities-and-comments.md](/home/auro/code/wowhead_cli/skills/wowhead/references/entities-and-comments.md)
- guides and bundles: see [references/guides-and-bundles.md](/home/auro/code/wowhead_cli/skills/wowhead/references/guides-and-bundles.md)
- timelines: see [references/timelines.md](/home/auro/code/wowhead_cli/skills/wowhead/references/timelines.md)
- tool-state commands: see [references/tools.md](/home/auro/code/wowhead_cli/skills/wowhead/references/tools.md)

## Notes

- This skill is consumer-facing.
- Keep roadmap, packaging, and internal architecture details out of this skill.
