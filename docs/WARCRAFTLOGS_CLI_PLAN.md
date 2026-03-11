# Warcraft Logs CLI Plan

## Why Warcraft Logs Needs Strong Isolation

`warcraftlogs` is clearly an API-first integration, but it is also the most auth- and query-heavy service in this group.

It should be planned as a dedicated API client with typed query helpers rather than as a generic HTTP integration.

This is the strongest candidate for a language exception if one becomes necessary. A TypeScript package is acceptable here if it stays isolated behind the service CLI boundary described in [REPO_STRUCTURE_AND_PACKAGING.md](/home/auro/code/wowhead_cli/docs/REPO_STRUCTURE_AND_PACKAGING.md).

## Research Summary

Observed from official documentation entry points:
- official docs live at `https://www.warcraftlogs.com/api/docs`
- the official docs describe OAuth 2.0 flows
- the official docs describe a GraphQL-based v2 API
- official docs distinguish public client access from user-authorized access
- browserless access to the docs entry points was Cloudflare-challenged during planning research, which is an operational signal worth preserving

## Access Model

This should be an API-first, auth-heavy service:
- OAuth client management
- token acquisition and refresh
- typed GraphQL query helpers
- reusable report, fight, actor, and ranking query patterns

## Likely CLI Shape

- `warcraftlogs auth ...`
- `warcraftlogs report <code>`
- `warcraftlogs query <saved-query>`
- `warcraftlogs actor ...`
- `warcraftlogs rankings ...`

## What Can Reuse Shared Code

- auth/config persistence
- cache backends and TTL policy
- HTTP transport and retry behavior
- output shaping

## What Should Stay Deeply Service-Specific

This service is a good reason not to over-generalize:

- GraphQL query shape
- report/fight/actor vocabulary
- auth scopes and access levels
- saved-query ergonomics

## First Useful Slice

1. auth bootstrap and token storage
2. one public GraphQL query path
3. one report-oriented helper
4. strong environment diagnostics for credentials and scopes

## Risks

- the query surface is broad enough to overwhelm a weak initial CLI
- schema-aware tooling matters more here than on any other service
- this integration may need a more deliberate test strategy because of auth and private/public boundaries

## Source Links

- `https://www.warcraftlogs.com/api/docs`
- `https://classic.warcraftlogs.com/v2-api-docs/warcraft`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
