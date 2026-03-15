# Wowhead

## Best For

- item, quest, spell, npc, faction, and guide lookup
- comments and linked-entity traversal
- Wowhead timelines:
  - `news`
  - `blue-tracker`
- stable tool-state inspection:
  - `talent-calc`
  - `profession-tree`
  - `dressing-room`
  - `profiler`

## Start With

- unknown object: `wowhead search "<query>"`
- conservative next step: `wowhead resolve "<query>"`
- known entity: `wowhead entity <type> <id>`
- known guide: `wowhead guide <id-or-url>`
- timeline scan: `wowhead news ...` or `wowhead blue-tracker ...`

## Effective Use

- prefer `entity` first, then `entity-page` only when you need fuller linked-entity context
- use `comments` when you need more than the default embedded comment slice
- use `guides <category>` when the guide family is known but the exact guide is not
- use `guide-full` or `guide-export` when you need the raw guide body plus additive `analysis_surfaces` for comparison-oriented workflows
- use `guide-query --kind analysis_surfaces` when you want section-backed guide topics without discarding the underlying guide text
- use timeline filters like `--author`, `--type`, `--region`, and `--forum` instead of scanning broad result sets manually
- use guide filters like `--author`, `--updated-after`, `--patch-min`, and `--sort`
- use `news-post` and `blue-topic` once you already have a specific URL

## Boundaries

- database-family browse/filter pages are intentionally deferred
- `dressing-room` and `profiler` are state inspectors, not full decoders
- do not assume Wowhead tool URLs expose enough stable state for deep reverse-engineering
- treat Wowhead `analysis_surfaces` as an additive page-level layer extracted from trusted section structure, not as a replacement for the raw guide page
