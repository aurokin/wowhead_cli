# Warcraft Logs CLI Plan

## Goal

Build `warcraftlogs` as an official API-first provider for Warcraft Logs using the supported OAuth 2.0 and GraphQL APIs, not scraping.

The CLI should become the fastest trustworthy path for:
- guild progression and ranking lookups
- character ranking lookups
- report inspection
- fight/event/table/graph extraction from reports
- world metadata lookup for zones, encounters, regions, servers, and expansions
- authenticated user workflows when private reports or user-scoped data matter

## Current State

Implemented today:
- retail-only phase-1 standalone provider
- official OAuth client-credentials auth against the public GraphQL endpoint
- manual user-auth groundwork for:
  - authorization code flow
  - PKCE flow
- persisted user-token metadata and private-endpoint verification via `warcraftlogs auth whoami`
- auth lookup order:
  - repo-local `.env.local`
  - XDG config: `~/.config/warcraft/providers/warcraftlogs.env`
  - process environment
- runtime auth state path:
  - `~/.local/state/warcraft/providers/warcraftlogs.json`
- supported variables:
  - `WARCRAFTLOGS_CLIENT_ID`
  - `WARCRAFTLOGS_CLIENT_SECRET`
- commands:
  - `warcraftlogs doctor`
  - `warcraftlogs auth status`
  - `warcraftlogs auth client`
  - `warcraftlogs auth token`
  - `warcraftlogs auth whoami`
  - `warcraftlogs auth login`
  - `warcraftlogs auth pkce-login`
  - `warcraftlogs auth logout`
  - `warcraftlogs rate-limit`
  - `warcraftlogs regions`
  - `warcraftlogs expansions`
  - `warcraftlogs server`
  - `warcraftlogs zones`
  - `warcraftlogs zone`
  - `warcraftlogs encounter`
  - `warcraftlogs guild`
  - `warcraftlogs guild-members`
  - `warcraftlogs guild-attendance`
  - `warcraftlogs guild-rankings`
  - `warcraftlogs guild-reports`
  - `warcraftlogs character`
  - `warcraftlogs character-rankings`
  - `warcraftlogs reports`
  - `warcraftlogs report`
  - `warcraftlogs report-fights`
  - `warcraftlogs report-master-data`
  - `warcraftlogs report-player-details`
  - `warcraftlogs report-events`
  - `warcraftlogs report-table`
  - `warcraftlogs report-graph`
  - `warcraftlogs report-rankings`
- unit coverage for the current JSON contract
- live coverage for:
  - `regions`
  - `server`
  - `guild`
  - `guild-members`
  - `expansions`
  - `zone`
  - `guild-rankings`
  - `guild-reports`
  - `reports`
  - `report`
  - constrained `report-master-data`
  - constrained `report-player-details`
  - constrained `report-table`
  - constrained `report-graph`
  - constrained `report-rankings`

Current intentional boundary:
- standalone only for now
- not yet wired into the `warcraft` wrapper
- retail/main site profile only
- public endpoint only
- typed fields only; no raw GraphQL passthrough
- no wrapper-level user-auth routing yet
- no classic/fresh site-profile routing yet

What changed in the research baseline:
- we now have a local rendered docs dump under `research/warcraftlogs-docs/`
- we now also have local rendered docs dumps under:
  - `research/warcraftlogs-docs-classic/`
  - `research/warcraftlogs-docs-fresh/`
- the dump is produced by [dump_warcraftlogs_docs.py](/home/auro/code/wowhead_cli/scripts/dump_warcraftlogs_docs.py)
- the dump confirms Warcraft Logs has an official OAuth 2.0 + GraphQL integration surface that is broad enough for a full CLI

This means `warcraftlogs` should be planned as an official integration first, with scraping treated only as a fallback for unsupported site workflows.

Shared auth direction for this provider is defined in [AUTH_ARCHITECTURE_PLAN.md](/home/auro/code/wowhead_cli/docs/AUTH_ARCHITECTURE_PLAN.md). `warcraftlogs` is one of the two providers that should define the shared OAuth-oriented auth architecture.

## Immediate Next Steps

