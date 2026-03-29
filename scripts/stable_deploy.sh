#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
XDG_DATA_HOME_DEFAULT="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_ROOT="${WARCRAFT_INSTALL_ROOT:-$XDG_DATA_HOME_DEFAULT/warcraft}"
VENV_DIR="${WARCRAFT_STABLE_VENV_DIR:-$INSTALL_ROOT/install/venv}"
SKILLS_DIR="${WARCRAFT_STABLE_SKILLS_DIR:-$INSTALL_ROOT/skills}"
LOCAL_BIN_DIR="${WARCRAFT_LOCAL_BIN_DIR:-$HOME/.local/bin}"
STABLE_BRANCH="${WARCRAFT_STABLE_BRANCH:-}"
LINK_BIN=true
EXPORT_SKILLS=true
INSTALL_DEV=false
INSTALL_REDIS=false
ALLOW_NON_MASTER=false
ALLOW_DIRTY=false
BIN_NAMES="${WARCRAFT_BIN_NAMES:-warcraft wowhead method icy-veins raiderio warcraft-wiki wowprogress simc warcraftlogs}"
BOOTSTRAP_PACKAGES=(
  "pip"
  "setuptools"
  "wheel"
  "hatchling>=1.24.0"
)

detect_stable_branch() {
  if [[ -n "$STABLE_BRANCH" ]]; then
    printf '%s\n' "$STABLE_BRANCH"
    return 0
  fi

  if git -C "$ROOT_DIR" rev-parse --verify --quiet "refs/remotes/origin/HEAD" >/dev/null 2>&1; then
    local origin_head_ref
    origin_head_ref="$(git -C "$ROOT_DIR" symbolic-ref --quiet "refs/remotes/origin/HEAD" 2>/dev/null || true)"
    if [[ -n "$origin_head_ref" ]]; then
      printf '%s\n' "${origin_head_ref##refs/remotes/origin/}"
      return 0
    fi
  fi

  local has_master=false
  local has_main=false

  if git -C "$ROOT_DIR" show-ref --verify --quiet "refs/heads/master"; then
    has_master=true
  fi

  if git -C "$ROOT_DIR" show-ref --verify --quiet "refs/heads/main"; then
    has_main=true
  fi

  if [[ "$has_master" == "true" ]] && [[ "$has_main" == "true" ]]; then
    return 1
  fi

  if [[ "$has_master" == "true" ]]; then
    printf 'master\n'
    return 0
  fi

  if [[ "$has_main" == "true" ]]; then
    printf 'main\n'
    return 0
  fi

  return 1
}

bootstrap_runtime_ready() {
  "$VENV_DIR/bin/python" - <<'PY'
import importlib.metadata
import sys

required = ("pip", "setuptools", "wheel", "hatchling")
missing = []

for package in required:
    try:
        importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        missing.append(package)

if missing:
    sys.stderr.write("Missing bootstrap packages: " + ", ".join(missing) + "\n")
    raise SystemExit(1)
PY
}

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
    --allow-dirty)
      ALLOW_DIRTY=true
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
  if ! STABLE_BRANCH="$(detect_stable_branch)"; then
    echo "Could not determine the stable branch for this repository." >&2
    echo "Set WARCRAFT_STABLE_BRANCH or use --allow-non-master for a deliberate exception." >&2
    exit 1
  fi
  CURRENT_BRANCH="$(git -C "$ROOT_DIR" branch --show-current)"
  if [[ "$CURRENT_BRANCH" != "$STABLE_BRANCH" ]]; then
    echo "Stable deploys must run from the stable branch '$STABLE_BRANCH'. Current branch: $CURRENT_BRANCH" >&2
    echo "Use --allow-non-master only for deliberate exceptions." >&2
    exit 1
  fi
fi

if [[ "$ALLOW_DIRTY" != "true" ]] && git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if ! git -C "$ROOT_DIR" diff --quiet --ignore-submodules=all \
    || ! git -C "$ROOT_DIR" diff --cached --quiet --ignore-submodules=all \
    || [[ -n "$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal)" ]]; then
    echo "Stable deploys must run from a clean worktree." >&2
    echo "Commit or stash your changes first, or use --allow-dirty for a deliberate exception." >&2
    exit 1
  fi
fi

VENV_CREATED=false
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  VENV_CREATED=true
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

if [[ "$VENV_CREATED" == "true" ]] || ! bootstrap_runtime_ready >/dev/null 2>&1; then
  if ! "$VENV_DIR/bin/python" -m pip install --quiet --upgrade "${BOOTSTRAP_PACKAGES[@]}"; then
    if ! bootstrap_runtime_ready >/dev/null 2>&1; then
      echo "Stable deploy requires pip, setuptools, wheel, and hatchling available in $VENV_DIR." >&2
      echo "Bootstrap install failed, so the deploy cannot continue." >&2
      exit 1
    fi
    echo "Bootstrap package upgrade failed; continuing with the existing stable runtime toolchain." >&2
  fi
fi

"$VENV_DIR/bin/pip" install --no-build-isolation --upgrade "$PACKAGE_SPEC"

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
