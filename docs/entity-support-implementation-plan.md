# Entity Support Implementation Plan

## Status

- Overall: in progress
- Current phase: Phase 1 - entity type routing and advertised support audit
- Last updated: 2026-03-07

## Goal

Bring the CLI's advertised entity and guide features up to their actual supported level, including the types that currently fail live, while keeping the regular agent-facing responses compact and consistent.

## Acceptance Criteria

- Every advertised entity type has at least one passing live `entity` example.
- `entity`, `entity-page`, `comments`, `guide`, and `guide-full` use a coherent contract with minimal duplication.
- Linked-entity preview counts and `fetch_more_command` hints are trustworthy.
- Guide preview/full surfaces are internally consistent about what `linked_entities` means.
- README and skill docs describe only behavior that is verified by tests.

## Phases

### Phase 1 - Entity Type Routing And Support Audit

Status: in progress

Work:

- Audit every advertised entity type against live Wowhead behavior.
- Separate parser-level entity recognition from command-level fetch support.
- Refactor URL/tooltip/page resolution so type-specific routing can be encoded cleanly.
- Fix the currently broken advertised types or narrow the surface temporarily with precise errors while implementation is incomplete.
- Add live and fixture coverage for each supported type.

Exit criteria:

- All advertised entity types resolve through the right tooltip and page routes.
- Unsupported behavior fails with structured errors instead of raw upstream 404s.

### Phase 2 - Contract Normalization

Status: pending

Work:

- Normalize `entity`, `guide`, `entity-page`, `comments`, and `guide-full` around one canonical page URL field per object.
- Remove duplicate page/comment URL fields where the same value is repeated in multiple places.
- Decide whether `ok` remains part of success payloads everywhere or only in error payloads.
- Align guide preview fields with the newer entity contract.

Exit criteria:

- Agents can treat command outputs as one family of data contracts without type-specific exceptions.

### Phase 3 - Linked Entity Quality

Status: pending

Work:

- Reconcile href-derived and gatherer-derived linked entities into one normalized internal relation layer.
- Improve preview ranking so the first few items are useful follow-up targets.
- Add type counts and preview diversity without overloading the default response.
- Fix `fetch_more_command` so it matches the reported counts.

Exit criteria:

- Default previews are good enough for agents to choose the next step without noise-heavy follow-up calls.

### Phase 4 - Tooltip And Text Cleanup

Status: pending

Work:

- Improve tooltip HTML-to-text normalization.
- Remove repeated title fragments and malformed duplicate text.
- Consider adding a shorter summary field when that helps agents scan content quickly.

Exit criteria:

- Tooltip text is readable and compact across representative entity types.

## Current Findings

### Live Entity Samples Checked

- `achievement 776`
- `currency 3008`
- `item 19019`
- `npc 448`
- `object 185919`
- `quest 86739`
- `spell 49020`
- `transmog-set 12547`
- `zone 1519`
- `guide 3143`
- `guide-full 3143`

### Advertised Types Currently Failing Live

These were failing through the original generic routing model:

- `battle-pet`
- `faction`
- `mount`
- `pet`
- `recipe`

Current state after the first phase 1 refactor:

- `faction`: working via faction page route plus page-metadata tooltip fallback
- `pet`: working via pet page route plus page-metadata tooltip fallback
- `recipe`: working via spell-route aliasing
- `mount`: working via tooltip redirect resolution to an underlying item page
- `battle-pet`: working via tooltip redirect resolution to an underlying NPC page

### Confirmed Contract Issues

- Some preview items still surface low-signal names or poor ordering.

### Recently Fixed Contract Issues

- `fetch_more_command` for regular entity/comment linked-entity previews now scales to the known deduped count instead of hard-coding `--max-links 200`.
- `guide` and `guide-full` now both treat `linked_entities` as the merged deduped guide relation set, with `source_counts` exposing href/gatherer contributions.
- Lightweight linked-entity previews now suppress low-signal labels such as raw type names or URL-like anchor text and rank more actionable relation types ahead of noisy same-type/item-heavy results.
- Entity tooltips now expose a cleaned `tooltip.text` and a shorter title-stripped `tooltip.summary` for fast agent scanning.
- `guide` and `guide-full` now use `guide.page_url` as the canonical guide source and rely on `citations.comments` instead of duplicating the comment-thread URL under `guide.comments_url`.

### Route Resolution Findings

- `faction` pages exist at `/faction=<id>`, but Nether tooltip requests for `faction` return `Entity type is invalid`.
- `pet` pages exist at `/pet=<id>`, but Nether tooltip requests for `pet` return `Entity type is invalid`.
- `mount` tooltip requests redirect to an underlying item tooltip. Example checked: `mount 460 -> item 84101`.
- `battle-pet` tooltip requests redirect to an underlying NPC tooltip. Example checked: `battle-pet 39 -> npc 2671`.
- `recipe` does not appear to be a first-class Wowhead page type. The working model is recipe spell pages, for example `recipe 2549 -> spell 2549`.

## Progress Log

### 2026-03-07

- Created this plan document.
- Confirmed the current routing implementation is still generic `/<entity_type>=<id>` for page fetches and `/tooltip/<entity_type>/<id>` for tooltip fetches.
- Confirmed multiple advertised entity types fail live under that generic model.
- Completed the first phase 1 routing audit for the failing advertised types.
- Implemented an internal entity access plan / resolver model to separate requested type/id from underlying tooltip/page fetch targets.
- Added search result support for `Faction` and `Hunter Pet` suggestion types.
- Added page-metadata tooltip fallback for `faction` and `pet`.
- Added spell-route aliasing for `recipe`.
- Added tooltip-redirect page resolution for `mount` and `battle-pet`.
- Added unit coverage for the new routing behavior and live contract coverage for the special-route entity types.
- Verified with `pytest -q` and live smokes for `faction 529`, `recipe 2549`, `mount 460`, and `battle-pet 39`.
- Fixed regular entity/comment `fetch_more_command` hints so large previews suggest an appropriate `--max-links` value.
- Verified live on `currency 3008`, which now reports `wowhead entity-page currency 3008 --max-links 308`.
- Normalized `guide` and `guide-full` so both use the same merged `linked_entities` semantics.
- Added `source_counts` to guide linked-entity payloads so href and gatherer contributions remain visible.
- Verified live on guide `3143`, where both `guide` and `guide-full` now report `linked_entities.count = 52`.
- Added lightweight preview ranking and diversity selection so regular previews prefer actionable relation types over low-signal rows.
- Added low-signal name suppression for labels like `item` and URL-shaped anchor text in the lightweight preview surface.
- Verified live improvements on `npc 448`, `item 19019`, and `currency 3008`.
- Added tooltip-specific cleanup for bracket artifacts and repeated sentence fragments.
- Added `tooltip.summary` as a short agent-facing scan field while keeping full `tooltip.text` and `tooltip.html`.
- Verified live improvements on `spell 49020`, `mount 460`, and `quest 86739`.
- Removed duplicate guide comment URL fields and normalized guide page URL naming across `guide` and `guide-full`.
- Verified live on `guide 3143` and `guide-full 3143`, both of which now expose `guide.page_url`.
