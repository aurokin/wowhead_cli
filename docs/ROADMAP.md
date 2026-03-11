# Roadmap

## Current Priorities

### 1. Cache And Freshness Operations

Goal:
Keep the cache and hydrated local data trustworthy and easy to inspect.

Open work:
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

1. shared Redis visibility and stats commands

## Success Criteria

- agents can find the right local bundle or bundles without manual path hunting
- agents can query across exported guides in one step
- agents can go from an ambiguous query to the correct retrieval command with less guesswork
- cache and hydration freshness are inspectable enough that stale or confusing data can be debugged quickly
