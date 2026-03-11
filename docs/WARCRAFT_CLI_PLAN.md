# Warcraft CLI Plan

## Purpose

`warcraft` should be the root orchestration CLI for this repo.

It is not the place where service-specific logic should live. Its job is to help an agent:
- decide which backing service is most relevant
- route to the right service CLI when the source is already known
- expose shared discovery and environment checks when those concepts become cross-service

## What The Wrapper Should Do

- `warcraft search`: fan out to service-specific search providers where that is practical
- `warcraft resolve`: conservatively pick the best service and next command
- `warcraft <service> ...`: proxy through to `wowhead`, `method`, `raiderio`, `simc`, `raidbots`, or `warcraftlogs`
- expose shared inspection commands only when the concept is truly shared across services

## What The Wrapper Should Not Do

- it should not hide source provenance
- it should not impose one universal data model across article sites, APIs, and local tools
- it should not become the place where parsers, API schemas, or SimC execution logic live

## Recommended First Contract

Start narrow:

- `warcraft wowhead ...`
- `warcraft search ...`
- `warcraft resolve ...`
- `warcraft doctor`

That is enough to validate:
- command routing
- service discovery
- agent-facing ergonomics
- shared environment inspection

The packaging and language boundaries for the wrapper are defined in [REPO_STRUCTURE_AND_PACKAGING.md](/home/auro/code/wowhead_cli/docs/REPO_STRUCTURE_AND_PACKAGING.md).

## Shared Code It Should Reuse

- command routing helpers
- shared output shaping and field projection
- shared cache/environment inspection
- shared search and resolve interfaces

## Shared Code It Should Not Own

The wrapper should consume shared libraries, not become one:

- no service parsers
- no API schema logic
- no SimC execution logic
- no service-specific ranking logic

## Risks

- putting too much real business logic in the wrapper
- hiding which source answered the question
- forcing all services into one command grammar too early

## Source Links

- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
