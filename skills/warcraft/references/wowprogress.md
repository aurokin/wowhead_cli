# WowProgress

## Best For

- guild progression
- character progression summaries
- PvE rankings
- sample-backed guild and leaderboard analytics

## Start With

- exact guild: `wowprogress guild <region> <realm> <name>`
- guild history: `wowprogress guild-history <region> <realm> <name>`
- guild ranks across tiers: `wowprogress guild-ranks <region> <realm> <name>`
- exact character: `wowprogress character <region> <realm> <name>`
- leaderboard: `wowprogress leaderboard pve <region>`
- discovery: `wowprogress search "<query>"`, `wowprogress resolve "<query>"`

## Effective Use

- use structured `region realm name` input whenever possible
- direct guild and character lookups normalize common region and realm variants like `na`, `Mal'Ganis`, and `area 52`
- rely on `sample`, `distribution`, and `threshold` commands for ranking/progression analysis
- use `guild-history` when you need the full per-tier raid timeline
- use `guild-ranks` when the question is specifically about final ranks across tiers
- use the guild-profile analytics surfaces when the browser would require jumping between leaderboard rows and guild pages
- check the sampling metadata on leaderboard and guild-profile samples so you know how much of the top slice you actually have
- use guild-profile filters like `--faction`, `--world-rank-max`, or `--encounter` when you need a narrower sampled slice

## Boundaries

- better for progression and rankings than for guide or gameplay explanation
- keep analytics answers tied to the sampled slice and freshness metadata
