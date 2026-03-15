# RaidPlan CLI Plan

## Why Add It

`raidplan` is worth adding because it covers a planning workflow that the current providers do not:
- boss strategy planning
- mechanic assignments
- shareable encounter plans
- structured raid notes that agents can inspect or help generate

It complements guide and log providers well. Guides explain strategy, logs explain what happened, and RaidPlan can represent what the group plans to do.

## Research Summary

Current signals from the live site:
- the product is built around encounter planning and visual raid assignments
- shareable plan URLs are a core part of the workflow
- the useful unit of data is likely a plan or encounter-specific assignment set rather than a general article page

## Access Model

This should be treated as a planning/workflow provider:
- identify whether public shared plans are readable without auth
- prefer stable public plan URLs and exported plan data where possible
- treat creation/editing as a later phase, not the first milestone
- model raid, boss, difficulty, assignment groups, and notes explicitly

## Likely CLI Shape

- `raidplan doctor`
- `raidplan search "<query>"`
- `raidplan resolve "<query>"`
- `raidplan plan <url-or-id>`
- `raidplan plan-export <url-or-id>`
- `raidplan plan-query <bundle> "<query>"`
- later: `raidplan create` or `raidplan update`

The first useful slice should stay narrow:
- `doctor`
- fetch one public plan
- export/query a local plan bundle

## What Can Reuse Shared Code

- shared output shaping
- shared article-like bundle storage/query if a plan can be normalized into sections and entities
- wrapper provider contract

## What Should Stay Service-Specific

- plan parsing and visual-assignment extraction
- boss/encounter normalization
- any editor or sharing workflow
- any authenticated create/update flow

## What This Service Should Validate

- whether planning/assignment documents fit the existing bundle/query model
- whether encounter-plan queries need their own wrapper query family
- how planning data should connect to guide, sim, and log providers

## Risks

- the most valuable workflows may depend on private or authenticated plans
- visual assignment data may be harder to normalize than guide/wiki content
- creation/editing automation could have very different constraints than read-only plan retrieval

## Source Links

- `https://raidplan.io/`
- [Roadmap](/home/auro/code/warcraft_cli/docs/ROADMAP.md)
