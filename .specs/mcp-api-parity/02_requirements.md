# Requirements: MCP–Aptible API Parity (Deploy API, Tiers 1–3)

<!-- spec-nav:start -->
**Spec navigation:** [State](00_state.md) · [Discovery](01_discovery.md) · [Requirements](02_requirements.md) · [Design](03_design.md) · [Tasks](04_tasks.md) · [Execution](05_execution.md)
<!-- spec-nav:end -->

This document translates the approved [`01_discovery.md`](01_discovery.md) boundary into testable
requirements for the three priority tiers. Terminology follows the existing codebase: an
"account" is the user-facing "environment"; a "vhost" is the user-facing "endpoint." Each
requirement below maps to exactly one new or extended MCP tool family from discovery's scope.

Every requirement's actor is the resource manager that will own the behavior — some already exist
(`Account_Manager`, `App_Manager`, `Database_Manager`, `Service_Manager`, `Vhost_Manager`,
`Operation_Manager`, matching [`models/`](../../models)), others are new components this feature
introduces (`Backup_Manager`, `Log_Drain_Manager`, `Metric_Drain_Manager`, `Certificate_Manager`,
`Maintenance_Manager`). Naming a manager here is a behavioral grouping, not a design commitment —
[03_design.md](03_design.md) decides the actual class/module layout.

## Revision Note (post-design-research correction)

