# WowProgress CLI Plan

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

This should be treated as a rankings/profile service:
- fetch leaderboard and profile HTML
- extract guild, character, realm, and progression context
- cache leaderboard slices because the pages are expensive and fast-moving

## Likely CLI Shape

- `wowprogress doctor`
- `wowprogress search "<query>"`
- `wowprogress resolve "<query>"`
- `wowprogress guild <name-or-url>`
- `wowprogress character <name-or-url>`
- `wowprogress leaderboard <kind> [filters]`

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

## What This Service Should Validate

- whether profile and leaderboard payloads can share any contract with `raiderio`
- whether cross-source guild/character resolution belongs in shared code or only in the wrapper

## Risks

- the site is old and filter-heavy, so HTML stability may be inconsistent
- rankings are time-sensitive and may need careful cache policy
- some useful pages may not map cleanly to stable identifiers

## Source Links

- `https://www.wowprogress.com/`
- `https://www.wowprogress.com/char_level/us`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
