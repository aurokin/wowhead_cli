# Roadmap

## Goal

Evolve this repo from a single-service `wowhead` CLI into a Warcraft data monorepo with:
- separate service CLIs for distinct data sources
- shared core libraries where the behavior is genuinely common
- root-level skills that are not tied to one CLI package
- a top-level `warcraft` CLI that can route agents to the right service when they are unsure

The first new service after this restructure should be `method`.

## Planning Principles

- Keep service boundaries explicit. Do not hide very different access models behind one giant code path.
- Share infrastructure, not site-specific assumptions.
- Prefer a thin `warcraft` wrapper over a monolithic all-in-one implementation.
- Keep skills at the repo root so agents can discover the right workflow before they know the exact backend.
- Treat API-first, article-first, and local-tool integrations as different families.

## Service Landscape

| Service | Access model | High-level implementation direction | Notes |
| --- | --- | --- | --- |
| Wowhead | HTML pages plus embedded page data | Keep as a page-extraction and bundle-oriented CLI | Already implemented; becomes the first consumer of shared core libraries |
| Method.gg | Server-rendered article/guide pages with visible section nav and metadata | Build as an article extraction CLI with guide bundles and section query | Good first expansion target; close to Wowhead guide workflows without pretending the markup is the same |
| Icy Veins | Server-rendered article pages with guide metadata and nav links | Build as an article extraction CLI with search/resolve and section query | Similar family to Method.gg; likely shares article and bundle primitives |
| Raider.IO | Public API with documented schema and rate limits | Build as an API-first CLI with typed endpoints and cached profile/leaderboard lookups | Do not scrape beyond published endpoints; shared HTTP/cache code is useful, article tooling is not |
| SimulationCraft | Local Git repo, local builds, local command execution | Build as a local-tool CLI with sync, build, inspect, and run workflows | This should shape the monorepo abstractions because it is not a network service |
| Raidbots | Web workflow built around SimulationCraft input and result pages | Start with result/report parsing and workflow helpers, then evaluate deeper automation carefully | Should likely depend on local `simc` support rather than acting as a standalone data source |
| Warcraft Logs | Authenticated API with complex query workflows | Build as an API-first CLI with typed query helpers, auth management, and reusable report patterns | This is likely the most complex service and should stay strongly isolated |

## What The Research Suggests

- `Method.gg` and `Icy Veins` are article-first sources. They look much closer to guide extraction and local bundles than to entity APIs.
- `Raider.IO` is API-first. Its developer API is documented via Swagger/OpenAPI and publishes rate-limit expectations.
- `Warcraft Logs` should be treated as API-first and auth-heavy rather than a scraping target.
- `SimulationCraft` is fundamentally a local-repo integration, not a site integration.
- `Raidbots` should be approached as a workflow layer around SimulationCraft inputs and simulation results, not as the primary source of character truth.

## Target Repo Shape

A good end state is:

- `packages/warcraft-core`
- `packages/warcraft-content`
- `packages/warcraft-api`
- `packages/warcraft-cli`
- `packages/wowhead-cli`
- `packages/method-cli`
- `packages/icy-veins-cli`
- `packages/raiderio-cli`
- `packages/simc-cli`
- `packages/raidbots-cli`
- `packages/warcraftlogs-cli`
- `skills/warcraft/`
- `skills/wowhead/`
- `skills/method/`
- `skills/icy-veins/`
- `skills/raiderio/`
- `skills/simc/`
- `skills/raidbots/`
- `skills/warcraftlogs/`

The important split is conceptual, not naming. Shared code should live in explicit libraries, and each service CLI should remain individually runnable.

## Shared Code That Probably Belongs In Core

- output shaping, field projection, and pretty-print behavior
- cache backends, TTL policy, and cache inspection/repair
- HTTP client primitives, retries, throttling, and headers
- local bundle/index storage, freshness tracking, and query helpers
- common search/resolve patterns where the concept is shared
- auth/session helpers for API-backed services
- root command routing for the `warcraft` wrapper

## Code That Should Stay Service-Specific

