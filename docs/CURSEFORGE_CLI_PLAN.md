# CurseForge CLI Plan

## Why It Matters

`curseforge` is a strong future provider for addon and mod discovery.

For Warcraft-focused agent workflows, it can become the best source for:
- addon lookup
- addon metadata
- author and project pages
- file/version discovery
- changelog and release history
- dependency and compatibility checks

It is especially useful when `warcraft-wiki` provides programming context and `curseforge` provides the real packaged addon surface agents or users actually install.

## Likely Scope

Read-first, metadata-first provider.

Initial target surface:
- `curseforge doctor`
- `curseforge search "<query>"`
- `curseforge resolve "<query>"`
- `curseforge addon <slug-or-id>`
- `curseforge files <slug-or-id>`
- `curseforge changelog <slug-or-id>`

Useful later surfaces:
- addon dependency graph
- release/channel filtering
- game-version compatibility
- author/project exploration

## Implementation Direction

Start conservatively:
- prefer documented/public metadata surfaces when available
- keep project-page parsing provider-specific
- focus on addon metadata, files, and compatibility before any write/auth flows

## Shared vs Local

Likely shared:
- output/error shaping
- cache and HTTP primitives
- wrapper search/resolve contracts

Provider-specific:
- CurseForge search/ranking behavior
- addon/file/changelog parsing
- compatibility/version normalization

## Priority

Backlog only for now.

It is valuable, but not ahead of the current quality passes and non-auth providers already in progress.
