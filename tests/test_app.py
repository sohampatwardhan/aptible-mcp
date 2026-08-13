import pytest
from unittest.mock import MagicMock

from models.app import App, AppManager
from api_client import AptibleApiClient
from models.base import ResourceBase


@pytest.fixture
def mock_api_client():
    """
    Fixture providing a mock AptibleApiClient.
    """
    mock_client = MagicMock(spec=AptibleApiClient)
    return mock_client


@pytest.fixture
def app_manager(mock_api_client):
    """
    Fixture providing an AppManager with a mock API client.
    """
    return AppManager(mock_api_client)


@pytest.fixture
def sample_app_data():
    """
    Fixture providing sample app data for testing.
    """
    return {
        "id": 123,
        "handle": "test-app",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "status": "provisioned",
        "_links": {
            "self": {"href": "https://api.aptible.com/apps/123"},
            "account": {"href": "https://api.aptible.com/accounts/456"},
            "services": {"href": "https://api.aptible.com/apps/123/services"},
        },
    }


@pytest.fixture
def sample_apps_data():
    """
    Fixture providing sample data for multiple apps.
    """
    return [
        {
            "id": 123,
            "handle": "test-app-1",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "status": "provisioned",
            "_links": {
                "self": {"href": "https://api.aptible.com/apps/123"},
                "account": {"href": "https://api.aptible.com/accounts/456"},
                "services": {"href": "https://api.aptible.com/apps/123/services"},
            },
        },
        {
            "id": 789,
            "handle": "test-app-2",
            "created_at": "2023-01-02T12:00:00Z",
            "updated_at": "2023-01-02T12:00:00Z",
            "status": "provisioned",
            "_links": {
                "self": {"href": "https://api.aptible.com/apps/789"},
                "account": {"href": "https://api.aptible.com/accounts/456"},
                "services": {"href": "https://api.aptible.com/apps/789/services"},
            },
        },
    ]


@pytest.fixture
def sample_services_data():
    """
    Fixture providing sample services data for testing.
    """
    return [
        {
            "id": 111,
            "process_type": "web",
            "command": "python app.py",
            "container_count": 2,
            "container_memory_limit_mb": 512,
        },
        {
            "id": 222,
            "process_type": "worker",
            "command": "python worker.py",
            "container_count": 1,
            "container_memory_limit_mb": 1024,
        },
    ]


class TestApp:
    """
    Tests for the App model.
    """

    def test_app_init(self, sample_app_data):
        """
        Test that App can be initialized from valid data.
        """
        app = App.model_validate(sample_app_data)

        assert app.id == 123
        assert app.handle == "test-app"
        assert app.created_at == "2023-01-01T12:00:00Z"
        assert app.updated_at == "2023-01-01T12:00:00Z"
        assert app.status == "provisioned"
        assert app.links == {
            "self": {"href": "https://api.aptible.com/apps/123"},
            "account": {"href": "https://api.aptible.com/accounts/456"},
            "services": {"href": "https://api.aptible.com/apps/123/services"},
        }

    def test_app_inheritance(self):
        """
        Test that App inherits from ResourceBase.
        """
        assert issubclass(App, ResourceBase)

    def test_account_id_computed_field(self, sample_app_data):
        """
        Test that account_id is correctly computed from links.
        """
        app = App.model_validate(sample_app_data)
        assert app.account_id == 456

    def test_account_id_missing_account_link(self):
        """
        Test that account_id raises exception when account link is missing.
        """
        app_data = {
            "id": 123,
            "handle": "test-app",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "status": "provisioned",
            "_links": {
                "self": {"href": "https://api.aptible.com/apps/123"},
            },
        }
        app = App.model_validate(app_data)

        with pytest.raises(Exception, match="Account is missing from _links"):
            _ = app.account_id

    def test_account_id_missing_href(self):
        """
        Test that account_id raises exception when href is missing.
        """
        app_data = {
            "id": 123,
            "handle": "test-app",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "status": "provisioned",
            "_links": {
                "self": {"href": "https://api.aptible.com/apps/123"},
                "account": {"not_href": "https://api.aptible.com/accounts/456"},
            },
        }
        app = App.model_validate(app_data)

        with pytest.raises(Exception, match="Account link is missing href"):
            _ = app.account_id