Highest-value next implementation slices:
- make `character-rankings` more reliable across public characters before treating it as fully validated
- deepen report workflows beyond the current phase-1 slice:
  - safer event pagination patterns once `events(...)` can be validated more broadly
  - additional report detail surfaces after the current player/ranking slice is proven
- start the deep encounter analytics slice for report-link-driven questions:
  - encounter identity from report URLs
  - fight-scoped actor/ability normalization
  - typed buff/cast/damage workflows instead of ad hoc event math

After that:
- user-auth plumbing
- wrapper integration
- future site-profile routing for `classic` and `fresh`

## Site Variant Research

We now have rendered docs dumps for:
- retail:
  - `https://www.warcraftlogs.com`
- classic:
  - `https://classic.warcraftlogs.com`
- fresh:
  - `https://fresh.warcraftlogs.com`

Current research result:
- all three sites expose the same OAuth docs content
- all three sites expose the same normalized GraphQL schema surface
- all three manifests currently contain `110` normalized GraphQL docs pages

This is an important architectural result:
- retail/classic/fresh should not become separate CLI packages
- they should become site profiles inside one `warcraftlogs` provider
- the split is operational and product-scoped, not schema-scoped

## Variant Strategy

Recommended long-term provider shape:
- one provider: `warcraftlogs`
- future site profiles:
  - `retail`
  - `classic`
  - `fresh`

The provider should eventually route:
- base site URL
- OAuth endpoints
- GraphQL endpoint root
- provider policy metadata

through a site-profile layer rather than command duplication.

## Expansion Filter Planning

This provider needs explicit wrapper-expansion planning before it is added to `warcraft`.

Recommended policy:
- phase 1:
  - retail-only implementation
  - if routed through `warcraft`, classify as `fixed` to `retail`
- phase 2:
  - keep retail-only wrapper behavior
- phase 3:
  - add `classic` and `fresh` site profiles
  - reclassify `warcraftlogs` from `fixed retail` to `profiled`

Important consequence:
- the current wrapper expansion vocabulary is still mostly wowhead-shaped
- `classic-fresh` is not currently a first-class wrapper expansion key
- we should not pretend the existing wrapper expansion keys already cover all Warcraft Logs site variants cleanly

So phase 3 must include:
- site-profile routing in `warcraftlogs`
- wrapper expansion vocabulary review
- explicit mapping from wrapper expansion keys to Warcraft Logs site profiles
- provider registry metadata updates in the `warcraft` wrapper

Current planning direction:
- `retail` -> `www.warcraftlogs.com`
- classic-family wrapper keys -> `classic.warcraftlogs.com`
- `classic-fresh` or equivalent future wrapper key -> `fresh.warcraftlogs.com`

This mapping is still a planning target, not an implemented contract.

## Official Access Model

Warcraft Logs officially supports OAuth 2.0 and GraphQL:
- OAuth docs landing page: `https://www.warcraftlogs.com/api/docs`
- public GraphQL endpoint: `https://www.warcraftlogs.com/api/v2/client`
- user-auth GraphQL endpoint: `https://www.warcraftlogs.com/api/v2/user`
- authorization URI: `https://www.warcraftlogs.com/oauth/authorize`
- token URI: `https://www.warcraftlogs.com/oauth/token`

Supported auth flows from the official docs:
- client credentials flow
  - public API only
  - good for most read-first CLI queries
- authorization code flow
  - user-authorized private/user data
- PKCE code flow
  - user-authorized private/user data without client-secret distribution

From the official docs:
- public data belongs under `/api/v2/client`
- user/private data belongs under `/api/v2/user`
- the API is schema-driven GraphQL
- rate-limit state is queryable via `RateLimitData`

## Confirmed Official Schema Surface

The rendered GraphQL docs dump confirms these top-level query families:
- `characterData`
- `gameData`
- `guildData`
- `progressRaceData`
- `rateLimitData`
- `reportData`
- `userData`
- `worldData`
- `reportComponentData`
- `systemReportComponentData`

This is already enough for a substantial CLI without scraping.

### Guild and Progression Surface

Confirmed from `GuildData`, `Guild`, and `GuildZoneRankings`:
- fetch a guild by:
  - `id`
  - or `name + serverSlug + serverRegion`
- list guilds by:
  - page/limit
  - server id
  - server slug + region
