# Auth Architecture Plan

## Goal

Build a shared auth architecture that is:
- consumer-friendly
- XDG-first
- safe to extend
- narrow enough to avoid fake abstraction

The main near-term auth consumers are:
- `warcraftlogs`
- `blizzard-api`
- `raidbots`

The important design decision is that these do **not** all belong to the same auth class.

## Auth Consumer Classes

### 1. Official OAuth API Providers

These are the providers that should shape the shared auth design.

- `warcraftlogs`
- `blizzard-api`

Shared characteristics:
- official developer auth model
- explicit client registration
- stable token endpoints
- documented client-credentials and/or user-auth flows
- typed API contracts where auth is a first-class requirement

These providers justify shared work for:
- credential discovery
- token persistence
- auth status reporting
- callback handling
- refresh/expiry helpers

### 2. Session or Workflow Providers

These providers may need authentication later, but they should not define the shared OAuth abstraction.

- `raidbots`

Shared characteristics:
- product workflow first, not public API first
- deeper automation may depend on browser/session state
- any future auth may look more like site automation or session persistence than official OAuth

This class should reuse only the generic storage and status pieces if they fit. It should not force OAuth-specific abstractions into places they do not belong.

### 3. Light-Credential Providers

Possible future class:
- API-key providers
- app-token providers
- providers with simple static credentials but no user auth

This class is not the primary driver for the current design.

## Current Research

### Warcraft Logs

Official signals support a full OAuth-first integration:
- official OAuth 2.0 docs
- client-credentials flow
- authorization-code flow
- PKCE flow
- public GraphQL endpoint
- user GraphQL endpoint

This means:
- `warcraftlogs` should keep using provider-local OAuth logic
- shared auth work should be designed to support it cleanly
- later user auth should be built on the same credential/state foundation

### Blizzard API

Official Battle.net docs confirm:
- OAuth 2.0 is required
- client credentials are used for most API requests
- authorization code is required for user WoW profile endpoints
- client registration, redirect URIs, authorize URI, token URI, and scopes are documented
- access tokens expire and must be refreshed/reacquired intentionally

This makes `blizzard-api` the second real validation point for the shared auth system.

### Raidbots

Current official and product signals do **not** justify treating Raidbots like a clean OAuth/API provider:
- support content focuses on SimulationCraft workflow, addon input, and result analysis
- there is no public official developer OAuth/API story in the support docs
- site/frontend signals suggest internal API access and user-level gating exist, but not as a public integration contract

This means:
- `raidbots` should not shape the shared OAuth abstraction
- if deeper automation needs auth later, treat it as session/workflow auth
- only share credential/state primitives if they fit naturally

## Shared Responsibilities

The shared layer should handle only the parts that are genuinely common.

### Shared Credential Discovery

Preferred order:
1. repo-local `.env.local`
2. XDG provider env
3. process environment

Provider env path pattern:
- `~/.config/warcraft/providers/<provider>.env`

Examples:
- `~/.config/warcraft/providers/warcraftlogs.env`
- `~/.config/warcraft/providers/blizzard-api.env`

This matches current `warcraftlogs` behavior and should become the default auth discovery contract.

### Shared Token and Session State

Static credentials should stay separate from runtime-issued state.

Recommended runtime state root:
- `~/.local/state/warcraft/providers/`

Examples:
- `~/.local/state/warcraft/providers/warcraftlogs.json`
- `~/.local/state/warcraft/providers/blizzard-api.json`
- `~/.local/state/warcraft/providers/raidbots.json`

This state should eventually store:
- issued access tokens
- refresh tokens where applicable
- expiry timestamps
- provider-specific auth metadata
- session metadata where that is the real auth model

Do not store issued tokens in `.env.local` or provider `.env` files.

### Shared Auth Status Reporting

Every auth-capable provider should eventually be able to report:
- whether static credentials are present
- where credentials came from
- whether a token/session file exists
- whether the token/session is currently valid
- expiry information when available
- which auth mode is active

