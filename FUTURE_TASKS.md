# Future Tasks

## Priority 0: API Breakage Detection

1. Add a GitHub Actions matrix that runs live contract tests across multiple expansion profiles in separate jobs for clearer failure localization.
2. Add “schema snapshot” assertions for key command outputs (`search`, `entity`, `entity-page`, `comments`, `compare`) so field-level output drift is caught immediately.
3. Add a parser canary suite against a small set of hard-coded known URLs (one per entity type) to detect HTML/JS shape shifts independent of search results.
4. Add endpoint health metrics to live tests (status code, payload shape, response time buckets) and fail on sustained degradations.
5. Add a `wowhead doctor` command that runs lightweight endpoint checks locally for quick preflight validation.

## Priority 1: Performance and Efficiency

1. Add on-disk HTTP caching with TTL and per-command cache controls.
2. Add in-memory request dedupe for repeated entity/page fetches inside a single command execution.
3. Add adaptive retry/backoff tuned for 429/5xx responses.
4. Add optional concurrency controls for compare/comment hydration workloads.
5. Add streaming output mode for large result sets (`--stream` JSONL).

## Priority 2: Data Quality and Normalization

1. Add richer normalized adapters by entity type (`item`, `quest`, `npc`, `spell`) with stable, agent-friendly fields.
2. Add structured extraction of high-value page blocks (objectives, rewards, drop tables, criteria, etc.) where available.
3. Add source provenance for each normalized field (`href`, `gatherer`, `tooltip`, `comments`) to improve trust and debugging.
4. Add schema versioning in outputs (`schema_version`) with changelog discipline.
5. Add null/unknown semantics guidance and strict typing guarantees for downstream agents.

## Priority 3: Expansion and Routing Support

1. Expand profile mapping for special variants if routing changes (SoD, Anniversary, future classic branches).
2. Add profile auto-detection from URL input and cross-profile fallback lookup strategies.
3. Add command-level policy controls for canonical normalization (global vs command-specific behavior).
4. Add validation checks to ensure generated links always match selected expansion policy.
5. Add tests for profile aliases and migration safety when Wowhead introduces new prefixes.

## Priority 4: Query/Compare UX for Agents

1. Add a multi-step “resolve” flow (`search -> pick best candidate -> fetch`) as a single command for agents.
2. Add a ranking signal bundle for search results (exact match, type match, popularity, expansion relevance).
3. Add compare presets (`--preset gear`, `--preset quest`, etc.) to include the right fields by default.
4. Add graph traversal command for linked entities with depth and relation filters.
5. Add citation packs that include all source URLs and per-claim anchors in one deterministic object.

## Priority 5: Comments Intelligence

1. Add richer comment filters (date ranges, minimum replies, author match, keyword match).
2. Add optional sentiment and consensus summaries over comment sets.
3. Add duplicate/near-duplicate comment detection to reduce noise.
4. Add deterministic “top insights” extraction with citation links for each insight.
5. Add comment freshness scoring and out-of-date weighting.

## Priority 6: CLI Output and Ergonomics

1. Add `--compact-max-chars` to tune truncation limits.
2. Add JSONPath/JMESPath-style selectors as an advanced alternative to dot-path `--fields`.
3. Add output profiles (`--profile agent`, `--profile human`, `--profile debug`) for repeatable payload shapes.
4. Add strict mode to fail when requested fields are missing (`--fields-strict`).
5. Add machine-readable diagnostics metadata (`timings`, `request_count`, `cache_hits`).

## Priority 7: Tooling and Developer Experience

1. Add golden fixture refresh tooling and a documented fixture update workflow.
2. Add contract test data catalog documenting why each canary entity was chosen.
3. Add benchmark script for cold vs warm cache performance.
4. Add lint/type checks in CI (ruff/mypy) and enforce with pre-commit.
5. Add release workflow with semantic versioning and changelog generation.

## Priority 8: Governance and Safety

1. Add explicit rate-limit policy and user-agent strategy documentation.
2. Add legal/robots compliance guardrails and clear operational boundaries.
3. Add usage telemetry hooks (opt-in) for detecting high-failure command patterns.
4. Add redaction options for potentially sensitive output fields in logs.
5. Add failure mode playbook for endpoint or parser breakages.
