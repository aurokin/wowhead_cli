# Roadmap

## Goal

Evolve this repo from a single-service `wowhead` CLI into a Warcraft data monorepo with:
- separate service CLIs for distinct data sources
- shared core libraries where the behavior is genuinely common
- root-level skills that are not tied to one CLI package
- a top-level `warcraft` CLI that can route agents to the right service when they are unsure

The first new service after this restructure should be `method`.

## Planning Documents

- [Warcraft wrapper plan](/home/auro/code/wowhead_cli/docs/WARCRAFT_CLI_PLAN.md)
- [Wowhead CLI plan](/home/auro/code/wowhead_cli/docs/WOWHEAD_CLI_PLAN.md)
- [Method.gg CLI plan](/home/auro/code/wowhead_cli/docs/METHOD_CLI_PLAN.md)
- [Icy Veins CLI plan](/home/auro/code/wowhead_cli/docs/ICY_VEINS_CLI_PLAN.md)
- [Raider.IO CLI plan](/home/auro/code/wowhead_cli/docs/RAIDERIO_CLI_PLAN.md)
- [SimulationCraft CLI plan](/home/auro/code/wowhead_cli/docs/SIMC_CLI_PLAN.md)
- [Raidbots CLI plan](/home/auro/code/wowhead_cli/docs/RAIDBOTS_CLI_PLAN.md)
- [Warcraft Logs CLI plan](/home/auro/code/wowhead_cli/docs/WARCRAFTLOGS_CLI_PLAN.md)

## Planning Principles

- Keep service boundaries explicit. Do not hide very different access models behind one giant code path.
- Share infrastructure, not site-specific assumptions.
- Prefer a thin `warcraft` wrapper over a monolithic all-in-one implementation.
- Keep skills at the repo root so agents can discover the right workflow before they know the exact backend.
- Treat API-first, article-first, and local-tool integrations as different families.

## Service Landscape

| Service | Access model | High-level implementation direction | Notes |
| --- | --- | --- | --- |
| Wowhead | HTML pages plus embedded page data | Keep as a page-extraction and bundle-oriented CLI | [Plan](/home/auro/code/wowhead_cli/docs/WOWHEAD_CLI_PLAN.md) |
| Method.gg | Server-rendered article/guide pages with visible section nav and metadata | Build as an article extraction CLI with guide bundles and section query | [Plan](/home/auro/code/wowhead_cli/docs/METHOD_CLI_PLAN.md) |
| Icy Veins | Server-rendered article pages with guide metadata and nav links | Build as an article extraction CLI with search/resolve and section query | [Plan](/home/auro/code/wowhead_cli/docs/ICY_VEINS_CLI_PLAN.md) |
| Raider.IO | Public API with documented schema and rate limits | Build as an API-first CLI with typed endpoints and cached profile/leaderboard lookups | [Plan](/home/auro/code/wowhead_cli/docs/RAIDERIO_CLI_PLAN.md) |
| SimulationCraft | Local Git repo, local builds, local command execution | Build as a local-tool CLI with sync, build, inspect, and run workflows | [Plan](/home/auro/code/wowhead_cli/docs/SIMC_CLI_PLAN.md) |
| Raidbots | Web workflow built around SimulationCraft input and result pages | Start with result/report parsing and workflow helpers, then evaluate deeper automation carefully | [Plan](/home/auro/code/wowhead_cli/docs/RAIDBOTS_CLI_PLAN.md) |
| Warcraft Logs | Authenticated API with complex query workflows | Build as an API-first CLI with typed query helpers, auth management, and reusable report patterns | [Plan](/home/auro/code/wowhead_cli/docs/WARCRAFTLOGS_CLI_PLAN.md) |

## What The Research Suggests

- `Method.gg` and `Icy Veins` are article-first sources. They look much closer to guide extraction and local bundles than to entity APIs.
- `Raider.IO` is API-first. Its developer API is documented via Swagger/OpenAPI and publishes rate-limit expectations.
- `Warcraft Logs` should be treated as API-first and auth-heavy rather than a scraping target.
- `SimulationCraft` is fundamentally a local-repo integration, not a site integration.
- `Raidbots` should be approached as a workflow layer around SimulationCraft inputs and simulation results, not as the primary source of character truth.

Read the service-specific detail in:
- [Method.gg plan](/home/auro/code/wowhead_cli/docs/METHOD_CLI_PLAN.md)
- [Icy Veins plan](/home/auro/code/wowhead_cli/docs/ICY_VEINS_CLI_PLAN.md)
- [Raider.IO plan](/home/auro/code/wowhead_cli/docs/RAIDERIO_CLI_PLAN.md)
- [SimulationCraft plan](/home/auro/code/wowhead_cli/docs/SIMC_CLI_PLAN.md)
- [Raidbots plan](/home/auro/code/wowhead_cli/docs/RAIDBOTS_CLI_PLAN.md)
- [Warcraft Logs plan](/home/auro/code/wowhead_cli/docs/WARCRAFTLOGS_CLI_PLAN.md)

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

