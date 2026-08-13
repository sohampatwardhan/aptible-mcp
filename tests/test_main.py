import pytest
from unittest.mock import AsyncMock, Mock, patch

from models.app import App
from models.account import Account
from models.backup import Backup
from models.certificate import Certificate
from models.database import Database
from models.log_drain import LogDrain
from models.maintenance import MaintenanceEntry
from models.metric_drain import MetricDrain
from models.service import Service
from models.stack import Stack
from models.database import DatabaseImage
from models.operation import Operation
from models.vhost import Vhost
from main import (
    listAccounts,
    getAccount,
    getAccountsByStack,
    createAccount,
    renameEnvironment,
    getEnvironmentCaCertificate,
    listStacks,
    getStack,
    listApps,
    getApp,
    createApp,
    configureApp,
    deleteApp,
    renameApp,
    deployApp,
    rebuildApp,
    restartApp,
    listAvailableDatabaseTypes,
    listDatabases,
    getDatabase,
    createDatabase,
    deleteDatabase,
    listDatabaseBackups,
    restoreDatabaseFromBackup,
    listOrphanedBackups,
    purgeBackup,
    createLogDrain,
    listLogDrains,
    deprovisionLogDrain,
    createMetricDrain,
    listMetricDrains,
    deprovisionMetricDrain,
    uploadCertificate,
    listCertificates,
    listVhosts,
    getVhost,
    createVhost,
    deleteVhost,
    listServices,
    getService,
    scaleService,
    getServiceSettings,
    updateServiceSettings,
    listServiceVhosts,
    createCustomDomainEndpoint,
    createTypedEndpoint,
    createDatabaseEndpoint,
    modifyEndpoint,
    renewEndpoint,
    cancelOperation,
    replicateDatabase,
    cloneDatabase,
    modifyDatabaseIops,
    resizeDatabase,
    reloadDatabase,
    renameDatabase,
    restartDatabase,
    listDatabaseVersions,
    listMaintenanceEntries,
    runAppCommand,
)


