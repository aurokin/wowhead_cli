## When To Use

Use `warcraftlogs` when the user needs official Warcraft Logs API data instead of a guide or ranking-site summary.

Best fits:
- guild progression from the official source
- character identity lookups on the log platform
- report and fight inspection by report code
- world metadata like regions, servers, zones, and encounters

## Start Here

- health/auth:
  - `warcraftlogs doctor`
  - `warcraftlogs rate-limit`
- world metadata:
  - `warcraftlogs regions`
  - `warcraftlogs expansions`
  - `warcraftlogs server <region> <slug>`
  - `warcraftlogs zones`
  - `warcraftlogs zone <id>`
  - `warcraftlogs encounter <id>`
- direct lookup:
  - `warcraftlogs guild <region> <realm> <name>`
  - `warcraftlogs guild-rankings <region> <realm> <name>`
  - `warcraftlogs character <region> <realm> <name>`
  - `warcraftlogs character-rankings <region> <realm> <name>`
  - `warcraftlogs reports --guild-region ... --guild-realm ... --guild-name ...`
  - `warcraftlogs report <code>`
  - `warcraftlogs report-fights <code>`

## Current Boundaries

- current support is retail/main site only
- current auth is public OAuth client credentials only
- current surface is standalone; wrapper integration is deferred
- current commands use typed payloads, not raw GraphQL passthrough

## Inputs

- credentials are loaded in this order:
  - repo-local `.env.local`
  - XDG config: `~/.config/warcraft/providers/warcraftlogs.env`
  - process environment
- required variables:
  - `WARCRAFTLOGS_CLIENT_ID`
  - `WARCRAFTLOGS_CLIENT_SECRET`
- region/realm inputs still benefit from normalized forms:
  - `us`
  - `illidan`

## Good Consumer Workflows

- guild snapshot:
  - `warcraftlogs guild us illidan Liquid`
- guild progress in a specific zone:
  - `warcraftlogs guild us illidan Liquid --zone-id 38`
- guild rankings in a specific zone:
  - `warcraftlogs guild-rankings us illidan Liquid --zone-id 38 --size 20 --difficulty 5`
- character identity:
  - `warcraftlogs character us illidan Roguecane`
- character rankings, when the API allows them:
  - `warcraftlogs character-rankings us illidan Roguecane --zone-id 38 --difficulty 5 --metric dps --size 20`
- guild report listing:
  - `warcraftlogs reports --guild-region us --guild-realm illidan --guild-name Liquid --limit 10`
- report inspection:
  - `warcraftlogs report <code>`
  - `warcraftlogs report-fights <code> --difficulty 5`

## Notes

- prefer `warcraftlogs` when official log data matters more than convenience summaries
- use `wowprogress` or `raiderio` for their own ranking/profile strengths, not as substitutes for Warcraft Logs report data
- `character-rankings` can return a provider permission error or a provider-side failure for some characters; treat it as useful but less stable than `guild-rankings`
