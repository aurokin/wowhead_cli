# Wowhead CLI Plan

## Role In The Monorepo

`wowhead` remains the most mature service CLI and should become the first consumer of shared monorepo libraries.

It should keep its current command surface stable while shared infrastructure is extracted around it.

## Current Strengths

- page extraction and metadata parsing
- guide bundle export and query workflows
- local bundle inspection and refresh
- cache layers and cache inspection
- search and resolve patterns

## What Should Move Out First

The first shared extractions should be infrastructure that is already generic:

- output shaping and `--fields` projection
- structured error helpers
- cache backends and TTL/config plumbing
- shared config and environment handling
- HTTP transport and retry primitives
- bundle index, freshness, and local query primitives
- command routing helpers for root-level `search` and `resolve`

## What Should Stay Wowhead-Specific

- HTML parsing rules
- page JSON extraction
- entity routing quirks
- guide-body extraction
- Wowhead-specific ranking and link normalization

## What Should Wait For A Second Consumer

- article-level content abstractions beyond raw bundle storage
- search and resolve provider interfaces
- follow-up recommendation models

Those should move only after `method` proves they are not just Wowhead behavior with different names.

## Why Wowhead Matters To The Restructure

It is the strongest reference implementation for:
- agent-first CLI output
- local bundle workflows
- cache inspection and repair

But it should not define the shape of every other service. It should validate shared infrastructure, not dictate shared content models.

## Recommended Migration Posture

- keep `wowhead` runnable during the refactor
- move code only when a second consumer exists or the code is obviously generic
- use `wowhead` as the first backend behind `warcraft`

## Source Links

- [Usage](/home/auro/code/wowhead_cli/docs/USAGE.md)
- [Access Methods](/home/auro/code/wowhead_cli/docs/WOWHEAD_ACCESS_METHODS.md)
- [Expansion Research](/home/auro/code/wowhead_cli/docs/WOWHEAD_EXPANSION_RESEARCH.md)
