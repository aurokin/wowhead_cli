# Raider.IO

## Best For

- character and guild profile lookup
- Mythic+ runs
- sample-backed Mythic+ analytics

## Start With

- exact character: `raiderio character <region> <realm> <name>`
- exact guild: `raiderio guild <region> <realm> <name>`
- discovery: `raiderio search "<query>"`
- conservative match: `raiderio resolve "<query>"`

## Effective Use

- prefer structured queries like `character us illidan Roguecane`
- use `sample mythic-plus-runs` and `distribution mythic-plus-runs` for analytics questions
- use `sample mythic-plus-players` and `distribution mythic-plus-players` when you need participant-level slices instead of raw run rows
- narrow sampled analytics with filters like `--level-min`, `--contains-spec`, and `--player-region` when you need a tighter slice
- use `threshold mythic-plus-runs` for sampled estimates around score or key level targets
- treat the analytics outputs as sampled leaderboard-derived summaries, not authoritative universal truths
- check the filtering counts when you narrow a slice so you do not over-trust a tiny sample

## Boundaries

- strongest today on Mythic+ and profile data
- not the right primary source for raid-boss comp recommendations
