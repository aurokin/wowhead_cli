# Worktree And Installation Plan

## Purpose

This document defines the operator plan for turning the current single-checkout setup into:
- a stable machine-wide install cycle for the Warcraft CLIs and skills
- a parent worktree directory at `~/code/warcraft_cli/`
- a repeatable branch-worktree workflow that does not break the host
- a reserved `master/` checkout that always tracks `master`

It exists because this machine currently depends on the locally deployed CLIs and skill files. The move from one checkout at `~/code/warcraft_cli` to a parent worktree directory must be treated as a controlled cutover, not as a simple rename.

Use alongside:
- [Roadmap](../ROADMAP.md)
- [Repo Structure And Packaging](REPO_STRUCTURE_AND_PACKAGING.md)
- [Package Layout](PACKAGE_LAYOUT.md)
- [Documentation Map](../README.md)

## Current State

Today the machine-wide local deploy is coupled to the current checkout path in three ways:
- `scripts/dev_deploy.sh` creates a repo-local `.venv`
- `scripts/dev_deploy.sh` installs the root package in editable mode
- `scripts/dev_deploy.sh` writes `~/.local/bin/*` wrapper scripts that point at that repo-local `.venv`

That means the current host runtime is effectively tied to `/home/auro/code/warcraft_cli/`.

The current editable deployment should be treated as:
- the repo-local `.venv`
- the editable install metadata inside that `.venv`
- the `~/.local/bin/{warcraft,wowhead,method,icy-veins,raiderio,warcraft-wiki,wowprogress,simc,warcraftlogs}` wrappers that point back to it

## Locked Decisions

### Parent Workspace

`~/code/warcraft_cli/` becomes a parent directory, not an active checkout.

Recommended shape:
- `~/code/warcraft_cli/master/`
- `~/code/warcraft_cli/<branch>/`

`master/` is the stable checkout used for machine-wide deploys and for any host-level skill source that still needs a checkout path.

Sibling branch directories hold feature worktrees and experimental branches.

### Stable Machine Install

Machine-wide CLI access must no longer depend on a repo-local `.venv` inside a branch checkout.

The stable machine deploy should use:
- a fixed install root under `~/.local/share/warcraft/`
- a fixed venv path under that install root
- `~/.local/bin` wrappers that point only to that fixed venv

Branch worktrees may keep local `.venv` environments for development, but those branch-local environments must not own the machine-wide wrappers.

### Stable Skill Source

The source of truth for consumer skill content remains:
- `skills/warcraft/SKILL.md`
- `skills/warcraft/references/*.md`

Machine-level skill consumption must not silently follow whichever branch checkout happens to be active.

Use one of these stable models:
1. export skills during deploy into a fixed path under `~/.local/share/warcraft/`
2. if the host still requires a checkout-backed path, point it only at `~/code/warcraft_cli/master/`

Feature worktrees must not become the implicit skill source for the host.

### Deploy Ownership

Only the stable checkout may perform the machine-wide deploy.

Operational rule:
- `master/` may update the stable venv, wrappers, and stable skill export
- branch worktrees may update only their own local `.venv` and branch-local artifacts

### Install Mode Split

We need two distinct workflows:
- machine deploy: stable, explicit, not tied to a branch-local editable install
- branch-local development: fast, editable, disposable

The machine deploy should prefer a non-editable install into the fixed venv.

Branch-local development can continue to use editable installs inside the worktree-local `.venv`.

## Target Layout

Example target layout:

```text
~/code/warcraft_cli/
  master/
  feature-wrapper-routing/
  feature-warcraftlogs-cache/

~/.local/share/warcraft/
  install/
    venv/
  skills/

~/.local/bin/
  warcraft
  wowhead
  method
  icy-veins
  raiderio
  warcraft-wiki
  wowprogress
  simc
  warcraftlogs
```

## Implementation Phases

### Phase 1: Introduce The Stable Install Path

Goal:
- create a machine-wide runtime that does not depend on the current checkout path

Required work:
1. Add a stable deploy workflow that installs into a fixed venv outside the repo.
2. Make wrapper generation target that fixed venv instead of `<checkout>/.venv/bin/...`.
3. Decide and document the stable skill source path.
4. Keep the existing branch-local editable workflow available during the transition.

