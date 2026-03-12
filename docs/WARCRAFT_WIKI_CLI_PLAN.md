# Warcraft Wiki CLI Plan

## Status

`warcraft-wiki` is now implemented as a working provider.

Current command surface:
- `warcraft-wiki doctor`
- `warcraft-wiki search`
- `warcraft-wiki resolve`
- `warcraft-wiki article`
- `warcraft-wiki article-full`
- `warcraft-wiki article-export`
- `warcraft-wiki article-query`

## Why Add It

`warcraft-wiki` fills a gap that guide and ranking sites do not: broad reference material, lore, systems documentation, and addon/API documentation.

It is especially attractive for programming-oriented agent workflows because Warcraft Wiki has dedicated API and UI documentation that other planned services do not cover well.

## Research Summary

Observed from live pages:
- direct HTML fetch works without browser automation
- the site is MediaWiki-based and exposes stable page URLs
- World of Warcraft systems, classes, professions, lore, and addon/API documentation are all first-class content areas
- the wiki explicitly includes API and interface customization documentation

Sample observations from `https://warcraft.wiki.gg/wiki/Main_Page` and the API help area:
- the main page exposes broad Warcraft and World of Warcraft navigation
- the wiki is broad enough to act as a general-purpose reference source, not just a narrow guide site
- API documentation and editing guidance are available under stable wiki paths

## Access Model

This is now treated as a reference/documentation service backed by the MediaWiki API:
- use the built-in search API for article discovery
- fetch parsed article HTML and section metadata via the MediaWiki parse API
- support local article export/query for repeated lookups

## Likely CLI Shape

- `warcraft-wiki doctor`
- `warcraft-wiki search "<query>"`
- `warcraft-wiki resolve "<query>"`
- `warcraft-wiki article <title-or-url>`
- `warcraft-wiki article-full <title-or-url>`
- `warcraft-wiki article-export <title-or-url>`
- `warcraft-wiki article-query <bundle> "<query>"`

## What Can Reuse Shared Code

- article bundle export/load/query
- cache and HTTP infrastructure
- shared output shaping
- search and resolve payload contracts
- article follow-up and linked-entity merge helpers

## What Should Stay Service-Specific

- MediaWiki page parsing and title normalization
- category/template handling
- reference and infobox extraction
- wiki-specific search ranking

## What It Has Validated

- the shared article bundle layer works for reference material, not just class guides
- the shared article discovery/follow-up layer can support `article` surfaces in addition to `guide` surfaces

## What This Service Still Leaves Open

- whether documentation-oriented follow-up guidance should diverge further from guide-oriented follow-up guidance
- whether any MediaWiki-specific extraction belongs in shared code

## Risks

- wiki pages are much more heterogeneous than guide pages
- some useful structured data may live in templates or cargo metadata rather than the main body
- the best query unit may vary between lore pages, system pages, and API pages

## Source Links

- `https://warcraft.wiki.gg/wiki/Main_Page`
- `https://warcraft.wiki.gg/wiki/Warcraft_Wiki:API`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
