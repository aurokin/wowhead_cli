# Roadmap

## Goal

Evolve this repo from a single-service `wowhead` CLI into a Warcraft data monorepo with:
- separate service CLIs for distinct data sources
- shared core libraries where the behavior is genuinely common
- root-level skills that are not tied to one CLI package
- a top-level `warcraft` CLI that can route agents to the right service when they are unsure

The first new service after this restructure should be `method`.

The structural rules for packaging, language choice, installation, storage, auth, and wrapper boundaries are defined in [REPO_STRUCTURE_AND_PACKAGING.md](/home/auro/code/wowhead_cli/docs/REPO_STRUCTURE_AND_PACKAGING.md).
The concrete package tree is defined in [PACKAGE_LAYOUT.md](/home/auro/code/wowhead_cli/docs/PACKAGE_LAYOUT.md).
The execution order is controlled by [MIGRATION_CHECKLIST.md](/home/auro/code/wowhead_cli/docs/MIGRATION_CHECKLIST.md).
The wrapper/provider boundary is defined in [WRAPPER_PROVIDER_CONTRACT.md](/home/auro/code/wowhead_cli/docs/WRAPPER_PROVIDER_CONTRACT.md).

## Current Status

Completed:
- shared package split into `warcraft-core`, `warcraft-api`, and `warcraft-content`
- working `warcraft` wrapper
- working `wowhead` provider in package form with:
  - entity, guide, comments, compare, and bundle workflows
  - guide-category discovery with filtering and sorting
  - timeline-native `news` / `blue-tracker` with detail fetches
  - maintainable tool-state coverage for `talent-calc`, `profession-tree`, `dressing-room`, and `profiler`
- working `method` provider with explicit supported-family boundaries and live/fixture coverage
- working `icy-veins` provider with explicit supported-family boundaries and live/fixture coverage
- working `raiderio` provider with direct lookup, search/resolve, and first analytics primitives
- working `warcraft-wiki` provider with typed programming/reference surfaces and broad family coverage
- working `wowprogress` provider with direct lookup, search/resolve, and first analytics primitives
- working `simc` provider with readonly source analysis, runtime helpers, and managed checkout flow
- root `warcraft` skill

Validated shared so far:
- output/error shaping
- cache and HTTP infrastructure
- bundle/index/query scaffolding
- wrapper routing
- article bundle export/load/query
- article search/resolve payload shaping and follow-up contracts
- article linked-entity merge across multi-page guides
- article/reference bundle export/query outside class guides
- article-provider CLI support helpers
- article-provider test scaffolding
- wrapper expansion filtering and provider expansion metadata
- wrapper ranking policy with tunable provider-family and intent weighting
- shared path/XDG helpers
- sample-backed analytics direction for profile and leaderboard providers

Active next step:
- continue improving existing providers and wrapper discovery quality
- build reusable analytics systems for profile and leaderboard providers instead of one-off answer commands
- add static quality tooling from [LINTING_AND_COMPLEXITY_PLAN.md](/home/auro/code/wowhead_cli/docs/LINTING_AND_COMPLEXITY_PLAN.md) so refactor targets are easier to identify and prioritize
- focus on features, refactors, testing, code shareability, reliability, and performance before starting more auth-heavy providers
- roadmap cleanup after the recent provider quality passes
- for `raiderio`, prioritize:
  - deeper sample-backed analytics
  - clearer season-aware leaderboard workflows
  - richer normalized run/profile snapshots where the source supports them
- for `wowprogress`, prioritize:
  - deeper sample-backed analytics
  - guild snapshot, history, and rank workflows that are easier than manual site navigation
  - guild/profile aggregation that is faster and clearer than browser workflows
  - reliability and normalization improvements around rankings/profile slices
- keep `wowhead` at the maintainability boundary now documented in [WOWHEAD_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/WOWHEAD_CLI_PLAN.md):
  - continue only on straightforward structured extraction
  - do not push `dressing-room` / `profiler` into reverse-engineering work without an explicit product decision

## Planning Documents