@pytest.fixture
def mock_account_manager():
    """
    Fixture providing a mock AccountManager.
    """
    with patch("main.account_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_stack_manager():
    """
    Fixture providing a mock StackManager.
    """
    with patch("main.stack_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_app_manager():
    """
    Fixture providing a mock AppManager.
    """
    with patch("main.app_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_database_manager():
    """
    Fixture providing a mock DatabaseManager.
    """
    with patch("main.database_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_backup_manager():
    """
    Fixture providing a mock BackupManager.
    """
    with patch("main.backup_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_log_drain_manager():
    """
    Fixture providing a mock LogDrainManager.
    """
    with patch("main.log_drain_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_maintenance_manager():
    """
    Fixture providing a mock MaintenanceManager.
    """
    with patch("main.maintenance_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_metric_drain_manager():
    """
    Fixture providing a mock MetricDrainManager.
    """
    with patch("main.metric_drain_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_certificate_manager():
    """
    Fixture providing a mock CertificateManager.
    """
    with patch("main.certificate_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_vhost_manager():
    """
    Fixture providing a mock VhostManager.
    """
    with patch("main.vhost_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_service_manager():
    """
    Fixture providing a mock ServiceManager.
    """
    with patch("main.service_manager") as mock_manager:
        yield mock_manager


@pytest.fixture
def mock_operation_manager():
    """
    Fixture providing a mock OperationManager.
    """
    with patch("main.operation_manager") as mock_manager:
        yield mock_manager


@pytest.mark.asyncio
async def test_list_accounts(mock_account_manager):
    """
    Test that list_accounts correctly returns account data.
    """
    mock_accounts = [
        Account(
            id=1,
            handle="test-account-1",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            links={"stack": {"href": "https://api.aptible.com/stacks/123"}},
        ),
        Account(
            id=2,
            handle="test-account-2",
            created_at="2023-01-02T12:00:00Z",
            updated_at="2023-01-02T12:00:00Z",
            links={"stack": {"href": "https://api.aptible.com/stacks/456"}},
        ),
    ]
    mock_account_manager.list = AsyncMock(return_value=mock_accounts)

    result = await listAccounts()
    mock_account_manager.list.assert_called_once()
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["handle"] == "test-account-1"
    assert result[0]["stack_id"] == 123
    assert result[1]["id"] == 2
    assert result[1]["handle"] == "test-account-2"
    assert result[1]["stack_id"] == 456


@pytest.mark.asyncio
async def test_list_accounts_omits_unknown_embedded_credentials(mock_account_manager):
    account = Account.model_validate(
        {
            "id": 1,
            "handle": "thrive-prod",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "_links": {"stack": {"href": "https://api.aptible.com/stacks/123"}},
            "url": "https://user:password@logs.example.com",
            "authToken": "unexpected-token",
            "_embedded": {
                "log_drains": [{"password": "embedded-password"}],
                "certificates": [{"private_key": "embedded-private-key"}],
            },
        }
    )
    mock_account_manager.list = AsyncMock(return_value=[account])

    result = await listAccounts()

    assert result == [
        {
            "id": 1,
            "handle": "thrive-prod",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "stack_id": 123,
        }
    ]


@pytest.mark.asyncio
async def test_get_account_success(mock_account_manager):
    """
    Test get_account successfully retrieves an account by handle.
    """
    mock_account = Account(
        id=1,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/123"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    result = await getAccount("test-account")
    mock_account_manager.get.assert_called_once_with("test-account")
    assert result["id"] == 1
    assert result["handle"] == "test-account"
    assert result["stack_id"] == 123


@pytest.mark.asyncio
async def test_get_account_not_found(mock_account_manager):
    """
    Test get_account returns None when account is not found.
    """
    mock_account_manager.get = AsyncMock(return_value=None)

    result = await getAccount("nonexistent-account")
    mock_account_manager.get.assert_called_once_with("nonexistent-account")
    assert result is None


@pytest.mark.asyncio
async def test_get_accounts_by_stack_success(mock_stack_manager, mock_account_manager):
    """
    Test get_accounts_by_stack successfully retrieves accounts for a stack.
    """
    mock_stack = Stack(
        id=123,
        name="test-stack",
        region="us-east-1",
        public=False,
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        organization_id="org-123",
    )
    mock_stack_manager.get = AsyncMock(return_value=mock_stack)

    mock_accounts = [
        Account(
            id=1,
            handle="test-account-1",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            links={"stack": {"href": "https://api.aptible.com/stacks/123"}},
        ),
        Account(
            id=2,
            handle="test-account-2",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            links={"stack": {"href": "https://api.aptible.com/stacks/123"}},
        ),
    ]
    mock_account_manager.get_by_stack_id = AsyncMock(return_value=mock_accounts)

    result = await getAccountsByStack("test-stack")

    mock_stack_manager.get.assert_called_once_with("test-stack")
    mock_account_manager.get_by_stack_id.assert_called_once_with(123)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["handle"] == "test-account-1"
    assert result[1]["id"] == 2
    assert result[1]["handle"] == "test-account-2"


@pytest.mark.asyncio
async def test_get_accounts_by_stack_not_found(mock_stack_manager):
    """
    Test get_accounts_by_stack raises an exception when stack is not found.
    """
    mock_stack_manager.get = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await getAccountsByStack("nonexistent-stack")

    mock_stack_manager.get.assert_called_once_with("nonexistent-stack")
    assert "Stack nonexistent-stack not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_account_success(mock_stack_manager, mock_account_manager):
    """
    Test create_account successfully creates a new account.
    """
    mock_stack = Stack(
        id=123,
        name="test-stack",
        region="us-east-1",
        public=False,
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        organization_id="org-123",
    )
    mock_stack_manager.get = AsyncMock(return_value=mock_stack)

    mock_account = Account(
        id=42,
        handle="new-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/123"}},
    )
    mock_account_manager.create = AsyncMock(return_value=mock_account)

    result = await createAccount("new-account", "test-stack")

    mock_stack_manager.get.assert_called_once_with("test-stack")
    mock_account_manager.create.assert_called_once_with(
        {"handle": "new-account", "stack_id": 123}
    )
    assert result["id"] == 42
    assert result["handle"] == "new-account"
    assert result["stack_id"] == 123


@pytest.mark.asyncio
async def test_create_account_stack_not_found(mock_stack_manager):
    """
    Test create_account raises an exception when stack is not found.
    """
    mock_stack_manager.get = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await createAccount("new-account", "nonexistent-stack")

    mock_stack_manager.get.assert_called_once_with("nonexistent-stack")
    assert "Stack nonexistent-stack not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_list_stacks(mock_stack_manager):
    """
    Test that list_stacks correctly returns stack data.
    """
    mock_stacks = [
        Stack(
            id=123,
            name="test-stack-1",
            region="us-east-1",
            public=False,
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            organization_id="org-123",
        ),
        Stack(
            id=456,
            name="test-stack-2",
            region="us-west-1",
            public=True,
            created_at="2023-01-02T12:00:00Z",
            updated_at="2023-01-02T12:00:00Z",
            organization_id="org-456",
        ),
    ]
    mock_stack_manager.list = AsyncMock(return_value=mock_stacks)

    result = await listStacks()

    mock_stack_manager.list.assert_called_once()
    assert len(result) == 2
    assert result[0]["id"] == 123
    assert result[0]["name"] == "test-stack-1"
    assert result[0]["region"] == "us-east-1"
    assert result[1]["id"] == 456
    assert result[1]["name"] == "test-stack-2"
    assert result[1]["public"] is True


@pytest.mark.asyncio
async def test_get_stack_success(mock_stack_manager):
    """
    Test get_stack successfully retrieves a stack by name.
    """
    mock_stack = Stack(
        id=123,
        name="test-stack",
        region="us-east-1",
        public=False,
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        organization_id="org-123",
    )
    mock_stack_manager.get = AsyncMock(return_value=mock_stack)

    result = await getStack("test-stack")

    mock_stack_manager.get.assert_called_once_with("test-stack")
    assert result["id"] == 123
    assert result["name"] == "test-stack"
    assert result["region"] == "us-east-1"


@pytest.mark.asyncio
async def test_get_stack_not_found(mock_stack_manager):
    """
    Test get_stack returns None when stack is not found.
    """
    mock_stack_manager.get = AsyncMock(return_value=None)

    result = await getStack("nonexistent-stack")

    mock_stack_manager.get.assert_called_once_with("nonexistent-stack")
    assert result is None


@pytest.mark.asyncio
async def test_list_apps(mock_app_manager):
    """
    Test that list_apps correctly returns app data.
    """
    mock_apps = [
        App(
            id=1,
            handle="test-app-1",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            status="provisioned",
            links={"account": {"href": "https://api.aptible.com/accounts/123"}},
        ),
        App(
            id=2,
            handle="test-app-2",
            created_at="2023-01-02T12:00:00Z",
            updated_at="2023-01-02T12:00:00Z",
            status="provisioning",
            links={"account": {"href": "https://api.aptible.com/accounts/456"}},
        ),
    ]
    mock_app_manager.list = AsyncMock(return_value=mock_apps)

    result = await listApps()

    mock_app_manager.list.assert_called_once()
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["handle"] == "test-app-1"
    assert result[0]["status"] == "provisioned"
    assert result[1]["id"] == 2
    assert result[1]["handle"] == "test-app-2"


@pytest.mark.asyncio
async def test_get_app_single_match(mock_app_manager):
    """
    Test get_app with a single matching app.
    """
    mock_apps = [
        App(
            id=1,
            handle="test-app",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            status="provisioned",
            links={"account": {"href": "https://api.aptible.com/accounts/123"}},
        )
    ]
    mock_app_manager.list = AsyncMock(return_value=mock_apps)

    result = await getApp("test-app")

    mock_app_manager.list.assert_called_once()
    assert result["id"] == 1
    assert result["handle"] == "test-app"
    assert result["status"] == "provisioned"


@pytest.mark.asyncio
async def test_get_app_with_account(mock_app_manager, mock_account_manager):
    """
    Test get_app with multiple apps and an account handle.
    """
    mock_apps = [
        App(
            id=1,
            handle="test-app",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            status="provisioned",
            links={"account": {"href": "https://api.aptible.com/accounts/123"}},
        ),
        App(
            id=2,
            handle="test-app",
            created_at="2023-01-02T12:00:00Z",
            updated_at="2023-01-02T12:00:00Z",
            status="provisioning",
            links={"account": {"href": "https://api.aptible.com/accounts/456"}},
        ),
    ]
    mock_app_manager.list = AsyncMock(return_value=mock_apps)

    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    result = await getApp("test-app", "test-account")

    mock_app_manager.list.assert_called_once()
    mock_account_manager.get.assert_called_once_with("test-account")
    assert result["id"] == 1
    assert result["handle"] == "test-app"


@pytest.mark.asyncio
async def test_get_app_no_match(mock_app_manager):
    """
    Test get_app with no matching app.
    """
    mock_app_manager.list = AsyncMock(return_value=[])

    with pytest.raises(Exception) as excinfo:
        await getApp("nonexistent-app")

    mock_app_manager.list.assert_called_once()
    assert "No app with handle nonexistent-app" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_app_multiple_matches_no_account(mock_app_manager):
    """
    Test get_app with multiple matches but no account provided.
    """
    mock_apps = [
        App(
            id=1,
            handle="test-app",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            status="provisioned",
            links={"account": {"href": "https://api.aptible.com/accounts/123"}},
        ),
        App(
            id=2,
            handle="test-app",
            created_at="2023-01-02T12:00:00Z",
            updated_at="2023-01-02T12:00:00Z",
            status="provisioning",
            links={"account": {"href": "https://api.aptible.com/accounts/456"}},
        ),
    ]
    mock_app_manager.list = AsyncMock(return_value=mock_apps)

    with pytest.raises(Exception) as excinfo:
        await getApp("test-app")

    mock_app_manager.list.assert_called_once()
    assert "Multiple apps found with handle test-app" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_app_success(mock_app_manager, mock_account_manager):
    """
    Test create_app successfully creates a new app.
    """
    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    mock_app = App(
        id=1,
        handle="new-app",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        status="provisioning",
        links={"account": {"href": "https://api.aptible.com/accounts/123"}},
    )
    mock_app_manager.create = AsyncMock(return_value=mock_app)

    result = await createApp("new-app", "test-account", "example/image:latest")
    mock_account_manager.get.assert_called_once_with("test-account")
    mock_app_manager.create.assert_called_once_with(
        {
            "handle": "new-app",
            "account_id": 123,
            "docker_image": "example/image:latest",
        }
    )
    assert result["id"] == 1
    assert result["handle"] == "new-app"
    assert result["status"] == "provisioning"


@pytest.mark.asyncio
async def test_create_app_account_not_found(mock_account_manager):
    """
    Test create_app raises an exception when account is not found.
    """
    mock_account_manager.get = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await createApp("new-app", "nonexistent-account", "example/image:latest")

    mock_account_manager.get.assert_called_once_with("nonexistent-account")
    assert "Account nonexistent-account not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_configure_app_success(mock_app_manager):
    """
    Test configure_app successfully sets environment variables.
    """
    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_app_manager.configure = AsyncMock()

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        env_vars = {
            "DATABASE_URL": "postgres://user:pass@host:5432/db",
            "API_KEY": "secret-key",
        }
        await configureApp("test-app", "test-account", env_vars)
        mock_app_manager.configure.assert_called_once_with(1, env_vars)


@pytest.mark.asyncio
async def test_configure_app_not_found():
    """
    Test configure_app raises an exception when app is not found.
    """
    with patch("main.getApp", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await configureApp("nonexistent-app", "test-account", {"KEY": "VALUE"})

        assert "App nonexistent-app not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_delete_app_success(mock_app_manager):
    """
    Test delete_app successfully deletes an app.
    """
    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_app_manager.delete = AsyncMock()
    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        with patch("main.App.account_id", return_value=123):
            await deleteApp("test-app")
            mock_app_manager.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_app_not_found():
    """
    Test delete_app raises an exception when app is not found.
    """
    with patch("main.getApp", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await deleteApp("nonexistent-app", "test-account")
        assert "App nonexistent-app not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_list_available_database_types(mock_database_manager):
    """
    Test list_available_database_types correctly returns database type data.
    """
    mock_db_types = [
        DatabaseImage(
            id=1,
            name="PostgreSQL",
            version="14",
            docker_repo="aptible/postgresql",
            docker_ref="14",
            type="postgresql",
            description="PostgreSQL database",
            default=True,
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            links={},
        ),
        DatabaseImage(
            id=2,
            name="MongoDB",
            version="6.0",
            docker_repo="aptible/mongodb",
            docker_ref="6.0",
            type="mongodb",
            description="MongoDB database",
            default=False,
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            links={},
        ),
    ]
    mock_database_manager.list_available_types = AsyncMock(return_value=mock_db_types)

    result = await listAvailableDatabaseTypes()

    mock_database_manager.list_available_types.assert_called_once()
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["name"] == "PostgreSQL"
    assert result[0]["version"] == "14"
    assert result[0]["default"] is True
    assert result[1]["id"] == 2
    assert result[1]["name"] == "MongoDB"


@pytest.mark.asyncio
async def test_list_databases(mock_database_manager):
    """
    Test list_databases correctly returns database data.
    """
    mock_databases = [
        Database(
            id=1,
            handle="test-db-1",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            status="provisioned",
            type="postgresql",
            links={
                "account": {"href": "https://api.aptible.com/accounts/123"},
                "database_image": {"href": "https://api.aptible.com/database_images/1"},
            },
        ),
        Database(
            id=2,
            handle="test-db-2",
            created_at="2023-01-02T12:00:00Z",
            updated_at="2023-01-02T12:00:00Z",
            status="provisioning",
            type="mongodb",
            links={
                "account": {"href": "https://api.aptible.com/accounts/456"},
                "database_image": {"href": "https://api.aptible.com/database_images/2"},
            },
        ),
    ]
    mock_database_manager.list = AsyncMock(return_value=mock_databases)

    result = await listDatabases()

    mock_database_manager.list.assert_called_once()
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["handle"] == "test-db-1"
    assert result[0]["status"] == "provisioned"
    assert result[1]["id"] == 2
    assert result[1]["handle"] == "test-db-2"


@pytest.mark.asyncio
async def test_get_database_single_match(mock_database_manager):
    """
    Test get_database with a single matching database.
    """
    mock_databases = [
        Database(
            id=1,
            handle="test-db",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            status="provisioned",
            type="postgresql",
            links={
                "account": {"href": "https://api.aptible.com/accounts/123"},
                "database_image": {"href": "https://api.aptible.com/database_images/1"},
            },
        )
    ]
    mock_database_manager.list = AsyncMock(return_value=mock_databases)

    result = await getDatabase("test-db")

    mock_database_manager.list.assert_called_once()
    assert result["id"] == 1
    assert result["handle"] == "test-db"
    assert result["status"] == "provisioned"


@pytest.mark.asyncio
async def test_get_database_with_account(mock_database_manager, mock_account_manager):
    """
    Test get_database with multiple databases and an account handle.
    """
    mock_databases = [
        Database(
            id=1,
            handle="test-db",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            status="provisioned",
            type="postgresql",
            links={
                "account": {"href": "https://api.aptible.com/accounts/123"},
                "database_image": {"href": "https://api.aptible.com/database_images/1"},
            },
        ),
        Database(
            id=2,
            handle="test-db",
            created_at="2023-01-02T12:00:00Z",
            updated_at="2023-01-02T12:00:00Z",
            status="provisioning",
            type="mongodb",
            links={
                "account": {"href": "https://api.aptible.com/accounts/456"},
                "database_image": {"href": "https://api.aptible.com/database_images/2"},
            },
        ),
    ]
    mock_database_manager.list = AsyncMock(return_value=mock_databases)

    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    result = await getDatabase("test-db", "test-account")

    mock_database_manager.list.assert_called_once()
    mock_account_manager.get.assert_called_once_with("test-account")
    assert result["id"] == 1
    assert result["handle"] == "test-db"


@pytest.mark.asyncio
async def test_get_database_no_match(mock_database_manager):
    """
    Test get_database with no matching database.
    """
    mock_database_manager.list = AsyncMock(return_value=[])

    with pytest.raises(Exception) as excinfo:
        await getDatabase("nonexistent-db")

    mock_database_manager.list.assert_called_once()
    assert "No database with handle nonexistent-db" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_database_multiple_matches_no_account(mock_database_manager):
    """
    Test get_database with multiple matches but no account provided.
    """
    mock_databases = [
        Database(
            id=1,
            handle="test-db",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            status="provisioned",
            type="postgresql",
            links={
                "account": {"href": "https://api.aptible.com/accounts/123"},
                "database_image": {"href": "https://api.aptible.com/database_images/1"},
            },
        ),
        Database(
            id=2,
            handle="test-db",
            created_at="2023-01-02T12:00:00Z",
            updated_at="2023-01-02T12:00:00Z",
            status="provisioning",
            type="mongodb",
            links={
                "account": {"href": "https://api.aptible.com/accounts/456"},
                "database_image": {"href": "https://api.aptible.com/database_images/2"},
            },
        ),
    ]
    mock_database_manager.list = AsyncMock(return_value=mock_databases)

    with pytest.raises(Exception) as excinfo:
        await getDatabase("test-db")

    mock_database_manager.list.assert_called_once()
    assert "Multiple databases found with handle test-db" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_database_success(mock_database_manager, mock_account_manager):
    """
    Test create_database successfully creates a new database.
    """

    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    mock_database = Database(
        id=1,
        handle="new-db",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        status="provisioning",
        type="postgresql",
        links={
            "account": {"href": "https://api.aptible.com/accounts/123"},
            "database_image": {"href": "https://api.aptible.com/database_images/42"},
        },
    )
    mock_database_manager.create = AsyncMock(return_value=mock_database)

    result = await createDatabase("new-db", "test-account", 42)
    mock_account_manager.get.assert_called_once_with("test-account")
    mock_database_manager.create.assert_called_once_with(
        {
            "handle": "new-db",
            "account_id": 123,
            "image_id": 42,
        }
    )
    assert result["id"] == 1
    assert result["handle"] == "new-db"
    assert result["status"] == "provisioning"


@pytest.mark.asyncio
async def test_create_database_account_not_found(mock_account_manager):
    """
    Test create_database raises an exception when account is not found.
    """
    mock_account_manager.get = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await createDatabase("new-db", "nonexistent-account", 42)

    mock_account_manager.get.assert_called_once_with("nonexistent-account")
    assert "Account nonexistent-account not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_delete_database_success(mock_database_manager):
    """
    Test delete_database successfully deletes a database.
    """
    mock_database_data = {
        "id": 1,
        "handle": "test-db",
        "status": "provisioned",
        "type": "postgresql",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {
            "account": {"href": "https://api.aptible.com/accounts/123"},
            "database_image": {"href": "https://api.aptible.com/database_images/1"},
        },
    }
    # Use AsyncMock for the delete method to make it awaitable
    mock_database_manager.delete = AsyncMock()

    with patch("main.getDatabase", new=AsyncMock(return_value=mock_database_data)):
        with patch("main.Database.account_id", return_value=123):
            await deleteDatabase("test-db", "test-account")
            mock_database_manager.delete.assert_called_once_with(
                mock_database_data["id"]
            )


@pytest.mark.asyncio
async def test_delete_database_not_found():
    """
    Test delete_database raises an exception when database is not found.
    """
    with patch("main.getDatabase", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await deleteDatabase("nonexistent-db", "test-account")

        assert "Database nonexistent-db not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_list_database_backups(mock_backup_manager):
    """
    Test list_database_backups resolves the database and returns its backups.
    """
    mock_database_data = {
        "id": 1,
        "handle": "test-db",
        "status": "provisioned",
        "type": "postgresql",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {
            "account": {"href": "https://api.aptible.com/accounts/123"},
            "database_image": {"href": "https://api.aptible.com/database_images/1"},
        },
    }

    mock_backups = [
        Backup(
            id=1,
            created_at="2023-01-01T12:00:00Z",
            links={"database": {"href": "https://api.aptible.com/databases/1"}},
        )
    ]
    mock_backup_manager.list_for_database = AsyncMock(return_value=mock_backups)

    with patch("main.getDatabase", new=AsyncMock(return_value=mock_database_data)):
        result = await listDatabaseBackups("test-db", "test-account", max_age="1w")

        mock_backup_manager.list_for_database.assert_called_once_with(1, "1w")
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["database_id"] == 1


@pytest.mark.asyncio
async def test_list_database_backups_not_found():
    """
    Test list_database_backups raises an exception when the database is not found.
    """
    with patch("main.getDatabase", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await listDatabaseBackups("nonexistent-db")

        assert "Database nonexistent-db not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_restore_database_from_backup_success(
    mock_backup_manager, mock_database_manager
):
    """
    Test restore_database_from_backup restores a backup and returns the resulting database.
    """
    mock_account = {
        "id": 456,
        "handle": "dest-account",
    }

    mock_database_data = {
        "id": 2,
        "handle": "restored-db",
        "status": "provisioning",
        "type": "postgresql",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {
            "account": {"href": "https://api.aptible.com/accounts/456"},
            "database_image": {"href": "https://api.aptible.com/database_images/1"},
        },
    }

    mock_backup_manager.restore = AsyncMock()
    restored_database = Database.model_validate(mock_database_data)
    mock_database_manager.list = AsyncMock(side_effect=[[], [restored_database]])

    with patch("main.getAccount", new=AsyncMock(return_value=mock_account)):
        result = await restoreDatabaseFromBackup(1, "restored-db", "dest-account")

        mock_backup_manager.restore.assert_called_once_with(1, "restored-db", 456)
        assert result["id"] == 2
        assert result["handle"] == "restored-db"


@pytest.mark.asyncio
async def test_restore_without_destination_scopes_discovery_to_source_account(
    mock_backup_manager, mock_database_manager
):
    backup = Backup(
        id=1,
        created_at="2023-01-01T12:00:00Z",
        links={"account": {"href": "https://api.aptible.com/accounts/321"}},
    )
    restored_database = Database.model_validate(
        _database_payload(2, "restored-db", account_id=321)
    )
    foreign_namesake = Database.model_validate(
        _database_payload(3, "restored-db", account_id=999)
    )
    mock_backup_manager.get_by_id = AsyncMock(return_value=backup)
    mock_backup_manager.restore = AsyncMock()
    mock_database_manager.list = AsyncMock(
        side_effect=[[foreign_namesake], [foreign_namesake, restored_database]]
    )

    result = await restoreDatabaseFromBackup(1, "restored-db")

    mock_backup_manager.get_by_id.assert_awaited_once_with(1)
    mock_backup_manager.restore.assert_awaited_once_with(1, "restored-db", None)
    assert result["id"] == 2
    assert result["account_id"] == 321


@pytest.mark.asyncio
async def test_restore_resolves_source_account_through_backup_database(
    mock_backup_manager, mock_database_manager
):
    backup = Backup(
        id=1,
        created_at="2023-01-01T12:00:00Z",
        links={"database": {"href": "https://api.aptible.com/databases/7"}},
    )
    source_database = Database.model_validate(_database_payload(7, "source", 321))
    restored_database = Database.model_validate(
        _database_payload(8, "restored-db", account_id=321)
    )
    mock_backup_manager.get_by_id = AsyncMock(return_value=backup)
    mock_backup_manager.restore = AsyncMock()
    mock_database_manager.get_by_id = AsyncMock(return_value=source_database)
    mock_database_manager.list = AsyncMock(side_effect=[[], [restored_database]])

    result = await restoreDatabaseFromBackup(1, "restored-db")

    mock_database_manager.get_by_id.assert_awaited_once_with(7)
    mock_backup_manager.restore.assert_awaited_once_with(1, "restored-db", None)
    assert result["account_id"] == 321


@pytest.mark.asyncio
async def test_restore_requires_account_scope_before_billed_operation(
    mock_backup_manager, mock_database_manager
):
    backup = Backup(
        id=1,
        created_at="2023-01-01T12:00:00Z",
        links={},
    )
    mock_backup_manager.get_by_id = AsyncMock(return_value=backup)
    mock_backup_manager.restore = AsyncMock()

    with pytest.raises(ValueError, match="provide destination_account_handle"):
        await restoreDatabaseFromBackup(1, "restored-db")

    mock_backup_manager.restore.assert_not_awaited()
    mock_database_manager.list.assert_not_called()


@pytest.mark.asyncio
async def test_restore_database_from_backup_destination_account_not_found():
    """
    Test restore_database_from_backup raises when the destination account is not found.
    """
    with patch("main.getAccount", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await restoreDatabaseFromBackup(1, "restored-db", "nonexistent-account")

        assert "Account nonexistent-account not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_list_orphaned_backups(mock_backup_manager, mock_account_manager):
    """
    Test list_orphaned_backups resolves the account and returns its orphaned backups.
    """
    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    mock_backups = [Backup(id=1, created_at="2023-01-01T12:00:00Z", links={})]
    mock_backup_manager.list_orphaned = AsyncMock(return_value=mock_backups)

    result = await listOrphanedBackups("test-account")

    mock_backup_manager.list_orphaned.assert_called_once_with(123)
    assert len(result) == 1
    assert result[0]["id"] == 1


@pytest.mark.asyncio
async def test_list_orphaned_backups_account_not_found(mock_account_manager):
    """
    Test list_orphaned_backups raises when the account is not found.
    """
    mock_account_manager.get = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await listOrphanedBackups("nonexistent-account")

    assert "Account nonexistent-account not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_purge_backup(mock_backup_manager):
    """
    Test purge_backup calls the manager with the backup id.
    """
    mock_backup_manager.purge = AsyncMock()

    await purgeBackup(42)

    mock_backup_manager.purge.assert_called_once_with(42)


@pytest.mark.asyncio
async def test_create_log_drain(mock_log_drain_manager, mock_account_manager):
    """
    Test create_log_drain resolves the account and creates the drain with config fields.
    """
    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    mock_drain = LogDrain(
        id=1,
        handle="my-drain",
        drain_type="https_post",
        status="pending",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"account": {"href": "https://api.aptible.com/accounts/123"}},
        url="https://alice:log-password@logs.example.com/ingest",
        authToken="echoed-auth-token",
    )
    mock_log_drain_manager.create = AsyncMock(return_value=mock_drain)

    result = await createLogDrain(
        "test-account", "my-drain", "https_post", {"url": "https://example.com"}
    )

    mock_log_drain_manager.create.assert_called_once_with(
        123, "my-drain", "https_post", url="https://example.com"
    )
    assert result["id"] == 1
    assert result["handle"] == "my-drain"
    assert result["drain_type"] == "https_post"
    assert "url" not in result
    assert "authToken" not in result


@pytest.mark.asyncio
async def test_create_log_drain_account_not_found(mock_account_manager):
    """
    Test create_log_drain raises when the account is not found.
    """
    mock_account_manager.get = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await createLogDrain("nonexistent-account", "my-drain", "https_post")

    assert "Account nonexistent-account not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_list_log_drains(mock_log_drain_manager, mock_account_manager):
    """
    Test list_log_drains resolves the account and returns its log drains.
    """
    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    mock_drains = [
        LogDrain(
            id=1,
            handle="my-drain",
            drain_type="https_post",
            status="provisioned",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            links={"account": {"href": "https://api.aptible.com/accounts/123"}},
        )
    ]
    mock_log_drain_manager.list_for_account = AsyncMock(return_value=mock_drains)

    result = await listLogDrains("test-account")

    mock_log_drain_manager.list_for_account.assert_called_once_with(123)
    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["handle"] == "my-drain"


@pytest.mark.asyncio
async def test_deprovision_log_drain(mock_log_drain_manager):
    """
    Test deprovision_log_drain calls the manager with the drain id.
    """
    mock_log_drain_manager.deprovision = AsyncMock()

    await deprovisionLogDrain(7)

    mock_log_drain_manager.deprovision.assert_called_once_with(7)


@pytest.mark.asyncio
async def test_create_metric_drain(mock_metric_drain_manager, mock_account_manager):
    """
    Test create_metric_drain resolves the account and creates the drain with configuration.
    """
    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    mock_drain = MetricDrain(
        id=1,
        handle="my-metric-drain",
        drain_type="datadog",
        status="pending",
        drain_configuration={"api_key": "secret"},
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"account": {"href": "https://api.aptible.com/accounts/123"}},
    )
    mock_metric_drain_manager.create = AsyncMock(return_value=mock_drain)

    result = await createMetricDrain(
        "test-account", "my-metric-drain", "datadog", {"api_key": "secret"}
    )

    mock_metric_drain_manager.create.assert_called_once_with(
        123, "my-metric-drain", "datadog", {"api_key": "secret"}
    )
    assert result["id"] == 1
    assert result["handle"] == "my-metric-drain"
    assert result["drain_type"] == "datadog"
    assert result["drain_configuration"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_create_metric_drain_account_not_found(mock_account_manager):
    """
    Test create_metric_drain raises when the account is not found.
    """
    mock_account_manager.get = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await createMetricDrain("nonexistent-account", "my-metric-drain", "datadog")

    assert "Account nonexistent-account not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_list_metric_drains(mock_metric_drain_manager, mock_account_manager):
    """
    Test list_metric_drains resolves the account and returns its metric drains.
    """
    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    mock_drains = [
        MetricDrain(
            id=1,
            handle="my-metric-drain",
            drain_type="datadog",
            status="provisioned",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            links={"account": {"href": "https://api.aptible.com/accounts/123"}},
        )
    ]
    mock_metric_drain_manager.list_for_account = AsyncMock(return_value=mock_drains)

    result = await listMetricDrains("test-account")

    mock_metric_drain_manager.list_for_account.assert_called_once_with(123)
    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["handle"] == "my-metric-drain"


@pytest.mark.asyncio
async def test_deprovision_metric_drain(mock_metric_drain_manager):
    """
    Test deprovision_metric_drain calls the manager with the drain id.
    """
    mock_metric_drain_manager.deprovision = AsyncMock()

    await deprovisionMetricDrain(9)

    mock_metric_drain_manager.deprovision.assert_called_once_with(9)


@pytest.mark.asyncio
async def test_upload_certificate(
    mock_certificate_manager, mock_account_manager, tmp_path, monkeypatch
):
    """
    Test upload_certificate resolves the account and uploads the certificate.
    """
    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    mock_certificate = Certificate(
        id=1,
        common_name="example.com",
        fingerprint="abc123",
        links={"account": {"href": "https://api.aptible.com/accounts/123"}},
    )
    mock_certificate_manager.upload = AsyncMock(return_value=mock_certificate)

    certificate = tmp_path / "certificate.pem"
    certificate.write_text("cert-body")
    private_key = tmp_path / "private-key.pem"
    private_key.write_text("private-key")
    private_key.chmod(0o600)
    monkeypatch.setenv("APTIBLE_MCP_CERTIFICATE_DIR", str(tmp_path))

    result = await uploadCertificate(
        "test-account", "certificate.pem", "private-key.pem"
    )

    mock_certificate_manager.upload.assert_called_once_with(
        123, "cert-body", "private-key"
    )
    assert result["id"] == 1
    assert result["common_name"] == "example.com"
    assert result["fingerprint"] == "abc123"


@pytest.mark.asyncio
async def test_upload_certificate_account_not_found(mock_account_manager):
    """
    Test upload_certificate raises when the account is not found.
    """
    mock_account_manager.get = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await uploadCertificate(
            "nonexistent-account", "certificate.pem", "private-key.pem"
        )

    assert "Account nonexistent-account not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_upload_certificate_rejects_path_escape(
    mock_account_manager, tmp_path, monkeypatch
):
    mock_account_manager.get = AsyncMock(
        return_value=Account(
            id=123,
            handle="test-account",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
        )
    )
    monkeypatch.setenv("APTIBLE_MCP_CERTIFICATE_DIR", str(tmp_path))

    with pytest.raises((FileNotFoundError, ValueError)):
        await uploadCertificate("test-account", "../certificate.pem", "key.pem")


@pytest.mark.asyncio
async def test_list_certificates(mock_certificate_manager, mock_account_manager):
    """
    Test list_certificates resolves the account and returns its certificates.
    """
    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    mock_certificates = [
        Certificate(
            id=1,
            common_name="example.com",
            fingerprint="abc123",
            links={"account": {"href": "https://api.aptible.com/accounts/123"}},
        )
    ]
    mock_certificate_manager.list_for_account = AsyncMock(
        return_value=mock_certificates
    )

    result = await listCertificates("test-account")

    mock_certificate_manager.list_for_account.assert_called_once_with(123)
    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["common_name"] == "example.com"


@pytest.mark.asyncio
async def test_list_vhosts(mock_vhost_manager):
    """
    Test list_vhosts correctly returns vhost data.
    """
    mock_vhosts = [
        Vhost(
            id=1,
            status="provisioned",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            external_host="app-123.aptible.com",
            links={
                "service": {"href": "https://api.aptible.com/services/123"},
            },
        ),
        Vhost(
            id=2,
            status="provisioning",
            created_at="2023-01-02T12:00:00Z",
            updated_at="2023-01-02T12:00:00Z",
            external_host="app-456.aptible.com",
            links={
                "service": {"href": "https://api.aptible.com/services/456"},
            },
        ),
    ]
    mock_vhost_manager.list = AsyncMock(return_value=mock_vhosts)

    result = await listVhosts()

    mock_vhost_manager.list.assert_called_once()
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["external_host"] == "app-123.aptible.com"
    assert result[0]["status"] == "provisioned"
    assert result[1]["id"] == 2
    assert result[1]["external_host"] == "app-456.aptible.com"


@pytest.mark.asyncio
async def test_get_vhost_success(mock_vhost_manager):
    """
    Test get_vhost successfully retrieves a vhost by ID.
    """
    mock_vhost = Vhost(
        id=1,
        status="provisioned",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        external_host="app-123.aptible.com",
        links={
            "service": {"href": "https://api.aptible.com/services/123"},
        },
    )
    mock_vhost_manager.get = AsyncMock(return_value=mock_vhost)

    result = await getVhost("1")

    mock_vhost_manager.get.assert_called_once_with("1")
    assert result["id"] == 1
    assert result["external_host"] == "app-123.aptible.com"
    assert result["status"] == "provisioned"


@pytest.mark.asyncio
async def test_get_vhost_not_found(mock_vhost_manager):
    """
    Test get_vhost returns None when vhost is not found.
    """
    mock_vhost_manager.get = AsyncMock(return_value=None)

    result = await getVhost("999")

    mock_vhost_manager.get.assert_called_once_with("999")
    assert result is None


@pytest.mark.asyncio
async def test_create_vhost_success(mock_service_manager, mock_vhost_manager):
    """
    Test create_vhost successfully creates a new vhost.
    """
    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_services = [
        Service(
            id=123,
            handle="web",
            process_type="web",
            container_count=2,
            container_memory_limit_mb=1024,
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            links={
                "app": {"href": "https://api.aptible.com/apps/1"},
            },
        ),
        Service(
            id=456,
            handle="worker",
            process_type="worker",
            container_count=1,
            container_memory_limit_mb=512,
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            links={
                "app": {"href": "https://api.aptible.com/apps/1"},
            },
        ),
    ]

    mock_vhost = Vhost(
        id=42,
        status="provisioning",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        external_host="app-123.aptible.com",
        links={
            "service": {"href": "https://api.aptible.com/services/123"},
        },
    )

    mock_service_manager.list_by_app = AsyncMock(return_value=mock_services)
    mock_vhost_manager.create = AsyncMock(return_value=mock_vhost)

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        result = await createVhost("test-app", "web", "test-account")

        mock_service_manager.list_by_app.assert_called_once_with(1)
        mock_vhost_manager.create.assert_called_once_with({"service_id": 123})

        assert result["id"] == 42
        assert result["external_host"] == "app-123.aptible.com"
        assert result["status"] == "provisioning"


@pytest.mark.asyncio
async def test_create_vhost_app_not_found():
    """
    Test create_vhost raises an exception when app is not found.
    """

    with patch("main.getApp", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await createVhost("nonexistent-app", "web", "test-account")

        assert "App nonexistent-app not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_vhost_service_not_found(mock_service_manager):
    """
    Test create_vhost raises an exception when service is not found.
    """

    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_services = []

    mock_service_manager.list_by_app = AsyncMock(return_value=mock_services)

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        with pytest.raises(Exception) as excinfo:
            await createVhost("test-app", "nonexistent-service", "test-account")

        mock_service_manager.list_by_app.assert_called_once_with(1)
        assert (
            "No service with handle nonexistent-service found in app test-app"
            in str(excinfo.value)
        )


@pytest.mark.asyncio
async def test_delete_vhost(mock_vhost_manager):
    """
    Test delete_vhost successfully calls the manager.
    """

    mock_vhost_manager.delete_vhost = AsyncMock()

    await deleteVhost(42)
    mock_vhost_manager.delete_vhost.assert_called_once_with(42)


@pytest.mark.asyncio
async def test_list_services(mock_service_manager):
    """
    Test list_services returns services for an app.
    """

    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_services = [
        Service(
            id=1,
            handle="web",
            process_type="web",
            container_count=2,
            container_memory_limit_mb=1024,
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            links={
                "app": {"href": "https://api.aptible.com/apps/1"},
            },
        ),
        Service(
            id=2,
            handle="worker",
            process_type="worker",
            container_count=1,
            container_memory_limit_mb=512,
            created_at="2023-01-02T12:00:00Z",
            updated_at="2023-01-02T12:00:00Z",
            links={
                "app": {"href": "https://api.aptible.com/apps/1"},
            },
        ),
    ]

    mock_service_manager.list_by_app = AsyncMock(return_value=mock_services)

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        result = await listServices("test-app", "test-account")

        mock_service_manager.list_by_app.assert_called_once_with(1)

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["handle"] == "web"
        assert result[0]["process_type"] == "web"
        assert result[0]["container_count"] == 2
        assert result[1]["id"] == 2
        assert result[1]["handle"] == "worker"


@pytest.mark.asyncio
async def test_list_services_app_not_found():
    """
    Test list_services raises an exception when app is not found.
    """

    with patch("main.getApp", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await listServices("nonexistent-app", "test-account")

        assert "App nonexistent-app not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_service_success(mock_service_manager):
    """
    Test get_service successfully retrieves a service.
    """

    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_service = Service(
        id=1,
        handle="web",
        process_type="web",
        container_count=2,
        container_memory_limit_mb=1024,
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={
            "app": {"href": "https://api.aptible.com/apps/1"},
        },
    )

    mock_service_manager.get_by_handle_and_app = AsyncMock(return_value=mock_service)

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        result = await getService("test-app", "web", "test-account")

        mock_service_manager.get_by_handle_and_app.assert_called_once_with("web", 1)

        assert result["id"] == 1
        assert result["handle"] == "web"
        assert result["process_type"] == "web"
        assert result["container_count"] == 2


@pytest.mark.asyncio
async def test_get_service_app_not_found():
    """
    Test get_service raises an exception when app is not found.
    """

    with patch("main.getApp", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await getService("nonexistent-app", "web", "test-account")

        assert "App nonexistent-app not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_service_not_found(mock_service_manager):
    """
    Test get_service raises an exception when service is not found.
    """

    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_service_manager.get_by_handle_and_app = AsyncMock(return_value=None)

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        with pytest.raises(Exception) as excinfo:
            await getService("test-app", "nonexistent-service", "test-account")

        mock_service_manager.get_by_handle_and_app.assert_called_once_with(
            "nonexistent-service", 1
        )
        assert (
            "No service with handle nonexistent-service found in app test-app"
            in str(excinfo.value)
        )


@pytest.mark.asyncio
async def test_scale_service_success(mock_service_manager):
    """
    Test scale_service successfully scales a service.
    """

    mock_service_data = {
        "id": 1,
        "handle": "web",
        "process_type": "web",
        "container_count": 2,
        "container_memory_limit_mb": 1024,
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"app": {"href": "https://api.aptible.com/apps/1"}},
    }

    mock_updated_service = Service(
        id=1,
        handle="web",
        process_type="web",
        container_count=4,
        container_memory_limit_mb=2048,
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-03T12:00:00Z",
        links={
            "app": {"href": "https://api.aptible.com/apps/1"},
        },
    )

    mock_service_manager.scale = AsyncMock(return_value=mock_updated_service)

    with patch("main.getService", new=AsyncMock(return_value=mock_service_data)):
        result = await scaleService(
            "test-app",
            "web",
            container_count=4,
            container_memory_limit_mb=2048,
            account_handle="test-account",
        )

        mock_service_manager.scale.assert_called_once_with(1, 4, 2048)

        assert result["id"] == 1
        assert result["handle"] == "web"
        assert result["container_count"] == 4
        assert result["container_memory_limit_mb"] == 2048


@pytest.mark.asyncio
async def test_scale_service_no_parameters():
    """
    Test scale_service raises an exception when no scaling parameters are provided.
    """
    with pytest.raises(ValueError) as excinfo:
        await scaleService("test-app", "web", account_handle="test-account")

    assert "Must specify at least one of container_count or container_size" in str(
        excinfo.value
    )


@pytest.mark.asyncio
async def test_list_service_vhosts(mock_vhost_manager):
    """
    Test list_service_vhosts returns vhosts for a service.
    """

    mock_service_data = {
        "id": 1,
        "handle": "web",
        "process_type": "web",
        "container_count": 2,
        "container_memory_limit_mb": 1024,
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"app": {"href": "https://api.aptible.com/apps/1"}},
    }

    mock_vhosts = [
        Vhost(
            id=1,
            status="provisioned",
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            external_host="app-123.aptible.com",
            links={
                "service": {"href": "https://api.aptible.com/services/1"},
            },
        ),
        Vhost(
            id=2,
            status="provisioned",
            created_at="2023-01-02T12:00:00Z",
            updated_at="2023-01-02T12:00:00Z",
            external_host="custom-domain.example.com",
            links={
                "service": {"href": "https://api.aptible.com/services/1"},
            },
        ),
    ]

    mock_vhost_manager.list_by_service = AsyncMock(return_value=mock_vhosts)

    with patch("main.getService", new=AsyncMock(return_value=mock_service_data)):
        with patch("main.Service.model_validate") as mock_validate:
            mock_service = Mock()
            mock_service.id = 1
            mock_validate.return_value = mock_service

            result = await listServiceVhosts("test-app", "web", "test-account")

            mock_vhost_manager.list_by_service.assert_called_once_with(1)

            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[0]["external_host"] == "app-123.aptible.com"
            assert result[1]["id"] == 2
            assert result[1]["external_host"] == "custom-domain.example.com"


@pytest.mark.asyncio
async def test_create_custom_domain_endpoint_success(mock_vhost_manager):
    """
    Test createCustomDomainEndpoint resolves the service and composes
    VhostManager.create_custom_domain correctly.
    """
    mock_service_data = {
        "id": 123,
        "handle": "web",
        "process_type": "web",
        "container_count": 2,
        "container_memory_limit_mb": 1024,
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"app": {"href": "https://api.aptible.com/apps/1"}},
    }

    mock_vhost = Vhost(
        id=42,
        status="provisioning",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        external_host="custom-domain.example.com",
        user_domain="custom-domain.example.com",
        links={"service": {"href": "https://api.aptible.com/services/123"}},
    )

    mock_vhost_manager.create_custom_domain = AsyncMock(return_value=mock_vhost)

    with patch("main.getService", new=AsyncMock(return_value=mock_service_data)):
        result = await createCustomDomainEndpoint(
            "test-app",
            "web",
            "custom-domain.example.com",
            managed_tls=True,
            account_handle="test-account",
        )

        mock_vhost_manager.create_custom_domain.assert_called_once_with(
            123,
            "custom-domain.example.com",
            managed_tls=True,
            certificate_fingerprint=None,
            container_ports=None,
        )
        assert result["id"] == 42
        assert result["user_domain"] == "custom-domain.example.com"


@pytest.mark.asyncio
async def test_create_custom_domain_endpoint_service_not_found():
    """
    Test createCustomDomainEndpoint propagates the not-found error raised by
    getService instead of attempting provisioning.
    """
    with patch(
        "main.getService",
        new=AsyncMock(side_effect=Exception("No service with handle web found")),
    ):
        with pytest.raises(Exception) as excinfo:
            await createCustomDomainEndpoint(
                "test-app", "web", "custom-domain.example.com"
            )

        assert "No service with handle web found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_typed_endpoint_success(mock_vhost_manager):
    """
    Test createTypedEndpoint composes VhostManager.create_custom_domain with
    the requested endpoint type and container ports, without managed TLS.
    """
    mock_service_data = {
        "id": 123,
        "handle": "web",
        "process_type": "web",
        "container_count": 2,
        "container_memory_limit_mb": 1024,
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"app": {"href": "https://api.aptible.com/apps/1"}},
    }

    mock_vhost = Vhost(
        id=43,
        status="provisioning",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        external_host="tcp-endpoint.example.com",
        type="tcp",
        container_ports=[5432],
        links={"service": {"href": "https://api.aptible.com/services/123"}},
    )

    mock_vhost_manager.create_custom_domain = AsyncMock(return_value=mock_vhost)

    with patch("main.getService", new=AsyncMock(return_value=mock_service_data)):
        result = await createTypedEndpoint(
            "test-app",
            "web",
            "tcp-endpoint.example.com",
            "tcp",
            container_ports=[5432],
            account_handle="test-account",
        )

        mock_vhost_manager.create_custom_domain.assert_called_once_with(
            123,
            "tcp-endpoint.example.com",
            managed_tls=False,
            certificate_fingerprint=None,
            endpoint_type="tcp",
            container_ports=[5432],
        )
        assert result["id"] == 43
        assert result["type"] == "tcp"
        assert result["container_ports"] == [5432]


@pytest.mark.asyncio
async def test_create_typed_endpoint_rejects_unknown_type(mock_vhost_manager):
    with pytest.raises(ValueError, match="tcp, tls, grpc"):
        await createTypedEndpoint(
            "test-app",
            "web",
            "endpoint.example.com",
            "smtp",  # type: ignore[arg-type]
        )

    mock_vhost_manager.create_custom_domain.assert_not_called()


@pytest.mark.asyncio
async def test_create_database_endpoint_success(mock_vhost_manager):
    """
    Test createDatabaseEndpoint resolves the database and composes
    VhostManager.create_database_endpoint correctly.
    """
    mock_database_data = {
        "id": 7,
        "handle": "main-db",
        "status": "provisioned",
        "type": "postgresql",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_vhost = Vhost(
        id=44,
        status="provisioning",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        external_host="db-endpoint.example.com",
        type="tcp",
        links={
            "database": {"href": "https://api.aptible.com/databases/7"},
            "service": {"href": "https://api.aptible.com/services/1"},
        },
    )

    mock_vhost_manager.create_database_endpoint = AsyncMock(return_value=mock_vhost)

    with patch("main.getDatabase", new=AsyncMock(return_value=mock_database_data)):
        result = await createDatabaseEndpoint(
            "main-db", account_handle="test-account", internal=True
        )

        mock_vhost_manager.create_database_endpoint.assert_called_once_with(
            7, internal=True, ip_whitelist=None
        )
        assert result["id"] == 44
        assert result["external_host"] == "db-endpoint.example.com"


@pytest.mark.asyncio
async def test_create_database_endpoint_not_found():
    """
    Test createDatabaseEndpoint raises an exception naming the handle when the
    database does not exist, instead of attempting provisioning.
    """
    with patch("main.getDatabase", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await createDatabaseEndpoint("nonexistent-db")

        assert "Database nonexistent-db not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_modify_endpoint_success(mock_vhost_manager):
    """
    Test modifyEndpoint passes only the supplied fields to VhostManager.modify.
    """
    mock_vhost = Vhost(
        id=42,
        status="provisioned",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-02T12:00:00Z",
        external_host="app-123.aptible.com",
        container_ports=[8080],
        links={"service": {"href": "https://api.aptible.com/services/123"}},
    )

    mock_vhost_manager.modify = AsyncMock(return_value=mock_vhost)

    result = await modifyEndpoint(42, container_ports=[8080])

    mock_vhost_manager.modify.assert_called_once_with(42, container_ports=[8080])
    assert result["id"] == 42
    assert result["container_ports"] == [8080]


@pytest.mark.asyncio
async def test_modify_endpoint_no_parameters():
    """
    Test modifyEndpoint raises when no modifiable fields are supplied.
    """
    with pytest.raises(ValueError) as excinfo:
        await modifyEndpoint(42)

    assert (
        "Must specify at least one of container_ports or certificate_fingerprint"
        in str(excinfo.value)
    )


@pytest.mark.asyncio
async def test_renew_endpoint_success(mock_vhost_manager):
    """
    Test renewEndpoint triggers a TLS renewal and returns the updated vhost.
    """
    mock_vhost = Vhost(
        id=42,
        status="renewing",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-03T12:00:00Z",
        external_host="app-123.aptible.com",
        links={"service": {"href": "https://api.aptible.com/services/123"}},
    )

    mock_vhost_manager.renew = AsyncMock(return_value=mock_vhost)

    result = await renewEndpoint(42)

    mock_vhost_manager.renew.assert_called_once_with(42)
    assert result["id"] == 42
    assert result["status"] == "renewing"


@pytest.mark.asyncio
async def test_rename_app_success(mock_app_manager):
    """
    Test renameApp successfully renames an app to a new handle.
    """
    mock_app_data = {
        "id": 1,
        "handle": "old-name",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_renamed_app = App(
        id=1,
        handle="new-name",
        status="provisioned",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-02T12:00:00Z",
        links={"account": {"href": "https://api.aptible.com/accounts/123"}},
    )
    mock_app_manager.rename = AsyncMock(return_value=mock_renamed_app)

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        result = await renameApp("old-name", "new-name", "test-account")

        mock_app_manager.rename.assert_called_once_with(1, "new-name")
        assert result["id"] == 1
        assert result["handle"] == "new-name"


@pytest.mark.asyncio
async def test_rename_app_not_found():
    """
    Test renameApp raises an exception when the app is not found.
    """
    with patch("main.getApp", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await renameApp("nonexistent-app", "new-name")

        assert "App nonexistent-app not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_deploy_app_success(mock_app_manager):
    """
    Test deployApp triggers a deploy and returns the updated app.
    """
    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_deployed_app = App(
        id=1,
        handle="test-app",
        status="provisioned",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-03T12:00:00Z",
        links={"account": {"href": "https://api.aptible.com/accounts/123"}},
    )
    mock_app_manager.deploy = AsyncMock(return_value=mock_deployed_app)

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        result = await deployApp(
            "test-app",
            docker_image="example/image:latest",
            account_handle="test-account",
        )

        mock_app_manager.deploy.assert_called_once_with(1, "example/image:latest", None)
        assert result["id"] == 1
        assert result["updated_at"] == "2023-01-03T12:00:00Z"


@pytest.mark.asyncio
async def test_deploy_app_not_found():
    """
    Test deployApp raises an exception when the app is not found.
    """
    with patch("main.getApp", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await deployApp("nonexistent-app")

        assert "App nonexistent-app not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_rebuild_app_success(mock_app_manager):
    """
    Test rebuildApp triggers a rebuild and returns the updated app.
    """
    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_rebuilt_app = App(
        id=1,
        handle="test-app",
        status="provisioned",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-03T12:00:00Z",
        links={"account": {"href": "https://api.aptible.com/accounts/123"}},
    )
    mock_app_manager.rebuild = AsyncMock(return_value=mock_rebuilt_app)

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        result = await rebuildApp("test-app", "test-account")

        mock_app_manager.rebuild.assert_called_once_with(1)
        assert result["id"] == 1
        assert result["updated_at"] == "2023-01-03T12:00:00Z"


@pytest.mark.asyncio
async def test_rebuild_app_not_found():
    """
    Test rebuildApp raises an exception when the app is not found.
    """
    with patch("main.getApp", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await rebuildApp("nonexistent-app")

        assert "App nonexistent-app not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_restart_app_success(mock_app_manager):
    """
    Test restartApp triggers a restart and returns the updated app.
    """
    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }

    mock_restarted_app = App(
        id=1,
        handle="test-app",
        status="provisioned",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-03T12:00:00Z",
        links={"account": {"href": "https://api.aptible.com/accounts/123"}},
    )
    mock_app_manager.restart = AsyncMock(return_value=mock_restarted_app)

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        result = await restartApp("test-app", "test-account")

        mock_app_manager.restart.assert_called_once_with(1)
        assert result["id"] == 1
        assert result["updated_at"] == "2023-01-03T12:00:00Z"


@pytest.mark.asyncio
async def test_restart_app_not_found():
    """
    Test restartApp raises an exception when the app is not found.
    """
    with patch("main.getApp", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await restartApp("nonexistent-app")

        assert "App nonexistent-app not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_service_settings_success(mock_service_manager):
    """
    Test getServiceSettings returns the service's current settings.
    """
    mock_service_data = {
        "id": 1,
        "handle": "web",
        "process_type": "web",
        "container_count": 2,
        "container_memory_limit_mb": 1024,
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"app": {"href": "https://api.aptible.com/apps/1"}},
    }

    mock_service_manager.get_settings = AsyncMock(
        return_value={
            "force_zero_downtime": True,
            "naive_health_check": False,
            "restart_free_scaling": False,
            "stop_timeout": 90,
        }
    )

    with patch("main.getService", new=AsyncMock(return_value=mock_service_data)):
        result = await getServiceSettings("test-app", "web", "test-account")

        mock_service_manager.get_settings.assert_called_once_with(1)
        assert result["force_zero_downtime"] is True
        assert result["stop_timeout"] == 90


@pytest.mark.asyncio
async def test_update_service_settings_success(mock_service_manager):
    """
    Test updateServiceSettings applies the requested settings.
    """
    mock_service_data = {
        "id": 1,
        "handle": "web",
        "process_type": "web",
        "container_count": 2,
        "container_memory_limit_mb": 1024,
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"app": {"href": "https://api.aptible.com/apps/1"}},
    }

    mock_updated_service = Service(
        id=1,
        handle="web",
        process_type="web",
        container_count=2,
        container_memory_limit_mb=1024,
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-03T12:00:00Z",
        links={"app": {"href": "https://api.aptible.com/apps/1"}},
    )

    mock_service_manager.update_settings = AsyncMock(return_value=mock_updated_service)

    with patch("main.getService", new=AsyncMock(return_value=mock_service_data)):
        result = await updateServiceSettings(
            "test-app",
            "web",
            {"naive_health_check": True},
            account_handle="test-account",
        )

        mock_service_manager.update_settings.assert_called_once_with(
            1, naive_health_check=True
        )
        assert result["id"] == 1
        assert result["updated_at"] == "2023-01-03T12:00:00Z"


@pytest.mark.asyncio
async def test_cancel_operation_success(mock_operation_manager):
    """
    Test cancelOperation cancels a running operation and returns its status.
    """
    mock_operation = Operation(
        id=99,
        resource_id=1,
        resource_type="app",
        type="deploy",
        status="running",
        cancelled=True,
        links={},
    )

    mock_operation_manager.cancel = AsyncMock(return_value=mock_operation)

    result = await cancelOperation(99)

    mock_operation_manager.cancel.assert_called_once_with(99)
    assert result["id"] == 99
    assert result["cancelled"] is True


@pytest.mark.asyncio
async def test_cancel_operation_already_terminal(mock_operation_manager):
    """
    Test cancelOperation raises when the operation is already terminal.
    """
    mock_operation_manager.cancel = AsyncMock(
        side_effect=Exception(
            "Operation 99 is already succeeded and cannot be cancelled"
        )
    )

    with pytest.raises(Exception) as excinfo:
        await cancelOperation(99)

    assert "already succeeded and cannot be cancelled" in str(excinfo.value)


@pytest.mark.asyncio
async def test_rename_environment_success(mock_account_manager):
    """
    Test renameEnvironment successfully renames an environment.
    """
    mock_account = Account(
        id=123,
        handle="old-name",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    mock_renamed_account = Account(
        id=123,
        handle="new-name",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-02T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.rename = AsyncMock(return_value=mock_renamed_account)

    result = await renameEnvironment("old-name", "new-name")

    mock_account_manager.get.assert_called_once_with("old-name")
    mock_account_manager.rename.assert_called_once_with(123, "new-name")
    assert result["id"] == 123
    assert result["handle"] == "new-name"


@pytest.mark.asyncio
async def test_rename_environment_not_found(mock_account_manager):
    """
    Test renameEnvironment raises an exception when the environment is not found.
    """
    mock_account_manager.get = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await renameEnvironment("nonexistent-account", "new-name")

    assert "Account nonexistent-account not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_environment_ca_certificate_configured(mock_account_manager):
    """
    Test getEnvironmentCaCertificate returns the CA certificate when configured.
    """
    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)
    mock_account_manager.get_ca_certificate = AsyncMock(
        return_value="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
    )

    result = await getEnvironmentCaCertificate("test-account")

    mock_account_manager.get_ca_certificate.assert_called_once_with(123)
    assert result is not None
    assert "BEGIN CERTIFICATE" in result


@pytest.mark.asyncio
async def test_get_environment_ca_certificate_unconfigured(mock_account_manager):
    """
    Test getEnvironmentCaCertificate returns None when no CA certificate is configured.
    """
    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)
    mock_account_manager.get_ca_certificate = AsyncMock(return_value=None)

    result = await getEnvironmentCaCertificate("test-account")

    assert result is None


@pytest.mark.asyncio
async def test_get_environment_ca_certificate_not_found(mock_account_manager):
    """
    Test getEnvironmentCaCertificate raises an exception when the environment is not found.
    """
    mock_account_manager.get = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await getEnvironmentCaCertificate("nonexistent-account")

    assert "Account nonexistent-account not found" in str(excinfo.value)


def _database_payload(
    database_id: int = 1,
    handle: str = "test-db",
    account_id: int = 123,
    status: str = "provisioned",
) -> dict:
    """
    Build a getDatabase-shaped payload for the Tier 3 database tool tests.
    """
    return {
        "id": database_id,
        "handle": handle,
        "status": status,
        "type": "postgresql",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {
            "account": {"href": f"https://api.aptible.com/accounts/{account_id}"},
            "database_image": {"href": "https://api.aptible.com/database_images/1"},
        },
    }


@pytest.mark.asyncio
async def test_replicate_database_success(mock_database_manager):
    """
    Test replicateDatabase replicates the source database and returns the
    replica fetched afterwards.
    """
    source_data = _database_payload(1, "test-db")
    replica_data = _database_payload(2, "test-db-replica", status="provisioning")
    existing_namesake = Database.model_validate(
        _database_payload(99, "test-db-replica", account_id=999)
    )
    existing_same_account = Database.model_validate(
        _database_payload(98, "test-db-replica", account_id=123)
    )

    mock_database_manager.replicate = AsyncMock()
    mock_database_manager.list = AsyncMock(
        side_effect=[
            [existing_namesake, existing_same_account],
            [
                existing_namesake,
                existing_same_account,
                Database.model_validate(replica_data),
            ],
        ]
    )

    with patch(
        "main.getDatabase", new=AsyncMock(return_value=source_data)
    ) as mock_get_database:
        result = await replicateDatabase(
            "test-db", "test-db-replica", 4096, 20, "test-account"
        )

    mock_database_manager.replicate.assert_called_once_with(
        1, "test-db-replica", 4096, 20
    )
    mock_get_database.assert_called_once_with("test-db", "test-account")
    assert result["id"] == 2
    assert result["handle"] == "test-db-replica"


@pytest.mark.asyncio
async def test_replicate_database_reconciles_delayed_visibility(mock_database_manager):
    source_data = _database_payload(1, "test-db")
    replica = Database.model_validate(_database_payload(2, "replica"))
    mock_database_manager.replicate = AsyncMock()
    mock_database_manager.list = AsyncMock(side_effect=[[], [], [replica]])

    with (
        patch("main.getDatabase", new=AsyncMock(return_value=source_data)),
        patch("main.asyncio.sleep", new=AsyncMock()) as sleep,
    ):
        result = await replicateDatabase("test-db", "replica")

    sleep.assert_awaited_once_with(1.0)
    assert result["id"] == 2


@pytest.mark.asyncio
async def test_replicate_database_source_not_found(mock_database_manager):
    """
    Test replicateDatabase raises when the source database is not found and
    never starts a replication operation.
    """
    mock_database_manager.replicate = AsyncMock()

    with patch("main.getDatabase", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await replicateDatabase("nonexistent-db", "replica")

    assert "Database nonexistent-db not found" in str(excinfo.value)
    mock_database_manager.replicate.assert_not_called()


@pytest.mark.asyncio
async def test_clone_database_success(mock_database_manager):
    """
    Test cloneDatabase clones the source database and returns the new clone
    fetched afterwards.
    """
    source_data = _database_payload(1, "test-db")
    clone_data = _database_payload(3, "test-db-clone", status="provisioning")

    mock_database_manager.clone = AsyncMock()
    mock_database_manager.list = AsyncMock(
        side_effect=[[], [Database.model_validate(clone_data)]]
    )

    with patch(
        "main.getDatabase", new=AsyncMock(return_value=source_data)
    ) as mock_get_database:
        result = await cloneDatabase("test-db", "test-db-clone", "test-account")

    mock_database_manager.clone.assert_called_once_with(1, "test-db-clone")
    mock_get_database.assert_called_once_with("test-db", "test-account")
    assert result["id"] == 3
    assert result["handle"] == "test-db-clone"


@pytest.mark.asyncio
async def test_clone_database_not_found_after_clone(mock_database_manager):
    """
    Test cloneDatabase raises when the cloned database cannot be found after
    the clone operation completes.
    """
    mock_database_manager.clone = AsyncMock()
    mock_database_manager.list = AsyncMock(return_value=[])

    with (
        patch(
            "main.getDatabase",
            new=AsyncMock(return_value=_database_payload(1, "test-db")),
        ),
        patch("main.asyncio.sleep", new=AsyncMock()) as sleep,
    ):
        with pytest.raises(Exception) as excinfo:
            await cloneDatabase("test-db", "test-db-clone")

    assert "Expected one new database with handle test-db-clone" in str(excinfo.value)
    assert "in account 123, found 0" in str(excinfo.value)
    assert sleep.await_count == 9


@pytest.mark.asyncio
async def test_modify_database_iops_success(mock_database_manager):
    """
    Test modifyDatabaseIops resolves the database and returns the modified one.
    """
    modified_database = Database.model_validate(_database_payload(1, "test-db"))
    mock_database_manager.modify_iops = AsyncMock(return_value=modified_database)

    with patch(
        "main.getDatabase",
        new=AsyncMock(return_value=_database_payload(1, "test-db")),
    ):
        result = await modifyDatabaseIops("test-db", 3000, "gp3", "test-account")

    mock_database_manager.modify_iops.assert_called_once_with(1, 3000, "gp3")
    assert result["id"] == 1
    assert result["handle"] == "test-db"


@pytest.mark.asyncio
async def test_modify_database_iops_requires_a_field(mock_database_manager):
    """
    Test modifyDatabaseIops rejects a call that would change nothing.
    """
    mock_database_manager.modify_iops = AsyncMock()

    with pytest.raises(ValueError) as excinfo:
        await modifyDatabaseIops("test-db")

    assert "provisioned_iops or ebs_volume_type" in str(excinfo.value)
    mock_database_manager.modify_iops.assert_not_called()


@pytest.mark.asyncio
async def test_resize_database_success(mock_database_manager):
    """
    Test resizeDatabase resolves the database and returns the resized one.
    """
    resized_database = Database.model_validate(_database_payload(1, "test-db"))
    mock_database_manager.resize = AsyncMock(return_value=resized_database)

    with patch(
        "main.getDatabase",
        new=AsyncMock(return_value=_database_payload(1, "test-db")),
    ):
        result = await resizeDatabase("test-db", 7168, 100, "m5", "test-account")

    mock_database_manager.resize.assert_called_once_with(1, 7168, 100, "m5")
    assert result["id"] == 1


@pytest.mark.asyncio
async def test_resize_database_requires_a_field(mock_database_manager):
    """
    Test resizeDatabase rejects a call that would change nothing.
    """
    mock_database_manager.resize = AsyncMock()

    with pytest.raises(ValueError) as excinfo:
        await resizeDatabase("test-db")

    assert "container_size, disk_size, or instance_profile" in str(excinfo.value)
    mock_database_manager.resize.assert_not_called()


@pytest.mark.asyncio
async def test_reload_database_success(mock_database_manager):
    """
    Test reloadDatabase resolves the database and returns the reloaded one.
    """
    reloaded_database = Database.model_validate(_database_payload(1, "test-db"))
    mock_database_manager.reload = AsyncMock(return_value=reloaded_database)

    with patch(
        "main.getDatabase",
        new=AsyncMock(return_value=_database_payload(1, "test-db")),
    ):
        result = await reloadDatabase("test-db", "test-account")

    mock_database_manager.reload.assert_called_once_with(1)
    assert result["handle"] == "test-db"


@pytest.mark.asyncio
async def test_reload_database_not_found(mock_database_manager):
    """
    Test reloadDatabase raises when the database is not found.
    """
    mock_database_manager.reload = AsyncMock()

    with patch("main.getDatabase", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await reloadDatabase("nonexistent-db")

    assert "Database nonexistent-db not found" in str(excinfo.value)
    mock_database_manager.reload.assert_not_called()


@pytest.mark.asyncio
async def test_rename_database_success(mock_database_manager):
    """
    Test renameDatabase resolves the database and returns it under its new
    handle.
    """
    renamed_database = Database.model_validate(_database_payload(1, "new-db-name"))
    mock_database_manager.rename = AsyncMock(return_value=renamed_database)

    with patch(
        "main.getDatabase",
        new=AsyncMock(return_value=_database_payload(1, "old-db-name")),
    ):
        result = await renameDatabase("old-db-name", "new-db-name", "test-account")

    mock_database_manager.rename.assert_called_once_with(1, "new-db-name")
    assert result["handle"] == "new-db-name"


@pytest.mark.asyncio
async def test_restart_database_success(mock_database_manager):
    """
    Test restartDatabase resolves the database and returns the restarted one.
    """
    restarted_database = Database.model_validate(_database_payload(1, "test-db"))
    mock_database_manager.restart = AsyncMock(return_value=restarted_database)

    with patch(
        "main.getDatabase",
        new=AsyncMock(return_value=_database_payload(1, "test-db")),
    ):
        result = await restartDatabase("test-db", "test-account")

    mock_database_manager.restart.assert_called_once_with(1)
    assert result["id"] == 1


@pytest.mark.asyncio
async def test_list_database_versions_success(mock_database_manager):
    """
    Test listDatabaseVersions returns the images available for a type.
    """
    mock_images = [
        DatabaseImage(
            id=1,
            version="14",
            type="postgresql",
            description="PostgreSQL 14",
            links={},
        ),
        DatabaseImage(
            id=2,
            version="15",
            type="postgresql",
            description="PostgreSQL 15",
            links={},
        ),
    ]
    mock_database_manager.list_versions_for_type = AsyncMock(return_value=mock_images)

    result = await listDatabaseVersions("postgresql")

    mock_database_manager.list_versions_for_type.assert_called_once_with("postgresql")
    assert [image["version"] for image in result] == ["14", "15"]


@pytest.mark.asyncio
async def test_list_database_versions_unknown_type(mock_database_manager):
    """
    Test listDatabaseVersions propagates the manager's error for an unknown
    database type rather than returning an empty list.
    """
    mock_database_manager.list_versions_for_type = AsyncMock(
        side_effect=ValueError("No database type found named nonexistent")
    )

    with pytest.raises(ValueError) as excinfo:
        await listDatabaseVersions("nonexistent")

    assert "No database type found named nonexistent" in str(excinfo.value)


@pytest.mark.asyncio
async def test_list_maintenance_entries_success(
    mock_maintenance_manager, mock_account_manager
):
    """
    Test listMaintenanceEntries resolves the environment and returns its
    app and database maintenance entries.
    """
    mock_account = Account(
        id=123,
        handle="test-account",
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        links={"stack": {"href": "https://api.aptible.com/stacks/789"}},
    )
    mock_account_manager.get = AsyncMock(return_value=mock_account)

    mock_entries = [
        MaintenanceEntry(
            id=1,
            handle="test-app",
            status="scheduled",
            resource_type="app",
            links={"account": {"href": "https://api.aptible.com/accounts/123"}},
        ),
        MaintenanceEntry(
            id=2,
            handle="test-db",
            status="scheduled",
            resource_type="database",
            links={"account": {"href": "https://api.aptible.com/accounts/123"}},
        ),
    ]
    mock_maintenance_manager.list_for_account = AsyncMock(return_value=mock_entries)

    result = await listMaintenanceEntries("test-account")

    mock_maintenance_manager.list_for_account.assert_called_once_with(123)
    assert len(result) == 2
    assert result[0]["resource_type"] == "app"
    assert result[1]["resource_type"] == "database"


@pytest.mark.asyncio
async def test_list_maintenance_entries_account_not_found(
    mock_maintenance_manager, mock_account_manager
):
    """
    Test listMaintenanceEntries raises when the environment is not found
    instead of returning an empty list.
    """
    mock_account_manager.get = AsyncMock(return_value=None)
    mock_maintenance_manager.list_for_account = AsyncMock()

    with pytest.raises(Exception) as excinfo:
        await listMaintenanceEntries("nonexistent-account")

    assert "Account nonexistent-account not found" in str(excinfo.value)
    mock_maintenance_manager.list_for_account.assert_not_called()


@pytest.mark.asyncio
async def test_run_app_command_success(mock_app_manager):
    """
    Test runAppCommand resolves the app and returns the command's output.
    """
    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }
    mock_app_manager.run_command = AsyncMock(return_value="migration complete")

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        result = await runAppCommand(
            "test-app", "bundle exec rake db:migrate", False, "test-account"
        )

    mock_app_manager.run_command.assert_called_once_with(
        1, "bundle exec rake db:migrate", False
    )
    assert result == "migration complete"


@pytest.mark.asyncio
async def test_run_app_command_app_not_found(mock_app_manager):
    """
    Test runAppCommand raises when the app is not found and never starts an
    execute operation.
    """
    mock_app_manager.run_command = AsyncMock()

    with patch("main.getApp", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception) as excinfo:
            await runAppCommand("nonexistent-app", "ls")

    assert "App nonexistent-app not found" in str(excinfo.value)
    mock_app_manager.run_command.assert_not_called()


@pytest.mark.asyncio
async def test_run_app_command_failure_includes_output(mock_app_manager):
    """
    Test runAppCommand propagates a failed operation's error, including any
    output captured before the failure.
    """
    mock_app_data = {
        "id": 1,
        "handle": "test-app",
        "status": "provisioned",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "links": {"account": {"href": "https://api.aptible.com/accounts/123"}},
    }
    mock_app_manager.run_command = AsyncMock(
        side_effect=Exception("Operation 5 failed: boom\nOutput:\ncommand not found")
    )

    with patch("main.getApp", new=AsyncMock(return_value=mock_app_data)):
        with pytest.raises(Exception) as excinfo:
            await runAppCommand("test-app", "bad-command")

    assert "Operation 5 failed: boom" in str(excinfo.value)
    assert "command not found" in str(excinfo.value)
