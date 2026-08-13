# Aptible MCP

An MCP server for [Aptible](https://www.aptible.com).

> [!NOTE]
> This MCP server is still under development.

## Overview

This project provides MCP tools for interacting with the Aptible API. It uses Pydantic models for standardized data handling and provides consistent CRUD operations for Aptible resources.

## Features

- Standardized models for Aptible resources (Account, App, Database, etc.)
- Consistent CRUD operations across resource types
- Pydantic validation for request/response data
- Type hints for better developer experience

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

## Usage

This MCP server assumes you are currently logged in via the [Aptible CLI](https://www.aptible.com/docs/reference/aptible-cli/overview). This README also assumes you have [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just) installed, which you can do using Homebrew by running `brew install uv just`.

Once logged in via the Aptible CLI, start the MCP server with:

```bash
uv run python main.py
```

Or add the MCP server to your client config:

```json
{
  "mcpServers": {
    "aptible": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/aptible-mcp",
        "run",
        "main.py"
      ]
    }
  }
}
```

To determine where this configuration should live, reference the documentation for your MCP Client. For reference, Claude Desktop stores [its configuration](https://modelcontextprotocol.io/docs/develop/connect-local-servers) in `~/Library/Application Support/Claude/claude_desktop_config.json` on MacOS and `%APPDATA%\Claude\claude_desktop_config.json` on Windows. Claude Code stores [its configuration](https://code.claude.com/docs/en/settings) in `~/.claude.json`.

## Testing

To run tests + linting

```bash
just test

just typecheck

just lint
```


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
