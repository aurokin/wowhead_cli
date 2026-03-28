#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
XDG_DATA_HOME_DEFAULT="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_ROOT="${WARCRAFT_INSTALL_ROOT:-$XDG_DATA_HOME_DEFAULT/warcraft}"
VENV_DIR="${WARCRAFT_STABLE_VENV_DIR:-$INSTALL_ROOT/install/venv}"
SKILLS_DIR="${WARCRAFT_STABLE_SKILLS_DIR:-$INSTALL_ROOT/skills}"
LOCAL_BIN_DIR="${WARCRAFT_LOCAL_BIN_DIR:-$HOME/.local/bin}"
LINK_BIN=true
EXPORT_SKILLS=true
INSTALL_DEV=false
INSTALL_REDIS=false
ALLOW_NON_MASTER=false
BIN_NAMES="${WARCRAFT_BIN_NAMES:-warcraft wowhead method icy-veins raiderio warcraft-wiki wowprogress simc warcraftlogs}"

while (($#)); do
  case "$1" in
    --link-bin)
      LINK_BIN=true
      ;;
    --no-link-bin)
      LINK_BIN=false
      ;;
    --export-skills)
      EXPORT_SKILLS=true
      ;;
    --no-export-skills)
      EXPORT_SKILLS=false
      ;;
    --with-dev)
      INSTALL_DEV=true
      ;;
    --with-redis)
      INSTALL_REDIS=true
      ;;
    --allow-non-master)
      ALLOW_NON_MASTER=true
      ;;
    --bin-name)
      shift
      if [[ -z "${1:-}" ]]; then
        echo "--bin-name requires a value" >&2
        exit 2
      fi
      BIN_NAMES="$1"
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python binary '$PYTHON_BIN' not found." >&2
  exit 1
fi

if [[ "$ALLOW_NON_MASTER" != "true" ]] && git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  CURRENT_BRANCH="$(git -C "$ROOT_DIR" branch --show-current)"
  if [[ "$CURRENT_BRANCH" != "master" ]]; then
    echo "Stable deploys must run from the master branch. Current branch: $CURRENT_BRANCH" >&2
    echo "Use --allow-non-master only for deliberate exceptions." >&2
    exit 1
  fi
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

PACKAGE_SPEC="$ROOT_DIR"
EXTRAS=()
if [[ "$INSTALL_DEV" == "true" ]]; then
  EXTRAS+=("dev")
fi
if [[ "$INSTALL_REDIS" == "true" ]]; then
  EXTRAS+=("redis")
fi
if ((${#EXTRAS[@]})); then
  EXTRAS_CSV="$(IFS=,; echo "${EXTRAS[*]}")"
  PACKAGE_SPEC="$ROOT_DIR[$EXTRAS_CSV]"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel >/dev/null
"$VENV_DIR/bin/pip" install --upgrade "$PACKAGE_SPEC"

if [[ "$EXPORT_SKILLS" == "true" ]]; then
  "$VENV_DIR/bin/python" "$ROOT_DIR/scripts/export_stable_skills.py" --output-dir "$SKILLS_DIR"
  echo "Exported stable skills to $SKILLS_DIR"
fi

if [[ "$LINK_BIN" == "true" ]]; then
  mkdir -p "$LOCAL_BIN_DIR"
  for BIN_NAME in $BIN_NAMES; do
    WRAPPER_PATH="$LOCAL_BIN_DIR/$BIN_NAME"
    cat > "$WRAPPER_PATH" <<WRAP
#!/usr/bin/env bash
exec "$VENV_DIR/bin/$BIN_NAME" "\$@"
WRAP
    chmod +x "$WRAPPER_PATH"
    echo "Linked $WRAPPER_PATH -> $VENV_DIR/bin/$BIN_NAME"
  done
fi

echo "Stable deploy complete."
echo "Stable venv: $VENV_DIR"
echo "Run with: warcraft doctor"
