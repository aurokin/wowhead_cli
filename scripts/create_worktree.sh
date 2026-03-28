#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURRENT_BRANCH="$(git -C "$ROOT_DIR" branch --show-current)"
ALLOW_NON_MASTER=false
RUN_DEV_DEPLOY=false

usage() {
  echo "Usage: $0 <branch-name> [--dev-deploy] [--allow-non-master]" >&2
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

BRANCH_NAME=""
while (($#)); do
  case "$1" in
    --dev-deploy)
      RUN_DEV_DEPLOY=true
      ;;
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
      if [[ -n "$BRANCH_NAME" ]]; then
        echo "Branch name already set to '$BRANCH_NAME'" >&2
        usage
        exit 2
      fi
      BRANCH_NAME="$1"
      ;;
  esac
  shift
done

if [[ -z "$BRANCH_NAME" ]]; then
  usage
  exit 2
fi

if [[ "$BRANCH_NAME" == "master" ]]; then
  echo "Refusing to create a sibling worktree named 'master'." >&2
  exit 2
fi

if [[ "$ALLOW_NON_MASTER" != "true" ]] && [[ "$CURRENT_BRANCH" != "master" ]]; then
  echo "Create sibling worktrees from the reserved master checkout. Current branch: $CURRENT_BRANCH" >&2
  echo "Use --allow-non-master only for deliberate exceptions." >&2
  exit 1
fi

PARENT_DIR="$(dirname "$ROOT_DIR")"
TARGET_DIR="$PARENT_DIR/$BRANCH_NAME"

if [[ -e "$TARGET_DIR" ]]; then
  echo "Target path already exists: $TARGET_DIR" >&2
  exit 1
fi

if git -C "$ROOT_DIR" rev-parse --verify --quiet "refs/heads/$BRANCH_NAME" >/dev/null; then
  echo "Local branch already exists: $BRANCH_NAME" >&2
  echo "Use git worktree add directly if you intend to attach that existing branch." >&2
  exit 1
fi

git -C "$ROOT_DIR" worktree add "$TARGET_DIR" -b "$BRANCH_NAME"
echo "Created worktree: $TARGET_DIR"

if [[ "$RUN_DEV_DEPLOY" == "true" ]]; then
  make -C "$TARGET_DIR" dev-deploy-no-link
fi