- [Repo structure and packaging](/home/auro/code/wowhead_cli/docs/REPO_STRUCTURE_AND_PACKAGING.md)
- [Package layout](/home/auro/code/wowhead_cli/docs/PACKAGE_LAYOUT.md)
- [Migration checklist](/home/auro/code/wowhead_cli/docs/MIGRATION_CHECKLIST.md)
- [Wrapper provider contract](/home/auro/code/wowhead_cli/docs/WRAPPER_PROVIDER_CONTRACT.md)
- [Expansion filtering plan](/home/auro/code/wowhead_cli/docs/EXPANSION_FILTERING_PLAN.md)
- [Linting and complexity plan](/home/auro/code/wowhead_cli/docs/LINTING_AND_COMPLEXITY_PLAN.md)
- [Warcraft wrapper plan](/home/auro/code/wowhead_cli/docs/WARCRAFT_CLI_PLAN.md)
- [Wowhead CLI plan](/home/auro/code/wowhead_cli/docs/WOWHEAD_CLI_PLAN.md)
- [Method.gg CLI plan](/home/auro/code/wowhead_cli/docs/METHOD_CLI_PLAN.md)
- [Icy Veins CLI plan](/home/auro/code/wowhead_cli/docs/ICY_VEINS_CLI_PLAN.md)
- [Raider.IO CLI plan](/home/auro/code/wowhead_cli/docs/RAIDERIO_CLI_PLAN.md)
- [WowProgress CLI plan](/home/auro/code/wowhead_cli/docs/WOWPROGRESS_CLI_PLAN.md)
- [Warcraft Wiki CLI plan](/home/auro/code/wowhead_cli/docs/WARCRAFT_WIKI_CLI_PLAN.md)
- [Blizzard API CLI plan](/home/auro/code/wowhead_cli/docs/BLIZZARD_API_CLI_PLAN.md)
- [Undermine Exchange CLI plan](/home/auro/code/wowhead_cli/docs/UNDERMINE_EXCHANGE_CLI_PLAN.md)
- [RaidPlan CLI plan](/home/auro/code/wowhead_cli/docs/RAIDPLAN_CLI_PLAN.md)
- [CurseForge CLI plan](/home/auro/code/wowhead_cli/docs/CURSEFORGE_CLI_PLAN.md)
- [SimulationCraft CLI plan](/home/auro/code/wowhead_cli/docs/SIMC_CLI_PLAN.md)
- [SimulationCraft migration inventory](/home/auro/code/wowhead_cli/docs/SIMC_MIGRATION_INVENTORY.md)
- [SimulationCraft implementation plan](/home/auro/code/wowhead_cli/docs/SIMC_IMPLEMENTATION_PLAN.md)
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
| WowProgress | Server-rendered rankings and profile pages | Build as a rankings/profile CLI with guild, character, and progress lookups plus cached leaderboard slices | [Plan](/home/auro/code/wowhead_cli/docs/WOWPROGRESS_CLI_PLAN.md) |
| Warcraft Wiki | Server-rendered MediaWiki pages plus wiki metadata | Build as a reference CLI for lore, systems, and addon/API documentation with article export/query | [Plan](/home/auro/code/wowhead_cli/docs/WARCRAFT_WIKI_CLI_PLAN.md) |
| Blizzard API | Official authenticated game-data and profile APIs | Build as an API-first CLI for canonical game data, profile data, and auth-aware official lookups | [Plan](/home/auro/code/wowhead_cli/docs/BLIZZARD_API_CLI_PLAN.md) |
| Undermine Exchange | Market-data web workflows and auction-oriented views | Build as a market-data CLI for item, commodity, and price-history lookups once the public surface is stable | [Plan](/home/auro/code/wowhead_cli/docs/UNDERMINE_EXCHANGE_CLI_PLAN.md) |
| RaidPlan | Planning/editor workflow with shareable encounter plans | Build as a read-first planning CLI for public plan fetch, export, and query before attempting editing flows | [Plan](/home/auro/code/wowhead_cli/docs/RAIDPLAN_CLI_PLAN.md) |
| CurseForge | Addon/mod discovery pages plus file and release metadata | Build as a read-first addon metadata CLI for search, project, file, changelog, and compatibility lookups | [Plan](/home/auro/code/wowhead_cli/docs/CURSEFORGE_CLI_PLAN.md) |
| SimulationCraft | Local Git repo, readonly source inspection, local builds, local command execution | Build as a local-tool CLI with readonly source analysis, sync/build/run workflows, build decoding, and agent-facing APL reasoning helpers | [Plan](/home/auro/code/wowhead_cli/docs/SIMC_CLI_PLAN.md) |
| Raidbots | Web workflow built around SimulationCraft input and result pages | Start with result/report parsing and workflow helpers, then evaluate deeper automation carefully | [Plan](/home/auro/code/wowhead_cli/docs/RAIDBOTS_CLI_PLAN.md) |
| Warcraft Logs | Official OAuth 2.0 + GraphQL API with public and user-auth endpoints | Build as an API-first CLI with typed guild, character, report, rankings, world-data, and auth workflows over the official API | [Plan](/home/auro/code/wowhead_cli/docs/WARCRAFTLOGS_CLI_PLAN.md) |

