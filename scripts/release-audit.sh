#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPORT_DIR="$PROJECT_DIR/.security/dependency-audit"
SBOM_PATH="$REPORT_DIR/runtime-sbom.cdx.json"

if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' "Error: uv is required to run the release audit." >&2
  exit 2
fi

mkdir -p "$REPORT_DIR"
uv export --quiet --project "$PROJECT_DIR" --locked --no-dev --format cyclonedx1.5 \
  --output-file "$SBOM_PATH"

if [ -n "${GH_TOKEN:-}" ]; then
  APTIBLE_MCP_AUDIT_GITHUB_TOKEN=$GH_TOKEN
elif command -v gh >/dev/null 2>&1; then
  APTIBLE_MCP_AUDIT_GITHUB_TOKEN=$(gh auth token 2>/dev/null || true)
else
  APTIBLE_MCP_AUDIT_GITHUB_TOKEN=""
fi

if [ -z "$APTIBLE_MCP_AUDIT_GITHUB_TOKEN" ]; then
  printf '%s\n' "Error: authenticate gh or set GH_TOKEN before the release audit." >&2
  exit 2
fi
export APTIBLE_MCP_AUDIT_GITHUB_TOKEN

set -- \
  --root "$PROJECT_DIR" \
  --mode release \
  --sbom "$SBOM_PATH" \
  --github-token-env APTIBLE_MCP_AUDIT_GITHUB_TOKEN \
  --revision "$(git -C "$PROJECT_DIR" rev-parse HEAD)" \
  --format human

if [ -n "${NVD_API_KEY:-}" ]; then
  set -- "$@" --nvd-api-key-env NVD_API_KEY
fi

exec uv run --project "$PROJECT_DIR" --locked python \
  "$PROJECT_DIR/.agents/skills/dependency-security-audit/scripts/dependency_security_audit.py" \
  "$@"
