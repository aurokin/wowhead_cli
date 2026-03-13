# Expansion Filtering Plan

## Goal

Add expansion-aware behavior to the `warcraft` wrapper without making the results less trustworthy.

When a caller asks for a specific version of the game, the wrapper must not silently mix in results from providers that do not clearly support that version.

## Why This Matters

Expansion ambiguity is a trust problem, not just a ranking problem.

If a user asks for `wotlk`, `classic`, or `retail`, and the wrapper returns a result from a provider that only publishes retail content, agents will treat the tool as unreliable and users will assume it is broken.

## Non-Goals

- Do not invent a fake universal expansion model for every provider.
- Do not claim expansion support for providers that only happen to mention an expansion in article text.
- Do not weaken the current `wowhead` expansion contract.
- Do not silently coerce an unsupported provider into `retail`.

## Current State

- `wowhead` has a real expansion-routing model and a tested expansion profile system.
- `warcraft` does not expose a global expansion flag.
- Other providers do not yet advertise whether they are:
  - expansion-aware
  - retail-only
  - expansion-ambiguous

## Core Rule

When `warcraft` is given an explicit expansion:

- include only providers that can honestly satisfy that expansion request
- exclude providers that cannot
- report which providers were excluded and why

This should be conservative by default.

## Provider Expansion Modes

Every provider should declare one expansion support mode.

### `profiled`

The provider can actively switch behavior based on the requested expansion.

Example:
- `wowhead`

Expected behavior:
- accepts wrapper expansion context
- routes requests through provider-specific expansion profiles
- can reject unsupported expansion/provider combinations explicitly

### `fixed`

The provider has a known fixed scope, usually `retail`.

Examples right now:
- `method`
- `icy-veins`
- `raiderio`
- `wowprogress`
- `warcraft-wiki`

Expected behavior:
- does not switch content source by expansion
- may declare `supported_expansions = ["retail"]`
- is excluded when the wrapper requests another expansion

### `none`

The provider cannot reliably claim expansion filtering semantics yet.

Possible examples later:
- providers with mixed historical/reference content where version scoping is unclear

Expected behavior:
- excluded from expansion-filtered wrapper search and resolve
- clearly reported as excluded

## Wrapper Behavior

## `warcraft search`

Without `--expansion`:
- current cross-provider fanout stays in place

With `--expansion <x>`:
- include only providers whose expansion mode allows `<x>`
- annotate results with expansion provenance
- return excluded-provider metadata

The wrapper must not silently keep non-matching providers in the result set.

## `warcraft resolve`

Without `--expansion`:
- current behavior stays in place

With `--expansion <x>`:
- only consider providers whose expansion mode allows `<x>`
- preserve expansion context in the chosen match
- if no providers can satisfy the request, fail clearly instead of widening scope

## `warcraft doctor`

Doctor should report:
- whether each provider supports expansion filtering
- the provider expansion mode
- supported expansions for fixed/profiled providers

This gives agents a way to inspect support before making assumptions.

## Initial Provider Matrix

This is the conservative starting point.

| Provider | Mode | Supported expansions | Notes |
| --- | --- | --- | --- |
| `wowhead` | `profiled` | provider-defined profiles | Real expansion routing already exists |
| `method` | `fixed` | `retail` | Current live scope is retail article content |
| `icy-veins` | `fixed` | `retail` | Current live scope is retail guide content |
| `raiderio` | `fixed` | `retail` | Current API use is retail-first |
| `wowprogress` | `fixed` | `retail` | Current supported surfaces are retail-focused |
| `warcraft-wiki` | `none` initially | none | Mixed reference content needs deliberate policy before opt-in |
| `simc` | `none` initially | none | Local analysis is versioned differently and should not be forced into wrapper expansion search yet |

This matrix should be treated as contract, not inference.

## Output Requirements

When expansion filtering is active, wrapper responses should include:

- requested expansion
- included providers
- excluded providers
- exclusion reasons

This is required for trust and debugging.

Suggested exclusion reasons:

- `provider_fixed_to_other_expansion`
- `provider_has_no_expansion_support`
- `provider_does_not_support_requested_expansion`

## Testing Requirements

This feature needs strong contract tests before rollout.

### Wrapper unit tests

- `search` includes only valid providers for a requested expansion
- `resolve` excludes providers that cannot satisfy the expansion
- excluded-provider metadata is always present when filtering is active
- `retail` filtering does not accidentally behave like “no filter”

### Provider contract tests

- provider registrations declare valid expansion metadata
- `wowhead` expansion passthrough remains intact
- fixed providers advertise the right expansion set

### Wrapper live tests

- `warcraft --expansion retail search ...` still returns expected `wowhead` results
- `warcraft --expansion wotlk search ...` only returns `wowhead` results unless more providers are added intentionally
- `warcraft --expansion wotlk resolve ...` never resolves to a retail-only provider

## Rollout Plan

### Phase 1

- document provider expansion modes
- update wrapper/provider contract
- add provider registry metadata only

### Phase 2

- add `warcraft --expansion`
- apply expansion filtering to wrapper `search` and `resolve`
- surface included/excluded provider metadata

### Phase 3

- add doctor reporting for expansion support
- add compact/debug output for expansion filtering decisions

### Phase 4

- review providers individually and promote any that gain real non-retail support

## Risks

### High

- treating retail-only providers as “close enough” when non-retail expansions are requested

### High

- silently mixing expansion-ambiguous results with expansion-aware results

### Medium

- assuming reference providers like `warcraft-wiki` can be expansion-filtered before a real policy exists

### Medium

- exposing `--expansion` before the wrapper also explains excluded providers

## Recommendation

Implement this as a trust feature, not a convenience filter.

The safe default is:
- explicit provider expansion metadata
- conservative filtering
- explicit exclusions
- no silent widening of scope
