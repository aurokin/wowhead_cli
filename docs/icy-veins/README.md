# Icy Veins CLI

## Goal

Make `icy-veins` a fully functioning, clearly scoped, and well-tested WoW guide/article CLI.

That means:
- explicit family support
- predictable discovery behavior
- family-aware `guide-full` traversal
- strong live and recorded-fixture coverage
- docs that say exactly what is supported and what is not

## Current Status

`icy-veins` is implemented and useful today, but it is not hardened to the same level as `method`.

Current command surface:
- `icy-veins doctor`
- `icy-veins search`
- `icy-veins resolve`
- `icy-veins guide`
- `icy-veins guide-full`
- `icy-veins guide-export`
- `icy-veins guide-query`

Current strengths:
- live WoW guide fetch works
- shared article bundle export/load/query works
- search and resolve work for many common guide queries
- guide-family navigation and page TOC extraction work on many pages
- explicit family metadata is now emitted on supported pages
- supported families are now explicitly defined in the implementation and docs
- class hubs and role guides now have local-only traversal instead of over-expanding in `guide-full`
- broad class and role queries now prefer the corresponding class hub or role guide, while specialized families penalize those broad hubs
- unsupported or bad WoW refs now fail with structured `invalid_guide_ref`
- unsupported query families like patch notes, class changes, hotfixes, and news now return a `scope_hint` instead of misleading guide matches
- dedicated Icy Veins live tests now exist
- recorded real-page fixtures now exist across representative supported and intentionally unsupported WoW page shapes
- PvP and stat-priority families are now explicitly validated by recorded and live coverage
- resources, macros/addons, Mythic+ tips, and simulations are now also explicitly validated by recorded and live coverage
- leveling, builds/talents, rotation, gems/enchants/consumables, and spell-summary pages are now also explicitly validated by recorded and live coverage
- local bundle export/query works

Current weaknesses:
- family-aware ranking is still too generic across some supported families
- recorded-fixture coverage is better now, but still not yet as deep as Method
- family scope is strong across the main supported families, but still needs more depth around rarer edge-case templates

## Research Summary

Icy Veins offers a much broader WoW surface than just spec guide landing pages.

Validated live page families:
- class hub guides
- role guides
- main spec guides
- easy mode pages
- leveling guides
- spec subpages such as builds, rotation, stat priority, gems, gear, spell summary, resources, Mythic+ tips, macros/addons, and simulations
- raid-specific spec guides
- expansion/special-mode guides such as The War Within preview pages, Remix pages, and Torghast pages

Observed from the live WoW sitemap:
- roughly 4,000+ WoW URLs exist under `/wow/`
- the site contains many old and special-purpose pages that still look guide-like
- sitemap filtering must remain WoW-specific and family-aware

Important implementation conclusion:
- the parser model is broad enough to support more than one Icy Veins guide family
- the real work is defining supported families and applying the right traversal/ranking rules for each family

## Target Scope

The CLI should intentionally support these families:

- `class_hub`
  - examples: `monk-guide`, `warrior-guide`
- `role_guide`
  - examples: `healing-guide`
- `spec_guide`
  - examples: `mistweaver-monk-pve-healing-guide`
- `easy_mode`
  - examples: `fury-warrior-pve-dps-easy-mode`
- `leveling`
  - examples: `mistweaver-monk-leveling-guide`
- `pvp`
  - examples: `mistweaver-monk-pvp-guide`
- `spec_subpage`
  - builds/talents
  - rotation/cooldowns
  - stat priority
  - gems/enchants/consumables
  - gear/best in slot
  - spell summary
  - resources
  - Mythic+ tips
  - macros/addons
  - simulations
- `raid_guide`
  - examples: `mistweaver-monk-pve-healing-nerub-ar-palace-raid-guide`
- `expansion_guide`
  - examples: `mistweaver-monk-the-war-within-pve-guide`
- `special_event_guide`
  - examples: Remix and Torghast pages

The CLI should explicitly reject or deprioritize these until we intentionally support them:
- patch-analysis pages
- news-like pages
- one-off old system pages that are not part of a guide family

## Command Expectations

### `search`

`search` should:
- search only intentionally supported or intentionally recognized families
- rank family matches appropriately for the query
- avoid surfacing unsupported/news-like WoW slugs as if they were guides
- expose enough metadata for the caller to understand the matched family

### `resolve`

`resolve` should:
- resolve clearly when the top match is family-appropriate and sufficiently better than alternatives
- stay conservative for ambiguous queries
- behave differently for broad class-hub queries vs spec-guide queries vs subpage queries

### `guide`

`guide` should:
- return a valid summary for every supported family
- fail clearly for unsupported/non-guide WoW pages
- avoid duplicated headings
- provide guide family metadata so the caller understands what kind of page they received

### `guide-full`

`guide-full` should:
- walk only the relevant family graph for the current page
- avoid exploding from a class hub into unrelated class hubs
- avoid traversing navigational blocks that are clearly site-wide or family-external
- produce a stable page set for export/query reuse

