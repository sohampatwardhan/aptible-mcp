# Spec State: MCP–Aptible API Parity

<!-- spec-nav:start -->
**Spec navigation:** [State](00_state.md) · [Discovery](01_discovery.md) · [Requirements](02_requirements.md) · [Design](03_design.md) · [Tasks](04_tasks.md) · [Execution](05_execution.md)
<!-- spec-nav:end -->

| Gate | Status | Evidence |
|---|---|---|
| Discovery | approved | Approved 2026-08-12 — full boundary (scope, non-goals, chosen approach, tiering) accepted as written |
| Requirements | approved | Re-approved 2026-08-12 after design-research correction — 25 requirements / 78 criteria across Tiers 1-3 |
| Design | approved | Approved 2026-08-12 — 5 new managers, 6 extended managers, 1 shared helper, 25 properties covering all 78 criteria |
| Tasks | approved | Approved 2026-08-12 — 19 leaf tasks across 8 stages, 2 checkpoints (Tier 1/Tier 2 gates) |
| Audit | not_run | — |
| Execution | not_started | — |

## Change Control

- 2026-08-12: Scoped down from "full API + Dashboard parity" to "Deploy API parity" only, per
  user decision during discovery; Auth API (organizations, users, roles, SSO, SCIM, MFA, tokens)
  moved to a separate future spec.
- 2026-08-12: Discovery approved as written; proceeding to requirements.
- 2026-08-12: Requirements approved as written; proceeding to design.
- 2026-08-12: Design research (CLI-source ground truth) found App settings, Database dump,
  Database one-off execute, and Container recovery map to no real API operation; dropped per user
  decision. Endpoint TLS renewal narrowed to app endpoints; Environment CA certificate narrowed to
  read-only. Requirements renumbered to 25/78 criteria and re-approved same session.
- 2026-08-12: Design approved as written; proceeding to tasks.
- 2026-08-12: Tasks approved as written; proceeding to execution.
