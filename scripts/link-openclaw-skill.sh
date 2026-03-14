#!/usr/bin/env bash
set -euo pipefail

# Link this repo's warcraft skill into OpenClaw's local skills directory.
#
# Usage:
#   ./scripts/link-openclaw-skill.sh
#   ./scripts/link-openclaw-skill.sh /custom/openclaw/skills/dir
#
# Optional env vars:
#   OPENCLAW_SKILLS_DIR=/path/to/skills
#   OPENCLAW_SKILL_NAME=warcraft
#   OPENCLAW_SKILL_PATH=/path/to/skill/folder

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEFAULT_TARGET_DIR="$HOME/.openclaw/skills"
TARGET_DIR="${1:-${OPENCLAW_SKILLS_DIR:-$DEFAULT_TARGET_DIR}}"

SOURCE_SKILL_PATH="${OPENCLAW_SKILL_PATH:-$REPO_ROOT/skills/warcraft}"
SKILL_NAME="${OPENCLAW_SKILL_NAME:-$(basename "$SOURCE_SKILL_PATH")}"
TARGET_PATH="$TARGET_DIR/$SKILL_NAME"

if [[ ! -d "$SOURCE_SKILL_PATH" ]]; then
  echo "Skill directory not found: $SOURCE_SKILL_PATH" >&2
  exit 1
fi

if [[ ! -f "$SOURCE_SKILL_PATH/SKILL.md" ]]; then
  echo "SKILL.md missing in source skill: $SOURCE_SKILL_PATH" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"

if [[ -L "$TARGET_PATH" ]]; then
  echo "Updating symlink: $TARGET_PATH"
  rm "$TARGET_PATH"
elif [[ -e "$TARGET_PATH" ]]; then
  echo "Refusing to overwrite non-symlink path: $TARGET_PATH" >&2
  exit 1
else
  echo "Linking: $TARGET_PATH"
fi

ln -s "$SOURCE_SKILL_PATH" "$TARGET_PATH"

echo "Done."
echo "OpenClaw skill linked: $SKILL_NAME -> $SOURCE_SKILL_PATH"