class TestAppManager:
    """
    Tests for the AppManager class.
    """

    @pytest.mark.asyncio
    async def test_list(self, app_manager, mock_api_client, sample_apps_data):
        """
        Test that list correctly returns all apps.
        """

        mock_api_client.get.return_value = {"_embedded": {"apps": sample_apps_data}}

        result = await app_manager.list()

        assert len(result) == 2
        assert isinstance(result[0], App)
        assert result[0].id == 123
        assert result[0].handle == "test-app-1"
        assert result[0].status == "provisioned"
        assert result[1].id == 789
        assert result[1].handle == "test-app-2"

        mock_api_client.get.assert_called_once_with("/apps?per_page=5000&no_embed=true")

    @pytest.mark.asyncio
    async def test_get_by_handle_found(
        self, app_manager, mock_api_client, sample_apps_data
    ):
        """
        Test get method successfully retrieves an app by handle.
        """

        mock_api_client.get.return_value = {"_embedded": {"apps": sample_apps_data}}

        result = await app_manager.get("test-app-1")

        assert result is not None
        assert isinstance(result, App)
        assert result.id == 123
        assert result.handle == "test-app-1"
        assert result.status == "provisioned"

        mock_api_client.get.assert_called_once_with("/apps?per_page=5000&no_embed=true")

    @pytest.mark.asyncio
    async def test_get_by_handle_not_found(
        self, app_manager, mock_api_client, sample_apps_data
    ):
        """
        Test get method returns None when app is not found.
        """

        mock_api_client.get.return_value = {"_embedded": {"apps": sample_apps_data}}

        result = await app_manager.get("nonexistent-app")

        assert result is None

        mock_api_client.get.assert_called_once_with("/apps?per_page=5000&no_embed=true")

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self, app_manager, mock_api_client, sample_apps_data
    ):
        """
        Test get_by_id method successfully retrieves an app by ID.
        """
        mock_api_client.get.return_value = sample_apps_data[0]

        result = await app_manager.get_by_id(sample_apps_data[0]["id"])

        assert result is not None
        assert isinstance(result, App)
        assert result.id == sample_apps_data[0]["id"]
        assert result.handle == sample_apps_data[0]["handle"]
        assert result.status == sample_apps_data[0]["status"]

        mock_api_client.get.assert_called_once_with(
            f"/apps/{sample_apps_data[0]['id']}"
        )

    @pytest.mark.asyncio
    async def test_create_with_docker_image(
        self, app_manager, mock_api_client, sample_app_data
    ):
        """
        Test create method with docker_image creates an app and triggers configure and deploy.
        """

        mock_api_client.post.return_value = sample_app_data
        mock_api_client.get.return_value = sample_app_data

        create_data = {
            "handle": "test-app",
            "account_id": 456,
            "docker_image": "nginx:latest",
        }

        result = await app_manager.create(create_data)

        assert isinstance(result, App)
        assert result.id == 123
        assert result.handle == "test-app"
        assert result.status == "provisioned"

        assert mock_api_client.post.call_count == 3

        mock_api_client.post.assert_any_call("/accounts/456/apps", create_data)

        mock_api_client.post.assert_any_call(
            "/apps/123/operations",
            {
                "type": "configure",
                "env": {
                    "FORCE_SSL": "1",
                    "APTIBLE_DOCKER_IMAGE": "nginx:latest",
                },
            },
        )

        mock_api_client.post.assert_any_call("/apps/123/operations", {"type": "deploy"})

        assert mock_api_client.wait_for_operation.call_count == 2

    @pytest.mark.asyncio
    async def test_create_without_docker_image(
        self, app_manager, mock_api_client, sample_app_data
    ):
        """
        Test create method without docker_image only creates app without configuring or deploying.
        """

        mock_api_client.post.return_value = sample_app_data

        create_data = {"handle": "test-app", "account_id": 456, "docker_image": None}

        result = await app_manager.create(create_data)

        assert isinstance(result, App)
        assert result.id == 123
        assert result.handle == "test-app"

        mock_api_client.post.assert_called_once_with("/accounts/456/apps", create_data)

        mock_api_client.wait_for_operation.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_missing_handle(self, app_manager):
        """
        Test create method raises exception when handle is missing.
        """
        create_data = {
            "handle": "",
            "account_id": 456,
            "docker_image": "nginx:latest",
        }

        with pytest.raises(Exception, match="A handle is required"):
            await app_manager.create(create_data)

    @pytest.mark.asyncio
    async def test_create_missing_account_id(self, app_manager):
        """
        Test create method raises exception when account_id is missing.
        """
        create_data = {
            "handle": "test-app",
            "account_id": None,
            "docker_image": "nginx:latest",
        }

        with pytest.raises(Exception, match="An account_id is required"):
            await app_manager.create(create_data)

    @pytest.mark.asyncio
    async def test_configure(self, app_manager, mock_api_client):
        """
        Test configure method sends correct operation data and waits for operation.
        """

        app_id = 123
        env = {"NODE_ENV": "production", "PORT": "8080"}

        operation_response = {"id": "op-123"}
        mock_api_client.post.return_value = operation_response

        await app_manager.configure(app_id, env)

        mock_api_client.post.assert_called_once_with(
            "/apps/123/operations", {"type": "configure", "env": env}
        )

        mock_api_client.wait_for_operation.assert_called_once_with("op-123")

    @pytest.mark.asyncio
    async def test_deploy(self, app_manager, mock_api_client, sample_app_data):
        """
        Test deploy method sends correct operation data and waits for operation.
        """

        app_id = 123

        operation_response = {"id": "op-456"}
        mock_api_client.post.return_value = operation_response
        mock_api_client.get.return_value = sample_app_data

        result = await app_manager.deploy(app_id)

        assert isinstance(result, App)
        assert result.id == 123
        mock_api_client.post.assert_called_once_with(
            "/apps/123/operations", {"type": "deploy"}
        )

        mock_api_client.wait_for_operation.assert_called_once_with("op-456")

    @pytest.mark.asyncio
    async def test_deploy_with_docker_image(
        self, app_manager, mock_api_client, sample_app_data
    ):
        """
        Test deploy method with docker_image includes settings in operation data.
        """
        app_id = 123
        mock_api_client.post.return_value = {"id": "op-456"}
        mock_api_client.get.return_value = sample_app_data

        result = await app_manager.deploy(app_id, docker_image="custom-image:v1")

        assert isinstance(result, App)
        mock_api_client.post.assert_called_once_with(
            "/apps/123/operations",
            {
                "type": "deploy",
                "settings": {"APTIBLE_DOCKER_IMAGE": "custom-image:v1"},
            },
        )
        mock_api_client.wait_for_operation.assert_called_once_with("op-456")

    @pytest.mark.asyncio
    async def test_deploy_with_git_ref(
        self, app_manager, mock_api_client, sample_app_data
    ):
        """
        Test deploy method with git_ref includes git_ref in operation data.
        """
        app_id = 123
        mock_api_client.post.return_value = {"id": "op-456"}
        mock_api_client.get.return_value = sample_app_data

        result = await app_manager.deploy(app_id, git_ref="main")

        assert isinstance(result, App)
        mock_api_client.post.assert_called_once_with(
            "/apps/123/operations",
            {
                "type": "deploy",
                "git_ref": "main",
            },
        )
        mock_api_client.wait_for_operation.assert_called_once_with("op-456")

    @pytest.mark.asyncio
    async def test_rename_success(self, app_manager, mock_api_client, sample_app_data):
        """
        Test rename method sends PUT request and returns updated App.
        """
        app_id = 123
        updated_data = {**sample_app_data, "handle": "new-app-handle"}
        mock_api_client.put.return_value = updated_data

        result = await app_manager.rename(app_id, "new-app-handle")

        assert isinstance(result, App)
        assert result.handle == "new-app-handle"
        mock_api_client.put.assert_called_once_with(
            "/apps/123", {"handle": "new-app-handle"}
        )

    @pytest.mark.asyncio
    async def test_rebuild_success(self, app_manager, mock_api_client, sample_app_data):
        """
        Test rebuild method sends rebuild operation and returns App.
        """
        app_id = 123
        mock_api_client.post.return_value = {"id": "op-reb-1"}
        mock_api_client.get.return_value = sample_app_data

        result = await app_manager.rebuild(app_id)

        assert isinstance(result, App)
        mock_api_client.post.assert_called_once_with(
            "/apps/123/operations", {"type": "rebuild"}
        )
        mock_api_client.wait_for_operation.assert_called_once_with("op-reb-1")

    @pytest.mark.asyncio
    async def test_rebuild_failure(self, app_manager, mock_api_client):
        """
        Test rebuild method propagates failure exception from wait_for_operation.
        """
        app_id = 123
        mock_api_client.post.return_value = {"id": "op-reb-2"}
        mock_api_client.wait_for_operation.side_effect = Exception(
            "Operation op-reb-2 failed: Build error"
        )

        with pytest.raises(Exception, match="Build error"):
            await app_manager.rebuild(app_id)

    @pytest.mark.asyncio
    async def test_restart_success(self, app_manager, mock_api_client, sample_app_data):
        """
        Test restart method sends restart operation and returns App.
        """
        app_id = 123
        mock_api_client.post.return_value = {"id": "op-rst-1"}
        mock_api_client.get.return_value = sample_app_data

        result = await app_manager.restart(app_id)

        assert isinstance(result, App)
        mock_api_client.post.assert_called_once_with(
            "/apps/123/operations", {"type": "restart"}
        )
        mock_api_client.wait_for_operation.assert_called_once_with("op-rst-1")

    @pytest.mark.asyncio
    async def test_restart_failure(self, app_manager, mock_api_client):
        """
        Test restart method propagates failure exception from wait_for_operation.
        """
        app_id = 123
        mock_api_client.post.return_value = {"id": "op-rst-2"}
        mock_api_client.wait_for_operation.side_effect = Exception(
            "Operation op-rst-2 failed: Restart timeout"
        )

        with pytest.raises(Exception, match="Restart timeout"):
            await app_manager.restart(app_id)

    @pytest.mark.asyncio
    async def test_run_command_success(self, app_manager, mock_api_client, monkeypatch):
        """
        Test run_command starts execute operation, waits, and fetches logs.
        """
        app_id = 123
        mock_api_client.post.return_value = {"id": 999}
        mock_api_client.api_url = "http://localhost:3000"
        mock_api_client._get_headers.return_value = {}

        mock_logs = "bundle exec rake db:migrate output"

        from models.operation import OperationManager

        async def mock_logs_fn(self_op, op_id):
            assert op_id == 999
            return mock_logs

        monkeypatch.setattr(OperationManager, "logs", mock_logs_fn)

        result = await app_manager.run_command(app_id, "bundle exec rake db:migrate")

        assert result == mock_logs
        mock_api_client.post.assert_called_once_with(
            "/apps/123/operations",
            {
                "type": "execute",
                "command": "bundle exec rake db:migrate",
                "interactive": False,
            },
        )
        mock_api_client.wait_for_operation.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_run_command_failure_with_output(
        self, app_manager, mock_api_client, monkeypatch
    ):
        """
        Test run_command includes captured output on operation failure.
        """
        app_id = 123
        mock_api_client.post.return_value = {"id": 999}
        mock_api_client.wait_for_operation.side_effect = Exception(
            "Operation 999 failed: Command exited with status 1"
        )

        from models.operation import OperationManager

        async def mock_logs_fn(self_op, op_id):
            return "Error: table users does not exist"

        monkeypatch.setattr(OperationManager, "logs", mock_logs_fn)

        with pytest.raises(Exception, match="Command exited with status 1") as exc_info:
            await app_manager.run_command(app_id, "bundle exec rake db:migrate")

        assert "Output:" in str(exc_info.value)
        assert "Error: table users does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_by_id(self, app_manager, mock_api_client, sample_app_data):
        """
        Test delete method when app exists and is found by ID.
        """
        mock_api_client.get.return_value = sample_app_data
        operation_response = {"id": "op-789"}
        mock_api_client.post.return_value = operation_response

        await app_manager.delete(sample_app_data["id"])

        mock_api_client.get.assert_called_once_with(f"/apps/{sample_app_data['id']}")

        mock_api_client.post.assert_called_once_with(
            f"/apps/{sample_app_data['id']}/operations", {"type": "deprovision"}
        )
        mock_api_client.wait_for_operation.assert_called_once_with("op-789")

    @pytest.mark.asyncio
    async def test_get_services(
        self, app_manager, mock_api_client, sample_services_data
    ):
        """
        Test get_services method correctly calls the service manager.
        """

        mock_service_manager = MagicMock()
        mock_service_manager.list_by_app.return_value = sample_services_data

        app_manager.service_manager = mock_service_manager

        result = await app_manager.get_services(123)

        assert result == sample_services_data

        mock_service_manager.list_by_app.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_get_services_no_service_manager(self, app_manager):
        """
        Test get_services method raises exception when service manager is not injected.
        """

        app_manager.service_manager = None

        with pytest.raises(
            Exception, match="ServiceManager not injected into AppManager"
        ):
            await app_manager.get_services(123)
