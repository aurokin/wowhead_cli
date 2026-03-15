# Package Layout

## Purpose

This document defines the intended package layout for the Warcraft monorepo.

It is the concrete companion to:
- [Roadmap](/home/auro/code/warcraft_cli/docs/ROADMAP.md)
- [Repo Structure And Packaging](/home/auro/code/warcraft_cli/docs/REPO_STRUCTURE_AND_PACKAGING.md)

## Workspace Model

Use:
- a root developer workspace
- one `pyproject.toml` per package
- lightweight root scripts, docs, and shared tooling only

This gives us:
- package isolation
- independent builds
- a usable developer workflow

## Package Naming

Keep the current alignment pattern:
- package project names end in `-cli` when they are service-facing CLI packages
- command names stay short and service-oriented

Examples:
- `warcraft-core-cli` -> shared package, no end-user command
- `warcraft` -> umbrella command
- `wowhead-cli` -> `wowhead`
- `method-cli` -> `method`
- `icy-veins-cli` -> `icy-veins`
- `raiderio-cli` -> `raiderio`
- `simc-cli` -> `simc`
- `raidbots-cli` -> `raidbots`
- `warcraftlogs-cli` -> `warcraftlogs`

## Target Directory Shape

Recommended initial layout:

- `packages/warcraft-core/`
- `packages/warcraft-api/`
- `packages/warcraft-content/`
- `packages/warcraft-cli/`
- `packages/wowhead-cli/`
- `packages/method-cli/`
- `packages/icy-veins-cli/`
- `packages/raiderio-cli/`
- `packages/simc-cli/`
- `packages/raidbots-cli/`
- `packages/warcraftlogs-cli/`
- `skills/warcraft/`
- `docs/`
- `scripts/`
- `tests/` for root-level migration and workspace checks only

## Per-Package Structure

Each package should be independently buildable and follow the same basic shape:

- `pyproject.toml`
- `README.md` if package-specific docs are needed
- `src/<package_name>/`
- `tests/`

Shared packages should not expose unrelated CLI entrypoints.

## Dependency Direction

Allowed:
- service package -> `warcraft-core`
- service package -> `warcraft-api`
- service package -> `warcraft-content`
- `warcraft-cli` -> shared packages
- `warcraft-cli` -> service CLI invocation

Not allowed:
- service package -> another service package
- shared package -> service package

## Umbrella Package Behavior

Installing `warcraft` should install the full current service set by default.

Individual service packages should also remain installable on their own.

That means the umbrella package is a convenience distribution, not the only supported entrypoint.

## Root-Level Responsibilities

The repo root should own:
- high-level docs
- workspace scripts
- shared CI/release configuration
- migration checks

It should not become an implicit package that other packages import from.

## Storage Layout

Use XDG-style defaults where appropriate.

Recommended defaults:
- config: `~/.config/warcraft/` or `XDG_CONFIG_HOME/warcraft/`
- data: `~/.local/share/warcraft/` or `XDG_DATA_HOME/warcraft/`
- cache: `~/.cache/warcraft/` or `XDG_CACHE_HOME/warcraft/`

Within those roots, prefer:
- `shared/`
- one directory per service

## Milestone Mapping

Milestone 1:
- `warcraft-core`
- `warcraft-api`
- `warcraft-content`
- `warcraft-cli`
- `wowhead-cli`
- `method-cli` with stubbed commands

Milestone 2:
- real `method-cli`

Later milestones:
- `icy-veins-cli`
- `raiderio-cli`
- `simc-cli`
- `raidbots-cli`
- `warcraftlogs-cli`

## Rules

- every package must remain independently buildable
- shared code moves only when it is truly shared
- package boundaries and dependency direction must stay documented
- architecture docs must be updated whenever package layout or dependency rules change
