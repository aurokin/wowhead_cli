# Warcraft Wiki CLI

## Status

`warcraft-wiki` is now implemented as a working family-aware reference CLI across both programming and non-programming Warcraft Wiki surfaces.

Current command surface:
- `warcraft-wiki doctor`
- `warcraft-wiki search`
- `warcraft-wiki resolve`
- `warcraft-wiki article`
- `warcraft-wiki article-full`
- `warcraft-wiki api`
- `warcraft-wiki api-full`
- `warcraft-wiki event`
- `warcraft-wiki event-full`
- `warcraft-wiki article-export`
- `warcraft-wiki article-query`

Current quality notes:
- search and article retrieval work for broad wiki pages
- programming pages like `API_CreateFrame` and `UIHANDLER_OnKeyDown` now rank and resolve as first-class programming surfaces
- typed programming surfaces now exist for high-signal lookups:
  - `api` / `api-full`
  - `event` / `event-full`
- programming extraction now strips the worst wiki chrome and filters edit-action links from linked entities
- non-programming wiki coverage now includes explicit classification for key system/reference families like `Expansion`, `Profession`, `Renown`, `Zone_scaling`, and class pages
- `article` and `article-full` now expose extracted `reference` metadata so programming and system pages are easier for agents to traverse
- family-hint query cleanup now helps lore/faction/guide phrasing resolve to the underlying article instead of ranking the generic family word too highly
- zone-hint query cleanup now helps pages like `Elwynn Forest` resolve cleanly instead of letting the family word pollute search
- validated live/reference coverage now includes:
  - API functions
  - UI handlers
  - API changes pages
  - programming howto pages
  - systems pages
  - expansion pages
  - class pages
  - profession pages
  - faction pages
  - lore pages
  - zone pages
  - guide-style pages

## Why Add It

`warcraft-wiki` fills a gap that guide and ranking sites do not: broad reference material, lore, systems documentation, addon/API documentation, patch-history context, and general gameplay reference.

It is especially attractive for programming-oriented agent workflows because Warcraft Wiki has dedicated API and UI documentation that other planned services do not cover well.

It is also important for non-programming workflows because it covers:
- expansion overviews
- systems like renown, housing, zone scaling, and Timewalking
- classes, races, professions, factions, and zones
- patches and historical change context
- general lore and world reference

## Research Summary

Observed from live pages:
- direct HTML fetch works without browser automation
- the site is MediaWiki-based and exposes stable page URLs
- World of Warcraft systems, classes, professions, lore, and addon/API documentation are all first-class content areas
- the wiki explicitly includes API and interface customization documentation
- the wiki also includes deep non-programming reference pages that are useful for gameplay, historical, and design-context queries

Programming/reference observations:
- API function pages exist under stable titles like `API_CreateFrame`
- UI/event/framework documentation exists under stable titles like `Widget_API`, `Widget_script_handlers`, `UIHANDLER_OnKeyDown`, and `XML_schema`
- how-to and interface customization documentation exists under stable guide-style titles
- API change pages exist under patch-scoped titles

Non-programming observations:
- expansion overviews exist and are current enough to be useful reference anchors
- classes, professions, renown, zone scaling, housing, and other major systems have dedicated pages
- guide-like wiki pages exist for classes, groups, dungeons, and learning flows
- patch pages and historical expansion pages provide useful change/history context

Sample observations from the main page, API help area, and non-programming pages:
- the main page exposes broad Warcraft and World of Warcraft navigation
- the wiki is broad enough to act as a general-purpose reference source, not just a narrow guide site
- API documentation and editing guidance are available under stable wiki paths
- pages like `Expansion`, `Profession`, `Renown`, `Zone_scaling`, and `Housing` confirm that the wiki is also a high-value systems reference source

## Access Model

This is now treated as a reference/documentation service backed by the MediaWiki API:
- use the built-in search API for article discovery
- fetch parsed article HTML and section metadata via the MediaWiki parse API
- support local article export/query for repeated lookups
- classify article families locally so search, resolve, and extraction can behave differently for:
  - programming reference pages
  - systems/gameplay pages
  - lore/reference pages
  - guide/howto pages

## Current CLI Shape

- `warcraft-wiki doctor`
- `warcraft-wiki search "<query>"`
- `warcraft-wiki resolve "<query>"`
- `warcraft-wiki article <title-or-url>`
- `warcraft-wiki article-full <title-or-url>`
- `warcraft-wiki api <query>`
- `warcraft-wiki api-full <query>`
- `warcraft-wiki event <query>`
- `warcraft-wiki event-full <query>`
- `warcraft-wiki article-export <title-or-url>`
- `warcraft-wiki article-query <bundle> "<query>"`

## Target Support Scope

The goal is for `warcraft-wiki` to become a fully intentional reference CLI across both programming and non-programming families.

### Programming Families

