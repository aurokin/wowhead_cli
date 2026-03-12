# Raider.IO CLI Plan

## Status

`raiderio` is the next active provider after `method` and `icy-veins`.

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
- optional app-key support for higher rate limits

## Likely CLI Shape

- `raiderio search-character <name> --region us --realm area-52`
- `raiderio character <region> <realm> <name>`
- `raiderio guild <region> <realm> <name>`
- `raiderio mythic-plus ...`
- `raiderio raiding ...`

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
3. one mythic-plus leaderboard path
4. simple search/resolve support for name and region/realm routing

## Risks

- region/realm/name resolution needs clear CLI ergonomics
- live-tracking endpoints may deserve a later phase
- rate-limit policy needs to be explicit from day one

## Source Links

- `https://raider.io/api`
- `https://raider.io/openapi.json`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
