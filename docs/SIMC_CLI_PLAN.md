# SimulationCraft CLI Plan

## Why SimC Is Structurally Important

`simc` is not just another web integration. It is a local-tool and local-repository integration, and the monorepo should be designed with that in mind.

If the shared abstractions only work for HTTP services, the structure is too narrow.

## Research Summary

Observed from the official repository and README:
- SimulationCraft is a local simulator written in C++
- the command-line binary is `simc`
- the graphical interface is explicitly described as largely unmaintained
- the project expects local builds on Linux rather than packaged Linux releases
- parameter-file and command-line driven execution are first-class workflows

## Access Model

This should be a local-tool service:
- local repo sync
- local build management
- local binary execution
- profile and report helpers

## Likely CLI Shape

- `simc sync`
- `simc build`
- `simc version`
- `simc run <profile-or-file>`
- `simc inspect <profile-or-result>`

## What Can Reuse Shared Code

- output shaping
- local cache/state directories
- bundle/report indexing if result storage becomes useful
- wrapper routing from `warcraft`

## What This Service Should Validate

`simc` is the test for whether the monorepo abstractions work for local tools as well as network services.

If a shared layer assumes HTTP everywhere, it is the wrong layer.

## What Should Stay SimC-Specific

- git sync policy
- build orchestration
- binary invocation
- result/report parsing
- environment validation

## First Useful Slice

1. manage a local SimulationCraft checkout
2. verify or build the CLI binary
3. run a local profile with controlled output capture

## Risks

- local build requirements will vary by platform
- this integration needs strong environment diagnostics
- result parsing should not be over-generalized too early

## Source Links

- `https://github.com/simulationcraft/simc`
- [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md)
