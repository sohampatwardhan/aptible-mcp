import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Literal, Optional

from api_client import AptibleApiClient
from examples import aptible, github_actions
from models import (
    AccountManager,
    App,
    AppManager,
    BackupManager,
    CertificateManager,
    Database,
    DatabaseManager,
    LogDrainManager,
    MaintenanceManager,
    MetricDrainManager,
    OperationManager,
    StackManager,
    VhostManager,
)
from models.service import Service, ServiceManager

api_client = AptibleApiClient()


@asynccontextmanager
async def app_lifespan(_: FastMCP) -> AsyncIterator[None]:
    """Release the shared asynchronous HTTP connection pool on shutdown."""
    try:
        yield
    finally:
        await api_client.close()


mcp = FastMCP("aptible", lifespan=app_lifespan)


account_manager = AccountManager(api_client)
app_manager = AppManager(api_client)
backup_manager = BackupManager(api_client)
certificate_manager = CertificateManager(api_client)
database_manager = DatabaseManager(api_client)
log_drain_manager = LogDrainManager(api_client)
maintenance_manager = MaintenanceManager(api_client)
metric_drain_manager = MetricDrainManager(api_client)
operation_manager = OperationManager(api_client)
stack_manager = StackManager(api_client)
service_manager = ServiceManager(api_client)
vhost_manager = VhostManager(api_client)
app_manager.service_manager = service_manager


DATABASE_DISCOVERY_ATTEMPTS = 10
DATABASE_DISCOVERY_DELAY_SECONDS = 1.0


def _model_int_field(resource: Any, field: str) -> Optional[int]:
    """Read an integer field, including Pydantic computed fields, safely."""
    value = resource.model_dump().get(field)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


@mcp.tool()
async def listAccounts() -> List[Dict[str, Any]]:
    """
    List all accounts/environments.
    """
    accounts = await account_manager.list()
    return [account.model_dump() for account in accounts]


@mcp.tool()
async def getAccount(account_handle: str) -> Optional[Dict[str, Any]]:
    """
    Get account/environment by handle.
    """
    account = await account_manager.get(account_handle)
    return account.model_dump() if account else None


@mcp.tool()
async def getAccountsByStack(stack_name: str) -> List[Dict[str, Any]]:
    """
    Get all accounts/environments in a stack by stack name.
    """
    stack = await stack_manager.get(stack_name)
    if not stack:
        raise Exception(f"Stack {stack_name} not found.")

    accounts = await account_manager.get_by_stack_id(stack.id)
    return [account.model_dump() for account in accounts]


@mcp.tool()
async def createAccount(account_name: str, stack_name: str) -> Dict[str, Any]:
    """
    Create a new account/environment.
    """
    stack = await stack_manager.get(stack_name)
    if not stack:
        raise Exception(f"Stack {stack_name} not found.")
    data = {"handle": account_name, "stack_id": stack.id}
    account = await account_manager.create(data)
    return account.model_dump()