While researching exact request shapes for [03_design.md](03_design.md) against the Aptible CLI source (the
only ground truth available, since Aptible publishes no separate machine-readable API schema —
see [`01_discovery.md`](01_discovery.md)'s "no formal OpenAPI spec exists" constraint), four
originally-approved requirements turned out not to map to any real, wrappable API operation. Per
user decision, they were dropped and the remaining requirements renumbered contiguously:

- **App settings** — the example field (`force_zero_downtime`) is a Service-level field, not an
  App-level one; it's already covered by Requirement 15 (service settings). No distinct
  app-settings resource exists beyond the environment-variable configuration the existing
  `configureApp` tool already handles. Dropped, no replacement needed.
- **Database dump** and **Database one-off execute** — the official CLI implements both by
  opening a local SSH tunnel and running `pg_dump`/`psql` as a local subprocess; neither is a
  server-side API operation. This is exactly the SSH-tunnel mechanism discovery already excluded
  as a non-goal, and exactly the "shell out" approach discovery already rejected (Approach C).
  Dropped.
- **Container recovery** — confirmed to not be a user-triggerable operation at all; Aptible
  restarts crashed containers automatically, with no API/CLI hook for a human (or agent) to
  invoke it manually. Dropped — the closest available lever is the ordinary app/database restart
  already covered by Requirements 13 and 20.

Two narrower corrections, applied without dropping the requirement:

- **Endpoint TLS renewal** (Requirement 10): confirmed for app endpoints; unconfirmed for
  database endpoints. Scoped to app endpoints only.
- **Environment CA certificate** (Requirement 23): reading the CA certificate is confirmed;
  no CLI command or API evidence confirms a write/set path. Scoped to read-only; setting a new CA
  certificate is not included pending further verification (noted under Open Questions).

## Assumptions

- All new tools authenticate the same way as existing tools (via `AptibleApiClient`); no new
  authentication requirement is introduced.
- "Async operation" means an Aptible operation resource that starts `queued`/`running` and
  resolves to `succeeded` or `failed` — the same lifecycle `wait_for_operation` already handles in
  [`api_client.py`](../../api_client.py).
- Where a tool takes an app, database, or environment identifier, it accepts a handle (and an
  optional environment handle for disambiguation) following the exact existing pattern in
  `getApp`/`getDatabase` in [`main.py`](../../main.py).

---

## Tier 1 — Backups, Drains, Endpoints

### Requirement 1: List database backups

**User Story:** As an agent operating a database, I want to list its available backups, so that
I can choose one to restore or evaluate backup coverage.

#### Acceptance Criteria

1. **R1.1** WHEN a caller requests backups for a database handle, THE Backup_Manager SHALL return the list
   of backups for that database, each including its identifier and creation timestamp.
2. **R1.2** WHEN a caller requests backups with a maximum age filter, THE Backup_Manager SHALL exclude
   backups older than that age from the returned list.
3. **R1.3** IF the specified database handle does not exist, THEN THE Backup_Manager SHALL raise an error
   naming the handle instead of returning an empty list.

### Requirement 2: Restore a database from backup

**User Story:** As an agent recovering from a bad deploy or data issue, I want to restore a
database from a specific backup, so that the database's data returns to a known-good point in
time.

#### Acceptance Criteria

1. **R2.1** WHEN a caller requests a restore for a valid backup identifier, THE Backup_Manager SHALL start
   a restore operation and return the resulting new database resource once the operation succeeds.
2. **R2.2** IF the restore operation fails, THEN THE Backup_Manager SHALL raise an error including the
   operation's failure message.
3. **R2.3** IF the specified backup identifier does not exist, THEN THE Backup_Manager SHALL raise an error
   naming the identifier instead of starting an operation.

### Requirement 3: List and purge orphaned backups

**User Story:** As an agent managing storage costs, I want to find and purge orphaned backups
(backups whose source database no longer exists), so that unused backups don't accumulate.

#### Acceptance Criteria

1. **R3.1** WHEN a caller requests orphaned backups for an environment, THE Backup_Manager SHALL return
   the list of backups in that environment whose source database has been deleted.
2. **R3.2** WHEN a caller requests a purge for a specific backup identifier, THE Backup_Manager SHALL
   delete that backup and return confirmation.
3. **R3.3** IF the specified backup identifier does not exist, THEN THE Backup_Manager SHALL raise an error
   naming the identifier.

### Requirement 4: Log drain lifecycle

**User Story:** As an agent setting up observability, I want to create, list, and remove log
drains for an environment, so that application logs reach an external log store (e.g. Datadog,
Papertrail, syslog).

#### Acceptance Criteria

1. **R4.1** WHEN a caller creates a log drain with a valid destination type and connection details, THE
   Log_Drain_Manager SHALL provision the drain and return the resulting resource, including its
   identifier and status.
2. **R4.2** WHEN a caller lists log drains for an environment, THE Log_Drain_Manager SHALL return every log
   drain provisioned in that environment.
3. **R4.3** WHEN a caller deprovisions a log drain by identifier, THE Log_Drain_Manager SHALL remove it and
   return confirmation.
4. **R4.4** IF a log drain create request specifies an unsupported destination type, THEN THE
   Log_Drain_Manager SHALL raise an error naming the unsupported type instead of attempting
   provisioning.
5. **R4.5** IF the specified log drain identifier does not exist on deprovision, THEN THE Log_Drain_Manager
   SHALL raise an error naming the identifier.

### Requirement 5: Metric drain lifecycle

**User Story:** As an agent setting up observability, I want to create, list, and remove metric
drains for an environment, so that container metrics reach an external monitoring service (e.g.
Datadog, InfluxDB).

#### Acceptance Criteria

1. **R5.1** WHEN a caller creates a metric drain with a valid destination type and connection details, THE
   Metric_Drain_Manager SHALL provision the drain and return the resulting resource, including its
   identifier and status.
2. **R5.2** WHEN a caller lists metric drains for an environment, THE Metric_Drain_Manager SHALL return
   every metric drain provisioned in that environment.
3. **R5.3** WHEN a caller deprovisions a metric drain by identifier, THE Metric_Drain_Manager SHALL remove
   it and return confirmation.
4. **R5.4** IF a metric drain create request specifies an unsupported destination type, THEN THE
   Metric_Drain_Manager SHALL raise an error naming the unsupported type instead of attempting
   provisioning.
5. **R5.5** IF the specified metric drain identifier does not exist on deprovision, THEN THE
   Metric_Drain_Manager SHALL raise an error naming the identifier.

### Requirement 6: Custom domain endpoint with managed TLS

**User Story:** As an agent exposing an app publicly, I want to create an endpoint bound to my own
domain with Aptible-managed TLS, so that traffic to my domain reaches the app over HTTPS without
me sourcing a certificate myself.

#### Acceptance Criteria

1. **R6.1** WHEN a caller creates an endpoint for a service specifying a custom domain and requesting
   managed TLS, THE Vhost_Manager SHALL provision the endpoint and return the resulting resource,
   including any DNS validation records required to complete provisioning.
2. **R6.2** IF the specified service does not exist, THEN THE Vhost_Manager SHALL raise an error naming the
   service instead of attempting provisioning.
3. **R6.3** IF the specified domain is an apex domain that Aptible's managed TLS does not support, THEN THE
   Vhost_Manager SHALL raise an error explaining the restriction instead of attempting
   provisioning.

### Requirement 7: Custom domain endpoint with a customer-provided certificate

**User Story:** As an agent exposing an app publicly with an existing certificate, I want to
create an endpoint using a certificate I supply, so that I retain control over my own TLS
material.

#### Acceptance Criteria

1. **R7.1** WHEN a caller uploads a certificate and private key, THE Certificate_Manager SHALL store the
   certificate and return its identifier and fingerprint.
2. **R7.2** WHEN a caller creates an endpoint referencing a stored certificate's fingerprint, THE
   Vhost_Manager SHALL provision the endpoint using that certificate.
3. **R7.3** WHEN a caller lists certificates for the environment, THE Certificate_Manager SHALL return
   every stored certificate with its identifier and expiration date.
4. **R7.4** IF the supplied certificate and private key do not form a valid pair, THEN THE
   Certificate_Manager SHALL raise an error instead of storing the certificate.
5. **R7.5** IF an endpoint create request references a certificate fingerprint that does not exist, THEN
   THE Vhost_Manager SHALL raise an error naming the fingerprint instead of attempting
   provisioning.

### Requirement 8: Additional endpoint types (TCP, TLS, gRPC)

**User Story:** As an agent exposing a non-HTTP service, I want to create TCP, TLS, or gRPC
endpoints (not just default HTTPS), so that I can expose services that don't speak HTTP/1.1.

#### Acceptance Criteria

1. **R8.1** WHEN a caller creates an endpoint specifying type TCP, TLS, or gRPC along with the container
   ports to expose, THE Vhost_Manager SHALL provision an endpoint of that type bound to those
   ports.
2. **R8.2** WHEN a caller lists endpoints for a service, THE Vhost_Manager SHALL include each endpoint's
   type in the returned resource.
3. **R8.3** IF a TLS-type endpoint create request omits a certificate reference, THEN THE Vhost_Manager
   SHALL raise an error instead of attempting provisioning.

### Requirement 9: Database endpoints

**User Story:** As an agent that needs external clients to reach a database directly, I want to
create an endpoint that exposes a database (rather than an app service), so that authorized
external clients can connect to it.

#### Acceptance Criteria

1. **R9.1** WHEN a caller creates a database endpoint for a valid database handle, THE Vhost_Manager SHALL
   provision the endpoint and return its resulting hostname and port.
2. **R9.2** IF the specified database handle does not exist, THEN THE Vhost_Manager SHALL raise an error
   naming the handle instead of attempting provisioning.

### Requirement 10: Endpoint modification and TLS renewal

**User Story:** As an agent maintaining an existing endpoint, I want to modify its configuration
or trigger a TLS renewal, so that I don't have to delete and recreate the endpoint for routine
changes.

#### Acceptance Criteria

1. **R10.1** WHEN a caller modifies an existing endpoint's supported settings (e.g. container ports,
   certificate reference), THE Vhost_Manager SHALL apply the change and return the updated
   resource.
