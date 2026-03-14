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
  - `warcraftlogs server <region> <slug>`
  - `warcraftlogs zones`
  - `warcraftlogs encounter <id>`
- direct lookup:
  - `warcraftlogs guild <region> <realm> <name>`
  - `warcraftlogs character <region> <realm> <name>`
  - `warcraftlogs report <code>`
  - `warcraftlogs report-fights <code>`

## Current Boundaries

- current support is retail/main site only
- current auth is public OAuth client credentials only
- current surface is standalone; wrapper integration is deferred
- current commands use typed payloads, not raw GraphQL passthrough

## Inputs

- credentials must be configured:
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
- character identity:
  - `warcraftlogs character us illidan Roguecane`
- report inspection:
  - `warcraftlogs report <code>`
  - `warcraftlogs report-fights <code> --difficulty 5`

## Notes

- prefer `warcraftlogs` when official log data matters more than convenience summaries
- use `wowprogress` or `raiderio` for their own ranking/profile strengths, not as substitutes for Warcraft Logs report data