- guild fields include:
  - identity
  - server
  - faction
  - description
  - tags
  - competition mode
  - stealth mode
- guild supports:
  - `attendance(...)`
  - `members(...)`
  - `zoneRanking(zoneId: ...)`
- zone ranking supports:
  - `progress`
  - `speed`
  - `completeRaidSpeed`
  with world / region / server rank positions

This makes official guild/ranking workflows first-class.

Current live caveat:
- `attendance(...)` is documented and implemented, but public live queries can still return provider-side internal errors, so it should not be treated as a stable live-contract surface yet

Current report boundary:
- `guild-reports` is now implemented as the convenience guild-scoped history view
- `report-fights` remains on the stable broad fight-list contract
- richer fight-filter and phase-transition workflows are still deferred until the public API behavior is reliable enough to support them honestly

### Character Surface

Confirmed from `CharacterData` and `Character`:
- fetch a character by:
  - `id`
  - or `name + serverSlug + serverRegion`
- list characters for a guild by `guildID`
- character fields include:
  - canonical ID
  - class ID
  - faction
  - guild rank
  - guild memberships
  - level
  - visibility flags
- character supports:
  - `encounterRankings(...)`
  - `zoneRankings(...)`
  - `gameData(specID, forceUpdate)`

Important boundary:
- some ranking/game data is documented as non-frozen and may change without notice
- private-log inclusion is possible on some ranking queries only via the user endpoint

### Report Surface

Confirmed from `ReportData`, `Report`, and `ReportEventPaginator`:
- fetch a report by `code`
- opt into `allowUnlisted` when appropriate
- list reports by:
  - guild identity
  - guild tag
  - user id
  - date range
  - zone id
  - game zone id
  - page/limit
- report fields include:
  - code
  - title
  - owner
  - guild
  - guild tag
  - region
  - visibility
  - archive status
  - zone
  - start/end time
  - revision
  - segments / exported segments
  - phases
- report supports:
  - `events(...)`
  - `fights(...)`
  - `graph(...)`
  - `masterData(...)`
  - `playerDetails(...)`
  - `rankings(...)`
  - `table(...)`

Important pagination and cost behavior:
- event data is paginated via `ReportEventPaginator`
- pagination continues through `nextPageTimestamp`
- `events`, `graph`, and `table` all expose rich filter arguments
- archived-report access is restricted unless the retrieving user has archive access
- practical phase-1 behavior:
  - `report-player-details` is a stable way to inspect role buckets and participants for a report slice before drilling into lower-level event data
  - `report-table` and `report-graph` should accept user-friendly enum-like CLI values and normalize them to GraphQL enum values
  - `report-events` should require a narrowed slice such as `fightIDs`, `encounterID`, or an explicit time window instead of encouraging whole-report pulls
  - even valid narrowed `events(...)` queries can still return `null` event data on some public reports, so the command contract should expose that honestly instead of forcing fake summaries
  - `report-rankings` can legitimately return zero rows for a valid public report slice, so the command contract should surface that plainly

### World and Static Metadata Surface

Confirmed from `WorldData` and `GameData`:
- `worldData` supports:
  - expansions
  - regions
  - subregions
  - servers
  - zones
  - encounters
- `gameData` supports:
  - abilities
  - achievements
  - affixes
  - classes
  - enchants
  - factions
  - items
  - item sets
  - maps
  - NPCs
  - specs
  - zones

Important caching signal:
- the docs explicitly say game data changes only on major game patches and should be cached aggressively
- `Zone.frozen` provides a strong freezing/caching signal for zone-scoped data

### User and Private Surface

Confirmed from `UserData` and `User`:
- `currentUser` exists only on the user endpoint
- user fields include:
  - id
  - name
  - avatar
  - battle tag
  - guilds
  - claimed characters

Important scope boundary:
- several fields explicitly require user authentication with the `view-user-profile` scope
- examples include:
  - `Guild.currentUserRank`
  - user guilds
  - user characters
  - some claimed/private character data

### Race and Live Competition Surface

Confirmed from `ProgressRaceData`:
- `progressRace(...)`
- `detailedComposition(...)`

