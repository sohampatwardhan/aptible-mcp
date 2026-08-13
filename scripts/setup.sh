#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' "Error: uv is required but was not found on PATH." >&2
  printf '%s\n' "Install it from https://docs.astral.sh/uv/getting-started/installation/ and rerun this script." >&2
  exit 1
fi

if [ ! -f "$PROJECT_DIR/pyproject.toml" ] || [ ! -f "$PROJECT_DIR/uv.lock" ]; then
  printf '%s\n' "Error: pyproject.toml and uv.lock must be present beside this setup script." >&2
  exit 1
fi

printf '%s\n' "Synchronizing Aptible MCP dependencies from the locked environment..."
uv sync --project "$PROJECT_DIR" --locked --no-dev

printf '%s\n' "Verifying the MCP server can be imported..."
uv run --project "$PROJECT_DIR" --locked --no-dev python -c 'import main'

if [ -n "${APTIBLE_TOKEN:-}" ]; then
  printf '%s\n' "Authentication: APTIBLE_TOKEN is configured."
elif [ -n "${HOME:-}" ] && [ -f "$HOME/.aptible/tokens.json" ]; then
  printf '%s\n' "Authentication: an Aptible CLI token file is available."
else
  printf '%s\n' "Authentication is not configured yet."
  printf '%s\n' "Set APTIBLE_TOKEN or log in with the Aptible CLI before starting the server."
fi

printf '%s\n' "Setup complete. Start the server with:"
printf '  uv run --project %s --locked --no-dev python main.py\n' "$PROJECT_DIR"
