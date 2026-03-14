# WowProgress

## Best For

- guild progression
- character progression summaries
- PvE rankings
- sample-backed guild and leaderboard analytics

## Start With

- exact guild: `wowprogress guild <region> <realm> <name>`
- exact character: `wowprogress character <region> <realm> <name>`
- leaderboard: `wowprogress leaderboard pve <region>`
- discovery: `wowprogress search "<query>"`, `wowprogress resolve "<query>"`

## Effective Use

- use structured `region realm name` input whenever possible
- rely on `sample`, `distribution`, and `threshold` commands for ranking/progression analysis
- use the guild-profile analytics surfaces when the browser would require jumping between leaderboard rows and guild pages

## Boundaries

- better for progression and rankings than for guide or gameplay explanation
- keep analytics answers tied to the sampled slice and freshness metadata