Important boundary:
- this data is only active during an ongoing race
- the docs say the JSON is not frozen and may change without notice

### Rate Limits

Confirmed from `RateLimitData`:
- `limitPerHour`
- `pointsSpentThisHour`
- `pointsResetIn`

This should be part of `doctor` and auth diagnostics from day one.

## Product Direction

`warcraftlogs` should be an API-first CLI with typed query helpers over the official schema.

The CLI should not start with arbitrary raw GraphQL strings as the main product.
Raw query support may be useful later, but the default UX should be shaped around stable workflows agents actually need.

## Command Families

The full target shape should cover these families.

### Environment and Auth

- `warcraftlogs doctor`
- `warcraftlogs auth login`
- `warcraftlogs auth pkce-login`
- `warcraftlogs auth logout`
- `warcraftlogs auth status`
- `warcraftlogs auth token`
- `warcraftlogs auth client`

These commands should clearly surface:
- current auth mode
- endpoint family in use (`client` vs `user`)
- configured client id
- token expiry
- scope availability
- rate-limit state

### Guild Workflows

- `warcraftlogs guild <region> <realm> <name>`
- `warcraftlogs guild-members <region> <realm> <name>`
- `warcraftlogs guild-attendance <region> <realm> <name>`
- `warcraftlogs guild-rankings <region> <realm> <name>`
- `warcraftlogs guild-reports <region> <realm> <name>`

The ranking command should explicitly support:
- `--zone-id`
- `--difficulty`
- `--size`
- `--kind progress|speed|complete-raid-speed`

### Character Workflows

- `warcraftlogs character <region> <realm> <name>`
- `warcraftlogs character-rankings <region> <realm> <name>`
- `warcraftlogs character-zone-rankings <region> <realm> <name>`
- `warcraftlogs character-game-data <region> <realm> <name>`

Ranking support should include:
- encounter
- zone
- metric
- compare mode
- timeframe
- bracket
- class/spec/role filters
- include-private toggle only when user auth supports it

### Report Workflows

- `warcraftlogs report <code>`
- `warcraftlogs report-fights <code>`
- `warcraftlogs report-events <code>`
- `warcraftlogs report-table <code>`
- `warcraftlogs report-graph <code>`
- `warcraftlogs report-rankings <code>`
- `warcraftlogs report-player-details <code>`
- `warcraftlogs report-master-data <code>`

These commands should support:
- fight id filters
- encounter filters
- difficulty filters
- kill/wipe/trash filters
- source/target/ability filters
- query-language `filterExpression`
- pagination via `nextPageTimestamp`
- translation toggle
- low-bandwidth toggles when the user does not need actor/ability expansion

### Deep Encounter Analytics

This is the next major product-quality target for `warcraftlogs`.

The goal is to make report-link questions safe and repeatable for agents without pushing them into inconsistent manual event calculations.

Typical target questions:
- buff uptime for one or more players in a specific fight
- cast sequences during a pull or sub-window
- damage on a specific wave of enemies
- damage from a specific ability or combination of players
- encounter-phase and wave breakdowns from one report URL

The CLI should own the difficult parts:
- report URL parsing
- fight selection and encounter identity
- actor normalization
- ability normalization
- windowing and pagination
- wave or phase segmentation
- typed summaries with explicit scope and provenance

The agent should not be expected to:
- hand-stitch paginated event streams
- infer wave boundaries from raw timestamps alone
- compute buff uptime from ad hoc event joins
- merge player, ability, and target identity manually across inconsistent slices

#### Planned Encounter Command Family

- `warcraftlogs encounter <report-link-or-code>`
- `warcraftlogs encounter-players <report-link-or-code>`
- `warcraftlogs encounter-buffs <report-link-or-code>`
- `warcraftlogs encounter-casts <report-link-or-code>`
- `warcraftlogs encounter-damage-breakdown <report-link-or-code>`
- `warcraftlogs encounter-waves <report-link-or-code>`
- `warcraftlogs encounter-phases <report-link-or-code>`

These commands should accept:
- report code or full report URL
- `--fight-id`
- `--encounter-id`
- `--start-time`
- `--end-time`
- `--source`
- `--target`
- `--ability`
- `--hostility-type`
- `--difficulty`
- `--kill-only`
- `--wipe-only`

