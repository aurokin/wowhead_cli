#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
XDG_DATA_HOME_DEFAULT="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_ROOT="${WARCRAFT_INSTALL_ROOT:-$XDG_DATA_HOME_DEFAULT/warcraft}"
INSTALL_RELEASES_DIR="${WARCRAFT_STABLE_RELEASES_DIR:-$INSTALL_ROOT/install/releases}"
CURRENT_LINK="${WARCRAFT_STABLE_CURRENT_LINK:-$INSTALL_ROOT/install/current}"
SKILLS_LINK="${WARCRAFT_STABLE_SKILLS_LINK:-$INSTALL_ROOT/skills}"
EXPLICIT_VENV_DIR="${WARCRAFT_STABLE_VENV_DIR:-}"
EXPLICIT_SKILLS_DIR="${WARCRAFT_STABLE_SKILLS_DIR:-}"
RELEASE_ID="${WARCRAFT_STABLE_RELEASE_ID:-}"
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

BUILD_VENV_DIR=""
BUILD_SKILLS_DIR=""
ACTIVE_VENV_DIR=""
ACTIVE_SKILLS_DIR=""
ACTIVE_RELEASE_ROOT=""
TMP_RELEASE_ROOT=""
PREVIOUS_SKILLS_DIR=""
VERSIONED_LAYOUT=true

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

detect_release_id() {
  if [[ -n "$RELEASE_ID" ]]; then
    printf '%s\n' "$RELEASE_ID"
    return 0
  fi

  local timestamp
  timestamp="$(date -u +%Y%m%d%H%M%S)"

  local short_sha="manual"
  if git -C "$ROOT_DIR" rev-parse --verify --quiet HEAD >/dev/null 2>&1; then
    short_sha="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
  fi

  printf '%s-%s\n' "$timestamp" "$short_sha"
}

