# Next Feature Plans

## Status

- Overall: in progress
- Last updated: 2026-03-08

## Goal

Plan the next two feature areas after the entity-support cleanup work:

1. stronger local bundle tooling beyond single-guide retrieval
2. better cross-entity discovery and ranking so agents can reach the right entity faster

These two tracks should stay cleanly separated at the command surface, but they can share lower-level scoring and manifest/index primitives.

## Shared Foundation - Cache And Freshness

Before expanding either track too far, the project should treat caching as a deliberate data layer instead of just a small HTTP convenience.

Current state:

- the CLI now has a configurable transport cache with file and optional Redis backends
- the transport cache now has longer default TTLs for stable entity/page fetches
- the CLI now also has a normalized `entity` response cache for repeated `entity` lookups with the same flags
- invalid cache configuration now fails as a structured CLI error instead of a traceback
- it still does not yet have a broader normalized durable entity store that can be reused for guide hydration
- it is useful for immediate retries and nearby repeated lookups
- it is not yet a durable entity store or a full shared cache across agents

### Goals

- keep common entity lookups fast without forcing every repeated request through live Wowhead
- separate short-lived transport caching from reusable local entity storage
- allow shared cache backends in multi-agent environments
- make freshness rules explicit per data class

### Proposed cache layers

1. transport cache
- existing HTTP/text cache
- still useful for raw response reuse
- should become configurable instead of hard-coded

2. entity cache
- normalized `entity` payload cache keyed by expansion, entity type, and entity id
- designed for reuse by `entity`, guide hydration, and future resolver work
- file-backed by default
- optional Redis backend for shared environments

3. bundle-local hydrated store
- durable local entity payloads written into guide bundles when requested
- used for bundle-local exploration even when the global cache is cold

### Proposed TTL defaults

These are starting defaults, not fixed rules:

- search suggestions: 15 minutes
- comment replies / volatile comment subrequests: 15 to 30 minutes
- tooltip and entity page transport cache: 1 hour
- normalized entity cache for common objects like spells, items, NPCs, currencies, factions: 1 hour by default
- guide page transport cache: 1 hour by default
- hydrated bundle entities: refresh on demand, with `--max-age-hours 24` as a reasonable default policy for daily guide refresh workflows

Reasoning:

- a one-hour TTL is usually safe for most entity data and avoids repeated fetch churn
- guides can change daily, so bundle refresh policy should be explicit rather than assuming very long freshness
- transport cache and hydrated local storage should not be forced to share the same TTL

### Backend plan

Start with:

- file-backed transport cache
- file-backed normalized entity cache

Then add optional:

- Redis transport/entity cache backend for shared or concurrent agent environments

Redis support should stay optional and behind configuration, not required for the single-user local CLI path.

### Required design rules

- cache keys must include expansion and the normalized route target
- entity cache entries should store fetch timestamp and expiry metadata
- guide refresh logic should be able to reuse entity cache entries instead of always re-fetching linked entities
- bundle hydration should be able to populate from cache first, then live fetch only on misses/stale entries
- cache invalidation should be TTL-first; manual busting commands can come later if needed

## Current State

### Local bundle tooling

What exists now:

- `guide-export` writes one guide bundle to disk
- `guide-bundle-list` lists exported bundles under a root
- `guide-query` searches one bundle at a time by path or selector

Main gaps:

- no query across many bundles
- no metadata search over bundle titles, classes, expansions, or counts
- no hydrated local store for frequently referenced entities such as spells, items, NPCs, or talents
- guide bundles keep linked-entity references, but not local entity payloads for those references
- no normalized entity cache layer between the short-lived HTTP cache and durable bundle storage
- no bundle refresh/update workflow
- no explicit bundle inspect/stats command
- no root-level index, only directory scans

### Cross-entity discovery and ranking

What exists now:

- `search` returns normalized suggestions with type, id, name, and URL
- `entity` returns lightweight relation previews and follow-up hints
- `entity-page`, `comments`, `guide`, `guide-full`, and `compare` expose richer data

Main gaps:

- `search` ranking is still mostly upstream-order passthrough
- no CLI surface that resolves an ambiguous query to the best next command
- no confidence or rationale fields for search decisions
- no type-aware ranking improvements for common agent cases like quest vs NPC vs item ambiguity
- no related-entity guidance at search time

## Track A - Local Bundle Tooling

### Objective

Make exported bundles feel like a reusable local knowledge layer rather than isolated directories.

### Scope

1. add a root-level bundle index
2. add metadata discovery/search across bundles
3. add normalized local entity caching and reuse for frequently referenced linked entities
4. add bundle-local hydration for selected linked entities
5. add multi-bundle querying
6. add bundle inspect and refresh workflows

### Proposed Deliverables

#### A0. Cache and hydration strategy

Define how transport cache, normalized entity cache, and bundle hydration work together.

Add configurable cache policy inputs, for example:

