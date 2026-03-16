# Agent Instructions

## Package Manager
- Use `pip` with the local venv.
- Install: `pip install -e '.[dev]'`
- Redis extras: `pip install -e '.[dev,redis]'`
- Fast tests: `pytest -q`
- Live tests: `WOWHEAD_LIVE_TESTS=1 pytest -q -m live`
- Local deploy: `make dev-deploy`
- Lint: `make lint`
- Full lint report: `make lint-all`
- Complexity report: `make complexity`
- Type check: `make typecheck`
- Coverage: `make coverage` (currently blocked if the local Python build lacks `sqlite3`)

## Commit Attribution
- AI commits MUST include:
```text
Co-Authored-By: OpenAI Codex <noreply@openai.com>
```

## Key Conventions
- Use `wowhead`, not `wowhead-cli`, in commands and examples.
- Put global flags before the subcommand.
- Keep `README.md` short.
- Put detailed command behavior in `docs/USAGE.md`.
- Keep roadmap sequencing and current priority in `docs/ROADMAP.md`.
- Keep provider-specific docs in `docs/<cli>/README.md`.
- Keep the docs index in `docs/README.md`.
- Keep repo-wide product philosophy in `docs/foundation/PRODUCT_PRINCIPLES.md`.
- Keep repo-wide analytics rules in `docs/foundation/SAFE_ANALYTICS_RULES.md`.
- Keep shared identity semantics aligned with `docs/foundation/IDENTITY_CONTRACT.md` and `packages/warcraft-core/src/warcraft_core/identity.py`.
- Keep docs aligned with actual CLI behavior.
- Prefer updating docs when command contracts or output shapes change.
- Do not bolt on “smart answers” for analytics-heavy questions.
- Build reliable, sample-backed analytics primitives that agents can trust and compose.
- Treat normalization as an additive analysis layer, not a replacement for raw source content.
- Keep raw guide/article/log content and provenance accessible alongside normalized outputs.
- Follow `docs/foundation/SAFE_ANALYTICS_RULES.md` when adding sampled, compared, or derived analytics surfaces.
- Skills are consumer-facing workflow docs, not internal maintenance docs.
- Keep repo maintenance, roadmap, packaging, architecture, and generation workflow out of skill docs.
- `skills/warcraft/SKILL.md` and `skills/warcraft/references/*.md` are the source of truth for consumer skill content.
- In skill files, reference bundled docs with portable relative paths like `references/simc.md`, not absolute filesystem paths.
- Generated provider subskills belong under `.generated-skills/` and must not be edited manually.
- Do not mention generation or internal maintenance workflow inside consumer skill files.

## Local Skills
- Use the `warcraft` skill for root wrapper and provider-routing work. See `skills/warcraft/SKILL.md`.