#### Encounter Contract Principles

These commands should:
- require an explicit scope when whole-report analytics would be misleading or too expensive
- expose fight/window provenance in every payload
- surface truncation and pagination honestly
- prefer typed summary rows over raw GraphQL passthrough
- make actor, ability, and target identity stable across follow-up commands

They should not:
- pretend a raw event slice is a stable answer if Warcraft Logs returned partial or null data
- let agents silently compare different windows or fight selections
- flatten source uncertainty into fake precision

#### Planned Summary Shapes

The encounter analytics layer should provide first-class summaries for:
- buff uptime:
  - uptime seconds
  - uptime percent
  - applications
  - refreshes
  - scoped player and fight identity
- cast sequences:
  - ordered casts
  - timestamps relative to pull
  - optional player and window filters
- damage breakdowns:
  - by player
  - by ability
  - by target
  - by target group or wave
- wave and phase summaries:
  - named or inferred segment boundaries
  - segment-local damage/cast/buff summaries
  - explicit confidence when segmentation is inferred instead of directly exposed

#### Implementation Order

Recommended order:
1. `encounter` and report-link parsing
2. `encounter-players`
3. `encounter-buffs`
4. `encounter-casts`
5. `encounter-damage-breakdown`
6. `encounter-waves`
7. `encounter-phases`

This order is deliberate:
- identity and scope first
- then the high-value questions agents most often need
- then the harder segmentation work after actor/ability/window normalization is proven

### Report Listing Workflows

- `warcraftlogs reports --guild ...`
- `warcraftlogs reports --user-id ...`
- `warcraftlogs reports --guild-tag-id ...`
- `warcraftlogs reports --start-time ... --end-time ...`
- `warcraftlogs reports --zone-id ...`
- `warcraftlogs reports --game-zone-id ...`

### World and Static Metadata

- `warcraftlogs expansions`
- `warcraftlogs regions`
- `warcraftlogs subregion <id>`
- `warcraftlogs server <region> <slug>`
- `warcraftlogs zones`
- `warcraftlogs zone <id>`
- `warcraftlogs encounter <id>`
- `warcraftlogs abilities`
- `warcraftlogs items`
- `warcraftlogs npcs`
- `warcraftlogs specs`
- `warcraftlogs classes`

This metadata layer is important for:
- ID discovery
- ranking/report query composition
- reducing hard-coded IDs in agent flows

### Race Workflows

- `warcraftlogs progress-race`
- `warcraftlogs progress-race-guild`
- `warcraftlogs progress-race-composition`

These should stay clearly marked as unstable JSON-backed surfaces.

### Optional Advanced Surface Later

- `warcraftlogs graphql`
- `warcraftlogs saved-query ...`
- `warcraftlogs report-component ...`

These should come only after the typed workflows prove out.

## Output and Modeling Strategy

The CLI should expose stable typed outputs even when the GraphQL server returns `JSON` blobs.

High-value normalized models:
- guild snapshot
- guild ranking snapshot
- character snapshot
- character ranking snapshot
- report snapshot
- report fight summary
- report event page
- report table/graph result wrapper
- world metadata snapshot
- rate-limit snapshot

Every result should preserve:
- provider
- endpoint family (`client` or `user`)
- source object path
- key filters
- pagination state
- freshness timestamp

## Normalization Requirements

Warcraft Logs will need the same input quality standard we now use elsewhere:
- normalize region names conservatively
- normalize realm slugs
- normalize guild and character names without losing case-preserving display forms
- preserve the exact query inputs in output metadata

Because Warcraft Logs supports:
- `serverSlug`
- `serverRegion`
- `guildName`
- `characterName`

we should build on the shared Warcraft normalization layer instead of introducing another incompatible provider-local naming scheme.

## Caching and Freshness

Caching should be explicit and data-family-aware.

Recommended policy:
- `gameData`: cache aggressively
- `worldData`: cache aggressively, especially frozen zone metadata
- guild/character snapshots: short to medium TTL
- rankings: short TTL
- reports and report-derived views: medium TTL unless explicitly bypassed
- race data: very short TTL
- rate-limit data: very short TTL

