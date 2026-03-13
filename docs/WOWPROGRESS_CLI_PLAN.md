# WowProgress CLI Plan

## Status

`wowprogress` is now implemented as a working phase-1 provider.

Current command surface:
- `wowprogress doctor`
- `wowprogress search`
- `wowprogress resolve`
- `wowprogress guild`
- `wowprogress character`
- `wowprogress leaderboard`

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

## What This Service Has Validated

- whether profile and leaderboard payloads can share any contract with `raiderio`
- whether cross-source guild/character resolution belongs in shared code or only in the wrapper
- that a browser-fingerprint HTTP transport is enough for a real no-auth WowProgress provider without adding a browser-runtime dependency

## Risks

- the site is old and filter-heavy, so HTML stability may be inconsistent
- rankings are time-sensitive and may need careful cache policy
- some useful pages may not map cleanly to stable identifiers
- discovery remains intentionally structured because the public search surface is less reliable than direct profile and leaderboard routes

## Source Links

- `https://www.wowprogress.com/`
- `https://www.wowprogress.com/char_level/us`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
