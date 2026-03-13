# Method.gg CLI Plan

## Status

`method` is implemented and working, but it is not yet a fully covered Method.gg provider.

Current strengths:
- guide search, resolve, fetch, multi-page guide-full, export, and local bundle query all work for the current supported Method guide/article families
- it validates the shared article bundle and article discovery layers

Current limits:
- discovery is sitemap-rooted and still needs family-aware tuning
- parsing assumes the current Method guide template
- some Method content families are still not intentionally reviewed and classified yet
- premium/login are intentionally out of scope

## Why Method First

`method` is the best first additional CLI because it is close enough to Wowhead's guide workflows to reuse article and bundle infrastructure, but different enough to prove that the shared layer is not secretly Wowhead-only.

## Research Summary

Observed from a live guide page:
- direct HTML fetch works without browser automation for the sampled page
- the page includes `application/ld+json`
- guide metadata is visible in the server-rendered HTML
- section navigation is explicit in page links such as `/guides/mistweaver-monk/talents`
- patch and update metadata are visible in the page body

Sample observations from `https://www.method.gg/guides/mistweaver-monk`:
- title includes guide, section, expansion, and patch context
- `Last Updated: 26th Feb, 2026`
- section content such as `Introduction` is directly present in the HTML

## Access Model

This should be treated as an article-first service:
- fetch HTML
- extract metadata, section nav, author/update information, and section bodies
- export local guide bundles for repeated querying

Current practical access model:
- direct HTML fetch works for the supported guide family
- sitemap-backed discovery works for top-level guide URLs
- section pages are reachable from on-page guide navigation
- premium/login are not needed for the supported guide content

## Likely CLI Shape

- `method search "<query>"`
- `method guide <slug-or-url>`
- `method guide-full <slug-or-url>`
- `method guide-export <slug-or-url>`
- `method guide-query <bundle> "<query>"`

Current supported surface:
- supported root guide/article pages under `/guides/<slug>`
- supported section traversal under `/guides/<slug>/<section>`
- local export/query over supported guide/article pages
- currently validated families include class guides, profession guides, delve guides, reputation guides, and article guides

Explicitly out of scope for now:
- premium/login
- account-linked features
- premium-only workflows
- unsupported index-style roots such as `tier-list` and `world-of-warcraft`

## Supported Scope Target

To call `method` fully functioning, the supported scope needs to be explicit.

Phase-1 supported scope:
- supported root guide/article pages under `/guides/<slug>`
- linked section pages under `/guides/<slug>/<section>` when those pages belong to a supported guide family
- reliable search/resolve for supported guide/article pages
- reliable guide, guide-full, export, and query behavior for supported pages
- explicit structured failure for unsupported index-style roots

Phase-2 supported scope:
- other Method guide families that fit the same article model, if live research confirms stable patterns
- clearer unsupported-surface behavior for content that does not belong to the supported guide families

Out of scope until there is a clear data reason:
- premium/login
- news
- account/profile features
- premium Discord or ad-free flows

## What Can Reuse Shared Code

- bundle storage and indexing
- local query and ranking scaffolding
- cache backends and TTL handling
- HTTP transport and retry primitives
- shared output shaping
- search and resolve interfaces

Validated after milestone 2:
- article bundle export/load/query helpers are now shared in [warcraft_content.article_bundle](/home/auro/code/wowhead_cli/packages/warcraft-content/src/warcraft_content/article_bundle.py)
- article discovery payload helpers are now shared in [warcraft_content.article_discovery](/home/auro/code/wowhead_cli/packages/warcraft-content/src/warcraft_content/article_discovery.py)

## What Should Only Be Shared After `method`

If `method` and `wowhead` both need the same shapes, these become good candidates for `warcraft-content`:

- article metadata contracts
- section and navigation models
- article bundle export/query contracts
- article-oriented resolve and follow-up guidance

Current conclusion:
- bundle export/load/query is proven shared
- article search/resolve payload shaping, follow-up guidance, and multi-page linked-entity merge are also proven shared
- parsing, nav extraction, section extraction, and ranking inputs remain provider-specific

## What Should Stay Method-Specific

- HTML selectors and parsing rules
- guide slug resolution
- section and nav extraction
- guide ranking behavior

Also keep local to `method`:
- sitemap interpretation rules
- supported-content-family decisions
- Method-specific live fallback parsing

## What A Fully Functioning `method` CLI Means

The target is not “support every page on Method.gg.”