2. **R10.2** WHEN a caller triggers a TLS renewal for a managed-TLS app endpoint, THE Vhost_Manager SHALL
   start the renewal operation and return its resulting status.
3. **R10.3** IF the specified endpoint identifier does not exist, THEN THE Vhost_Manager SHALL raise an
   error naming the identifier instead of attempting the change.

---

## Tier 2 — App Lifecycle and Operation Control

### Requirement 11: App rename

**User Story:** As an agent correcting or standardizing naming, I want to rename an app, so that
its handle reflects current naming conventions without recreating the app.

#### Acceptance Criteria

1. **R11.1** WHEN a caller renames an app to a new handle that is unique within its environment, THE
   App_Manager SHALL apply the new handle and return the updated resource.
2. **R11.2** IF the requested new handle is already in use within the same environment, THEN THE App_Manager
   SHALL raise an error instead of applying the rename.
3. **R11.3** IF the specified app does not exist, THEN THE App_Manager SHALL raise an error naming the app
   instead of attempting the rename.

### Requirement 12: App deploy operation

**User Story:** As an agent shipping a new version, I want to trigger a deploy of a new Docker
image (or Git reference) to an app, so that the app runs the new version without me leaving the
session.

#### Acceptance Criteria

1. **R12.1** WHEN a caller triggers a deploy specifying a new Docker image reference, THE App_Manager SHALL
   start a deploy operation and return the resulting app resource once the operation succeeds.
