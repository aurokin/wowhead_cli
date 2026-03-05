#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LINK_BIN=true
BIN_NAME="${WOWHEAD_BIN_NAME:-wowhead}"

while (($#)); do
  case "$1" in
    --link-bin)
      LINK_BIN=true
      ;;
    --no-link-bin)
      LINK_BIN=false
      ;;
    --bin-name)
      shift
      if [[ -z "${1:-}" ]]; then
        echo "--bin-name requires a value" >&2
        exit 2
      fi
      BIN_NAME="$1"
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

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel >/dev/null
"$VENV_DIR/bin/pip" install -e '.[dev]'

if [[ "$LINK_BIN" == "true" ]]; then
  LOCAL_BIN_DIR="$HOME/.local/bin"
  mkdir -p "$LOCAL_BIN_DIR"
  WRAPPER_PATH="$LOCAL_BIN_DIR/$BIN_NAME"
  cat > "$WRAPPER_PATH" <<WRAP
#!/usr/bin/env bash
exec "$VENV_DIR/bin/wowhead" "\$@"
WRAP
  chmod +x "$WRAPPER_PATH"
  echo "Linked $WRAPPER_PATH -> $VENV_DIR/bin/wowhead"
fi

echo "Dev deploy complete."
echo "Run with: wowhead search \"defias\""