It is:
- the supported Method guide families are explicit
- search and resolve are trustworthy within that supported scope
- unsupported Method query families fail clearly at discovery time when we know the matching roots are intentionally out of scope
- guide and guide-full are resilient to normal template variation
- export and query remain stable across supported guide pages
- unsupported Method surfaces fail clearly instead of silently disappearing
- live and recorded tests prove the contract

## Main Gaps

1. Discovery still needs family-aware tuning.
- current search indexes supported root guide URLs from the sitemap
- this is much broader than class guides alone, but ranking still needs to understand guide families better

2. Parser resilience is too template-specific.
- current extraction depends on a small set of exact selectors for navigation, article body, patch, update date, and author
- we need either fallback selectors or explicit failure modes

3. Method-specific live quality gates are light.
- current tests are mostly mocked/parser tests
- we need live contract checks for Method itself, not just wrapper/shared behavior

4. Supported and unsupported Method surfaces need continued refinement.
- we now distinguish supported guide families from unsupported index-style roots, but more family review is still needed

## Quality Gates

The Method provider should be treated as complete only when all of these are true.

Contract gates:
- `doctor`, `search`, `resolve`, `guide`, `guide-full`, `guide-export`, and `guide-query` have stable output contracts
- unsupported Method content returns clear structured errors or stays out of discovery intentionally

Parser gates:
- class/spec guide pages parse correctly
- section navigation parses correctly
- author, patch, and last-updated metadata are handled when present and degrade safely when absent
- linked-entity extraction remains correct when guide sections vary

Bundle gates:
- exported bundles load and query correctly
- section queries, navigation queries, and linked-entity queries all behave consistently
- multi-page guides preserve section/page ordering

Live gates:
- one live class/spec guide contract test
- one live multi-page guide-full contract test
- one live search/resolve test
- one live unsupported-surface test proving intentional exclusion behavior

Fixture gates:
- recorded fixture for a normal class/spec guide
- recorded fixture for a guide section page
- recorded fixture for a page with missing or changed metadata blocks
- recorded fixture for a page shape we intentionally reject or ignore

## Implementation Plan

### Phase 1: Tighten The Current Supported Surface

1. Define the supported Method content families explicitly in code and docs.
2. Add Method-focused live tests for:
- search
- resolve
- guide
- guide-full
3. Add more recorded fixtures for supported and unsupported shapes.
4. Add parser fallback behavior or explicit structured failures for missing metadata/selectors.

Acceptance criteria:
- current supported Method guide/article families are well documented
- live and recorded tests cover the real contract
- parser regressions are more likely to fail tests than silently degrade
- unsupported index roots fail clearly instead of returning empty article payloads

### Phase 2: Improve Discovery And Unsupported-Surface Handling

1. Review Method sitemap and navigation families beyond the currently supported roots.
2. Decide which additional Method content families belong in scope.
3. Add clear unsupported-surface handling for everything else.
4. Expand search/resolve only when the new surface is intentionally supported.

Acceptance criteria:
- search results reflect the supported scope accurately
- unsupported content is excluded or rejected intentionally
- docs describe what Method content the CLI is expected to handle

### Phase 3: Reliability And Performance Pass

1. Review cache TTLs and cache keying for sitemap vs guide pages.
2. Add parser fallback paths where template drift is likely.
3. Review export/query performance on larger guides.
4. Add stronger wrapper/provider integration tests for Method-specific ranking and follow-up behavior.

Acceptance criteria:
- repeat guide fetches are efficient
- guide-full remains stable under common template variations
- wrapper discovery involving Method remains predictable

## Testing Strategy

Keep four layers of coverage:

1. Parser unit tests
- HTML fixtures to verify extraction logic directly

2. CLI contract tests
- mocked Method client responses
- command output shape and error behavior

3. Shared article layer tests
- export/load/query behavior through `warcraft-content`

4. Method live tests
- real site probes for a small stable set of supported pages

## Backlog That Is Explicitly Not In Scope

- premium/login
- account/session support
- premium-only content flows
- account-linked personalization
- non-guide Method features unless they are intentionally added to the supported scope

## First Useful Slice

1. fetch one guide page reliably
2. extract metadata, section nav, and section bodies
3. export one local bundle
4. support section query over that bundle

## Risks

- Method may split guide sections across multiple URLs in ways that differ from Wowhead
- article structure may vary by guide family
- search/discovery may need a different approach from direct slug access
- Method may change guide templates without warning
- Method may expose many content families that look similar but should not all be treated as supported automatically

## Source Links

- `https://www.method.gg/guides/mistweaver-monk`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
