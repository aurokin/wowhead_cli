#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OLD_VENV_DIR="$ROOT_DIR/.venv"
LOCAL_BIN_DIR="${WARCRAFT_LOCAL_BIN_DIR:-$HOME/.local/bin}"
BIN_NAMES="${WARCRAFT_BIN_NAMES:-warcraft wowhead method icy-veins raiderio warcraft-wiki wowprogress simc warcraftlogs}"
KEEP_VENV=false
DELETE_VENV=false
SKIP_UNINSTALL=false

while (($#)); do
  case "$1" in
    --keep-venv)
      KEEP_VENV=true
      ;;
    --delete-venv)
      DELETE_VENV=true
      ;;
    --skip-uninstall)
      SKIP_UNINSTALL=true
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

if [[ ! -d "$OLD_VENV_DIR" ]]; then
  echo "No repo-local .venv found at $OLD_VENV_DIR"
  exit 0
fi

BLOCKERS=()
for BIN_NAME in $BIN_NAMES; do
  WRAPPER_PATH="$LOCAL_BIN_DIR/$BIN_NAME"
  if [[ -f "$WRAPPER_PATH" ]] && grep -Fq "$OLD_VENV_DIR" "$WRAPPER_PATH"; then
    BLOCKERS+=("$WRAPPER_PATH")
  fi
done

if ((${#BLOCKERS[@]})); then
  echo "Refusing to retire $OLD_VENV_DIR because these wrappers still point at it:" >&2
  printf ' - %s\n' "${BLOCKERS[@]}" >&2
  echo "Run the stable deploy first so ~/.local/bin no longer references the repo-local .venv." >&2
  exit 1
fi

if [[ "$KEEP_VENV" == "true" ]]; then
  echo "Kept repo-local venv at $OLD_VENV_DIR"
  echo "No uninstall or archive work was performed."
  exit 0
fi

if [[ "$SKIP_UNINSTALL" != "true" ]] && [[ -x "$OLD_VENV_DIR/bin/pip" ]]; then
  "$OLD_VENV_DIR/bin/pip" uninstall -y warcraft >/dev/null || true
  echo "Uninstalled the editable warcraft package from $OLD_VENV_DIR"
fi

if [[ "$DELETE_VENV" == "true" ]]; then
  rm -rf "$OLD_VENV_DIR"
  echo "Deleted retired repo-local venv: $OLD_VENV_DIR"
  exit 0
fi

TIMESTAMP="$(date +%Y%m%d%H%M%S)"
ARCHIVE_PATH="$ROOT_DIR/.venv.retired.$TIMESTAMP"
mv "$OLD_VENV_DIR" "$ARCHIVE_PATH"
echo "Archived retired repo-local venv to $ARCHIVE_PATH"
