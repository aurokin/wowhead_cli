# Roadmap

## Current Priorities

### 1. Multi-Bundle Discovery And Query

Goal:
Make exported guide bundles behave like a reusable local knowledge base instead of isolated directories.

Open work:
- add content query across multiple bundles in one command
- add a compact bundle inspect or stats command for one bundle
- add index maintenance and repair flows when `index.json` is missing or stale

Why this matters:
- agents should be able to find the right bundle without already knowing a path
- agents should be able to search across many exported guides without iterating one bundle at a time
- indexed metadata search is now in place, so the next step is cross-bundle content retrieval

### 2. Cross-Entity Discovery And Resolution

Goal:
Make it easier for an agent to go from an ambiguous natural-language query to the correct next command.

Open work:
- improve `search` ranking beyond upstream order
- add a `resolve` command that chooses the best candidate and next command
- add narrowing controls such as preferred or required entity type
- add compact reasoning fields like confidence or match reasons
- add bounded follow-up guidance for when `entity`, `entity-page`, `guide`, or `comments` is the better next step

Why this matters:
- agents still spend work interpreting raw search result lists
- the CLI already has good retrieval surfaces, but the discovery step is still weaker than it should be

### 3. Cache And Freshness Operations

Goal:
Keep the cache and hydrated local data trustworthy and easy to inspect.

Open work:
- expose light cache or hydration inspection commands so agents can understand freshness without opening files directly
- add manual cache or index rebuild or bust workflows for repair cases
- decide whether shared Redis deployments need extra visibility or stats commands

Why this matters:
- the cache stack is now meaningful enough that agents need a way to inspect and repair it
- local data quality matters more as bundle usage grows

## Additional Work Worth Considering

These are lower priority, but still likely useful:
- bundle tagging or lightweight facets such as class/spec when we can derive them reliably
- optional multi-bundle ranking improvements once cross-bundle query exists
- manual guide refresh policies for larger roots with many bundles
- compact export summaries intended specifically for agent prompts

## Recommended Order

1. multi-bundle content query
2. bundle inspect and index repair workflows
3. `search` ranking cleanup
4. `resolve` command
5. search narrowing and follow-up guidance
6. cache and freshness inspection commands

## Success Criteria

- agents can find the right local bundle or bundles without manual path hunting
- agents can query across exported guides in one step
- agents can go from an ambiguous query to the correct retrieval command with less guesswork
- cache and hydration freshness are inspectable enough that stale or confusing data can be debugged quickly