The CLI should expose freshness in output because:
- ranking data is not frozen
- report event/table/graph data is not frozen
- race data is explicitly unstable during active races

## Testing Strategy

This provider needs a stronger-than-normal test plan.

### Unit and Contract Tests

- GraphQL payload builders
- response parsers
- normalization and endpoint selection
- auth mode selection
- pagination handling
- rate-limit parsing
- report event paginator handling

### Recorded Fixture Tests

Store recorded GraphQL responses for:
- guild lookup
- guild rankings
- character lookup
- character zone rankings
- report summary
- report fights
- report events page
- report table
- world data lookup
- rate-limit response

### Live Tests

Public live tests should cover:
- `doctor`
- `guild`
- `guild-rankings`
- `character`
- `character-zone-rankings`
- `report`
- `report-fights`
- `zones`
- `encounter`
- `rate-limit`

User-auth live tests should be opt-in and separate.

### Auth Tests

Do not require real user auth in default CI.
Instead:
- unit test token storage and selection logic
- unit test client/user endpoint routing
- keep user-auth integration tests manual or explicitly gated

## Phase Plan

### Phase 1: Public API Foundation

1. package skeleton
2. client credentials auth bootstrap
3. `doctor`
4. rate-limit query
5. world metadata:
   - regions
   - servers
   - zones
   - encounters
6. guild lookup
7. character lookup

### Phase 2: Rankings and Report Basics

1. guild rankings
2. character rankings
3. report lookup
4. report listing
5. report fights
6. report master data

### Phase 3: Report Analysis Surface

1. report events
2. report table
3. report graph
4. report player details
5. report rankings
6. event paginator handling
7. query-expression support

### Phase 4: User Auth and Private Data

1. auth code / PKCE flow
2. `auth status`
3. `currentUser`
4. private report access
5. include-private ranking options
6. user guilds and claimed characters

### Phase 5: Race and Advanced Workflows

1. progress race
2. detailed composition
3. optional raw GraphQL / saved query workflows
4. report-component exploration if justified

### Phase 6: Variant-Aware Site Profiles

1. add site-profile routing for:
   - retail
   - classic
   - fresh
2. verify auth and GraphQL endpoint behavior per site profile
3. decide the wrapper expansion-key mapping needed for classic/fresh
4. update wrapper provider metadata so `warcraft --expansion ...` can include Warcraft Logs honestly
5. add live tests for site-profile selection and wrapper expansion behavior

## What Can Reuse Shared Code

- config and credential storage patterns
- cache backends and TTL handling
- HTTP transport
- retry/backoff primitives
- output shaping
- structured error contracts
- shared normalization helpers for region/realm/name handling

## What Should Stay Service-Specific

- GraphQL query documents
- response parsers for Warcraft Logs JSON surfaces
- endpoint-family selection (`client` vs `user`)
- auth-flow details
- report/ranking/query-language ergonomics
- rate-limit interpretation

This provider is still a strong reason not to over-generalize API-first services too early.

## Risks

- GraphQL JSON-heavy surfaces can tempt us into weakly typed pass-through output
- report `events`, `table`, and `graph` are broad enough to become a dumping ground if not shaped carefully
- private/public endpoint mixing can create confusing failures if not surfaced explicitly
- report and ranking data are documented as non-frozen in important places
- race data is explicitly unstable
- archived report access has subscription constraints
- the docs landing page is Cloudflare-protected in browserless fetches, so local rendered docs dumps are useful operationally

## Recommended Product Boundaries

- default to official API integration
- do not scrape ranking/report pages when the GraphQL API already provides the data
- keep raw GraphQL support behind typed commands, not in place of them
- treat private-data workflows as a separate phase with explicit auth diagnostics

## Local Research Inputs

- rendered docs dump: `research/warcraftlogs-docs/`
- rendered docs dump: `research/warcraftlogs-docs-classic/`
- rendered docs dump: `research/warcraftlogs-docs-fresh/`
- dump script: [dump_warcraftlogs_docs.py](/home/auro/code/wowhead_cli/scripts/dump_warcraftlogs_docs.py)

## Source Links

- `https://www.warcraftlogs.com/api/docs`
- `https://www.warcraftlogs.com/v2-api-docs/warcraft/`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
