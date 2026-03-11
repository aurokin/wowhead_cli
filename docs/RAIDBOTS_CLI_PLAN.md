# Raidbots CLI Plan

## Why Raidbots Should Be Staged Carefully

`raidbots` is popular and useful, but it should not be planned like a normal public data API.

The strongest confirmed workflow is built around SimulationCraft input and simulation results, so this CLI should likely be introduced after `simc` rather than before it.

## Research Summary

Observed from official support content:
- Raidbots recommends the SimulationCraft addon and `/simc` workflow
- the official support docs state the Blizzard Armory API is often out of date
- official support explicitly says Raidbots uses SimulationCraft under the hood
- support content also makes it clear that spec support is constrained by SimulationCraft support

## Access Model

The safest high-level model is:
- workflow helper around SimulationCraft input
- result/report parsing where stable report URLs or exports exist
- cautious evaluation of any deeper automation later

## Likely CLI Shape

Initial scope should stay narrow:
- `raidbots explain-input`
- `raidbots result <url-or-id>`
- `raidbots inspect-report <url-or-id>`

Submission automation should be a later phase, not the first milestone.

## What Can Reuse Shared Code

- output shaping
- cache and local report storage
- wrapper routing

## What Should Stay Raidbots-Specific

- result parsing rules
- any submission workflow
- any session/cookie/browser constraints

## First Useful Slice

1. explain and validate SimulationCraft-style input
2. inspect known Raidbots results or report pages
3. connect this workflow cleanly to local `simc`

## Risks

- deeper automation may depend on unstable or undocumented flows
- workflow constraints may require browser automation or authenticated sessions
- this CLI should not become a substitute for `simc`

## Source Links

- `https://support.raidbots.com/article/54-installing-and-using-the-simulationcraft-addon`
- `https://support.raidbots.com/article/69-why-isnt-my-spec-supported`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