- HTML parsing rules and page-model extraction
- API schemas, query builders, and endpoint contracts
- service-specific entity models and identifiers
- service-specific ranking heuristics
- SimulationCraft build/run logic
- service-specific auth flows and operational constraints

## Root Skill Strategy

Add repo-level skills that mirror the service layout rather than nesting the guidance inside one CLI package.

Recommended direction:
- `skills/warcraft/SKILL.md`: orchestration skill for deciding which service or wrapper command to use
- one root skill per service for service-specific workflows
- keep service skills concise and route agents toward the right CLI and follow-up commands

Agents should prefer `warcraft` when the service is unclear, then drop to `wowhead`, `method`, `warcraftlogs`, and so on once the source is known.

## `warcraft` Wrapper Strategy

The wrapper should be a router and orchestration layer, not the only place business logic lives.

High-level responsibilities:
- `warcraft search`: search across service-specific search providers when available
- `warcraft resolve`: pick the best service and next command conservatively
- `warcraft <service> ...`: pass through to the service CLI when the caller already knows what they need
- shared discovery commands for local bundles, cache inspection, and environment checks when those concepts become cross-service

The wrapper should not erase source identity. Agents still need to know whether the answer came from Wowhead, Method.gg, Warcraft Logs, or another backend.

## Recommended Migration Order

1. Extract shared libraries from the current `wowhead` package without changing the existing `wowhead` command surface.
2. Introduce a minimal `warcraft` wrapper that can proxy `wowhead` and expose shared discovery later.
3. Move the current root skill layout to service-agnostic root-level skills.
4. Add `method` as the first article-style service on top of the shared content/bundle pieces.
5. Add `icy-veins` next if the shared article abstractions hold up.
6. Add `raiderio` as the first clearly API-first service on top of shared HTTP/cache/auth layers.
7. Add `simc` as the first local-tool integration and use it to validate non-network abstractions.
8. Add `raidbots` after `simc`, likely as a workflow-oriented companion.
9. Add `warcraftlogs` after the API-first/auth patterns have been proven elsewhere.

## Research Anchors

These are the high-level sources used to shape the plan:
- Raider.IO developer API and OpenAPI surface: `https://raider.io/api` and `https://raider.io/openapi.json`
- Method.gg guide pages such as `https://www.method.gg/guides/mistweaver-monk`
- Icy Veins guide pages such as `https://www.icy-veins.com/wow/warrior-guide`
- SimulationCraft repo: `https://github.com/simulationcraft/simc`
- Raidbots support guidance around the SimulationCraft addon: `https://support.raidbots.com/article/54-installing-and-using-the-simulationcraft-addon`
- Warcraft Logs official API docs entry points: `https://www.warcraftlogs.com/api/docs` and `https://classic.warcraftlogs.com/v2-api-docs/warcraft`

## First Execution Slice

When implementation starts, the first restructure pass should stay narrow:

1. Create the shared package skeleton and move only obviously shared infrastructure out of `wowhead`.
2. Add a minimal `warcraft` CLI that can proxy `wowhead` without changing existing behavior.
3. Move skills to root-level service directories and add `skills/warcraft/SKILL.md`.
4. Add a `method` package that proves the shared article and bundle abstractions.
5. Re-evaluate the package boundaries before adding the next service.

## Immediate Planning Priorities

- define the shared package boundaries before adding `method`
- define the root skill structure before adding another service-specific skill
- define the minimum viable `warcraft` wrapper contract
- decide how packaging and entrypoints will work in a multi-package Python monorepo
- identify which parts of the current `wowhead` codebase should move first and which should stay local until a second consumer exists

## Risks To Watch

- over-generalizing too early and building abstractions around one site’s quirks
- pushing article sites and API services through the same data model when they should stay distinct
- putting too much real logic in the `warcraft` wrapper instead of in shared libraries or service packages
- making root skills too vague to be useful
- letting the monorepo shape block delivery of the first new service

## Success Criteria

- agents can start from a root-level Warcraft skill and be routed to the right service
- each service remains independently testable and independently runnable
- shared code is real shared infrastructure, not accidental coupling
- adding `method` does not require copying large parts of `wowhead`
- the `warcraft` wrapper improves discovery without hiding source provenance
