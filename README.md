# Aptible MCP

An MCP server for managing [Aptible](https://www.aptible.com) resources through the Model Context
Protocol.

> [!IMPORTANT]
> **Current release: [v0.2.2](https://github.com/sohampatwardhan/aptible-mcp/releases/tag/v0.2.2).**
> The server implements feature-complete Deploy API parity across the supported resource groups
> below. Mutating tools can create, resize, restart, or delete billable infrastructure, so review
> tool arguments and the target environment before approving a call.

## Overview

This project exposes 74 MCP tools for inspecting and operating Aptible environments, apps,
databases, backups, endpoints, drains, certificates, services, maintenance entries, and operations.
It uses typed Pydantic models, an asynchronous HTTP client, bounded and cancellable operation
polling, and same-origin validation for authenticated Aptible API links.

## Features

- Deploy API coverage across all resource groups listed in [Tools](#tools)
- Non-blocking HTTP, pagination, operation polling, and operation-log retrieval
- Account-scoped reconciliation for database clone, replication, and restore operations
- Same-origin credential protection and trusted-file handling for certificate private keys
- Allowlisted resource responses that omit embedded API objects and redact secret-bearing fields
- Locked, reproducible source installation and a packaged MCPB desktop extension
- Release dependency auditing with CycloneDX, OSV, CISA KEV, GitHub, NVD, and `pip-audit`

## Structure

- `api_client.py` - API client for interacting with the Aptible API
- `models/` - Pydantic models for Aptible resources
  - `base.py` - Base models and resource manager
  - Resource-specific models (`account.py`, `app.py`, `backup.py`, `certificate.py`, `database.py`,
    `log_drain.py`, `maintenance.py`, `metric_drain.py`, `operation.py`, `service.py`, `stack.py`,
    `vhost.py`)
- `main.py` - MCP tools implementation

## Tools

`main.py` registers the following MCP tools, grouped by resource:

- **Accounts/Environments**: `listAccounts`, `getAccount`, `getAccountsByStack`, `createAccount`,
  `renameEnvironment`, `getEnvironmentCaCertificate`
- **Apps**: `listApps`, `getApp`, `createApp`, `configureApp`, `deleteApp`, `renameApp`,
  `deployApp`, `rebuildApp`, `restartApp`, `runAppCommand`
- **Databases**: `listAvailableDatabaseTypes`, `listDatabases`, `getDatabase`, `createDatabase`,
  `deleteDatabase`, `replicateDatabase`, `cloneDatabase`, `modifyDatabaseIops`, `resizeDatabase`,
  `reloadDatabase`, `renameDatabase`, `restartDatabase`, `listDatabaseVersions`
- **Backups**: `listDatabaseBackups`, `restoreDatabaseFromBackup`, `listOrphanedBackups`,
  `purgeBackup`
- **Log/Metric Drains**: `createLogDrain`, `listLogDrains`, `deprovisionLogDrain`,
  `createMetricDrain`, `listMetricDrains`, `deprovisionMetricDrain`
- **Certificates**: `uploadCertificate`, `listCertificates`
- **Maintenance**: `listMaintenanceEntries`
- **Stacks**: `listStacks`, `getStack`
- **VHosts/Endpoints**: `listVhosts`, `getVhost`, `createVhost`, `deleteVhost`,
  `createCustomDomainEndpoint`, `createTypedEndpoint`, `createDatabaseEndpoint`, `modifyEndpoint`,
  `renewEndpoint`
- **Services**: `listServices`, `getService`, `scaleService`, `getServiceSettings`,
  `updateServiceSettings`, `listServiceVhosts`
- **Operations**: `getOperationsForApp`, `getOperationsForDatabase`, `getOperationsForVhost`,
  `getOperationLogs`, `cancelOperation`
- **Examples**: `getProcfileExample`, `getAptibleYamlExample`, `getEndpointProvisionExample`,
  `getAppProvisionExample`, `getAppDeprovisionExample`, `getAppConfigureExample`,
  `getDatabaseProvisionExample`, `getDatabaseDeprovisionExample`, `getDatabaseRestoreExample`,
  `getBuildDeployExample`

## Install

### Desktop extension (`.mcpb`)

Download `aptible-mcp-0.2.2.mcpb` from the
[v0.2.2 GitHub release](https://github.com/sohampatwardhan/aptible-mcp/releases/tag/v0.2.2), then open it with an MCPB-compatible
desktop client. During installation, you can provide an Aptible access token. If you leave the
token blank, the server uses the credentials from an existing Aptible CLI login at
`~/.aptible/tokens.json`.

The bundle uses the MCPB 0.4 `uv` runtime and requires Python 3.13 or newer. The desktop client
manages the extracted bundle and starts `main.py` over stdio.

If you plan to use `uploadCertificate`, select a trusted certificate directory during MCPB setup.
The tool accepts filenames from that directory, never certificate or private-key contents as model
inputs. On POSIX systems, private-key files must have owner-only permissions (for example,
`chmod 600 private-key.pem`). Source installs should set `APTIBLE_MCP_CERTIFICATE_DIR` to the same
kind of trusted directory.

### From source

Install [uv](https://docs.astral.sh/uv/), clone this repository, and run the setup script:

```bash
git clone https://github.com/sohampatwardhan/aptible-mcp.git
cd aptible-mcp
./scripts/setup.sh
```

The setup script detects package metadata corruption from an interrupted or older environment. It
moves an affected `.venv` to a timestamped `.venv.corrupt.*` backup and lets `uv` build a clean
replacement. After confirming the replacement works, you can remove that backup manually.

The script synchronizes the checked-in lockfile with `uv sync --locked`, verifies that the server
imports successfully, and reports whether Aptible authentication is available. It does not install
system software, modify shell profiles, or print credentials.

Authenticate either by logging in with the Aptible CLI or by setting `APTIBLE_TOKEN` in the server
environment.

## Usage

This MCP server assumes you are authenticated with `APTIBLE_TOKEN` or are currently logged in via
the [Aptible CLI](https://www.aptible.com/docs/reference/aptible-cli/overview).

Once logged in via the Aptible CLI, start the MCP server with:

```bash
uv run --locked --no-dev python main.py
```

Or add the MCP server to your client config:

```json
{
  "mcpServers": {
    "aptible": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/aptible-mcp",
        "--frozen",
        "--no-dev",
        "python",
        "main.py"
      ]
    }
  }
}
```

To determine where this configuration should live, reference the documentation for your MCP
client. For reference, Claude Desktop stores its configuration in
`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS and
`%APPDATA%\Claude\claude_desktop_config.json` on Windows. Claude Code stores its configuration in
`~/.claude.json`.

## Build the MCPB package

Install the official MCPB CLI, validate the 0.4 manifest, and pack the repository:

```bash
npm install -g @anthropic-ai/mcpb
mcpb validate .
mcpb pack . aptible-mcp-0.2.2.mcpb
```

`.mcpbignore` excludes tests, local environments, caches, agent/spec artifacts, and secrets from
the release archive. Before publishing, inspect the archive listing printed by `mcpb pack` and
confirm that it contains `manifest.json`, `pyproject.toml`, `uv.lock`, `main.py`, `api_client.py`,
`models/`, `examples/`, and `scripts/setup.sh`.

## Testing

To run tests + linting

```bash
just test

just typecheck

just lint
```

Before a release, run the complete dependency gate:

```bash
gh auth login
just security-audit
```

The command exports the locked runtime graph as CycloneDX, runs the installed `pip-audit`, uses
the authenticated GitHub advisory API without exposing the token on the command line, and batches
NVD CVE lookups (up to 100 IDs per request) so the public NVD rate limit is respected. If you have
an NVD API key, set `NVD_API_KEY`; the audit also works without one. Reports are written under
`.security/dependency-audit/` and are excluded from packages and Git.


## Resource Models

All resource models extend the base `ResourceBase` class and include:
- `id` - Unique identifier
- `handle` - Human-readable identifier
- Additional resource-specific fields

## Resource Managers

Each resource type has a dedicated manager class that extends `ResourceManager` and provides:
- `list()` - List all resources
- `get(identifier)` - Get a specific resource
- `create(data)` - Create a new resource
- Resource-specific operations
