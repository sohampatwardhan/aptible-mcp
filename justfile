lint:
    uv run ruff check
    uv run ruff format --check
    uv run toml-sort --check pyproject.toml

pretty:
    uv run ruff check --fix
    uv run ruff format
    uv run toml-sort pyproject.toml

test:
    APTIBLE_TOKEN="foobar" \
    APTIBLE_API_ROOT_URL="http://localhost:3000" \
    APTIBLE_AUTH_ROOT_URL="http://localhost:3001" \
    uv run python -m pytest -v -s tests/

vendor-test:
    uv run python -m pytest -q \
      .agents/skills/spec-driven/tests/ \
      .agents/skills/dependency-security-audit/tests/

security-audit:
    ./scripts/release-audit.sh

typecheck:
    uv run mypy --show-traceback .
