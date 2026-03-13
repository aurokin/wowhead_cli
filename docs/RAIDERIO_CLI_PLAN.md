# Raider.IO CLI Plan

## Status

`raiderio` is now implemented as a phase-1 provider.

Current command surface:
- `raiderio doctor`
- `raiderio search`
- `raiderio resolve`
- `raiderio character`
- `raiderio guild`
- `raiderio mythic-plus-runs`

Current quality notes:
- structured `region realm name` queries now use direct profile probes before falling back to the weaker site search route
- live search/resolve quality is materially better for exact guild and character lookups
- leaderboard, broader Mythic+ surfaces, and richer profile workflows are still later-phase work

## Why Raider.IO Is Different

`raiderio` should be treated as an API-first integration, not a scraping project.

The official developer API is documented and exposes an OpenAPI surface. That should be the primary integration path.

## Research Summary

Observed from official developer materials:
- developer docs are served from `https://raider.io/api`
- OpenAPI is published at `https://raider.io/openapi.json`
- the sampled OpenAPI document reported version `0.62.5`
- the sampled OpenAPI document exposed 35 paths
- visible endpoint groups include character, guild, raiding, mythic plus, and live tracking
- the official API description states unauthenticated requests are limited to 200 requests per minute
- the official description prohibits automated scraping beyond the published endpoints

## Access Model

This should be an API-first service:
- typed request builders
- response normalization where helpful
- cache-aware profile and leaderboard fetches
- unauthenticated phase 1 support first
- optional app-key support deferred to a later phase

## Likely CLI Shape

- `raiderio doctor`
- `raiderio search "<query>"`
- `raiderio resolve "<query>"`
- `raiderio character <region> <realm> <name>`
- `raiderio guild <region> <realm> <name>`
- `raiderio mythic-plus-runs ...`

## What Can Reuse Shared Code

- HTTP client and retry primitives
- cache backends and TTL handling
- output shaping
- auth/config handling where needed

## What Should Not Be Forced Into Shared Models

- Raider.IO endpoint shapes should not be turned into a universal Warcraft entity contract
- Raider.IO ranking logic should not be treated as the generic search ranking layer for the repo

## What Should Stay Raider.IO-Specific

- endpoint catalog
- typed field selection
- rate-limit aware request policy
- response models and ranking rules

## First Useful Slice

1. character profile lookup
2. guild profile lookup
3. one mythic-plus runs path
4. `doctor`
5. conservative search/resolve built on the live site search surface

## Deferred To Later Phases

- app-key / elevated-rate-limit support
- stronger realm/region-aware discovery heuristics if the current search surface proves too shallow
- broader leaderboard coverage
- live-tracking endpoints

## Risks

- region/realm/name resolution needs clear CLI ergonomics
- live site search is usable now, but it is not part of the documented `/api/v1` developer surface
- auth/app-key support should not distort the initial provider shape
- rate-limit policy needs to be explicit from day one

## Source Links

- `https://raider.io/api`
- `https://raider.io/openapi.json`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