Implemented commands:
- `make stable-deploy`
- `make stable-deploy-no-link`
- `make export-stable-skills`

Acceptance gate:
- `warcraft`, `wowhead`, and at least one other provider command run from outside the repo
- `~/.local/bin/*` wrappers no longer mention `/home/auro/code/warcraft_cli/.venv`

### Phase 2: Cut Over And Retire The Current Editable Deployment

Goal:
- stop depending on the current repo-local editable installation

Required work:
1. Build the new stable venv.
2. Repoint `~/.local/bin/*` wrappers to the stable venv.
3. Verify the shell resolves the CLI wrappers to the new stable location.
4. Verify skill resolution uses the stable source.
5. Retire the old repo-local editable deployment.

Implemented command:
- `make retire-dev-deploy`

The retirement plan for the current editable deployment is:
1. treat the old deploy as a dedicated repo-local environment, not as a shared system Python install
2. cut traffic over first by rewriting the `~/.local/bin` wrappers
3. deactivate any shell session that is still sourced from `/home/auro/code/warcraft_cli/.venv`
4. optionally run the old `.venv/bin/pip uninstall warcraft` if we need an explicit uninstall audit trail
5. remove or archive the old repo-local `.venv` only after the new stable deploy is verified

Preferred cleanup:
- archive or remove `/home/auro/code/warcraft_cli/.venv` after cutover verification

This is safer than treating the old editable install like a global package uninstall because the current deploy is already isolated inside a dedicated venv.

Acceptance gate:
- no wrapper in `~/.local/bin/` points at `/home/auro/code/warcraft_cli/.venv`
- the old `.venv` is either removed or clearly marked as retired

### Phase 3: Rehome The Current Checkout

Goal:
- turn `~/code/warcraft_cli/` into the worktree parent directory

Required work:
1. move the current checkout from `~/code/warcraft_cli/` to `~/code/warcraft_cli/master/`
2. verify `git worktree list` reports `master/` as the main worktree
3. update any local scripts or operator notes that still assume the old path
4. verify the machine-wide CLIs still work after the repo move

Acceptance gate:
- the repo has been moved successfully
- machine-wide CLIs still resolve to the stable venv
- host-level skill access still works

### Phase 4: Start Branch Worktree Operations

Goal:
- enable parallel development without letting branch worktrees destabilize the host

Required work:
1. create branch worktrees as siblings under `~/code/warcraft_cli/`
2. use worktree-local `.venv` environments for branch-local testing
3. keep machine-wide deploys restricted to `master/`
4. document the branch-local workflow clearly in developer-facing install docs

Implemented command:
- `make worktree-add BRANCH="<branch-name>"`

Acceptance gate:
- at least one feature worktree is active
- branch-local edits do not affect machine-wide CLI routing until an explicit deploy is run from `master/`

## Verification Checklist

Before the repo move:
- stable venv created
- wrappers rewritten
- CLI smoke tests pass outside the repo
- stable skill source selected and verified

After the repo move:
- `git worktree list` shows `master/` as the main worktree
- `warcraft doctor` passes from a shell that is not sourced into a branch-local `.venv`
- at least one provider smoke command passes
- no machine wrapper references the old checkout path

## Documentation Updates Required During Implementation

When the implementation starts, keep these docs aligned:
- [README.md](../../README.md) for the short install and deploy entrypoint
- [USAGE.md](../USAGE.md) for any user-visible command changes
- [ROADMAP.md](../ROADMAP.md) for sequencing and current priority
- [Package Layout](PACKAGE_LAYOUT.md) for the worktree model
- this file for the cutover procedure and operator rules

## Operating Rules After Cutover

- Do not treat the parent `~/code/warcraft_cli/` directory as a runnable checkout.
- Do not point `~/.local/bin` wrappers at a branch worktree.
- Do not let branch worktrees become the machine-level skill source.
- Do not remove the old repo-local `.venv` until the stable venv is verified.
- Do use branch-local editable installs for fast iteration.
- Do use `master/` for machine-wide deploys, skill exports, and host-facing validation.
