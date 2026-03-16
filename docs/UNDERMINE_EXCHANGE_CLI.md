# Undermine Exchange CLI

## Why Add It

`undermine-exchange` is worth adding because it fills a market-data gap none of the current providers cover well:
- auction house pricing
- commodity and item market history
- realm and region market context
- trade-good and profession-material discovery

It also complements a future `blizzard-api` provider instead of replacing it. Official Blizzard auction APIs are authoritative for raw data, but Undermine Exchange is useful because it presents market-oriented views and history that agents can reason over directly.

## Research Summary

Current signals from the live site:
- the public site is focused on auction-house and commodity market workflows
- realm/region market views are central to the product
- item-specific pricing and history views appear to be first-class concepts
- the service is currently under maintenance, so implementation should be treated as backlog work until the public surface is stable again

## Access Model

This should be treated as a market-data provider with a cautious public-web-first approach:
- prefer stable public pages or documented data endpoints if available
- model realm, region, faction, commodity/item, and time-range explicitly
- cache carefully because market data is time-sensitive
- do not assume the site has a stable public API until that is confirmed

## Likely CLI Shape

- `undermine-exchange doctor`
- `undermine-exchange search "<query>"`
- `undermine-exchange resolve "<query>"`
- `undermine-exchange item <region> <realm> <item>`
- `undermine-exchange commodity <region> <commodity>`
- `undermine-exchange market <region> [--realm <realm>]`
- `undermine-exchange price-history <region> <item-or-commodity>`

The first useful slice should stay narrower:
- `doctor`
- one item/commodity market lookup
- one history or summary surface

## What Can Reuse Shared Code

- shared HTTP/cache infrastructure
- shared output shaping
- wrapper provider contract
- future market-data query patterns if a second market provider ever exists

## What Should Stay Service-Specific

- auction-house page parsing or endpoint interpretation
- market-summary normalization
- price-history extraction
- any realm/commodity taxonomy specific to the site

## What This Service Should Validate

- whether market-data workflows need their own wrapper query family
- whether auction-house summaries belong in shared code or remain provider-specific
- how to balance official Blizzard auction data against market-oriented community views

## Risks

- the public surface is currently under maintenance
- market data is highly time-sensitive and can make cache tuning tricky
- item/commodity naming may not map cleanly to one universal identifier without official-data crosswalks

## Source Links

- `https://undermine.exchange/`
- [Roadmap](/home/auro/code/warcraft_cli/docs/ROADMAP.md)
