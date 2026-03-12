---
name: warcraft
description: Route Warcraft data requests through the local `warcraft` wrapper when the source is unclear, then drop to the specific provider CLI once the source is known. Use for cross-provider search, resolve, doctor, and provider passthrough in the Warcraft CLI monorepo.
---

# Warcraft

Use the local `warcraft` command as the root entrypoint when the caller does not already know which provider they need.

## Current Scope

- `warcraft doctor`
- `warcraft search "<query>"`
- `warcraft resolve "<query>"`
- `warcraft wowhead ...`
- `warcraft method ...`
- `warcraft icy-veins ...`

Current provider state:
- `wowhead`: ready
- `method`: ready for guide search, resolve, fetch, export, and local query
- `icy-veins`: ready for guide search, resolve, fetch, export, and local query

## Standard Workflow

1. Source unclear:
- `warcraft resolve "<query>"`
- If unresolved, `warcraft search "<query>"`
2. Source known:
- `warcraft wowhead ...`, `warcraft method ...`, or `warcraft icy-veins ...`
3. Provider confirmed and you need deeper provider behavior:
- use the provider CLI directly, such as `wowhead ...`

## Usage Rules

- Prefer `warcraft` when the service is unknown.
- Prefer `resolve` for a conservative best-next-command recommendation.
- Prefer `search` when you want to inspect candidates across providers.
- Use `doctor` to confirm provider readiness before relying on a provider.
- Preserve provider provenance in your reasoning. Do not describe `warcraft` results as source-neutral.
- Use `method` when you need article-style guide content that is easier to traverse than the equivalent Wowhead guide surface.
- Use `icy-veins` when you need article-style guide content with page-family navigation and table-of-contents structure that may be easier to traverse than the equivalent Wowhead guide surface.

## Examples

```bash
warcraft doctor
warcraft search "frost death knight"
warcraft resolve "fairbreeze favors"
warcraft wowhead guide 3143
warcraft method search "mistweaver monk"
warcraft method guide mistweaver-monk
warcraft icy-veins search "mistweaver monk guide"
warcraft icy-veins guide mistweaver-monk-pve-healing-guide
```

## Provider Handoff

- For Wowhead-specific work, follow [wowhead/SKILL.md](/home/auro/code/wowhead_cli/skills/wowhead/SKILL.md).
