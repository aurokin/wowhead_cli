# Method

## Best For

- supported Method.gg guide/article families with simple article structure
- article fetch, export, and local query

## Start With

- discovery: `method search "<query>"`
- conservative match: `method resolve "<query>"`
- fetch: `method guide <slug>`
- deeper content: `method guide-full <slug>`
- local export/query: `method guide-export ...`, `method guide-query ...`

## Effective Use

- use Method when an article-style guide is easier to traverse than a Wowhead guide page
- prefer `guide` before `guide-full`
- expect explicit support boundaries; unsupported families return structured failures or `scope_hint`
- explicit embedded Wowhead talent-calc links show up as `build_references`; there is no slug/title-based guide hardlinking
- additive `analysis_surfaces` highlight comparison-relevant guide topics without replacing raw guide content

## Validated Families

- class guides
- profession guides
- delve guides
- reputation guides
- article guides

## Boundaries

- not all Method.gg content is intentionally supported
- tier-list and index-style roots are intentionally excluded
