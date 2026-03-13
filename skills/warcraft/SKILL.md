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
- `warcraft raiderio ...`
- `warcraft warcraft-wiki ...`
- `warcraft wowprogress ...`
- `warcraft simc ...`

Current provider state:
- `wowhead`: ready
- `method`: ready for supported guide/article-family search, resolve, fetch, export, and local query
- `icy-veins`: ready for guide search, resolve, fetch, export, and local query
- `raiderio`: ready for search, resolve, direct character, guild, and Mythic+ runs lookups
- `warcraft-wiki`: ready for article search, resolve, fetch, export, and local query
- `wowprogress`: ready for structured search, conservative resolve, direct guild, character, and PvE leaderboard lookups
- `simc`: ready for local repo inspection, repo resolution/config, managed checkout, version, spec-files, decode-build, APL list/graph/talent inspection, action tracing, prune/branch/intent analysis, branch comparison, analysis packets, first-cast timing, log inspection, and sync/build/run, with `search` and `resolve` structured `coming_soon`

## Standard Workflow

1. Source unclear:
- `warcraft resolve "<query>"`
- If unresolved, `warcraft search "<query>"`
2. Source known:
- `warcraft wowhead ...`, `warcraft method ...`, `warcraft icy-veins ...`, `warcraft raiderio ...`, `warcraft warcraft-wiki ...`, `warcraft wowprogress ...`, or `warcraft simc ...`
3. Provider confirmed and you need deeper provider behavior:
- use the provider CLI directly, such as `wowhead ...`

## Usage Rules

- Prefer `warcraft` when the service is unknown.
- Prefer `resolve` for a conservative best-next-command recommendation.
- Prefer `search` when you want to inspect candidates across providers.
- Use `warcraft --expansion <profile>` when version-specific correctness matters.
- Use `doctor` to confirm provider readiness before relying on a provider.
- Preserve provider provenance in your reasoning. Do not describe `warcraft` results as source-neutral.
- Use `method` when you need article-style guide content that is easier to traverse than the equivalent Wowhead guide surface.
- Treat `method` as scoped to currently supported guide/article families, not all Method.gg content.
- Validated Method families currently include class guides, profession guides, delve guides, reputation guides, and article guides.
- If a Method query clearly targets an unsupported family like tier lists, expect a `scope_hint` with no search candidates.
- If a Method root acts like an index surface rather than a real guide/article page, expect a structured `unsupported_guide_surface` failure instead of empty content.
- Use `icy-veins` when you need article-style guide content with page-family navigation and table-of-contents structure that may be easier to traverse than the equivalent Wowhead guide surface.
- `icy-veins` now intentionally supports more than just spec landing guides: class hubs, role guides, easy mode, leveling, PvP, spec subpages, raid guides, and special-event guide pages like Remix or Torghast.
- validated Icy Veins families now explicitly include PvP and stat-priority pages in addition to the broader guide families above.
- validated Icy Veins subpage coverage now also includes resources, macros/addons, Mythic+ tips, and simulations.
- validated Icy Veins subpage coverage now also includes leveling, builds/talents, rotation, gems/enchants/consumables, and spell-summary pages.
- For broad class or role queries like `monk guide` or `healing guide`, prefer letting `icy-veins resolve` pick the class hub or role guide before jumping straight to a spec page.
- If an Icy Veins query is really about patch notes, class changes, hotfixes, or news, expect a `scope_hint` instead of guide candidates.
- Use `raiderio` when you already know the region, realm, and character or guild you want, and need direct profile or Mythic+ run data.
- For exact Raider.IO lookups, prefer structured queries like `character us illidan Roguecane` or `guild us illidan Liquid`; the provider now probes direct profile surfaces for those.
- Use `warcraft-wiki` when you need general reference material, lore, systems pages, or addon/API documentation.
- Use `wowprogress` when you have or can supply structured `region realm name` inputs and need progression, roster, or leaderboard context rather than guide content.
- Use `simc` when you need local SimulationCraft repo inspection, build decoding, or direct binary execution against a local profile.
- Use `simc repo` when you need to understand or change which local SimulationCraft checkout is active.
- Use `simc checkout` when you want the CLI to manage a local SimulationCraft checkout under the XDG data root.
- Use `simc` for readonly APL inspection questions before escalating to a real sim run.
- Use `simc apl-prune`, `apl-branch-trace`, and `apl-intent` when you need conservative reasoning about likely list flow without running the simulation.
- Use `simc analysis-packet` when you want the compact agent-facing summary instead of assembling branch and intent outputs manually.
- Use `simc first-cast` and `simc log-actions` when you need to validate opener timing against real SimC execution instead of relying only on static APL reasoning.
- `warcraft search` now uses a tunable wrapper ranking layer on top of provider scores, with query-intent, provider-family, and result-kind boosts.
- the wrapper ranking layer also includes provider-specific intent boosts, for example character queries favoring `raiderio` and guild queries favoring `wowprogress`.
- inspect `wrapper_ranking` in wrapper results when ranking behavior matters.
- `warcraft resolve` does not just trust provider order; it prefers the strongest resolved provider result after applying the same wrapper ranking layer.
- use `warcraft search --compact --ranking-debug` or `warcraft resolve --compact --ranking-debug` when you want the ranking explanation without the full per-provider payloads.
- use `warcraft search --compact --expansion-debug` or `warcraft resolve --compact --expansion-debug` when you need a compact provider eligibility snapshot for expansion filtering.
- for narrow cases like leaderboard queries, the wrapper may emit a synthetic direct-route candidate even when the provider does not expose a native search surface for that exact query family.
- wrapper expansion filtering is conservative:
  - `wowhead` is currently the only profiled expansion-aware provider
  - `method`, `icy-veins`, `raiderio`, and `wowprogress` are treated as retail-only when wrapper expansion filtering is active
  - `warcraft-wiki` and `simc` are excluded from wrapper expansion-filtered `search` and `resolve` for now
  - inspect `included_providers` and `excluded_providers` when `--expansion` is set
  - use `--expansion-debug` when you need the full provider support snapshot in compact mode
  - do not assume `warcraft --expansion ... <provider> ...` will silently work for every provider; unsupported combinations now fail clearly

## Examples

```bash
warcraft doctor
warcraft --expansion wotlk search "thunderfury"
warcraft search "frost death knight"
warcraft resolve "fairbreeze favors"
warcraft wowhead guide 3143
warcraft method search "mistweaver monk"
warcraft method guide mistweaver-monk
warcraft icy-veins search "mistweaver monk guide"
warcraft icy-veins guide mistweaver-monk-pve-healing-guide
warcraft raiderio character us illidan Roguecane
warcraft warcraft-wiki article "World of Warcraft API"
warcraft wowprogress guild us illidan Liquid
warcraft simc doctor
warcraft simc spec-files mistweaver
warcraft simc apl-talents /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc
warcraft simc apl-intent /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
warcraft simc analysis-packet /home/auro/code/simc/ActionPriorityLists/default/monk_mistweaver.simc --targets 1
warcraft simc first-cast /home/auro/code/simc/profiles/MID1/MID1_Monk_Windwalker.simc tiger_palm --seeds 1 --max-time 20
```

## Provider Handoff

- For Wowhead-specific work, follow [wowhead/SKILL.md](/home/auro/code/wowhead_cli/skills/wowhead/SKILL.md).
