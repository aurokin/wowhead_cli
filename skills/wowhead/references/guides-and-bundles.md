# Guides And Bundles

## Best For

- direct guide lookup
- guide-family discovery
- local guide export and query

## Start With

- direct guide: `wowhead guide <id-or-url>`
- fuller guide: `wowhead guide-full <id-or-url>`
- guide family: `wowhead guides <category> [query]`
- local export: `wowhead guide-export <id-or-url> --out <dir>`
- local query: `wowhead guide-query <dir> "<query>"`

## Effective Use

- use `guides <category>` when the family is known but the guide is not
- use guide filters like:
  - `--author`
  - `--updated-after`
  - `--updated-before`
  - `--patch-min`
  - `--patch-max`
  - `--sort relevance|updated|published|rating`
- use bundle commands for trust and freshness:
  - `guide-bundle-list`
  - `guide-bundle-inspect`
  - `guide-bundle-refresh`
- use `guide-export --hydrate-linked-entities` only when the linked entities matter enough to justify the extra fetches

## Boundaries

- generic database-family browse/filter pages are intentionally deferred
- guide and bundle flows are the preferred structured surfaces today
