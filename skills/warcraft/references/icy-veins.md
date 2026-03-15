# Icy Veins

## Best For

- spec guides and broad guide-family navigation
- class hubs, role guides, and spec subpages

## Start With

- discovery: `icy-veins search "<query>"`
- conservative match: `icy-veins resolve "<query>"`
- fetch: `icy-veins guide <slug>`
- deeper content: `icy-veins guide-full <slug>`
- local export/query: `icy-veins guide-export ...`, `icy-veins guide-query ...`

## Effective Use

- use Icy Veins when the caller needs structured guide families rather than a single direct page
- for broad class or role queries, let `resolve` pick the hub first
- for narrow subpage questions, search terms like `easy mode`, `rotation`, `stat priority`, or `mythic+ tips` work well
- explicit embedded Wowhead talent-calc links show up as `build_references`; guide slugs and titles are not treated as build evidence by themselves
- additive `analysis_surfaces` highlight comparison-relevant guide topics without replacing raw guide content

## Validated Families

- class hubs
- role guides
- spec guides
- easy mode
- leveling
- PvP
- builds/talents
- rotation
- stat priority
- gems/enchants/consumables
- spell summary
- resources
- macros/addons
- Mythic+ tips
- simulations
- raid guides
- expansion guides
- special-event guides

## Boundaries

- patch notes, hotfixes, and news-like queries return `scope_hint` rather than guide results
