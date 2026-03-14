# WowProgress CLI Plan

## Status

`wowprogress` is now implemented as a working rankings/profile provider with its first sample-backed analytics primitives.

Current command surface:
- `wowprogress doctor`
- `wowprogress search`
- `wowprogress resolve`
- `wowprogress guild`
- `wowprogress character`
- `wowprogress leaderboard`
- `wowprogress sample`
- `wowprogress distribution`
- `wowprogress threshold`

Current quality notes:
- structured guild and character lookups are the primary search and resolve path
- direct route probes now treat canonical WowProgress realm forms like `US-Area 52` as exact matches for structured inputs like `area-52`
- exact short-name structured queries like `guild us area-52 xD` now resolve confidently instead of failing low-score conservatively
- structured realm normalization now tolerates some natural multi-word forms like `area 52`
- trailing unsupported qualifier terms are excluded explicitly and surfaced back as query-normalization metadata
- live guild and character retrieval coverage now validates rank extraction as well as basic profile parsing
- provider-local live coverage now exists for structured search, resolve, and leaderboard contracts
- PvE leaderboard sampling, distributions, and threshold estimates now expose freshness, provenance, and explicit caveats instead of pretending to be direct smart-answer surfaces

## Why Add It

`wowprogress` adds a different kind of value from guide and wiki sources: guild progression, character rankings, roster context, and recruitment-style profile discovery.

It overlaps somewhat with `raiderio`, but not enough to skip. The overlap is useful because it will force us to prove which profile/ranking abstractions are genuinely shared.

## Research Summary

Observed from live pages:
- direct HTML fetch works without browser automation
- current raid progression is visible in server-rendered guild ranking pages
- character ranking pages expose many sortable profile-style metrics
- the site is heavily leaderboard-oriented and filter-heavy

Sample observations from `https://www.wowprogress.com/` and `https://www.wowprogress.com/char_level/us`:
- current raid progression is listed directly in HTML
- guild, realm, and region context are visible
- character pages and ranking pages expose progression-style metrics and profile links

## Access Model

This is now treated as a rankings/profile service using browser-fingerprint HTTP fetches:
- fetch guild, character, and leaderboard HTML directly
- extract guild, character, realm, and progression context
- cache leaderboard and profile pages because the pages are expensive and fast-moving
- use the site-native `u_search` route conservatively for structured guild/character discovery
- avoid promising broad free-text discovery while the public search surface remains constrained

## Current CLI Shape

- `wowprogress doctor`
- `wowprogress search "<query>"`
- `wowprogress resolve "<query>"`
- `wowprogress guild <region> <realm> <name>`
- `wowprogress character <region> <realm> <name>`
- `wowprogress leaderboard pve <region> [--realm <realm>]`
- `wowprogress sample pve-leaderboard --region <region> [--realm <realm>]`
- `wowprogress distribution pve-leaderboard --region <region> --metric <metric> [--realm <realm>]`
- `wowprogress threshold pve-leaderboard --region <region> --metric <metric> --value <value> [--realm <realm>]`

## What Can Reuse Shared Code

- cache and HTTP infrastructure
- shared output shaping
- wrapper provider contract
- search and resolve payload contracts

## What Should Stay Service-Specific

- HTML parsing rules
- filter and ranking semantics
- guild/character identifier resolution
- site-specific leaderboard normalization
- leaderboard analytics semantics

## What This Service Has Validated

- whether profile and leaderboard payloads can share any contract with `raiderio`
- whether cross-source guild/character resolution belongs in shared code or only in the wrapper
- that a browser-fingerprint HTTP transport is enough for a real no-auth WowProgress provider without adding a browser-runtime dependency
- that leaderboard analytics can stay useful and trustworthy when they are framed as sampled primitives instead of fake direct answers

## Risks

- the site is old and filter-heavy, so HTML stability may be inconsistent
- rankings are time-sensitive and may need careful cache policy
- some useful pages may not map cleanly to stable identifiers
- discovery remains intentionally structured because the public search surface is less reliable than direct profile and leaderboard routes

## Source Links

- `https://www.wowprogress.com/`
- `https://www.wowprogress.com/char_level/us`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