validate_release_id() {
  local candidate="$1"

  if [[ ! "$candidate" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
    return 1
  fi

  if [[ "$candidate" == "." ]] || [[ "$candidate" == ".." ]]; then
    return 1
  fi

  return 0
}

prepare_layout() {
  if [[ -n "$EXPLICIT_VENV_DIR" ]] || [[ -n "$EXPLICIT_SKILLS_DIR" ]]; then
    VERSIONED_LAYOUT=false
    BUILD_VENV_DIR="${EXPLICIT_VENV_DIR:-$INSTALL_ROOT/install/venv}"
    BUILD_SKILLS_DIR="${EXPLICIT_SKILLS_DIR:-$INSTALL_ROOT/skills}"
    ACTIVE_VENV_DIR="$BUILD_VENV_DIR"
    ACTIVE_SKILLS_DIR="$BUILD_SKILLS_DIR"
    return 0
  fi

  RELEASE_ID="$(detect_release_id)"
  if ! validate_release_id "$RELEASE_ID"; then
    echo "Invalid stable release id: $RELEASE_ID" >&2
    echo "Release ids may contain only letters, numbers, dot, underscore, and hyphen." >&2
    exit 2
  fi
  ACTIVE_RELEASE_ROOT="$INSTALL_RELEASES_DIR/$RELEASE_ID"
  TMP_RELEASE_ROOT="$INSTALL_RELEASES_DIR/.tmp-$RELEASE_ID-$$"

  if [[ -e "$ACTIVE_RELEASE_ROOT" ]]; then
    echo "Stable release already exists: $ACTIVE_RELEASE_ROOT" >&2
    echo "Set WARCRAFT_STABLE_RELEASE_ID to a different value or remove the old release first." >&2
    exit 1
  fi

  rm -rf "$TMP_RELEASE_ROOT"
  mkdir -p "$TMP_RELEASE_ROOT"

  BUILD_VENV_DIR="$TMP_RELEASE_ROOT/venv"
  BUILD_SKILLS_DIR="$TMP_RELEASE_ROOT/skills"
  ACTIVE_VENV_DIR="$CURRENT_LINK/venv"
  ACTIVE_SKILLS_DIR="$CURRENT_LINK/skills"
}

replace_with_symlink() {
  local destination_path="$1"
  local target_path="$2"

  mkdir -p "$(dirname "$destination_path")"
  local tmp_link="${destination_path}.tmp.$$"
  rm -f "$tmp_link"
  ln -s "$target_path" "$tmp_link"

  if [[ -L "$destination_path" ]]; then
    mv -Tf "$tmp_link" "$destination_path"
    return 0
  elif [[ -e "$destination_path" ]]; then
    local backup_path="${destination_path}.backup.$(date -u +%Y%m%d%H%M%S)"
    mv "$destination_path" "$backup_path"
    echo "Backed up $destination_path to $backup_path"
  fi

  mv -Tf "$tmp_link" "$destination_path"
}

detect_existing_skills_dir() {
  if [[ ! -e "$CURRENT_LINK/skills" ]]; then
    return 1
  fi

  (
    cd "$CURRENT_LINK/skills" && pwd -P
  )
}

preserve_existing_skills() {
  if [[ "$VERSIONED_LAYOUT" != "true" ]] || [[ "$EXPORT_SKILLS" == "true" ]] || [[ -z "$PREVIOUS_SKILLS_DIR" ]]; then
    return 0
  fi

  mkdir -p "$(dirname "$BUILD_SKILLS_DIR")"
  ln -s "$PREVIOUS_SKILLS_DIR" "$BUILD_SKILLS_DIR"
  echo "Reused stable skills from $PREVIOUS_SKILLS_DIR"
}

refresh_versioned_runtime() {
  if [[ "$VERSIONED_LAYOUT" != "true" ]]; then
    return 0
  fi

  # Python entrypoint wrappers embed an absolute interpreter path, so once the
  # staged release moves from the temp directory into its immutable release id,
  # reinstall the package from the final location before repointing current/.
  "$ACTIVE_RELEASE_ROOT/venv/bin/python" -m pip install --no-build-isolation --upgrade "$PACKAGE_SPEC"
}

activate_release() {
  if [[ "$VERSIONED_LAYOUT" != "true" ]]; then
    return 0
  fi

  mv "$TMP_RELEASE_ROOT" "$ACTIVE_RELEASE_ROOT"
  refresh_versioned_runtime
  replace_with_symlink "$CURRENT_LINK" "$ACTIVE_RELEASE_ROOT"

  if [[ "$EXPORT_SKILLS" == "true" ]]; then
    replace_with_symlink "$SKILLS_LINK" "$ACTIVE_SKILLS_DIR"
  fi
}

cleanup_tmp_release() {
  if [[ "$VERSIONED_LAYOUT" == "true" ]] && [[ -n "$TMP_RELEASE_ROOT" ]] && [[ -e "$TMP_RELEASE_ROOT" ]]; then
    rm -rf "$TMP_RELEASE_ROOT"
  fi
}

bootstrap_runtime_ready() {
  "$BUILD_VENV_DIR/bin/python" - <<'PY'
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

prepare_layout
trap cleanup_tmp_release EXIT
PREVIOUS_SKILLS_DIR="$(detect_existing_skills_dir || true)"

VENV_CREATED=false
if [[ ! -d "$BUILD_VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$BUILD_VENV_DIR"
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
  if ! "$BUILD_VENV_DIR/bin/python" -m pip install --quiet --upgrade "${BOOTSTRAP_PACKAGES[@]}"; then
    if ! bootstrap_runtime_ready >/dev/null 2>&1; then
      echo "Stable deploy requires pip, setuptools, wheel, and hatchling available in $BUILD_VENV_DIR." >&2
      echo "Bootstrap install failed, so the deploy cannot continue." >&2
      exit 1
    fi
    echo "Bootstrap package upgrade failed; continuing with the existing stable runtime toolchain." >&2
  fi
fi

"$BUILD_VENV_DIR/bin/pip" install --no-build-isolation --upgrade "$PACKAGE_SPEC"

if [[ "$EXPORT_SKILLS" == "true" ]]; then
  "$BUILD_VENV_DIR/bin/python" "$ROOT_DIR/scripts/export_stable_skills.py" --output-dir "$BUILD_SKILLS_DIR"
  echo "Prepared stable skills at $BUILD_SKILLS_DIR"
else
  preserve_existing_skills
fi

activate_release

if [[ "$LINK_BIN" == "true" ]]; then
  mkdir -p "$LOCAL_BIN_DIR"
  for BIN_NAME in $BIN_NAMES; do
    WRAPPER_PATH="$LOCAL_BIN_DIR/$BIN_NAME"
    cat > "$WRAPPER_PATH" <<WRAP
#!/usr/bin/env bash
exec "$ACTIVE_VENV_DIR/bin/$BIN_NAME" "\$@"
WRAP
    chmod +x "$WRAPPER_PATH"
    echo "Linked $WRAPPER_PATH -> $ACTIVE_VENV_DIR/bin/$BIN_NAME"
  done
fi

echo "Stable deploy complete."
if [[ "$VERSIONED_LAYOUT" == "true" ]]; then
  echo "Stable release: $RELEASE_ID"
  echo "Stable release root: $ACTIVE_RELEASE_ROOT"
  echo "Stable current link: $CURRENT_LINK"
  if [[ "$EXPORT_SKILLS" == "true" ]]; then
    echo "Stable skills link: $SKILLS_LINK"
  fi
fi
echo "Stable venv: $ACTIVE_VENV_DIR"
echo "Run with: warcraft doctor"
