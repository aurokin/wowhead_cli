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
  - `warcraftlogs auth status`
  - `warcraftlogs auth client`
  - `warcraftlogs auth token`
  - `warcraftlogs auth whoami`
  - `warcraftlogs auth login --redirect-uri <uri>`
  - `warcraftlogs auth pkce-login --redirect-uri <uri>`
  - `warcraftlogs auth logout`
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
  - `warcraftlogs guild-members <region> <realm> <name>`
  - `warcraftlogs guild-attendance <region> <realm> <name>`
  - `warcraftlogs guild-rankings <region> <realm> <name>`
  - `warcraftlogs character <region> <realm> <name>`
  - `warcraftlogs character-rankings <region> <realm> <name>`
  - `warcraftlogs reports --guild-region ... --guild-realm ... --guild-name ...`
  - `warcraftlogs report <code>`
  - `warcraftlogs report-fights <code>`
  - `warcraftlogs report-player-details <code> --fight-id ...`
  - `warcraftlogs report-master-data <code>`
  - `warcraftlogs report-events <code> --fight-id ...`
  - `warcraftlogs report-table <code> --data-type damage-done --fight-id ...`
  - `warcraftlogs report-graph <code> --data-type damage-done --fight-id ...`
  - `warcraftlogs report-rankings <code> --fight-id ... --player-metric dps`

## Current Boundaries

- current support is retail/main site only
- public OAuth client credentials are the default auth mode
- manual user-auth groundwork now exists for authorization-code and PKCE exchange
- current surface is standalone; wrapper integration is deferred
- current commands use typed payloads, not raw GraphQL passthrough

## Inputs

- credentials are loaded in this order:
  - repo-local `.env.local`
  - XDG config: `~/.config/warcraft/providers/warcraftlogs.env`
  - process environment
- runtime auth state is stored separately:
  - `~/.local/state/warcraft/providers/warcraftlogs.json`
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
- guild roster:
  - `warcraftlogs guild-members us illidan Liquid --limit 5`
- guild attendance history:
  - `warcraftlogs guild-attendance us illidan Liquid --limit 2`
- character identity:
  - `warcraftlogs character us illidan Roguecane`
- character rankings, when the API allows them:
  - `warcraftlogs character-rankings us illidan Roguecane --zone-id 38 --difficulty 5 --metric dps --size 20`
- guild report listing:
  - `warcraftlogs reports --guild-region us --guild-realm illidan --guild-name Liquid --limit 10`
- report inspection:
  - `warcraftlogs report <code>`
  - `warcraftlogs report-fights <code> --difficulty 5`
  - `warcraftlogs report-player-details <code> --fight-id 47`
  - `warcraftlogs report-master-data <code> --actor-type Player`
  - `warcraftlogs report-events <code> --fight-id 47 --limit 100`
  - `warcraftlogs report-table <code> --data-type damage-done --fight-id 47`
  - `warcraftlogs report-graph <code> --data-type damage-done --fight-id 47`
  - `warcraftlogs report-rankings <code> --fight-id 47 --player-metric dps --timeframe historical --compare rankings`

## Notes

- prefer `warcraftlogs` when official log data matters more than convenience summaries
- use `wowprogress` or `raiderio` for their own ranking/profile strengths, not as substitutes for Warcraft Logs report data
- `character-rankings` can return a provider permission error or a provider-side failure for some characters; treat it as useful but less stable than `guild-rankings`
- `guild-members` depends on Warcraft Logs being able to verify the guild roster for that game; treat it as a retail-capable roster surface, not a universal promise across every future site profile
- `guild-attendance` is part of the official schema, but live public queries can still fail with a provider-side internal error; use it when it works, but do not assume the endpoint is fully stable
- `report-player-details` is the easiest way to inspect the participants in a report slice before deeper event/table work
- `report-table` and `report-graph` accept user-friendly enum filters like `damage-done` and normalize them for the API
- `report-events` intentionally requires a narrowed slice such as `--fight-id`, `--encounter-id`, `--start-time`, or `--end-time`
- `report-events` can still return `events: null` for some valid report slices; use it as a typed event-query surface, not a guarantee of non-empty data
- `report-rankings` can legitimately return zero rows for a valid public report slice
- `warcraftlogs auth status` is the first place to check when auth looks wrong; it shows credential source and whether any persisted auth state exists
- `warcraftlogs auth login --redirect-uri ...` and `warcraftlogs auth pkce-login --redirect-uri ...` are two-step flows:
  - first run prints the authorize URL and saves pending state locally
  - second run exchanges the returned `code` and `state`
- `warcraftlogs auth whoami` is the clearest verification that a saved user token actually works against the private user endpoint
- add `--scope view-user-profile` when you want a token that can access current-user profile fields