## What The Research Suggests

- `Method.gg` and `Icy Veins` are article-first sources. They look much closer to guide extraction and local bundles than to entity APIs.
- `Raider.IO` is API-first. Its developer API is documented via Swagger/OpenAPI and publishes rate-limit expectations.
- profile and leaderboard providers should grow through reusable analytics systems:
  - sampling
  - normalization
  - aggregation
  - provenance
  - freshness
- `Blizzard API` should be treated as the canonical official source for supported game-data and profile surfaces, with OAuth, region, and namespace rules treated as first-class concerns.
- `Warcraft Logs` should be treated as API-first and auth-heavy rather than a scraping target.
- `SimulationCraft` is fundamentally a local-repo integration, not a site integration, and the existing `simc_exp` work shows that readonly source-tree analysis is already a real use case.
- `Raidbots` should be approached as a workflow layer around SimulationCraft inputs and simulation results, not as the primary source of character truth.

Read the service-specific detail in:
- [Method.gg plan](/home/auro/code/wowhead_cli/docs/METHOD_CLI_PLAN.md)
- [Icy Veins plan](/home/auro/code/wowhead_cli/docs/ICY_VEINS_CLI_PLAN.md)
- [Raider.IO plan](/home/auro/code/wowhead_cli/docs/RAIDERIO_CLI_PLAN.md)
- [Blizzard API plan](/home/auro/code/wowhead_cli/docs/BLIZZARD_API_CLI_PLAN.md)
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
- `packages/wowprogress-cli`
- `packages/warcraft-wiki-cli`
- `packages/blizzard-api-cli`
- `packages/undermine-exchange-cli`
- `packages/raidplan-cli`
- `packages/curseforge-cli`
- `packages/simc-cli`
- `packages/raidbots-cli`
- `packages/warcraftlogs-cli`
- `skills/warcraft/`
- `skills/method/`
- `skills/icy-veins/`
- `skills/raiderio/`
- `skills/wowprogress/`
- `skills/warcraft-wiki/`
- `skills/blizzard-api/`
- `skills/undermine-exchange/`
- `skills/raidplan/`
- `skills/curseforge/`
- `skills/simc/`
- `skills/raidbots/`
- `skills/warcraftlogs/`

The important split is conceptual, not naming. Shared code should live in explicit libraries, and each service CLI should remain individually runnable.

The wrapper-specific behavior is described in [WARCRAFT_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/WARCRAFT_CLI_PLAN.md).
The package and language rules for that shape are defined in [REPO_STRUCTURE_AND_PACKAGING.md](/home/auro/code/wowhead_cli/docs/REPO_STRUCTURE_AND_PACKAGING.md).

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

Current validated subset:
- article bundle export/load/query is proven shared across `method` and `icy-veins` and now lives in [warcraft_content.article_bundle](/home/auro/code/wowhead_cli/packages/warcraft-content/src/warcraft_content/article_bundle.py)
- article search/resolve payload shaping, follow-up guidance, and multi-page linked-entity merge are proven shared across `method` and `icy-veins` and now live in [warcraft_content.article_discovery](/home/auro/code/wowhead_cli/packages/warcraft-content/src/warcraft_content/article_discovery.py)
- article parsing and navigation extraction are still provider-specific
- provider-local ranking remains provider-specific

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
- keep the root `warcraft` skill progressive-disclosure-first for now
- add service-specific root skills later only if they prove useful

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

