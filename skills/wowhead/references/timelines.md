# Timelines

## Best For

- topic history across Wowhead news
- topic history across the Wowhead blue tracker
- bounded date windows and timeline scans

## Start With

- news timeline: `wowhead news [query]`
- blue timeline: `wowhead blue-tracker [query]`
- specific news article: `wowhead news-post <url-or-path>`
- specific blue topic: `wowhead blue-topic <url-or-path>`

## Effective Use

- prefer timeline commands over generic search for news or blue-post research
- use `--date-from` and `--date-to` for bounded windows
- use `--page` and `--pages` for capped scans
- use stable listing-field filters instead of manually scanning result sets:
  - news:
    - `--author`
    - `--type`
  - blue tracker:
    - `--author`
    - `--region`
    - `--forum`
- inspect returned `facets` to understand the matched slice quickly

## Detail Fetches

- `news-post` returns:
  - extracted text
  - sections and section chunks
  - author metadata when present
  - related/recent-post buckets when Wowhead embeds them
- `blue-topic` returns:
  - normalized posts
  - participant summary
  - blue-author summary
  - richer per-post metadata like author page and forum-area slug