This belongs in:
- `doctor`
- and later provider-local `auth status`

### Shared Local Callback Support

For auth-code and PKCE flows, the shared layer should eventually provide:
- loopback callback listener
- callback URL validation against provider config
- state/nonce handling primitives
- browser-launch helper

This should be generic enough for both:
- `warcraftlogs`
- `blizzard-api`

But the provider-specific authorize URL, scopes, and token exchange logic should stay local.

## Provider-Local Responsibilities

These should remain provider-specific:
- authorize/token endpoints
- scopes
- grant-type rules
- refresh semantics
- OAuth payload details
- rate-limit interactions
- region/namespace rules
- user-auth vs public-auth endpoint splits
- session/cookie automation for workflow products

That means:
- `warcraftlogs` keeps its own OAuth and GraphQL rules
- `blizzard-api` keeps its own Battle.net OAuth plus namespace/region rules
- `raidbots` keeps any future browser/session logic local

## Command Shape

Add provider-local auth commands only when they are justified by the product.

Recommended long-term shape for OAuth-capable providers:
- `<provider> auth status`
- `<provider> auth login`
- `<provider> auth pkce-login`
- `<provider> auth logout`

Recommended current posture:
- `warcraftlogs`
  - phase 1: `doctor` is enough
  - later: `auth status`, then user-auth commands
- `blizzard-api`
  - likely add explicit `auth` commands early because auth is central to the provider
- `raidbots`
  - do not add auth commands until a real authenticated workflow is implemented

## What Not To Do

- do not build one giant universal auth abstraction first
- do not assume OAuth, API keys, and browser sessions are the same problem
- do not push provider-specific token rules into `warcraft-core`
- do not make `raidbots` requirements distort the clean OAuth path for official APIs
- do not mix static secrets and runtime-issued tokens in the same storage file

## Rollout Order

### Phase 1

Harden the shared auth foundation around what is already real:
- keep `.env.local` plus XDG provider env discovery
- add shared state-path helpers for issued token/session files
- add shared auth-status reporting primitives

### Phase 2

Use `warcraftlogs` to prove the first full user-auth flow:
- `auth status`
- auth-code login
- PKCE login
- logout
- runtime token persistence

### Phase 3

Use `blizzard-api` to validate that the shared OAuth foundation survives a second official provider with different rules:
- Battle.net OAuth
- scopes
- region and namespace concerns
- profile-vs-game-data auth splits

### Phase 4

Re-evaluate `raidbots` based on actual product need:
- stay public/workflow-only if possible
- if auth is needed, classify it explicitly as session/workflow auth
- reuse shared discovery/state/status only where it helps

## Testing Strategy

### Shared Tests

- XDG/env credential discovery
- state path resolution
- redacted auth status reporting

### Provider Tests

- token acquisition
- token refresh/reacquire behavior
- status payloads
- failure modes for missing or invalid credentials

### Live Tests

- `warcraftlogs`: public first, then user auth
- `blizzard-api`: public first, then user auth where required
- `raidbots`: only if a stable authenticated workflow is actually implemented

## Immediate Planning Consequences

- `warcraftlogs` and `blizzard-api` should be referenced together when discussing shared auth
- `raidbots` should stay in the auth conversation, but as a separate auth class
- future auth work should start with shared discovery/state/status helpers, not with a universal OAuth client abstraction

## Source Links

- Warcraft Logs OAuth and API docs:
  - `https://www.warcraftlogs.com/api/docs`
  - `https://www.warcraftlogs.com/v2-api-docs/warcraft/`
- Blizzard Battle.net OAuth docs:
  - `https://community.developer.battle.net/documentation/guides/using-oauth`
- Raidbots official product and support references:
  - `https://www.raidbots.com/`
  - `https://support.raidbots.com/article/15-simc-expert-mode`
  - `https://support.raidbots.com/article/54-installing-and-using-the-simulationcraft-addon`
