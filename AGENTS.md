# Agent Instructions

## Package Manager
- Use `pip` with the local venv.
- Install: `pip install -e '.[dev]'`
- Redis extras: `pip install -e '.[dev,redis]'`
- Fast tests: `pytest -q`
- Live tests: `WOWHEAD_LIVE_TESTS=1 pytest -q -m live`
- Local deploy: `make dev-deploy`

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
- Keep roadmap work in `docs/ROADMAP.md`.
- Keep docs aligned with actual CLI behavior.
- Prefer updating docs when command contracts or output shapes change.
- Root research and planning docs live under `docs/`.

## Local Skills
- Use the `warcraft` skill for root wrapper and provider-routing work. See `skills/warcraft/SKILL.md`.
- Use the `wowhead` skill for Wowhead CLI work. See `skills/wowhead/SKILL.md`.
