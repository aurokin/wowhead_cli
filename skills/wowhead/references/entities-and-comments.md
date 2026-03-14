# Entities And Comments

## Best For

- items, quests, spells, npcs, factions, mounts, pets, recipes
- tooltip text
- comment completeness checks

## Start With

- discovery: `wowhead search "<query>"`
- conservative match: `wowhead resolve "<query>"`
- main fetch: `wowhead entity <type> <id>`
- fuller page context: `wowhead entity-page <type> <id>`
- full comment thread: `wowhead comments <type> <id>`

## Effective Use

- prefer `entity.name` and `entity.page_url` over older tooltip-derived naming
- prefer `tooltip.summary` for quick scanning
- escalate to `entity-page` when linked-entity context matters
- check `comments.needs_raw_fetch` before calling `comments`
- use `--no-include-comments` for faster lookups when comments are irrelevant

## Special Cases

- `recipe` resolves through spell pages
- `mount` resolves through underlying item pages
- `battle-pet` resolves through underlying NPC pages
- `faction` and `pet` use page-metadata tooltip fallbacks