2. **R12.2** IF the deploy operation fails, THEN THE App_Manager SHALL raise an error including the
   operation's failure message.
3. **R12.3** IF the specified app does not exist, THEN THE App_Manager SHALL raise an error naming the app
   instead of starting a deploy.

### Requirement 13: App rebuild

**User Story:** As an agent responding to a base-image security patch, I want to trigger a
rebuild of an app's current release, so that the app picks up underlying image layer updates
without a new deploy.

#### Acceptance Criteria

1. **R13.1** WHEN a caller triggers a rebuild for an app, THE App_Manager SHALL start a rebuild operation
   and return the resulting app resource once the operation succeeds.
2. **R13.2** IF the rebuild operation fails, THEN THE App_Manager SHALL raise an error including the
   operation's failure message.

### Requirement 14: App restart

**User Story:** As an agent recovering from a stuck or misbehaving app, I want to restart it, so
that its containers restart without a full deploy.

#### Acceptance Criteria

1. **R14.1** WHEN a caller triggers a restart for an app, THE App_Manager SHALL start a restart operation
   and return the resulting app resource once the operation succeeds.
2. **R14.2** IF the restart operation fails, THEN THE App_Manager SHALL raise an error including the
   operation's failure message.

### Requirement 15: Service settings configuration

**User Story:** As an agent tuning a service's runtime behavior, I want to read and update
service-level settings (e.g. health check command, zero-downtime deploys), so that I can adjust
behavior per service without recreating it.

#### Acceptance Criteria

1. **R15.1** WHEN a caller requests a service's settings, THE Service_Manager SHALL return the current value
   of each supported setting.
2. **R15.2** WHEN a caller updates one or more supported service settings, THE Service_Manager SHALL apply
   the changes and return the updated settings.
3. **R15.3** IF a caller attempts to set an unsupported setting name, THEN THE Service_Manager SHALL raise
   an error naming the unsupported setting instead of applying any change.

### Requirement 16: Operation cancellation

**User Story:** As an agent that started an operation in error (or one running too long), I want
to cancel an in-progress operation, so that it stops without waiting for it to time out or
succeed/fail on its own.

#### Acceptance Criteria

1. **R16.1** WHEN a caller cancels an operation that is still queued or running, THE Operation_Manager SHALL
   request cancellation and return the operation's resulting status.
2. **R16.2** IF the specified operation has already reached a terminal state (`succeeded` or `failed`),
   THEN THE Operation_Manager SHALL raise an error explaining that it cannot be cancelled instead
   of requesting cancellation.
3. **R16.3** IF the specified operation identifier does not exist, THEN THE Operation_Manager SHALL raise an
   error naming the identifier.