The wrapper-specific behavior is described in [WARCRAFT_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/WARCRAFT_CLI_PLAN.md).

## Shared Now

- output shaping, field projection, and pretty-print behavior
- structured error contracts
- cache backends, TTL policy, and cache inspection/repair
- HTTP client primitives, retries, throttling hooks, and headers
- local bundle/index storage, freshness tracking, and query scaffolding
- root command routing for the `warcraft` wrapper
- shared config and environment handling

These should move first because the current `wowhead` CLI already proves them and multiple future services will need them quickly.

## Shared After `method`

- article and content primitives that survive a second article-style service
- shared search/resolve provider interfaces
- ranking explanation shapes for discovery commands
- follow-up command suggestion shapes
- auth/session persistence for API-first services

These should move only after `method` exists and validates that the abstractions are real instead of Wowhead-specific.

## Service-Specific

- HTML parsing rules and page-model extraction
- API schemas, query builders, and endpoint contracts
- service-specific entity models and identifiers
- service-specific ranking heuristics
- SimulationCraft build/run logic
- service-specific auth flows and operational constraints

## Do Not Generalize Yet

- one universal entity model across all services
- one universal article or guide parser
- one universal search ranking algorithm
- one universal command grammar beyond wrapper routing
- one universal response model for API, article, and local-tool services

## Root Skill Strategy

Add repo-level skills that mirror the service layout rather than nesting the guidance inside one CLI package.

Recommended direction:
- `skills/warcraft/SKILL.md`: orchestration skill for deciding which service or wrapper command to use
- one root skill per service for service-specific workflows
- keep service skills concise and route agents toward the right CLI and follow-up commands

Agents should prefer `warcraft` when the service is unclear, then drop to `wowhead`, `method`, `warcraftlogs`, and so on once the source is known.

See the dedicated wrapper plan in [WARCRAFT_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/WARCRAFT_CLI_PLAN.md).

## `warcraft` Wrapper Strategy

The wrapper should be a router and orchestration layer, not the only place business logic lives.

High-level responsibilities:
- `warcraft search`: search across service-specific search providers when available
- `warcraft resolve`: pick the best service and next command conservatively
- `warcraft <service> ...`: pass through to the service CLI when the caller already knows what they need
- shared discovery commands for local bundles, cache inspection, and environment checks when those concepts become cross-service

The wrapper should not erase source identity. Agents still need to know whether the answer came from Wowhead, Method.gg, Warcraft Logs, or another backend.

## Recommended Migration Order

1. Extract `warcraft-core` from the current `wowhead` package without changing the `wowhead` command surface.
2. Extract `warcraft-api` for shared HTTP transport, retry, throttling hooks, and config handling.
3. Extract `warcraft-content` for bundle/index/freshness/query primitives.
4. Introduce a minimal `warcraft` wrapper that can proxy `wowhead` and expose shared discovery later.
5. Move the current root skill layout to service-agnostic root-level skills.
6. Add `method` as the first article-style service on top of the shared content/bundle pieces. See [METHOD_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/METHOD_CLI_PLAN.md).
7. Re-evaluate which article-level abstractions are actually shared, then add `icy-veins` if they hold up. See [ICY_VEINS_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/ICY_VEINS_CLI_PLAN.md).
8. Add `raiderio` as the first clearly API-first service on top of shared HTTP/cache/auth layers. See [RAIDERIO_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/RAIDERIO_CLI_PLAN.md).
9. Add `simc` as the first local-tool integration and use it to validate non-network abstractions. See [SIMC_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/SIMC_CLI_PLAN.md).
10. Add `raidbots` after `simc`, likely as a workflow-oriented companion. See [RAIDBOTS_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/RAIDBOTS_CLI_PLAN.md).
11. Add `warcraftlogs` after the API-first/auth patterns have been proven elsewhere. See [WARCRAFTLOGS_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/WARCRAFTLOGS_CLI_PLAN.md).

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

1. Create `warcraft-core`, `warcraft-api`, and `warcraft-content` with only the shared-now pieces.
2. Move only obviously generic infrastructure out of `wowhead`.
3. Add a minimal `warcraft` CLI that can proxy `wowhead` without changing existing behavior.
4. Move skills to root-level service directories and add `skills/warcraft/SKILL.md`.
5. Add a `method` package that proves the shared article and bundle abstractions. The target scope is in [METHOD_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/METHOD_CLI_PLAN.md).
6. Re-evaluate the package boundaries before adding the next service.

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