@mcp.tool()
async def renameEnvironment(account_handle: str, new_handle: str) -> Dict[str, Any]:
    """
    Rename an environment to a new handle. Raises if the new handle is
    already in use within the organization.
    """
    account = await account_manager.get(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")

    renamed_account = await account_manager.rename(account.id, new_handle)
    return renamed_account.model_dump()


@mcp.tool()
async def getEnvironmentCaCertificate(account_handle: str) -> Optional[str]:
    """
    Get an environment's configured CA certificate, or None if none is
    configured.
    """
    account = await account_manager.get(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")

    return await account_manager.get_ca_certificate(account.id)


@mcp.tool()
async def listApps() -> List[Dict[str, Any]]:
    """
    List all apps.
    """
    apps = await app_manager.list()
    return [app.model_dump() for app in apps]


@mcp.tool()
async def getApp(
    app_handle: str, account_handle: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get app by handle.

    Because app names are only unique within an account/environment,
    an account handle can also be provided.
    """
    apps = await app_manager.list()
    matches = [app for app in apps if app.handle == app_handle]

    if len(matches) == 0:
        raise Exception(f"No app with handle {app_handle}.")

    if len(matches) == 1 and not account_handle:
        return matches[0].model_dump()

    if account_handle:
        account = await account_manager.get(account_handle)
        if not account:
            raise Exception(f"Account {account_handle} not found.")

        account_matches = [app for app in matches if app.account_id == account.id]

        if not account_matches:
            raise Exception(
                f"No app with handle {app_handle} in account {account_handle}."
            )

        return account_matches[0].model_dump()

    raise Exception(
        f"Multiple apps found with handle {app_handle}. Please provide an account handle."
    )


@mcp.tool()
async def createApp(
    app_handle: str, account_handle: str, docker_image: str
) -> Dict[str, Any]:
    """
    Create a new app.
    """
    account = await account_manager.get(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")
    data = {
        "handle": app_handle,
        "account_id": account.id,
        "docker_image": docker_image,
    }
    app = await app_manager.create(data)
    return app.model_dump()


@mcp.tool()
async def configureApp(
    app_handle: str, account_handle: Optional[str], env: Dict[str, str]
) -> None:
    """
    Configure app environment variables.
    """
    app_data = await getApp(app_handle, account_handle)
    if not app_data:
        raise Exception(f"App {app_handle} not found.")

    app = App.model_validate(app_data)
    await app_manager.configure(app.id, env)


@mcp.tool()
async def deleteApp(app_handle: str, account_handle: Optional[str] = None) -> None:
    """
    Delete an app.
    """
    app_data = await getApp(app_handle, account_handle)
    if not app_data:
        raise Exception(f"App {app_handle} not found.")

    app = App.model_validate(app_data)
    await app_manager.delete(app.id)


@mcp.tool()
async def renameApp(
    app_handle: str, new_handle: str, account_handle: Optional[str] = None
) -> Dict[str, Any]:
    """
    Rename an app to a new handle. Raises if the new handle is already in
    use within the app's environment.
    """
    app_data = await getApp(app_handle, account_handle)
    if not app_data:
        raise Exception(f"App {app_handle} not found.")

    app = App.model_validate(app_data)
    renamed_app = await app_manager.rename(app.id, new_handle)
    return renamed_app.model_dump()


@mcp.tool()
async def deployApp(
    app_handle: str,
    docker_image: Optional[str] = None,
    git_ref: Optional[str] = None,
    account_handle: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trigger a deploy of a new Docker image (or Git reference) to an app.
    If neither is supplied, performs a standard redeploy of the current
    release. Waits for the deploy operation to complete before returning.
    """
    app_data = await getApp(app_handle, account_handle)
    if not app_data:
        raise Exception(f"App {app_handle} not found.")

    app = App.model_validate(app_data)
    deployed_app = await app_manager.deploy(app.id, docker_image, git_ref)
    return deployed_app.model_dump()


@mcp.tool()
async def rebuildApp(
    app_handle: str, account_handle: Optional[str] = None
) -> Dict[str, Any]:
    """
    Rebuild an app's current release, picking up underlying image layer
    updates without a new deploy. Waits for the rebuild operation to
    complete before returning.
    """
    app_data = await getApp(app_handle, account_handle)
    if not app_data:
        raise Exception(f"App {app_handle} not found.")

    app = App.model_validate(app_data)
    rebuilt_app = await app_manager.rebuild(app.id)
    return rebuilt_app.model_dump()


@mcp.tool()
async def restartApp(
    app_handle: str, account_handle: Optional[str] = None
) -> Dict[str, Any]:
    """
    Restart an app's containers without a full deploy. Waits for the
    restart operation to complete before returning.
    """
    app_data = await getApp(app_handle, account_handle)
    if not app_data:
        raise Exception(f"App {app_handle} not found.")

    app = App.model_validate(app_data)
    restarted_app = await app_manager.restart(app.id)
    return restarted_app.model_dump()


@mcp.tool()
async def runAppCommand(
    app_handle: str,
    command: str,
    interactive: bool = False,
    account_handle: Optional[str] = None,
) -> str:
    """
    Run a single one-off command inside a new ephemeral container built from
    the app's current release, and return the command's captured output. The
    command runs to completion against live app data (it can read and write
    the app's databases), and running containers are left untouched. If the
    operation fails, an error is raised carrying any output captured before
    the failure.
    """
    app_data = await getApp(app_handle, account_handle)
    if not app_data:
        raise Exception(f"App {app_handle} not found.")

    app = App.model_validate(app_data)
    return await app_manager.run_command(app.id, command, interactive)


@mcp.tool()
async def listAvailableDatabaseTypes() -> List[Dict[str, Any]]:
    """
    List all available database types. When creating a database,
    the image id provided via this method is needed.
    """
    db_types = await database_manager.list_available_types()
    return [db_type.model_dump() for db_type in db_types]


@mcp.tool()
async def listDatabases() -> List[Dict[str, Any]]:
    """
    List all databases.
    """
    databases = await database_manager.list()
    return [db.model_dump() for db in databases]


@mcp.tool()
async def getDatabase(
    database_handle: str, account_handle: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get database by handle and optionally account handle.
    """
    databases = await database_manager.list()
    matches = [db for db in databases if db.handle == database_handle]

    if len(matches) == 0:
        raise Exception(f"No database with handle {database_handle}.")

    if len(matches) == 1 and not account_handle:
        return matches[0].model_dump()

    if account_handle:
        account = await account_manager.get(account_handle)
        if not account:
            raise Exception(f"Account {account_handle} not found.")

        account_matches = [db for db in matches if db.account_id == account.id]

        if not account_matches:
            raise Exception(
                f"No database with handle {database_handle} in account {account_handle}."
            )

        return account_matches[0].model_dump()

    raise Exception(
        f"Multiple databases found with handle {database_handle}. Please provide an account handle."
    )


async def _snapshot_database_ids(database_handle: str, account_id: int) -> set[int]:
    """Capture same-account IDs so discovery cannot select an old namesake."""
    databases = await database_manager.list()
    return {
        database.id
        for database in databases
        if database.handle == database_handle
        and _model_int_field(database, "account_id") == account_id
    }


async def _find_new_database(
    database_handle: str,
    existing_ids: set[int],
    account_id: int,
) -> Dict[str, Any]:
    """Reconcile a newly-created database within one account for a bounded time."""
    last_match_count = 0
    for attempt in range(DATABASE_DISCOVERY_ATTEMPTS):
        databases = await database_manager.list()
        matches = [
            database
            for database in databases
            if database.handle == database_handle
            and database.id not in existing_ids
            and _model_int_field(database, "account_id") == account_id
        ]
        last_match_count = len(matches)
        if last_match_count == 1:
            return matches[0].model_dump()
        if last_match_count > 1:
            break
        if attempt + 1 < DATABASE_DISCOVERY_ATTEMPTS:
            await asyncio.sleep(DATABASE_DISCOVERY_DELAY_SECONDS)

    raise Exception(
        f"Expected one new database with handle {database_handle} in account "
        f"{account_id}, found {last_match_count}."
    )


async def _restore_account_id(
    backup_id: int, destination_account_id: Optional[int]
) -> int:
    """Resolve the restore target before starting its billable operation."""
    if destination_account_id is not None:
        return destination_account_id

    backup = await backup_manager.get_by_id(backup_id)
    if not backup:
        raise Exception(f"Backup {backup_id} not found.")
    backup_account_id = _model_int_field(backup, "account_id")
    if backup_account_id is not None:
        return backup_account_id

    source_database_id = _model_int_field(backup, "database_id")
    if source_database_id is not None:
        source_database = await database_manager.get_by_id(source_database_id)
        if source_database:
            source_account_id = _model_int_field(source_database, "account_id")
            if source_account_id is not None:
                return source_account_id

    raise ValueError(
        f"Cannot determine the source account for backup {backup_id}; "
        "provide destination_account_handle explicitly."
    )


@mcp.tool()
async def createDatabase(
    database_handle: str, account_handle: str, image_id: int
) -> Dict[str, Any]:
    """
    Create a new database.
    The image_id should be the ID found via listAvailableDatabaseTypes.
    """
    account = await account_manager.get(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")

    data = {
        "handle": database_handle,
        "account_id": account.id,
        "image_id": image_id,
    }
    database = await database_manager.create(data)
    return database.model_dump()


@mcp.tool()
async def deleteDatabase(
    database_handle: str, account_handle: Optional[str] = None
) -> None:
    """
    Delete a database.
    """
    database_data = await getDatabase(database_handle, account_handle)
    if not database_data:
        raise Exception(f"Database {database_handle} not found.")

    database = Database.model_validate(database_data)
    await database_manager.delete(database.id)


@mcp.tool()
async def replicateDatabase(
    database_handle: str,
    replica_handle: str,
    container_size: Optional[int] = None,
    disk_size: Optional[int] = None,
    account_handle: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a read replica of an existing database and return the new replica
    database. This provisions an additional, separately-billed database that
    streams from the source; the source database itself is not modified. The
    replica is created in the source's environment, and this waits for the
    replication operation to finish before returning.
    """
    database_data = await getDatabase(database_handle, account_handle)
    if not database_data:
        raise Exception(f"Database {database_handle} not found.")

    database = Database.model_validate(database_data)
    source_account_id = _model_int_field(database, "account_id")
    if source_account_id is None:
        raise ValueError(
            f"Database {database.id} does not expose its account relation."
        )
    existing_ids = await _snapshot_database_ids(replica_handle, source_account_id)
    await database_manager.replicate(
        database.id, replica_handle, container_size, disk_size
    )

    return await _find_new_database(replica_handle, existing_ids, source_account_id)


@mcp.tool()
async def cloneDatabase(
    database_handle: str, new_handle: str, account_handle: Optional[str] = None
) -> Dict[str, Any]:
    """
    Clone a database into a new, fully independent database and return it.
    This provisions an additional, separately-billed database holding a
    point-in-time copy of the source's data; the source database itself is
    not modified, and the clone does not stay in sync with it afterward.
    Raises if the new handle is already in use in the target environment.
    """
    database_data = await getDatabase(database_handle, account_handle)
    if not database_data:
        raise Exception(f"Database {database_handle} not found.")

    database = Database.model_validate(database_data)
    source_account_id = _model_int_field(database, "account_id")
    if source_account_id is None:
        raise ValueError(
            f"Database {database.id} does not expose its account relation."
        )
    existing_ids = await _snapshot_database_ids(new_handle, source_account_id)
    await database_manager.clone(database.id, new_handle)

    return await _find_new_database(new_handle, existing_ids, source_account_id)


@mcp.tool()
async def modifyDatabaseIops(
    database_handle: str,
    provisioned_iops: Optional[int] = None,
    ebs_volume_type: Optional[str] = None,
    account_handle: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Change an existing database's provisioned IOPS and/or EBS volume type in
    place, and return the refreshed database. This modifies the live database's
    underlying storage and waits for the modify operation to complete; a failed
    operation leaves the database on its previous settings.
    """
    if provisioned_iops is None and ebs_volume_type is None:
        raise ValueError(
            "Must specify at least one of provisioned_iops or ebs_volume_type"
        )

    database_data = await getDatabase(database_handle, account_handle)
    if not database_data:
        raise Exception(f"Database {database_handle} not found.")

    database = Database.model_validate(database_data)
    modified_database = await database_manager.modify_iops(
        database.id, provisioned_iops, ebs_volume_type
    )
    return modified_database.model_dump()


@mcp.tool()
async def resizeDatabase(
    database_handle: str,
    container_size: Optional[int] = None,
    disk_size: Optional[int] = None,
    instance_profile: Optional[str] = None,
    account_handle: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Change an existing database's container size (MB of RAM), disk size (GB),
    and/or container profile, and return the refreshed database. Aptible
    applies this through a restart operation, so the database is briefly
    unavailable while it is resized. Disk size can only be increased, never
    decreased. A failed operation leaves the database at its previous size.
    """
    if container_size is None and disk_size is None and instance_profile is None:
        raise ValueError(
            "Must specify at least one of container_size, disk_size, or instance_profile"
        )

    database_data = await getDatabase(database_handle, account_handle)
    if not database_data:
        raise Exception(f"Database {database_handle} not found.")

    database = Database.model_validate(database_data)
    resized_database = await database_manager.resize(
        database.id, container_size, disk_size, instance_profile
    )
    return resized_database.model_dump()


@mcp.tool()
async def reloadDatabase(
    database_handle: str, account_handle: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reload an existing database, replacing its container with a fresh one
    without changing its configuration, and return the refreshed database.
    The database is briefly unavailable while it reloads. Its data and
    settings are preserved.
    """
    database_data = await getDatabase(database_handle, account_handle)
    if not database_data:
        raise Exception(f"Database {database_handle} not found.")

    database = Database.model_validate(database_data)
    reloaded_database = await database_manager.reload(database.id)
    return reloaded_database.model_dump()


@mcp.tool()
async def renameDatabase(
    database_handle: str, new_handle: str, account_handle: Optional[str] = None
) -> Dict[str, Any]:
    """
    Rename a database to a new handle and return the updated database. This
    changes only the database's name in Aptible; it does not restart the
    database or change its connection credentials. Raises if the new handle
    is already in use within the same environment.
    """
    database_data = await getDatabase(database_handle, account_handle)
    if not database_data:
        raise Exception(f"Database {database_handle} not found.")

    database = Database.model_validate(database_data)
    renamed_database = await database_manager.rename(database.id, new_handle)
    return renamed_database.model_dump()


@mcp.tool()
async def restartDatabase(
    database_handle: str, account_handle: Optional[str] = None
) -> Dict[str, Any]:
    """
    Restart an existing database without changing its size or configuration,
    and return the refreshed database. The database is briefly unavailable
    while it restarts. Use resizeDatabase instead when the restart is meant
    to apply a new container or disk size.
    """
    database_data = await getDatabase(database_handle, account_handle)
    if not database_data:
        raise Exception(f"Database {database_handle} not found.")

    database = Database.model_validate(database_data)
    restarted_database = await database_manager.restart(database.id)
    return restarted_database.model_dump()


@mcp.tool()
async def listDatabaseVersions(database_type: str) -> List[Dict[str, Any]]:
    """
    List the database images (versions) available for a database type, such
    as "postgresql" or "redis", to identify valid upgrade targets. Read-only.
    Raises if no such database type exists.
    """
    images = await database_manager.list_versions_for_type(database_type)
    return [image.model_dump() for image in images]


@mcp.tool()
async def listDatabaseBackups(
    database_handle: str,
    account_handle: Optional[str] = None,
    max_age: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List backups for a database, optionally excluding backups older than
    max_age (a relative duration string like "1w"/"1y"/"30d").
    """
    database_data = await getDatabase(database_handle, account_handle)
    if not database_data:
        raise Exception(f"Database {database_handle} not found.")

    database = Database.model_validate(database_data)
    backups = await backup_manager.list_for_database(database.id, max_age)
    return [backup.model_dump() for backup in backups]


@mcp.tool()
async def restoreDatabaseFromBackup(
    backup_id: int, new_handle: str, destination_account_handle: Optional[str] = None
) -> Dict[str, Any]:
    """
    Restore a backup into a new database with the given handle. This always
    creates a new database rather than restoring in place; if a destination
    account handle is provided, the new database is created there instead of
    the backup's source environment.
    """
    destination_account_id = None
    if destination_account_handle:
        account = await getAccount(destination_account_handle)
        if not account:
            raise Exception(f"Account {destination_account_handle} not found.")
        destination_account_id = account["id"]

    target_account_id = await _restore_account_id(backup_id, destination_account_id)
    existing_ids = await _snapshot_database_ids(new_handle, target_account_id)
    await backup_manager.restore(backup_id, new_handle, destination_account_id)

    return await _find_new_database(new_handle, existing_ids, target_account_id)


@mcp.tool()
async def listOrphanedBackups(account_handle: str) -> List[Dict[str, Any]]:
    """
    List orphaned backups (backups whose source database has been deleted)
    for an environment.
    """
    account = await getAccount(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")

    backups = await backup_manager.list_orphaned(account["id"])
    return [backup.model_dump() for backup in backups]


@mcp.tool()
async def purgeBackup(backup_id: int) -> None:
    """
    Purge a backup by identifier.
    """
    await backup_manager.purge(backup_id)


@mcp.tool()
async def createLogDrain(
    account_handle: str,
    handle: str,
    drain_type: str,
    config: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Create and provision a log drain for an environment. Supported drain
    types are syslog_tls_tcp, https_post, and elasticsearch_database; any
    other type is rejected before an API call is made. Additional
    destination-specific fields (e.g. host/port/token) are passed via config.
    """
    account = await getAccount(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")

    drain = await log_drain_manager.create(
        account["id"], handle, drain_type, **(config or {})
    )
    return drain.model_dump()


@mcp.tool()
async def listLogDrains(account_handle: str) -> List[Dict[str, Any]]:
    """
    List all log drains provisioned in an environment.
    """
    account = await getAccount(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")

    drains = await log_drain_manager.list_for_account(account["id"])
    return [drain.model_dump() for drain in drains]


@mcp.tool()
async def deprovisionLogDrain(drain_id: int) -> None:
    """
    Deprovision a log drain by identifier.
    """
    await log_drain_manager.deprovision(drain_id)


@mcp.tool()
async def createMetricDrain(
    account_handle: str,
    handle: str,
    drain_type: str,
    drain_configuration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Provision a metric drain in an environment. Supported drain types are
    influxdb_database, influxdb, influxdb2, and datadog; any other type is
    rejected before an API call is made. Destination-specific fields are
    passed as drain_configuration.
    """
    account = await getAccount(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")

    drain = await metric_drain_manager.create(
        account["id"], handle, drain_type, drain_configuration
    )
    return drain.model_dump()


@mcp.tool()
async def listMetricDrains(account_handle: str) -> List[Dict[str, Any]]:
    """
    List all metric drains provisioned in an environment.
    """
    account = await getAccount(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")

    drains = await metric_drain_manager.list_for_account(account["id"])
    return [drain.model_dump() for drain in drains]


@mcp.tool()
async def deprovisionMetricDrain(drain_id: int) -> None:
    """
    Deprovision a metric drain by identifier.
    """
    await metric_drain_manager.deprovision(drain_id)


@mcp.tool()
async def uploadCertificate(
    account_handle: str, certificate_filename: str, private_key_filename: str
) -> Dict[str, Any]:
    """
    Upload a certificate and private key from files in the trusted directory
    configured by APTIBLE_MCP_CERTIFICATE_DIR. Only filenames are accepted;
    paths outside that directory are rejected. Concatenate intermediate
    certificates into the certificate file because the API has no separate
    certificate-chain field.
    """
    account = await getAccount(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")

    certificate_body, private_key = await asyncio.gather(
        asyncio.to_thread(_read_certificate_file, certificate_filename),
        asyncio.to_thread(_read_certificate_file, private_key_filename, True),
    )
    certificate = await certificate_manager.upload(
        account["id"], certificate_body, private_key
    )
    return certificate.model_dump()


def _read_certificate_file(filename: str, private: bool = False) -> str:
    """Read a bounded certificate file from the explicitly trusted directory."""
    configured_dir = os.environ.get("APTIBLE_MCP_CERTIFICATE_DIR")
    if not configured_dir:
        raise RuntimeError(
            "APTIBLE_MCP_CERTIFICATE_DIR must be set before uploading certificates."
        )

    trusted_dir = Path(configured_dir).expanduser().resolve(strict=True)
    file_path = (trusted_dir / filename).resolve(strict=True)
    try:
        file_path.relative_to(trusted_dir)
    except ValueError as exc:
        raise ValueError(
            "Certificate filenames must stay within the trusted directory."
        ) from exc
    if not file_path.is_file():
        raise ValueError(f"Certificate file is not a regular file: {filename}")
    if file_path.stat().st_size > 1024 * 1024:
        raise ValueError(f"Certificate file exceeds the 1 MiB limit: {filename}")
    if private and os.name == "posix" and file_path.stat().st_mode & 0o077:
        raise PermissionError(
            f"Private key file must not be accessible by group or others: {filename}"
        )
    return file_path.read_text(encoding="utf-8")


@mcp.tool()
async def listCertificates(account_handle: str) -> List[Dict[str, Any]]:
    """
    List certificates uploaded to an environment.
    """
    account = await getAccount(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")

    certificates = await certificate_manager.list_for_account(account["id"])
    return [certificate.model_dump() for certificate in certificates]


@mcp.tool()
async def listMaintenanceEntries(account_handle: str) -> List[Dict[str, Any]]:
    """
    List the apps and databases in an environment that are currently scheduled
    for or undergoing Aptible maintenance, so their unavailability is not
    mistaken for an incident. Each entry is tagged with a resource_type of
    "app" or "database". Read-only.
    """
    account = await getAccount(account_handle)
    if not account:
        raise Exception(f"Account {account_handle} not found.")

    entries = await maintenance_manager.list_for_account(account["id"])
    return [entry.model_dump() for entry in entries]


@mcp.tool()
async def listStacks() -> List[Dict[str, Any]]:
    """
    List all stacks.
    """
    stacks = await stack_manager.list()
    return [stack.model_dump() for stack in stacks]


@mcp.tool()
async def getStack(stack_name: str) -> Optional[Dict[str, Any]]:
    """
    Get stack by name.
    """
    stack = await stack_manager.get(stack_name)
    return stack.model_dump() if stack else None


@mcp.tool()
async def listVhosts() -> List[Dict[str, Any]]:
    """
    List all vhosts/endpoints).
    """
    vhosts = await vhost_manager.list()
    return [vhost.model_dump() for vhost in vhosts]


@mcp.tool()
async def getVhost(vhost_id: str) -> Optional[Dict[str, Any]]:
    """
    Get vhost by ID.
    """
    vhost = await vhost_manager.get(vhost_id)
    return vhost.model_dump() if vhost else None


@mcp.tool()
async def createVhost(
    app_handle: str, service_handle: str, account_handle: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new vhost/endpoint for a Service.

    Service handle is a bit weird, since it's auto-assigned by Aptible
    and not set by the user. The user assigns with process_type in the procfile.
    Since this is being used by AI, that shouldn't matter, though.

    This tool intentionally creates only a default Aptible-hosted service
    endpoint. Use createCustomDomainEndpoint, createTypedEndpoint, or
    createDatabaseEndpoint for other endpoint types.
    """
    app_data = await getApp(app_handle, account_handle)
    if not app_data:
        raise Exception(f"App {app_handle} not found.")

    app = App.model_validate(app_data)

    services = await service_manager.list_by_app(app.id)
    service_matches = [s for s in services if s.handle == service_handle]

    if not service_matches:
        raise Exception(
            f"No service with handle {service_handle} found in app {app_handle}."
        )

    service = service_matches[0]
    vhost = await vhost_manager.create({"service_id": service.id})
    return vhost.model_dump()


@mcp.tool()
async def deleteVhost(vhost_id: int) -> None:
    """
    Delete a vhost/endpoint.
    """
    await vhost_manager.delete_vhost(vhost_id)


@mcp.tool()
async def listServices(
    app_handle: str, account_handle: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all services for a specific app.
    """
    app_data = await getApp(app_handle, account_handle)
    if not app_data:
        raise Exception(f"App {app_handle} not found.")

    app = App.model_validate(app_data)
    services = await service_manager.list_by_app(app.id)
    return [service.model_dump() for service in services]


@mcp.tool()
async def getService(
    app_handle: str, service_handle: str, account_handle: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a service by handle within a specific app.
    """
    app_data = await getApp(app_handle, account_handle)
    if not app_data:
        raise Exception(f"App {app_handle} not found.")

    app = App.model_validate(app_data)
    service = await service_manager.get_by_handle_and_app(service_handle, app.id)

    if not service:
        raise Exception(
            f"No service with handle {service_handle} found in app {app_handle}."
        )

    return service.model_dump()


@mcp.tool()
async def scaleService(
    app_handle: str,
    service_handle: str,
    container_count: Optional[int] = None,
    container_memory_limit_mb: Optional[int] = None,
    account_handle: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Scale a service by changing container count or size.
    """
    if container_count is None and container_memory_limit_mb is None:
        raise ValueError(
            "Must specify at least one of container_count or container_size"
        )

    service_data = await getService(app_handle, service_handle, account_handle)
    service = Service.model_validate(service_data)

    updated_service = await service_manager.scale(
        service.id, container_count, container_memory_limit_mb
    )
    return updated_service.model_dump()


@mcp.tool()
async def getServiceSettings(
    app_handle: str, service_handle: str, account_handle: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a service's current settings: force_zero_downtime,
    naive_health_check, restart_free_scaling, stop_timeout.
    """
    service_data = await getService(app_handle, service_handle, account_handle)
    service = Service.model_validate(service_data)

    return await service_manager.get_settings(service.id)


@mcp.tool()
async def updateServiceSettings(
    app_handle: str,
    service_handle: str,
    settings: Dict[str, Any],
    account_handle: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update one or more service settings (force_zero_downtime,
    naive_health_check, restart_free_scaling, stop_timeout). Raises if an
    unsupported setting name is provided.
    """
    service_data = await getService(app_handle, service_handle, account_handle)
    service = Service.model_validate(service_data)

    updated_service = await service_manager.update_settings(service.id, **settings)
    return updated_service.model_dump()


@mcp.tool()
async def listServiceVhosts(
    app_handle: str, service_handle: str, account_handle: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all vhosts for a specific service.
    """
    service_data = await getService(app_handle, service_handle, account_handle)
    service = Service.model_validate(service_data)

    vhosts = await vhost_manager.list_by_service(service.id)
    return [vhost.model_dump() for vhost in vhosts]


@mcp.tool()
async def createCustomDomainEndpoint(
    app_handle: str,
    service_handle: str,
    domain: str,
    managed_tls: bool = True,
    certificate_fingerprint: Optional[str] = None,
    container_ports: Optional[List[int]] = None,
    account_handle: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an HTTP/gRPC endpoint for a service bound to a custom domain, either
    with Aptible-managed TLS or a customer-provided certificate referenced by
    fingerprint. Managed TLS is not supported for apex or wildcard domains.
    """
    service_data = await getService(app_handle, service_handle, account_handle)
    service = Service.model_validate(service_data)

    vhost = await vhost_manager.create_custom_domain(
        service.id,
        domain,
        managed_tls=managed_tls,
        certificate_fingerprint=certificate_fingerprint,
        container_ports=container_ports,
    )
    return vhost.model_dump()


@mcp.tool()
async def createTypedEndpoint(
    app_handle: str,
    service_handle: str,
    domain: str,
    endpoint_type: Literal["tcp", "tls", "grpc"],
    container_ports: Optional[List[int]] = None,
    certificate_fingerprint: Optional[str] = None,
    account_handle: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a non-default endpoint type (tcp, tls, or grpc) for a service, bound
    to the given container ports. A TLS endpoint requires a certificate
    reference (certificate_fingerprint); managed TLS is not used for this tool.
    """
    if endpoint_type not in {"tcp", "tls", "grpc"}:
        raise ValueError("endpoint_type must be one of: tcp, tls, grpc")

    service_data = await getService(app_handle, service_handle, account_handle)
    service = Service.model_validate(service_data)

    vhost = await vhost_manager.create_custom_domain(
        service.id,
        domain,
        managed_tls=False,
        certificate_fingerprint=certificate_fingerprint,
        endpoint_type=endpoint_type,
        container_ports=container_ports,
    )
    return vhost.model_dump()


@mcp.tool()
async def createDatabaseEndpoint(
    database_handle: str,
    account_handle: Optional[str] = None,
    internal: bool = False,
    ip_whitelist: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create an endpoint exposing a database directly, so external clients can
    connect to it. Returns the resulting endpoint's hostname and port.
    """
    database_data = await getDatabase(database_handle, account_handle)
    if not database_data:
        raise Exception(f"Database {database_handle} not found.")

    database = Database.model_validate(database_data)
    vhost = await vhost_manager.create_database_endpoint(
        database.id, internal=internal, ip_whitelist=ip_whitelist
    )
    return vhost.model_dump()


@mcp.tool()
async def modifyEndpoint(
    vhost_id: int,
    container_ports: Optional[List[int]] = None,
    certificate_fingerprint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Modify an existing endpoint's supported settings (container ports and/or
    certificate reference).
    """
    fields: Dict[str, Any] = {}
    if container_ports is not None:
        fields["container_ports"] = container_ports
    if certificate_fingerprint is not None:
        fields["certificate_fingerprint"] = certificate_fingerprint

    if not fields:
        raise ValueError(
            "Must specify at least one of container_ports or certificate_fingerprint"
        )

    vhost = await vhost_manager.modify(vhost_id, **fields)
    return vhost.model_dump()


@mcp.tool()
async def renewEndpoint(vhost_id: int) -> Dict[str, Any]:
    """
    Trigger a TLS renewal for a managed-TLS app endpoint.
    """
    vhost = await vhost_manager.renew(vhost_id)
    return vhost.model_dump()


@mcp.tool()
async def getOperationsForApp(
    app_handle: str, account_handle: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get recent operations for a specific app.
    """
    app_data = await getApp(app_handle, account_handle)
    if not app_data:
        raise Exception(f"App {app_handle} not found.")

    app = App.model_validate(app_data)
    operations = await operation_manager.get_operations_for_app(app.id)
    return operations


@mcp.tool()
async def getOperationsForDatabase(
    database_handle: str, account_handle: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get recent operations for a specific database.
    """
    database_data = await getDatabase(database_handle, account_handle)
    if not database_data:
        raise Exception(f"Database {database_handle} not found.")

    database = Database.model_validate(database_data)
    operations = await operation_manager.get_operations_for_database(database.id)
    return operations


@mcp.tool()
async def getOperationsForVhost(vhost_id: int) -> List[Dict[str, Any]]:
    """
    Get recent operations for a specific vhost/endpoint.
    """
    operations = await operation_manager.get_operations_for_vhost(vhost_id)
    return operations


@mcp.tool()
async def getOperationLogs(operation_id: int) -> str:
    """
    Get logs for a specific operation.
    """
    logs = await operation_manager.logs(operation_id)
    return logs


@mcp.tool()
async def cancelOperation(operation_id: int) -> Dict[str, Any]:
    """
    Cancel an in-progress (queued or running) operation. Raises if the
    operation has already reached a terminal state (succeeded or failed),
    or if no operation exists with the given id.
    """
    operation = await operation_manager.cancel(operation_id)
    return operation.model_dump()


@mcp.tool()
async def getProcfileExample() -> str:
    """
    Gets an example Procfile for defining app processes.
    Keep in mind that 1-off tasks like running migrations are better suited
    for processes run via .aptible.yml, and do not belong in the Procfile.


    The finalized Procfile file should be located in /.aptible/Procfile
    in the build Docker image.
    """
    return aptible.PROCFILE


@mcp.tool()
async def getAptibleYamlExample() -> str:
    """
    Gets an example aptible.yml configuration file for deploy hooks.

    The finalized .aptible.yml file should be located in /.aptible/.aptible.yml
    in the build Docker image.
    """
    return aptible.APTIBLE_YAML


@mcp.tool()
async def getEndpointProvisionExample() -> str:
    """
    Gets an example of a GitHub Action for provisioning an endpoint.
    """
    return github_actions.PROVISION_ENDPOINT


@mcp.tool()
async def getAppProvisionExample() -> str:
    """
    Gets an example of a GitHub Action for provisioning an app.
    """
    return github_actions.PROVISION_APP


@mcp.tool()
async def getAppDeprovisionExample() -> str:
    """
    Gets an example of a GitHub Action for deprovisioning an app.
    """
    return github_actions.DEPROVISION_APP


@mcp.tool()
async def getAppConfigureExample() -> str:
    """
    Gets an example of a GitHub Action for configuring an app.
    """
    return github_actions.CONFIGURE_APP


@mcp.tool()
async def getDatabaseProvisionExample() -> str:
    """
    Gets an example of a GitHub Action for provisioning a database.
    """
    return github_actions.PROVISION_DATABASE


@mcp.tool()
async def getDatabaseDeprovisionExample() -> str:
    """
    Gets an example of a GitHub Action for deprovisioning a database.
    """
    return github_actions.DEPROVISION_DATABASE


@mcp.tool()
async def getDatabaseRestoreExample() -> str:
    """
    Gets an example of a GitHub Action for restoring a database from backup.
    """
    return github_actions.RESTORE_FROM_BACKUP


@mcp.tool()
async def getBuildDeployExample() -> str:
    """
    Gets an example of a GitHub Action for building, publishing, and deploying an app.
    """
    return github_actions.BUILD_PUBLISH_DEPLOY


if __name__ == "__main__":
    mcp.run(transport="stdio")
