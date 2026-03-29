#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XDG_DATA_HOME_DEFAULT="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_ROOT="${WARCRAFT_INSTALL_ROOT:-$XDG_DATA_HOME_DEFAULT/warcraft}"
INSTALL_RELEASES_DIR="${WARCRAFT_STABLE_RELEASES_DIR:-$INSTALL_ROOT/install/releases}"
CURRENT_LINK="${WARCRAFT_STABLE_CURRENT_LINK:-$INSTALL_ROOT/install/current}"
RELEASE_ID="${WARCRAFT_STABLE_RELEASE_ID:-}"
STABLE_BRANCH="${WARCRAFT_STABLE_BRANCH:-}"
ALLOW_NON_MASTER=false

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

replace_with_symlink() {
  local destination_path="$1"
  local target_path="$2"

  mkdir -p "$(dirname "$destination_path")"
  local tmp_link="${destination_path}.tmp.$$"
  rm -f "$tmp_link"
  ln -s "$target_path" "$tmp_link"

  if [[ -L "$destination_path" ]]; then
    rm -f "$destination_path"
  elif [[ -e "$destination_path" ]]; then
    local backup_path="${destination_path}.backup.$(date -u +%Y%m%d%H%M%S)"
    mv "$destination_path" "$backup_path"
    echo "Backed up $destination_path to $backup_path"
  fi

  mv "$tmp_link" "$destination_path"
}

list_release_ids() {
  if [[ ! -d "$INSTALL_RELEASES_DIR" ]]; then
    return 0
  fi

  local release_path
  while IFS= read -r release_path; do
    [[ -z "$release_path" ]] && continue
    basename "$release_path"
  done < <(find "$INSTALL_RELEASES_DIR" -mindepth 1 -maxdepth 1 -type d | sort)
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

usage() {
  echo "Usage: $0 <release-id> [--allow-non-master]" >&2
  echo "Or set WARCRAFT_STABLE_RELEASE_ID to the target release id." >&2
}

while (($#)); do
  case "$1" in
    --allow-non-master)
      ALLOW_NON_MASTER=true
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --*)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
    *)
      if [[ -n "$RELEASE_ID" ]]; then
        echo "Release id already set to '$RELEASE_ID'" >&2
        usage
        exit 2
      fi
      RELEASE_ID="$1"
      ;;
  esac
  shift
done

if [[ -z "$RELEASE_ID" ]]; then
  echo "Stable rollback requires a release id." >&2
  usage
  AVAILABLE_RELEASES="$(list_release_ids)"
  if [[ -n "$AVAILABLE_RELEASES" ]]; then
    echo "Available releases:" >&2
    printf ' - %s\n' $AVAILABLE_RELEASES >&2
  fi
  exit 2
fi

if ! validate_release_id "$RELEASE_ID"; then
  echo "Invalid stable release id: $RELEASE_ID" >&2
  echo "Release ids may contain only letters, numbers, dot, underscore, and hyphen." >&2
  exit 2
fi

if [[ "$ALLOW_NON_MASTER" != "true" ]] && git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if ! STABLE_BRANCH="$(detect_stable_branch)"; then
    echo "Could not determine the stable branch for this repository." >&2
    echo "Set WARCRAFT_STABLE_BRANCH or use --allow-non-master for a deliberate exception." >&2
    exit 1
  fi
  CURRENT_BRANCH="$(git -C "$ROOT_DIR" branch --show-current)"
  if [[ "$CURRENT_BRANCH" != "$STABLE_BRANCH" ]]; then
    echo "Stable rollback must run from the stable branch '$STABLE_BRANCH'. Current branch: $CURRENT_BRANCH" >&2
    echo "Use --allow-non-master only for deliberate exceptions." >&2
    exit 1
  fi
fi

TARGET_RELEASE_ROOT="$INSTALL_RELEASES_DIR/$RELEASE_ID"
if [[ ! -d "$TARGET_RELEASE_ROOT" ]]; then
  echo "Stable release not found: $TARGET_RELEASE_ROOT" >&2
  AVAILABLE_RELEASES="$(list_release_ids)"
  if [[ -n "$AVAILABLE_RELEASES" ]]; then
    echo "Available releases:" >&2
    printf ' - %s\n' $AVAILABLE_RELEASES >&2
  fi
  exit 1
fi

RESOLVED_RELEASES_DIR="$(cd "$INSTALL_RELEASES_DIR" && pwd -P)"
RESOLVED_TARGET_RELEASE_ROOT="$(cd "$TARGET_RELEASE_ROOT" && pwd -P)"
if [[ "$(dirname "$RESOLVED_TARGET_RELEASE_ROOT")" != "$RESOLVED_RELEASES_DIR" ]]; then
  echo "Stable release must resolve under $INSTALL_RELEASES_DIR: $RELEASE_ID" >&2
  exit 1
fi

CURRENT_TARGET=""
if [[ -L "$CURRENT_LINK" ]]; then
  CURRENT_TARGET="$(readlink "$CURRENT_LINK")"
fi

if [[ "$CURRENT_TARGET" == "$TARGET_RELEASE_ROOT" ]]; then
  echo "Stable release already active: $RELEASE_ID"
  echo "Stable current link: $CURRENT_LINK"
  exit 0
fi

replace_with_symlink "$CURRENT_LINK" "$TARGET_RELEASE_ROOT"

echo "Stable rollback complete."
echo "Stable release: $RELEASE_ID"
echo "Stable release root: $TARGET_RELEASE_ROOT"
echo "Stable current link: $CURRENT_LINK"
echo "Run with: warcraft doctor"
