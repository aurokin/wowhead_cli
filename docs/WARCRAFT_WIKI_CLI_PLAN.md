# Warcraft Wiki CLI Plan

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

This should be treated as a reference/documentation service:
- fetch article HTML
- extract page metadata, section headings, body content, and related links
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

## What Should Stay Service-Specific

- MediaWiki page parsing and title normalization
- category/template handling
- reference and infobox extraction
- wiki-specific search ranking

## What This Service Should Validate

- whether the shared article bundle layer works for reference material, not just class guides
- whether documentation-oriented follow-up guidance should become distinct from guide-oriented follow-up guidance

## Risks

- wiki pages are much more heterogeneous than guide pages
- some useful structured data may live in templates or cargo metadata rather than the main body
- the best query unit may vary between lore pages, system pages, and API pages

## Source Links

- `https://warcraft.wiki.gg/wiki/Main_Page`
- `https://warcraft.wiki.gg/wiki/Warcraft_Wiki:API`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
