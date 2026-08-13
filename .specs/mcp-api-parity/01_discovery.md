# Discovery: MCP–Aptible API Parity

<!-- spec-nav:start -->
**Spec navigation:** [State](00_state.md) · [Discovery](01_discovery.md) · [Requirements](02_requirements.md) · [Design](03_design.md) · [Tasks](04_tasks.md) · [Execution](05_execution.md)
<!-- spec-nav:end -->

## Problem and Outcome

The `aptible-mcp` server (this repository) exposes Aptible platform operations to MCP clients
(e.g. Claude Desktop, Claude Code) as typed tools. Today it covers 32 tools across accounts,
apps, databases, stacks, vhosts/endpoints, services, and operations — but only a subset of what
the Aptible Deploy API and CLI (aptible.com/docs/reference/aptible-cli) actually support, and
none of the operational depth available in the Aptible Dashboard for those same resources.

**Outcome:** close the gap between what an MCP client can do through this server and what an
Aptible user can do through the CLI/Dashboard for infrastructure/deploy operations, so an AI
agent using this MCP server is not forced to fall back to manual CLI/Dashboard use for common
lifecycle tasks (deploying, restoring a backup, wiring up a custom domain, shipping logs to a
SIEM, etc).

## Users and Current Workaround

- **Primary user:** a developer or AI agent operating an Aptible-hosted app/database through an
  MCP-capable client, trying to complete a full task (e.g. "restore this database from
  yesterday's backup," "point my custom domain at this app with a managed cert," "ship these logs
  to Datadog") without leaving the chat/agent session.
- **Current workaround:** drop out of the MCP session and run the `aptible` CLI or use the
  Dashboard directly for anything not in the 32 existing tools — which today is most
  backup/restore, endpoint/TLS, log/metric drain, and app/database lifecycle operations.

## Scope and Non-Goals

**In scope** (this spec — "Deploy API parity"): closing gaps in the infrastructure/deploy surface
that the current tools partially cover, specifically:

- **Apps:** rename, settings (e.g. force zero-downtime), deploy (image/git-based), rebuild,
  restart.
- **Databases:** replicate (read replicas), clone, dump, execute, rename, restart, modify,
  reload, versions.
- **Backups:** list, restore, orphaned, purge.
- **Endpoints/vhosts:** custom domains, managed TLS, custom certificate upload, TCP/TLS/gRPC
  endpoint types, database endpoints, modify, renew. (Today only the default `on-aptible.com`
  HTTPS endpoint type is supported.)
- **Log drains and metric drains:** create (per destination type), list, deprovision.
- **Services and operations:** service settings, operation cancel, one-off command execution
  (single request/response, not an interactive shell).
- **Environments/stacks:** rename, CA certificate management.
- **Maintenance apps/databases and container recovery.**

**Out of scope for this spec, deferred to a separate future spec** ("Auth API parity"):
organizations, users, roles/permissions, SSO/SAML, SCIM provisioning, MFA/U2F enforcement, and
access-token issuance/revocation. This surface is security-sensitive (it grants/revokes access)
and is a distinct product area (identity/org administration) from infrastructure operations —
see [`Approaches Considered`](#approaches-considered) and the architecture outline below. A user
message during this discovery confirmed this split.

**Non-goals (not addressed by any MCP tool, in this spec or a future one):**

- **Billing** (plans, invoices, payment methods, credits) — confirmed via Context7-backed
  research against `aptible.com/docs` that this is Dashboard-only; no CLI command or documented
  API endpoint exists.
- **Compliance readiness score dashboard** — same: Dashboard-rendered UI, not API-addressable.
- **Interactive SSH shells, database tunnels, and live/streaming log tailing** — these require a
  persistent bidirectional session or long-lived local process, which does not fit a
  request/response MCP tool call. The existing `getOperationLogs` tool (logs for a *completed*
  operation) and the new one-off command execution tool above cover the request/response-shaped
  subset of this need.

## Constraints and Success Measures

- **Constraint — architecture fit:** new tools must fit the existing `ResourceBase` /
  `ResourceManager` pattern (see [`models/base.py`](../../models/base.py)) and the existing
  `AptibleApiClient` HTTP wrapper (see [`api_client.py`](../../api_client.py)) unless a specific
  operation cannot be expressed as typed CRUD (e.g. `deploy`, `rebuild`, `restart`, one-off
  execution — these are operation-triggering actions, similar to the existing `configure` and
  `scale` methods on `App`/`Service`).
- **Constraint — no formal OpenAPI spec exists.** Aptible does not publish a machine-readable API
  schema (verified: `deploy-docs.aptible.com` now redirects into the consolidated
  `aptible.com/docs` site); every new tool's request/response shape must be confirmed against the
  CLI reference pages and, where ambiguous, the open-source `aptible/aptible-cli` source, not
  invented from memory.
- **Success measure:** every resource/operation listed as "in scope" above has a corresponding
  MCP tool, each with unit tests following the existing `tests/test_<resource>.py` pattern
  (mocked HTTP responses, no live API calls), and `just test` / `just typecheck` / `just lint`
  pass.
- **Success measure:** the tool catalog in [`main.py`](../../main.py) and
  [`README.md`](../../README.md) documents the new tools clearly enough that an agent can pick
  the right one without trial and error (matching the existing docstring style).

## Approaches Considered

| Approach | Benefits | Costs / risks | Decision |
|---|---|---|---|
| **A. Extend the existing `ResourceBase`/`ResourceManager` pattern**, adding one Pydantic model + manager per new resource (backups, log drains, metric drains, certificates, database-endpoint types) and bespoke action methods for non-CRUD operations (deploy, rebuild, restart, one-off run), phased into priority tiers. | Matches every existing convention in this codebase ([`models/account.py`](../../models/account.py), [`models/database.py`](../../models/database.py), etc. per [`CLAUDE.md`](../../CLAUDE.md)); reviewable in small, resource-scoped increments; reuses the existing test harness (mocked HTTP, `tests/test_*.py`). | Large surface: roughly 25-35 new tools across ~8 resource areas. Some operations (deploy, rebuild, one-off run) don't fit generic list/get/create/delete and need bespoke manager methods, same as `configure`/`scale` do today. | **Accepted** — lowest risk, no new runtime dependency, directly extends a pattern already proven in this repo. |
| **B. Auto-generate MCP tool bindings from the API's machine-readable schema** at build or runtime, instead of hand-writing each tool. | Would reduce hand-written boilerplate and stay in sync with API changes automatically. | Verified via Context7-backed research (`/websites/aptible`, `aptible.com/docs`) that Aptible does not publish an OpenAPI/Swagger spec or a schema-bearing API-reference subdomain — `deploy-docs.aptible.com` now redirects into the narrative docs site. Without a stable machine-readable schema, "generation" would mean scraping HAL root-document relations, which lack parameter typing/validation needed for useful LLM-facing tool signatures. | **Rejected** — no source schema exists to generate from; would produce worse-typed tools than hand-writing. |
| **C. Shell out to the `aptible` CLI** as a subprocess for the harder-to-model operations (deploy, rebuild, backup restore, one-off run) instead of calling the HTTP API directly. | The CLI already implements some intricate flows (e.g. git-based deploy semantics) correctly and is battle-tested. | Adds a hard runtime dependency (the `aptible` gem/CLI installed and authenticated) that this project does not have today — it talks to `api.aptible.com`/`auth.aptible.com` directly via `requests` and a JWT token ([`api_client.py`](../../api_client.py)). Breaks the existing "pure API client" architecture, complicates the existing mocked-HTTP test harness (would need subprocess mocking instead), and adds stdout/stderr parsing instead of typed JSON. | **Rejected** for the general case — inconsistent with current architecture and test strategy. Keep as a documented fallback only if a specific in-scope operation turns out to have no documented direct API endpoint (design phase will confirm case by case). |

## Chosen Direction

Approach A: extend the existing resource/manager pattern, phased into three priority tiers so the
work is independently shippable and reviewable:

1. **Tier 1 (highest value):** backups (list/restore/orphaned/purge), log drains, metric drains,
   endpoint custom domains + managed/custom TLS + additional endpoint types.
2. **Tier 2:** app deploy/rebuild/restart, app/service/environment settings and rename, operation
   cancel.
3. **Tier 3:** database replicate/clone/dump/execute/modify/reload/versions, maintenance
   apps/databases, container recovery, environment CA certificates, one-off command execution.

Requirements will formalize each tier's user stories and acceptance criteria; tasks will preserve
this tiering so Tier 1 can ship (and be reviewed/merged) before Tier 2/3 are implemented.

## Architecture and Flow Outline

The block diagram below shows the subsystem boundary this spec draws: resources in scope here,
the Auth API resources deferred to a separate future spec, and the explicit non-goals that no MCP
tool will address. Source IR:
[`diagrams/architecture-outline.json`](diagrams/architecture-outline.json).

```mermaid
block
  columns 3
  block:in_scope["In scope: Deploy API parity (this spec)"]
    apps["Apps: rename, settings, deploy, rebuild, restart"]
    databases["Databases: replicate, clone, dump, execute, rename, restart"]
    backups[("Backups: list, restore, orphaned, purge")]
    endpoints["Endpoints: custom domains, managed/custom TLS, TCP/TLS/gRPC/database endpoints"]
    drains["Log drains and metric drains: create, list, deprovision"]
    services_ops["Services and operations: settings, cancel, one-off run"]
    environments["Environments and stacks: rename, CA cert"]
    maintenance["Maintenance apps/DBs and container recovery"]
  end
  block:future_spec["Out of scope: separate future spec"]
    auth_api["Auth API: organizations, users, roles, permissions"]
    sso_mfa["SSO, SCIM, MFA/U2F, token management"]
  end
  block:non_goal["Non-goals: not addressed by any MCP tool"]
    billing(["Billing: plans, invoices, payment methods"])
    compliance_ui(["Compliance readiness score dashboard"])
    interactive(["Interactive SSH shells, DB tunnels, live log streaming"])
  end
```

## Failure and Verification Strategy

- **Failure handling:** follow the existing pattern — raise a descriptive `Exception` for
  not-found/ambiguous lookups (see `getApp`, `getDatabase` in [`main.py`](../../main.py)), and reuse
  `AptibleApiClient.wait_for_operation` for any new action that triggers an async operation
  (deploy, rebuild, restart, restore, replicate), so callers get a resolved success/failure result
  rather than a bare operation ID.
- **Verification:** every new tool gets a unit test under [`tests/`](../../tests) mocking the HTTP
  layer (same approach as [`tests/test_database.py`](../../tests/test_database.py), etc.), run via
  `just test`; `just typecheck` and `just lint` must stay clean. Tier 1 should be independently
  mergeable and verifiable before Tier 2/3 begin.

## Open Decisions

- **Activity/audit log:** Aptible's docs describe an "Activity" feed as a record of operations
  *and* other audited events (role/permission changes, auth attempts) — it straddles this spec's
  in-scope operations surface and the deferred Auth-API security-audit surface. Recommend
  deferring it alongside the Auth API spec; confirm in requirements.
  <!-- Owner: requirements phase -->
- **One-off command execution shape:** confirm during design whether the API supports a true
  single request/response "run this command, return output" call, or whether it is inherently
  session-based (like `aptible ssh`) and should instead move to the non-goals list.
- **Exact request/response schemas** for every Tier 1–3 operation are not yet confirmed line by
  line (this discovery prioritized resource-level breadth). Design phase must confirm each
  against the CLI reference pages and, where needed, `aptible/aptible-cli` source, before
  requirements criteria are written as testable acceptance criteria.

## Approval

Status: **Approved on 2026-08-12** — user approved the full boundary (scope split, non-goals,
chosen approach, tiering, open decisions) as written above. Proceeding to requirements.
