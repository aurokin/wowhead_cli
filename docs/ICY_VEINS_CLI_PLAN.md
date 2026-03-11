# Icy Veins CLI Plan

## Why It Matters

`icy-veins` is another article-first source and should be the next validation point after `method` if the shared article abstractions hold up.

## Research Summary

Observed from live guide pages:
- direct HTML fetch works on sampled WoW guide pages
- the pages include `application/ld+json`
- a `page_type: 'guides'` marker appears in the page source
- visible last-updated and author metadata are present
- the page exposes a table of contents for guide navigation

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

## What This Service Should Validate

`icy-veins` is the check on whether the article abstractions proven by `method` are actually reusable:

- article metadata contracts
- section models
- navigation models
- bundle export/query behavior

## What Should Stay Service-Specific

- parsing rules
- guide-family discovery
- ranking heuristics for articles and specs

## First Useful Slice

1. support direct guide fetch by URL or slug
2. extract metadata, table of contents, and sections
3. export/query local bundles

## Risks

- guide layouts may differ more between summary pages and spec pages than on Method
- Icy Veins navigation structure may need more normalization than Method

## Source Links

- `https://www.icy-veins.com/wow/healing-guide`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
