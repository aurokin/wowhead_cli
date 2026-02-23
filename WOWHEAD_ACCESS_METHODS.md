# Wowhead CLI Research Findings and Recommendations

Date: 2026-02-19  
Repository: `wowhead_cli`

## Objective

Identify practical, non-browser ways for an AI-agent CLI to query Wowhead, compare entities, traverse linked entities, include comments, and generate source citations.

## Repositories Analyzed

Cloned under `research/wowhead-clis/` (gitignored):

- `GatherMate2Miner` (`Nevcairiel/GatherMate2Miner`)
- `WowHead_Quest` (`mangostools/WowHead_Quest`)
- `wowhead_scraper` (`BreakBB/wowhead_scraper`)
- `wowhead-scraper` (`DBFBlackbull/wowhead-scraper`)
- `WowheadLootExtractor` (`menevia16a/WowheadLootExtractor`)
- `WowheadRipper` (`Sovak/WowheadRipper`)
- `WowheadSearch` (`TomasRytir/WowheadSearch`)

## How Existing Tools Access Wowhead

### 1) Direct page fetch + HTML/regex parsing

Most tools fetch entity pages like `https://www.wowhead.com/item=...` and parse:

- HTML headings/blocks (`h1`, info tables, infoboxes)
- Embedded JS payloads:
  - `$.extend(g_items[...], {...})`
  - `new Listview({... data: [...] ...})`
  - `WH.Gatherer.addData(...)`

Used by:

- `GatherMate2Miner`
- `WowHead_Quest`
- `wowhead_scraper`
- `wowhead-scraper`
- `WowheadLootExtractor`
- `WowheadRipper`

### 2) Embedded Listview extraction (high-value)

`WowheadLootExtractor` and `WowheadRipper` specifically target `new Listview(...)` blocks, which is a strong pattern for:

- drops
- contains
- fishing
- related table-like entity data

### 3) Browser-launch only (not data integration)

`WowheadSearch` opens `https://www.wowhead.com/wotlk/search?q=%query%` in browser; no structured data extraction.

## Wowhead Endpoints and Tooling Found

### Official / documented-facing

- Tooltip integration docs:
  - `https://www.wowhead.com/tooltips`
  - Uses `https://wow.zamimg.com/js/tooltips.js`
  - Supports `data-wowhead` parameters and embedding behavior

- OpenSearch:
  - `https://www.wowhead.com/opensearch/description?v=3`
  - Suggestion endpoint:
    - `https://www.wowhead.com/search/suggestions-open-search?q=<query>`

- Legacy item XML feed:
  - `https://www.wowhead.com/item=<id>&xml`
  - Returns structured XML, tooltip HTML, JSON fragments, and canonical link
  - Verified for items; not generally available for all entity types via same pattern

### Undocumented but useful in practice

- Rich suggestions endpoint:
  - `https://www.wowhead.com/search/suggestions-template?q=<query>`
  - Returns typed, ranked result objects

- Tooltip JSON endpoint:
  - `https://nether.wowhead.com/tooltip/<type>/<id>?dataEnv=<env>`
  - Example types that worked: `item`, `quest`, `npc`, `spell`, `mount`, `recipe`, `battle-pet`

- Comment reply endpoint:
  - `https://www.wowhead.com/comment/show-replies?id=<commentId>`

- Page-embedded comment dataset:
  - `var lv_comments0 = [...]`
  - Bound to `new Listview({ id: 'comments', data: lv_comments0, template: 'comment' })`

### Not found as public API

- `https://www.wowhead.com/api` -> 404
- `https://www.wowhead.com/developers` -> 404

No official, documented general-purpose REST API for full entity data was found.

## Comment Data Findings (Important for Agent UX)

- A large first page/set of comments is embedded directly in entity HTML as `lv_comments0`.
- Reply expansion is fetched via `/comment/show-replies`.
- Comment template JS references additional comment mutation endpoints (vote, edit, delete, report, etc.), but these are mostly authenticated/user-action oriented.
- This makes a read-focused CLI feasible without browser automation.

## Comparison of Access Methods

| Method | Speed | Coverage | Comment support | Comparison-friendly | Stability risk | Notes |
|---|---|---|---|---|---|---|
| Full page HTML + embedded JS parse | Medium | High | High | High | Medium | Best overall data richness |
| `nether.wowhead.com/tooltip/<type>/<id>` | High | Medium | Low | Low-Medium | Medium-High | Great for quick summary payloads |
| `search/suggestions-template` | High | Search only | None | Medium | Medium | Best entrypoint for query->entity candidates |
| Item `&xml` feed | High | Item-centric | None | Medium | Medium | Good fallback for item details |
| Browser automation | Low | High | High | High | High | Avoid per requirements |

## Recommendations

### Recommended primary strategy

Build the CLI around **direct HTTP + parser pipeline**, not browser automation:

1. Use `search/suggestions-template` for fast candidate discovery.
2. Fetch canonical entity page for selected IDs.
3. Parse embedded structured payloads (`g_*`, `Listview`, `WH.Gatherer.addData`).
4. Parse comments from `lv_comments0`, fetch missing replies via `/comment/show-replies`.
5. Emit canonical citation links for:
   - entity page
   - specific related entity links
   - comment anchors (`#comments:id=<commentId>`)

### Why this best matches the target CLI

- Supports multi-entity compare naturally.
- Supports linked-entity traversal (source chains, dropped-by, contains, rewards).
- Supports comments as first-class context.
- Avoids browser runtime overhead.

## Suggested CLI Capabilities (Product Shape)

- `search <query>`: typed candidates with canonical URLs
- `entity <type> <id>`: normalized core payload + linked entities
- `comments <type> <id>`: top comments + filters/sorting
- `compare <entityA> <entityB> ...`: field-wise diff + contextual links
- `links <type> <id>`: source/citation URL pack for downstream agents

## Engineering Guidance for Build Phase

- Add request throttling and retries (429-aware).
- Add local caching (raw HTML + parsed JSON).
- Treat parsers as versioned adapters; keep extraction logic modular.
- Validate entity and comment citations are stable and reproducible.
- Keep output schema deterministic for downstream AI tools.

## Risks and Caveats

- Wowhead markup and internal JS shapes can change.
- Some useful endpoints appear undocumented and may change.
- `robots.txt` includes aggressive crawler restrictions for some bot user agents; operational policy and access behavior should be reviewed before production-scale crawling.

## Bottom Line

For an AI-agent CLI, the highest-leverage path is:

- **Search via suggestions endpoint**
- **Retrieve rich data from entity pages and embedded JS**
- **Use `lv_comments0` + comment reply endpoint for community context**
- **Generate canonical links for every output artifact**

This gives the strongest balance of speed, depth, and non-browser operation.
