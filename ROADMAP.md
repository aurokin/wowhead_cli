# Roadmap

## Done

1. Implement `compare` command for multi-entity analysis with:
   - normalized summary fields
   - linked-entity overlap and unique sets
   - comment context and citation links
2. Research Wowhead version routing and codify expansion profiles:
   - profile key/alias mapping
   - path prefix mapping
   - default `dataEnv` mapping
3. Add global expansion selection and wire it through all data commands:
   - `search`, `entity`, `entity-page`, `comments`, `compare`
   - command output now reports `expansion`
   - expansion-aware URLs and tooltip `dataEnv` defaults
4. Add recorded fixture integration tests across expansion profiles:
   - command coverage: `search`, `entity`, `entity-page`, `comments`
   - fixture-backed routing assertions for profile URL and `dataEnv` behavior
5. Add optional canonical normalization mode:
   - global flag: `--normalize-canonical-to-expansion`
   - disabled by default
   - rewrites cross-prefix canonicals to selected expansion path
6. Add live integration contract testing and manual CI execution path:
   - env-gated live suite: `tests/test_live_integration.py`
   - manual GitHub workflow: `.github/workflows/live-wowhead-contracts.yml`
7. Add raw endpoint contract coverage for early breakage detection:
   - `tests/test_live_endpoint_contracts.py`
   - workflow now runs all `-m live` tests
8. Expand live breakage detection beyond items:
   - search-discovered retail `quest`/`npc`/`spell` coverage
   - command-flow contracts for `entity`, `entity-page`, `comments`, and mixed-type `compare`
   - raw endpoint/parser contracts for discovered non-item entities

## Next (Deferred, must do before broader rollout)

1. Review special-case product variants (for example: SoD/Anniversary if they gain dedicated routing) and update profile map.
2. Decide whether canonical cross-prefix redirects (notably some PTR pages) should be preserved verbatim or normalized to requested expansion.
3. Evaluate whether to make normalization behavior command-specific rather than global.

## After

1. Add request caching and rate limiting.
2. Add richer normalized adapters by entity type (`item`, `quest`, `npc`, `spell`).
