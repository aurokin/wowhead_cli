# Migration Checklist

## Purpose

This document is the execution checklist for the monorepo migration.

It translates the planning documents into a controlled sequence with verification gates.

Use alongside:
- [Roadmap](/home/auro/code/warcraft_cli/docs/ROADMAP.md)
- [Repo Structure And Packaging](/home/auro/code/warcraft_cli/docs/architecture/REPO_STRUCTURE_AND_PACKAGING.md)
- [Package Layout](/home/auro/code/warcraft_cli/docs/architecture/PACKAGE_LAYOUT.md)
- [Wrapper Provider Contract](/home/auro/code/warcraft_cli/docs/foundation/WRAPPER_PROVIDER_CONTRACT.md)

## Pre-Migration Gate

Before migration starts:

1. Tag the stable `wowhead` release.
2. Verify the current repo passes all relevant tests.
3. Verify one documented smoke workflow for each major `wowhead` feature area.

Current stable tag:
- `v0.1.0`

## Required Verification Before Code Moves

The pre-migration verification gate is:

- all current unit tests pass
- live tests pass when enabled
- smoke workflows pass for major `wowhead` behavior

The goal is user-important behavior parity, not frozen internals.

## Smoke Workflow Areas

At minimum, verify:
- search and resolve
- regular entity lookup
- entity-page and comments
- guide and guide-full
- guide-export and hydrated entities
- guide-bundle list/search/query/inspect/refresh
- cache inspect/clear/repair

## Milestone 1

Goal:
- create the structure for the new repo shape
- preserve `wowhead`
- introduce `warcraft`
- include stubbed `method`

Checklist:

1. Create package directories for:
- `warcraft-core`
- `warcraft-api`
- `warcraft-content`
- `warcraft-cli`
- `wowhead-cli`
- `method-cli`

2. Move only shared-now infrastructure into the shared packages.

3. Keep `wowhead` feature behavior intact while moving shared infrastructure underneath it.

4. Add the Python `warcraft` wrapper with:
- `warcraft wowhead ...`
- `warcraft search ...`
- `warcraft resolve ...`
- `warcraft doctor`

5. Register `method` as a provider with stubbed:
- `search`
- `resolve`
- `doctor`

6. Move to root-level `skills/warcraft/SKILL.md` with progressive disclosure.

7. Re-run verification gates.

Current status:
- completed
- package directories, shared package skeletons, `warcraft`, and stubbed `method` are present
- verification gate passed after the extraction pass

## Milestone 2

Goal:
- implement real `method`

Checklist:

1. Replace `method` stubs with real guide extraction.
2. Validate which article abstractions are truly shared.
3. Move only validated article abstractions into `warcraft-content`.
4. Re-run verification gates.

Current status:
- completed
- `method` now provides sitemap-backed `search` / `resolve`, real guide fetch, multi-page `guide-full`, bundle export, and local bundle query
- verification gate passed after the Method implementation

## What Moves First From `wowhead`

- output shaping and projection
- structured error helpers
- cache infrastructure
- config/environment handling
- HTTP transport primitives
- bundle/index/freshness/query scaffolding

## What Must Not Move Yet

- Wowhead-specific parsing rules
- Wowhead entity routing quirks
- Wowhead guide extraction details
- article-level abstractions that only Wowhead currently uses
- service-specific ranking behavior

## Acceptance Criteria For `wowhead`

After migration work:
- `wowhead` still covers user-important behavior
- wrapper passthrough works for `wowhead`
- tests still pass
- docs reflect the new package layout and command routing

## Documentation Gate

During migration, update docs whenever:
- package boundaries change
- provider contract changes
- wrapper behavior changes
- storage/auth/config rules change

Minimum docs to keep aligned:
- [Roadmap](/home/auro/code/warcraft_cli/docs/ROADMAP.md)
- [Repo Structure And Packaging](/home/auro/code/warcraft_cli/docs/architecture/REPO_STRUCTURE_AND_PACKAGING.md)
- [Package Layout](/home/auro/code/warcraft_cli/docs/architecture/PACKAGE_LAYOUT.md)
- [Wrapper Provider Contract](/home/auro/code/warcraft_cli/docs/foundation/WRAPPER_PROVIDER_CONTRACT.md)

## Risks To Watch During Migration

- moving service-specific code into shared packages too early
- breaking `wowhead` behavior while extracting infrastructure
- letting the wrapper become a second implementation layer
- silently drifting docs away from the real architecture
