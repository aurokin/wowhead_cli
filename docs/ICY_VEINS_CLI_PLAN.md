# Icy Veins CLI Plan

## Status

`icy-veins` is now implemented as a working provider on top of the shared article bundle layer.

Current command surface:
- `icy-veins doctor`
- `icy-veins search`
- `icy-veins resolve`
- `icy-veins guide`
- `icy-veins guide-full`
- `icy-veins guide-export`
- `icy-veins guide-query`

## Why It Matters

`icy-veins` is another article-first source and should be the next validation point after `method` if the shared article abstractions hold up.

## Research Summary

Observed from live guide pages:
- direct HTML fetch works on sampled WoW guide pages
- the pages include `application/ld+json`
- a `page_type: 'guides'` marker appears in the page source
- visible last-updated and author metadata are present
- the page exposes a table of contents for guide navigation
- guide-family navigation is page-to-page rather than purely section-anchor-based
- the main page also exposes an in-page table of contents anchored to headings

Sample observations from `https://www.icy-veins.com/wow/healing-guide`:
- title is visible in HTML
- `Last updated` metadata is server-rendered
- `Table of Contents` is visible in the page body

## Access Model

This should also be treated as an article-first service:
- fetch guide HTML
- extract metadata and navigation
- capture section content
- export local guide bundles when repeated querying is useful

## Likely CLI Shape

- `icy-veins search "<query>"`
- `icy-veins guide <slug-or-url>`
- `icy-veins guide-full <slug-or-url>`
- `icy-veins guide-export <slug-or-url>`
- `icy-veins guide-query <bundle> "<query>"`

## What Can Reuse Shared Code

- article bundle layout
- local query/index helpers
- cache and output infrastructure
- search and resolve interfaces

Validated against the current shared layer:
- the shared article bundle export/load/query contract in [warcraft_content.article_bundle](/home/auro/code/wowhead_cli/packages/warcraft-content/src/warcraft_content/article_bundle.py) fits Icy Veins page groups cleanly
- provider-specific parsing is still required before those helpers can be used

## What This Service Should Validate

`icy-veins` is the check on whether the article abstractions proven by `method` are actually reusable:

- article metadata contracts
- section models
- navigation models
- bundle export/query behavior

Current conclusion from live validation:
- bundle export/query behavior is reusable
- parsing and normalization are not yet shared and should stay local to the future `icy-veins` package

## What Should Stay Service-Specific

- parsing rules
- guide-family discovery
- ranking heuristics for articles and specs

## What It Has Validated

- the shared article bundle export/load/query contract is reusable across a second article-first provider
- provider-specific parsing and navigation extraction should still stay local

## Risks

- guide layouts may differ more between summary pages and spec pages than on Method
- Icy Veins navigation structure may need more normalization than Method
- discovery may need a site-specific strategy because the page exposes multiple related guide families, not just one clean slug graph

## Source Links

- `https://www.icy-veins.com/wow/healing-guide`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
