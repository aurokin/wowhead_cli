# Wrapper Provider Contract

## Purpose

This document defines how the Python `warcraft` wrapper interacts with service providers.

It exists to keep the wrapper thin, predictable, and language-agnostic at the provider boundary.

## Wrapper Philosophy

`warcraft` is:
- a router
- a discovery layer
- a thin orchestration layer

It is not:
- a second implementation of every service
- a parser owner
- an API schema owner

## Required Provider Capabilities

Every service provider must expose these wrapper-facing capabilities:

- `search`
- `resolve`
- `doctor`
- direct passthrough execution for service-specific commands

If a capability is not implemented yet, it must still exist and return a structured stub such as `coming_soon`.

That keeps the wrapper contract stable even while services are being built.

## Capability Expectations

### `search`

Purpose:
- return service-specific candidate matches for a free-text query

Minimum behavior:
- accept a query string
- return a structured result list
- return `coming_soon` if not implemented yet

### `resolve`

Purpose:
- return the best next service-specific command for a query when confidence is high

Minimum behavior:
- accept a query string
- return either a candidate resolution or a structured unresolved response
- return `coming_soon` if not implemented yet

### `doctor`

Purpose:
- report whether the service is ready to be used in the current environment

Examples of what it may check:
- package availability
- auth configuration
- local binary presence
- cache/storage roots
- required runtime such as Node for a non-Python package

This should always exist, even for stubbed providers.

## Invocation Strategy

Preferred order:
- Python-first for Python services
- shell/CLI boundary second

Practical meaning:
- Python services may be invoked through shared entrypoints or direct package hooks
- non-Python services should be invoked through a CLI boundary
- the wrapper should preserve a stable provider contract either way

## Mixed-Language Rule

If a service is implemented in another language:
- the wrapper still stays Python
- the provider is invoked as a CLI process
- stdout/stderr and exit code become the integration boundary
- the provider must still satisfy the same `search`, `resolve`, and `doctor` contract

## Provider Registration

The wrapper should know for each provider:
- provider name
- command name
- implementation language
- whether it is installed
- whether auth is configured
- whether `search`, `resolve`, and `doctor` are supported or stubbed

This registry should drive wrapper behavior instead of hardcoded special cases spread throughout the codebase.

## Search Fanout Rules

`warcraft search` should query:
- all installed unauthenticated providers
- all installed authenticated providers when auth is configured

Providers that are not ready should still report through `doctor`.

## Resolve Rules

`warcraft resolve` should:
- ask ready providers for candidate resolutions
- rank them conservatively
- preserve source provenance
- avoid pretending certainty when providers are stubbed or unavailable

## Doctor Rules

`warcraft doctor` should report:
- wrapper health
- installed providers
- provider readiness
- auth availability where relevant
- runtime availability for non-Python services
- storage/config root status

## Output Rules

The wrapper should preserve:
- service provenance
- suggested next command
- clear readiness/error state

It should not flatten all provider outputs into one fake universal model.

## Milestone Behavior

Milestone 1:
- `warcraft` proxies `wowhead`
- `method` exists as a registered provider with stubbed `search`, `resolve`, and `doctor` if needed
- wrapper commands exist even if some providers are not yet real

Milestone 2:
- `method` becomes a real provider behind the same contract

## Documentation Rule

Whenever provider capabilities, provider readiness rules, or wrapper/provider boundaries change:
- update this document
- update [Roadmap](/home/auro/code/wowhead_cli/docs/ROADMAP.md) if sequencing changes
- update [Repo Structure And Packaging](/home/auro/code/wowhead_cli/docs/REPO_STRUCTURE_AND_PACKAGING.md) if package or language rules change