Completed:
1. Extract `warcraft-core` from the current `wowhead` package without changing the `wowhead` command surface.
2. Extract `warcraft-api` for shared HTTP transport, retry, throttling hooks, and config handling.
3. Extract `warcraft-content` for bundle/index/freshness/query primitives.
4. Introduce a minimal `warcraft` wrapper that can proxy `wowhead` and expose shared discovery later.
5. Move the current root skill layout to service-agnostic root-level skills.
6. Add `method` as the first article-style service on top of the shared content/bundle pieces. See [METHOD_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/METHOD_CLI_PLAN.md).
7. Validate those article abstractions against `icy-veins`.
8. Add `raiderio` as the first clearly API-first service on top of shared HTTP/cache/auth layers, with auth deferred and search/resolve stubbed in phase 1. See [RAIDERIO_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/RAIDERIO_CLI_PLAN.md).
9. Add `warcraft-wiki` as a working reference/documentation provider and validate the shared article layer outside class guides. See [WARCRAFT_WIKI_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/WARCRAFT_WIKI_CLI_PLAN.md).
10. Add `wowprogress` as a working rankings/profile provider adjacent to `raiderio`, while keeping its HTML parsing and discovery constraints provider-specific. See [WOWPROGRESS_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/WOWPROGRESS_CLI_PLAN.md).

Next:
11. Add `simc` as the first local-tool integration and use it to validate readonly source analysis plus non-network execution abstractions. See [SIMC_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/SIMC_CLI_PLAN.md).
12. Add `raidbots` after `simc`, likely as a workflow-oriented companion. See [RAIDBOTS_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/RAIDBOTS_CLI_PLAN.md).
13. Add `blizzard-api` as the canonical official data provider for supported game-data and profile lookups once we are ready to tackle auth. Use it to validate OAuth, region handling, and namespace-aware API patterns. See [BLIZZARD_API_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/BLIZZARD_API_CLI_PLAN.md).
14. Add `warcraftlogs` after the API-first/auth patterns have been proven elsewhere. See [WARCRAFTLOGS_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/WARCRAFTLOGS_CLI_PLAN.md).
15. Add `undermine-exchange` once the public market-data surface is stable enough to plan against. See [UNDERMINE_EXCHANGE_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/UNDERMINE_EXCHANGE_CLI_PLAN.md).
16. Add `raidplan` as a planning/workflow provider once we decide to tackle read-first public plan extraction. See [RAIDPLAN_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/RAIDPLAN_CLI_PLAN.md).
17. Add `curseforge` as a read-first addon metadata provider once we want addon/project/file compatibility workflows. See [CURSEFORGE_CLI_PLAN.md](/home/auro/code/wowhead_cli/docs/CURSEFORGE_CLI_PLAN.md).

## Research Anchors

These are the high-level sources used to shape the plan:
- Raider.IO developer API and OpenAPI surface: `https://raider.io/api` and `https://raider.io/openapi.json`
- Method.gg guide pages such as `https://www.method.gg/guides/mistweaver-monk`
- Icy Veins guide pages such as `https://www.icy-veins.com/wow/warrior-guide`
- SimulationCraft repo: `https://github.com/simulationcraft/simc`
- Raidbots support guidance around the SimulationCraft addon: `https://support.raidbots.com/article/54-installing-and-using-the-simulationcraft-addon`
- Warcraft Logs official API docs entry points: `https://www.warcraftlogs.com/api/docs` and `https://classic.warcraftlogs.com/v2-api-docs/warcraft`

## Immediate Planning Priorities

 - add `simc` as the next non-auth provider using the readonly-analysis lessons already proven in `simc_exp`
 - add `blizzard-api` as the official canonical data source for supported game-data and profile lookups once auth work is in scope
- keep package boundaries and wrapper/provider contracts aligned with real code as the monorepo grows
- continue extracting only genuinely shared infrastructure as new providers prove the abstraction

## Lower-Priority Candidates

- `archon`
 - likely overlaps heavily with `warcraftlogs` and should be revisited after that ecosystem is in place
- `mythictrap`
  - strong raid-guide source, but less broad than `method` or `icy-veins`
- `dataforazeroth`
  - potentially useful for collections and achievement completion, but the site appears heavily app-driven and is lower priority than current sources

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