- `WOWHEAD_CACHE_BACKEND=file|redis`
- `WOWHEAD_CACHE_DIR=...`
- `WOWHEAD_REDIS_URL=...`
- `WOWHEAD_ENTITY_CACHE_TTL_SECONDS=3600`
- `WOWHEAD_GUIDE_CACHE_TTL_SECONDS=3600`

Add an internal normalized entity cache keyed by:

- expansion
- entity type
- entity id
- normalized response shape version

That cache should store compact `entity` payloads, not raw only-transport artifacts.

This becomes the shared reuse layer for:

- repeated `entity` calls
- linked-entity hydration during `guide-export`
- future `resolve`/search enrichment work

#### A1. Linked-entity hydration strategy

Define how much referenced-entity data a guide bundle should carry locally.

Current state:

- guide bundles already store linked-entity references through `linked-entities.jsonl`
- guide bundles already store raw gatherer-derived entity references through `gatherer-entities.jsonl`
- those rows are mostly relation records, not hydrated local entity payloads

Add a bounded enrichment layer, for example:

- `guide-export <guide> --hydrate-linked-entities`
- `guide-export <guide> --hydrate-types spell,item,npc`
- `guide-export <guide> --hydrate-limit 200`

Hydrated entity storage should be separate from the guide manifest body, for example:

- `entities/manifest.json`
- `entities/spell/49020.json`
- `entities/item/19019.json`

The hydrated payload should stay compact and reuse the normalized `entity` contract rather than dumping full `entity-page` blobs by default.

This solves the common case where a guide references the same spells, talents, items, or NPCs repeatedly and agents keep re-fetching them.

Hydration should use the normalized entity cache first, then live fetch only when cache entries are missing or stale.

#### A2. Bundle registry and root index

Add a root-level index file under the bundle root, for example:

- `wowhead_exports/index.json`

It should track:

- bundle path
- dir name
- guide id
- title
- canonical URL
- expansion
- export version
- updated timestamp
- counts summary
- lightweight facets if available, such as class/spec tags later

CLI additions:

- `guide-bundle-index rebuild [--root <dir>]`
- `guide-bundle-list` should prefer the index when present and fall back to directory scanning

#### A3. Bundle inspect/stats

Add a compact inspection command for one bundle:

- `guide-bundle-inspect <bundle-or-selector> [--root <dir>]`

It should expose:

- manifest summary
- available files
- counts
- source breakdown for linked entities
- hydrated-entity counts by type if local entity storage exists
- basic freshness info

This gives agents a clean way to decide whether a local bundle is enough before querying it.

#### A4. Multi-bundle discovery search

Add root-level metadata search:

- `guide-bundle-search "<query>" [--root <dir>]`

This is not full content search. It should match:

- title
- dir name
- guide id
- canonical URL
- later-added tags/facets

Output should include:

- ranked matches
- why the bundle matched
- suggested follow-up command

#### A5. Multi-bundle content query

Add query across many bundles:

- `guide-query-all "<query>" [--root <dir>]`

Capabilities:

- search sections/comments/navigation/linked entities across bundles
- keep bundle context on every match
- support existing filters like `--kind` and `--linked-source`
- rank both within-bundle and across-bundle

This is the feature that turns the local export set into a reusable agent dataset.

#### A6. Bundle refresh/update workflow

Add a way to refresh an existing bundle in place:

- `guide-export <guide> --update`
- or `guide-bundle-refresh <bundle-or-selector>`

Requirements:

- preserve bundle path unless the user asks to relocate it
- update manifest timestamps and export version
- support refresh cadence controls such as `--max-age-hours 24`
- distinguish guide-content refresh from hydrated-entity refresh
- allow incremental hydration so unchanged linked entities are not re-fetched unnecessarily
- allow refresh to consult entity cache before going back to live Wowhead
- keep writes atomic enough to avoid half-written bundles

Recommended additions:

- `guide-export <guide> --update`
- `guide-export <guide> --update --refresh-linked-entities`
- `guide-bundle-refresh <bundle-or-selector> [--root <dir>]`

The manifest/index should record:

- guide fetch timestamp
- last successful refresh timestamp
- last linked-entity hydration timestamp
- per-entity stored-at timestamps for hydrated entity rows when feasible
- cache policy metadata when hydration depends on shared cache configuration

### Acceptance Criteria

- agents can discover bundles without already knowing exact paths
- agents can search bundle metadata across a root
- repeated entity retrieval benefits from a shared normalized cache layer before bundle-local storage
- agents can reuse locally hydrated spell/item/npc/talent data from guide bundles without repeated live fetches
- agents can query content across multiple bundles in one call
- bundles can be refreshed without manual directory management
- root-level listing/search does not degrade badly as bundle count grows

### Risks

