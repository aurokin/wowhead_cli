# Method.gg CLI Plan

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

## Likely CLI Shape

- `method search "<query>"`
- `method guide <slug-or-url>`
- `method guide-full <slug-or-url>`
- `method guide-export <slug-or-url>`
- `method guide-query <bundle> "<query>"`

## What Can Reuse Shared Code

- bundle storage and indexing
- local query and ranking scaffolding
- cache backends and TTL handling
- HTTP transport and retry primitives
- shared output shaping
- search and resolve interfaces

## What Should Only Be Shared After `method`

If `method` and `wowhead` both need the same shapes, these become good candidates for `warcraft-content`:

- article metadata contracts
- section and navigation models
- article bundle export/query contracts
- article-oriented resolve and follow-up guidance

## What Should Stay Method-Specific

- HTML selectors and parsing rules
- guide slug resolution
- section and nav extraction
- guide ranking behavior

## First Useful Slice

1. fetch one guide page reliably
2. extract metadata, section nav, and section bodies
3. export one local bundle
4. support section query over that bundle

## Risks

- Method may split guide sections across multiple URLs in ways that differ from Wowhead
- article structure may vary by guide family
- search/discovery may need a different approach from direct slug access

## Source Links

- `https://www.method.gg/guides/mistweaver-monk`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