### `guide-export` / `guide-query`

These should:
- keep working across all supported families
- export enough metadata to tell which family the bundle represents
- keep family-aware traversal decisions stable in the resulting bundle

## Known Gaps To Fix

1. Family-aware traversal is incomplete.
- fixed for class hubs and role guides
- still needs broader review across all supported families

2. Headings are duplicated on real pages.
- fixed for the current heading-container pattern
- should still stay covered by regression tests as page shapes evolve

3. Unsupported or bad refs fail too late.
- fixed for unsupported/unclassified WoW slugs and 404 guide fetches

4. Discovery/ranking is too generic for some families.
- `easy mode`, `raid guide`, and special-event pages need continued family-aware ranking refinement instead of only slug text matching.
- unsupported query intent detection should stay explicit so news-like WoW queries do not silently degrade back into guide matches.

5. Documentation is not explicit enough.
- improved in `docs/USAGE.md`
- still needs long-term maintenance as family coverage expands

6. Test coverage is not deep enough yet.
- dedicated live coverage now exists
- recorded real-page fixture depth is still missing

## Phased Plan

### Phase 1: Correctness And Scope

Status: mostly completed.

- introduce explicit Icy Veins family classification
- add family metadata to discovery and fetch payloads
- fix heading duplication
- add structured invalid/unsupported failure behavior for bad WoW refs
- define how `guide-full` should behave for:
  - class hubs
  - role guides
  - spec-family pages
  - standalone/special-event pages

### Phase 2: Discovery And Traversal

Status: in progress.

- make sitemap discovery family-aware
- add family-aware ranking boosts and penalties
- ensure `resolve` handles:
  - main guide queries
  - easy mode queries
  - leveling queries
  - role/class-hub queries
  - raid-guide queries
  - special-event guide queries
- make `guide-full` traverse only the intended family graph for each family

### Phase 3: Coverage And Reliability

Status: started.

- add dedicated Icy Veins live tests
- add recorded fixtures for representative supported families
- add recorded fixtures for intentionally unsupported/non-guide WoW pages
- add regression tests around family-aware `guide-full`
- add regression tests for ranking and family classification

### Phase 4: Documentation And Polish

- update `docs/USAGE.md` with explicit supported families
- update this document with the validated support boundary
- update the root `warcraft` skill guidance so agents know when to choose Icy Veins
- make sure wrapper discovery/ranking works correctly for Icy Veins family types

## Testing Strategy

### Recorded Fixtures

Add or preserve fixtures for at least:
- class hub guide
- role guide
- main spec guide
- easy mode page
- leveling page
- raid guide
- expansion guide
- special-event guide
- explicitly unsupported/non-guide WoW page

### Live Tests

Add a dedicated Icy live test file covering:
- search
- resolve
- guide
- guide-full
- one class hub
- one role guide
- one easy mode page
- one raid guide
- one special-event guide
- one intentionally unsupported/non-guide failure path

### Contract Tests

Add regression coverage for:
- family classification
- heading dedupe
- family-aware traversal
- ranking boosts/penalties by family
- structured invalid/unsupported errors

## Shared vs Local Code

What can keep using shared code:
- article bundle export/load/query
- article discovery payload shaping
- linked-entity merge for multi-page bundles
- cache, output, and transport infrastructure

What should stay local to `icy-veins`:
- sitemap family classification
- family-aware ranking
- family-aware traversal rules
- Icy Veins page parsing
- Icy Veins-specific invalid/unsupported surface rules

## Quality Gates

`icy-veins` should be considered fully covered when:
- supported families are explicit in docs
- unsupported families fail clearly and consistently
- `guide-full` is family-aware and no longer over-traverses
- heading duplication is eliminated
- live coverage exists across representative supported families
- recorded fixtures exist across representative supported and unsupported families
- wrapper search/resolve behavior remains aligned with the Icy Veins family model

## Not In Scope Right Now

- login or premium support
- non-WoW Icy Veins games
- news ingestion
- patch-analysis pages as a first-class surface

## Source Links

- `https://www.icy-veins.com/sitemap.xml`
- `https://www.icy-veins.com/wow/monk-guide`
- `https://www.icy-veins.com/wow/healing-guide`
- `https://www.icy-veins.com/wow/fury-warrior-pve-dps-easy-mode`
- `https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-guide`
- `https://www.icy-veins.com/wow/mistweaver-monk-pve-healing-nerub-ar-palace-raid-guide`
- `https://www.icy-veins.com/wow/mistweaver-monk-the-war-within-pve-guide`
- `https://www.icy-veins.com/wow/mistweaver-monk-mists-of-pandaria-remix-guide`
- `https://www.icy-veins.com/wow/mistweaver-monk-torghast-guide-and-best-anima-powers`
- [Roadmap](/home/auro/code/warcraft_cli/docs/ROADMAP.md)