- scanning many JSONL files per query will get slow without an index
- adding Redis too early can complicate single-user local setups if configuration is not simple
- hydrating too many linked entities blindly can make exports slow and large
- local entity payloads can go stale faster than the parent guide unless freshness rules are explicit
- cache policy drift between file and Redis backends can make debugging freshness harder
- bundle metadata will drift if index rebuild/update rules are not strict
- multi-bundle ranking can become noisy if bundle-level and record-level scores are mixed casually

### Recommended Sequence

1. A0 cache and hydration strategy
2. A1 linked-entity hydration strategy
3. A2 bundle index
4. A3 bundle inspect
5. A4 metadata search
6. A6 refresh workflow
7. A5 multi-bundle content query

## Track B - Cross-Entity Discovery And Ranking

### Objective

Improve the path from a natural-language query to the right entity or follow-up command.

### Scope

1. improve search result ranking and structure
2. add a resolution-oriented command surface
3. expose reasoning, confidence, and follow-up guidance
4. reuse linked-entity data to guide next steps

### Proposed Deliverables

#### B1. Search contract cleanup

Upgrade `search` so it is not just a thin upstream suggestion wrapper.

Add fields like:

- `score`
- `match_reasons`
- `popularity_rank` or normalized popularity signal
- `best_next_command`
- `best_next_kind`

Keep the payload compact. The goal is not more data, but better decision data.

#### B2. Type-aware reranking

Add internal reranking on top of Wowhead suggestions.

Signals to consider:

- exact title match
- prefix match
- normalized token overlap
- popularity
- type priors for common ambiguous queries
- whether the result has a directly usable entity route

The reranker should stay deterministic and explainable.

#### B3. Resolution command

Add a command that answers: "what should I fetch next?"

Example:

- `resolve "Fairbreeze Favors"`

Output:

- best candidate
- alternates
- why the top candidate won
- suggested follow-up command such as `entity quest 86739`

This is better for agents than asking them to interpret raw search result lists every time.

#### B4. Search narrowing controls

Add options like:

- `search --entity-type quest`
- `search --prefer-type npc`
- `resolve --entity-type item`

This helps agents when they already know the likely shape of the target.

#### B5. Search-time follow-up guidance

For top-ranked results, include bounded hints about what command to run next:

- `entity`
- `guide`
- `entity-page`

Do not include heavy relation previews here. Keep it fast.

#### B6. Entity family and related-target guidance

Use lightweight relation signals to expose better escalation paths after resolution.

Examples:

- quest query should make it obvious when the likely next step is the quest page, comments, or a linked NPC
- item query should make it obvious when a spell or NPC is the more useful follow-up

This should reuse the compact linked-entity preview work already in place.

### Acceptance Criteria

- agents can go from ambiguous natural-language query to a best command in one step
- search results are ranked more usefully than raw upstream order
- ranking decisions are inspectable through compact reasons/confidence fields
- narrowing by desired entity type works without breaking general search
- the top-ranked next step is usually correct for representative quest, NPC, item, spell, and guide queries

### Risks

- type priors can overfit and hide valid alternates
- adding too many explanation fields can bloat the search payload
- a new `resolve` command can overlap awkwardly with `search` if their roles are not clearly separated

### Recommended Sequence

1. B1 search contract cleanup
2. B2 reranking
3. B3 resolve command
4. B4 narrowing controls
5. B5 follow-up guidance
6. B6 related-target guidance

## Shared Design Rules

- keep default payloads compact and agent-oriented
- prefer deterministic heuristics before adding heavier indexing or ML-style scoring
- avoid duplicating fields that only restate URLs or names in multiple places
- keep full exploration on rich commands, not on the discovery surface
- document a clear distinction between:
  - discovery (`search`, `resolve`, `guide-bundle-search`)
  - retrieval (`entity`, `guide`, `guide-query`)
  - exploration (`entity-page`, `guide-full`, multi-bundle deep query)

## Recommended Overall Order

The best order is:

1. Track B foundation: improve `search` and add `resolve`
2. Track A foundation: add bundle index and inspect/search
3. Track A expansion: add multi-bundle content query
4. Track B expansion: add better follow-up and related-target guidance

Reasoning:

- better search/resolve helps every live agent workflow immediately
- bundle indexing should exist before multi-bundle querying, or performance and selection logic will get messy fast
- cache/hydration/update rules should be designed before broader local bundle expansion, or the repo will accumulate stale duplicated entity payloads
- the later steps in both tracks benefit from the same scoring discipline established earlier

## Suggested First Implementation Slice

If we start immediately, the highest-value first slice is:

1. enhance `search` with compact scoring and `best_next_command`
2. add `resolve`
3. define cache configuration, TTL policy, and normalized entity cache layout
4. define linked-entity hydration layout and manifest timestamps
5. add `guide-bundle-index rebuild`
6. add `guide-bundle-search`

That gives agents a cleaner entry point on both live and local workflows without committing to the heaviest multi-bundle query work yet.