### Requirement 17: Environment rename

**User Story:** As an agent correcting or standardizing naming, I want to rename an environment,
so that its handle reflects current naming conventions without recreating the environment.

#### Acceptance Criteria

1. **R17.1** WHEN a caller renames an environment to a new handle that is unique within the organization,
   THE Account_Manager SHALL apply the new handle and return the updated resource.
2. **R17.2** IF the requested new handle is already in use, THEN THE Account_Manager SHALL raise an error
   instead of applying the rename.
3. **R17.3** IF the specified environment does not exist, THEN THE Account_Manager SHALL raise an error
   naming the environment instead of attempting the rename.

---

## Tier 3 — Database Maintenance, Maintenance Mode, One-off Execution

### Requirement 18: Database read replica creation

**User Story:** As an agent scaling read capacity, I want to create a read replica of an existing
database, so that read traffic can be served without adding load to the primary.

#### Acceptance Criteria

1. **R18.1** WHEN a caller requests a replica of an existing database with a handle and environment, THE
   Database_Manager SHALL start a replication operation and return the resulting replica database
   resource once the operation succeeds.
2. **R18.2** IF the replication operation fails, THEN THE Database_Manager SHALL raise an error including
   the operation's failure message.
3. **R18.3** IF the specified source database does not exist, THEN THE Database_Manager SHALL raise an
   error naming the database instead of starting replication.

### Requirement 19: Database clone

**User Story:** As an agent setting up a staging copy, I want to clone a database into a new,
independent database, so that I can test against realistic data without touching the source.

#### Acceptance Criteria

1. **R19.1** WHEN a caller requests a clone of an existing database into a new handle, THE Database_Manager
   SHALL start a clone operation and return the resulting new database resource once the operation
   succeeds.
2. **R19.2** IF the clone operation fails, THEN THE Database_Manager SHALL raise an error including the
   operation's failure message.
3. **R19.3** IF the requested new handle is already in use within the target environment, THEN THE
   Database_Manager SHALL raise an error instead of starting the clone.

### Requirement 20: Database modify, reload, rename, and restart

**User Story:** As an agent managing an existing database's configuration, I want to modify its
IOPS/volume type, change its container size or disk size, reload it, rename it, or restart it, so
that I can adjust an existing database without recreating it.

#### Acceptance Criteria

1. **R20.1** WHEN a caller modifies a database's provisioned IOPS or EBS volume type, THE Database_Manager
   SHALL start a modify operation and return the resulting database resource once the operation
   succeeds.
2. **R20.2** WHEN a caller changes a database's container size, disk size, or container profile, THE
   Database_Manager SHALL start a restart operation carrying the new values and return the
   resulting database resource once the operation succeeds.
3. **R20.3** WHEN a caller reloads a database, THE Database_Manager SHALL start a reload operation and
   return the resulting status once the operation succeeds.
4. **R20.4** WHEN a caller renames a database to a handle that is unique within its environment, THE
   Database_Manager SHALL apply the new handle and return the updated resource.
5. **R20.5** WHEN a caller restarts a database without changing its size, THE Database_Manager SHALL start
   a restart operation and return the resulting status once the operation succeeds.
6. **R20.6** IF any of the above operations fails, THEN THE Database_Manager SHALL raise an error including
   the operation's failure message.
7. **R20.7** IF the requested new handle in a rename is already in use within the same environment, THEN THE
   Database_Manager SHALL raise an error instead of applying the rename.

### Requirement 21: Database available versions

**User Story:** As an agent planning an upgrade, I want to list the database versions available
for a given database type, so that I know what upgrade targets exist before modifying a database.

#### Acceptance Criteria

1. **R21.1** WHEN a caller requests available versions for a database type, THE Database_Manager SHALL
   return the list of supported versions for that type.
2. **R21.2** IF the specified database type does not exist, THEN THE Database_Manager SHALL raise an error
   naming the type instead of returning an empty list.

### Requirement 22: Maintenance mode visibility