- `api_function`
- `ui_handler`
- `framework_page`
- `xml_schema`
- `cvar`
- `api_changes`
- `howto_programming`

### Non-Programming Families

- `system_reference`
  - examples: `Renown`, `Zone_scaling`, `Housing`
- `expansion_reference`
  - examples: `Expansion`, `World_of_Warcraft:_Legion`
- `class_reference`
  - examples: class overview and class-hall style pages
- `profession_reference`
  - examples: `Profession`
- `faction_reference`
- `zone_reference`
- `patch_reference`
- `lore_reference`
- `guide_reference`
  - wiki-native guides and how-to pages that are not programming-specific

The important point is that these families do not all need different commands immediately, but they do need:
- explicit classification
- explicit ranking behavior
- explicit extraction behavior
- explicit tests

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
- programming-specific section extraction
- non-programming family classification

## What It Has Validated

- the shared article bundle layer works for reference material, not just class guides
- the shared article discovery/follow-up layer can support `article` surfaces in addition to `guide` surfaces

## Current Gaps

Remaining quality notes:
- programming page extraction is still heuristic rather than template-aware
- typed metadata is strongest for straightforward API/function pages and framework pages may still vary more page-to-page than function references
- non-programming family support is now broad and validated, but Warcraft Wiki remains heterogeneous enough that future family additions should stay test-first

## Completion Plan

### Phase 1: Family Classification

Add local page-family classification for both:
- programming families
- non-programming families

This is the foundation for trustworthy ranking, resolution, extraction, and docs.

### Phase 2: Programming Reference Pass

Priorities:
- programming-aware search and resolve
- cleaner extraction for API/event/framework pages
- typed programming metadata
- filtered linked entities for programming pages

Expected outcomes:
- `resolve "CreateFrame"` should confidently choose `API CreateFrame`
- `resolve "OnKeyDown"` should confidently choose a `UIHANDLER_*` page when appropriate
- programming article output should be usable without dragging in large amounts of site chrome

### Phase 3: Non-Programming Reference Pass

Priorities:
- classify and validate major non-programming families
- improve ranking for systems, expansion, patch, profession, and lore queries
- decide which generic wiki guides/howtos are first-class supported surfaces
- make unsupported or weakly supported families explicit where needed

Expected outcomes:
- system queries like `renown`, `zone scaling`, or `housing` should rank strongly and cleanly
- expansion queries should resolve to expansion reference pages rather than incidental matches
- patch/history queries should resolve to patch/reference pages instead of generic articles

### Phase 4: Family-Aware Tests

Add live and recorded coverage for:

Programming:
- `API_CreateFrame`
- `UIHANDLER_OnKeyDown`
- `Widget_API`
- `XML_schema`
- one `API_changes` page
- one programming howto page

Non-programming:
- `Expansion`
- `Profession`
- `Renown`
- `Zone_scaling`
- `Housing`
- one class/reference page
- one patch/reference page

### Phase 5: Extraction And Query Polish

After the support families are explicit:
- improve article export/query for programming pages
- improve article export/query for systems/reference pages
- review whether any wiki-family metadata belongs in shared article code

## Risks

- wiki pages are much more heterogeneous than guide pages
- some useful structured data may live in templates or cargo metadata rather than the main body
- the best query unit may vary between lore pages, system pages, and API pages
- some pages mix content families, so classification rules need to be conservative and test-backed
- programming pages and non-programming reference pages may need different extraction cleanups even when they share the same MediaWiki source format

## Documentation Rule

This document should be kept explicit about:
- what programming surfaces are intentionally supported
- what non-programming families are intentionally supported
- what is still generic article support rather than family-aware support

The goal is to make `warcraft-wiki` trustworthy, not just broad.

## Source Links

- `https://warcraft.wiki.gg/wiki/Main_Page`
- `https://warcraft.wiki.gg/wiki/Warcraft_Wiki:API`
- `https://warcraft.wiki.gg/wiki/API_CreateFrame`
- `https://warcraft.wiki.gg/wiki/Widget_script_handlers`
- `https://warcraft.wiki.gg/wiki/Widget_API`
- `https://warcraft.wiki.gg/wiki/XML_schema`
- `https://warcraft.wiki.gg/wiki/User_interface_customization_guide`
- `https://warcraft.wiki.gg/wiki/UI_FAQ/AddOn_Author_Resources`
- `https://warcraft.wiki.gg/wiki/Guides`
- `https://warcraft.wiki.gg/wiki/Expansion`
- `https://warcraft.wiki.gg/wiki/Profession`
- `https://warcraft.wiki.gg/wiki/Renown`
- `https://warcraft.wiki.gg/wiki/Zone_scaling`
- `https://warcraft.wiki.gg/wiki/Housing`
- `https://warcraft.wiki.gg/wiki/Patch_2.2.0`
- [Roadmap](../ROADMAP.md)