**User Story:** As an agent auditing an environment's health, I want to see which apps or
databases are currently in maintenance mode, so that I know not to treat their unavailability as
an incident.

#### Acceptance Criteria

1. **R22.1** WHEN a caller lists apps or databases currently in maintenance mode for an environment, THE
   Maintenance_Manager SHALL return that list.
2. **R22.2** IF the specified environment does not exist, THEN THE Maintenance_Manager SHALL raise an error
   naming the environment instead of returning an empty list.

### Requirement 23: Environment CA certificate visibility

**User Story:** As an agent configuring private networking or mutual TLS for an environment, I
want to view the environment's configured CA certificate, so that I can confirm dependent
connections trust the correct certificate authority.

#### Acceptance Criteria

1. **R23.1** WHEN a caller requests an environment's current CA certificate, THE Account_Manager SHALL
   return it if one is configured.
2. **R23.2** IF the specified environment does not exist, THEN THE Account_Manager SHALL raise an error
   naming the environment instead of returning a certificate.

### Requirement 24: One-off command execution on an app service

**User Story:** As an agent performing a one-time task inside a running app's container (e.g. a
script or diagnostic command), I want to run a single command and get its output back, so that I
can complete the task without an interactive shell session.

#### Acceptance Criteria

1. **R24.1** WHEN a caller submits a command to run against a specific service of an existing app, THE
   Service_Manager SHALL start a one-off run operation and return the command's captured output
   once the operation completes.
2. **R24.2** IF the one-off run operation fails, THEN THE Service_Manager SHALL raise an error including the
   operation's failure message and any captured output.
3. **R24.3** IF the specified app or service does not exist, THEN THE Service_Manager SHALL raise an error
   naming the missing resource instead of starting the operation.

---

## Cross-Cutting Requirement

### Requirement 25: Consistent async-operation resolution

**User Story:** As an agent invoking any new operation-triggering tool from Tiers 1–3, I want
long-running operations resolved before the tool call returns, so that I always get a final
success/failure result rather than a bare in-progress operation reference.

#### Acceptance Criteria

1. **R25.1** WHEN any Tier 1–3 tool starts an Aptible operation, THE tool SHALL wait for that operation to
   reach a terminal state before returning, using the same resolution mechanism as
   `wait_for_operation` in [`api_client.py`](../../api_client.py).
2. **R25.2** IF an operation does not reach a terminal state within the API's own timeout behavior, THEN THE
   tool SHALL raise an error rather than returning an ambiguous partial result.

---

## Non-Functional / Risk Notes

- **Security:** Requirement 7 (custom certificates) accepts sensitive material (private keys) as
  a tool argument. No requirement here changes how this material is transmitted or stored beyond
  passing it to the existing authenticated `AptibleApiClient`; design must confirm nothing is
  logged.
- **Backward compatibility:** none of the above requirements change the behavior or signature of
  the 32 existing tools.
- **Evolving-technology constraint:** exact request/response field names for every requirement
  above were confirmed during design against the Aptible CLI source (`aptible/aptible-cli` on
  GitHub) and the official docs, since no OpenAPI schema exists — see [03_design.md](03_design.md)'s Current
  Technology Evidence section for the per-operation citations.

## Open Questions Carried Forward

- **Environment CA certificate write path** (Requirement 23): no CLI command or API evidence
  confirms a way to *set* a new CA certificate, only read one. If a write path is confirmed during
  implementation, this requirement can be extended; until then it stays read-only.
- Whether "Activity"/audit-log visibility belongs in this spec or the deferred Auth API spec
  remains unresolved; no requirement above covers it, consistent with deferring it.

## Approval

Status: **Approved on 2026-08-12** — revised (App settings, Database dump, Database one-off
execute, and Container recovery dropped as non-existent operations; Endpoint TLS renewal and
Environment CA certificate narrowed) per user decision during design research. 25 requirements /
78 criteria across Tiers 1-3 approved as written. Proceeding to design.
