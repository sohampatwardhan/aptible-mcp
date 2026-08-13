import pytest
from unittest.mock import MagicMock, AsyncMock

from models.service import Service, ServiceManager
from api_client import AptibleApiClient


@pytest.fixture
def mock_api_client():
    """
    Fixture providing a mock AptibleApiClient.
    """
    mock_client = MagicMock(spec=AptibleApiClient)
    return mock_client


@pytest.fixture
def service_manager(mock_api_client):
    """
    Fixture providing a ServiceManager with a mock API client.
    """
    return ServiceManager(mock_api_client)


@pytest.fixture
def sample_service_data():
    """
    Fixture providing sample service data for testing.
    """
    return {
        "id": 123,
        "handle": "web",
        "process_type": "web",
        "container_count": 2,
        "container_memory_limit_mb": 1024,
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "_links": {
            "app": {"href": "https://api.aptible.com/apps/456"},
            "service": {"href": "https://api.aptible.com/services/123"},
        },
    }


@pytest.fixture
def sample_services_data():
    """
    Fixture providing sample data for multiple services.
    """
    return [
        {
            "id": 123,
            "handle": "web",
            "process_type": "web",
            "container_count": 2,
            "container_memory_limit_mb": 1024,
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "_links": {
                "app": {"href": "https://api.aptible.com/apps/456"},
                "service": {"href": "https://api.aptible.com/services/123"},
            },
        },
        {
            "id": 789,
            "handle": "worker",
            "process_type": "worker",
            "container_count": 1,
            "container_memory_limit_mb": 512,
            "created_at": "2023-01-02T12:00:00Z",
            "updated_at": "2023-01-02T12:00:00Z",
            "_links": {
                "app": {"href": "https://api.aptible.com/apps/456"},
                "service": {"href": "https://api.aptible.com/services/789"},
            },
        },
    ]


@pytest.fixture
def sample_operation_response():
    """
    Fixture providing a sample operation response.
    """
    return {"id": "operation-123"}


class TestService:
    """
    Tests for the Service model.
    """

    def test_service_init(self, sample_service_data):
        """
        Test that Service can be initialized from valid data.
        """
        service = Service.model_validate(sample_service_data)

        assert service.id == 123
        assert service.handle == "web"
        assert service.process_type == "web"
        assert service.container_count == 2
        assert service.container_memory_limit_mb == 1024
        assert service.created_at == "2023-01-01T12:00:00Z"
        assert service.updated_at == "2023-01-01T12:00:00Z"
        assert service.links == {
            "app": {"href": "https://api.aptible.com/apps/456"},
            "service": {"href": "https://api.aptible.com/services/123"},
        }

    def test_transform_links(self, sample_service_data):
        """
        Test that _links is transformed to links during initialization.
        """
        # Data already has _links which should be transformed
        service = Service.model_validate(sample_service_data)

        assert "_links" not in sample_service_data
        assert "links" in sample_service_data
        assert service.links == {
            "app": {"href": "https://api.aptible.com/apps/456"},
            "service": {"href": "https://api.aptible.com/services/123"},
        }

    def test_app_id_computed_field(self, sample_service_data):
        """
        Test that the app_id computed field works correctly.
        """
        service = Service.model_validate(sample_service_data)

        assert service.app_id == 456

    def test_app_id_missing_app(self):
        """
        Test that app_id raises an exception when app is missing from links.
        """
        service_data = {
            "id": 123,
            "handle": "web",
            "process_type": "web",
            "container_count": 2,
            "container_memory_limit_mb": 1024,
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "links": {},
        }

        service = Service.model_validate(service_data)

        with pytest.raises(Exception) as excinfo:
            _ = service.app_id

        assert "App is missing from links" in str(excinfo.value)

    def test_app_id_missing_href(self):
        """
        Test that app_id raises an exception when app href is missing.
        """
        service_data = {
            "id": 123,
            "handle": "web",
            "process_type": "web",
            "container_count": 2,
            "container_memory_limit_mb": 1024,
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "links": {"app": {}},
        }

        service = Service.model_validate(service_data)

        with pytest.raises(Exception) as excinfo:
            _ = service.app_id

        assert "App link is missing href" in str(excinfo.value)


class TestServiceManager:
    """
    Tests for the ServiceManager class.
    """

    @pytest.mark.asyncio
    async def test_list_by_app(
        self, service_manager, mock_api_client, sample_services_data
    ):
        """
        Test list_by_app correctly returns services for an app.
        """
        app_id = 456
        # Setup mock response
        mock_api_client.get.return_value = {
            "_embedded": {"services": sample_services_data}
        }

        # Call the method being tested
        result = await service_manager.list_by_app(app_id)

        # Verify results
        assert len(result) == 2
        assert isinstance(result[0], Service)
        assert result[0].id == 123
        assert result[0].handle == "web"
        assert result[0].container_count == 2
        assert result[0].container_memory_limit_mb == 1024
        assert result[1].id == 789
        assert result[1].handle == "worker"
        assert result[1].container_count == 1
        assert result[1].container_memory_limit_mb == 512

        # Verify API call was made correctly
        mock_api_client.get.assert_called_once_with(
            f"/apps/{app_id}/services?per_page=5000&no_embed=true"
        )

    @pytest.mark.asyncio
    async def test_get_by_handle_and_app_found(
        self, service_manager, mock_api_client, sample_services_data
    ):
        """
        Test get_by_handle_and_app successfully retrieves a service.
        """
        app_id = 456

        # Setup mocks
        service_manager.list_by_app = AsyncMock(
            return_value=[
                Service.model_validate(sample_services_data[0]),
                Service.model_validate(sample_services_data[1]),
            ]
        )

        # Call the method being tested
        result = await service_manager.get_by_handle_and_app("worker", app_id)

        # Verify results
        assert result is not None
        assert isinstance(result, Service)
        assert result.id == 789
        assert result.handle == "worker"
        assert result.process_type == "worker"

        # Verify API call was made correctly
        service_manager.list_by_app.assert_called_once_with(app_id)

    @pytest.mark.asyncio
    async def test_get_by_handle_and_app_not_found(
        self, service_manager, mock_api_client, sample_services_data
    ):
        """
        Test get_by_handle_and_app returns None when service is not found.
        """
        app_id = 456

        # Setup mocks
        service_manager.list_by_app = AsyncMock(
            return_value=[
                Service.model_validate(sample_services_data[0]),
                Service.model_validate(sample_services_data[1]),
            ]
        )

        # Call the method being tested
        result = await service_manager.get_by_handle_and_app(
            "nonexistent-service", app_id
        )

        # Verify results
        assert result is None

        # Verify API call was made correctly
        service_manager.list_by_app.assert_called_once_with(app_id)

    @pytest.mark.asyncio
    async def test_scale_with_both_params(
        self,
        service_manager,
        mock_api_client,
        sample_service_data,
        sample_operation_response,
    ):
        """
        Test scale successfully updates both container count and memory.
        """
        service_id = 123
        container_count = 4
        container_memory_limit_mb = 2048

        # Setup mocks
        mock_api_client.post.return_value = sample_operation_response
        mock_api_client.wait_for_operation = AsyncMock()

        # Set up the updated service to return
        updated_service_data = sample_service_data.copy()
        updated_service_data["container_count"] = container_count
        updated_service_data["container_memory_limit_mb"] = container_memory_limit_mb
        updated_service = Service.model_validate(updated_service_data)

        service_manager.get_by_id = AsyncMock(return_value=updated_service)

        # Call the method being tested
        result = await service_manager.scale(
            service_id, container_count, container_memory_limit_mb
        )

        # Verify results
        assert isinstance(result, Service)
        assert result.id == service_id
        assert result.container_count == container_count
        assert result.container_memory_limit_mb == container_memory_limit_mb

        # Verify API calls were made correctly
        mock_api_client.post.assert_called_once_with(
            f"/services/{service_id}/operations",
            {
                "type": "scale",
                "container_count": container_count,
                "container_size": container_memory_limit_mb,
            },
        )
        mock_api_client.wait_for_operation.assert_called_once_with(
            sample_operation_response["id"]
        )
        service_manager.get_by_id.assert_called_once_with(service_id)

    @pytest.mark.asyncio
    async def test_scale_with_container_count_only(
        self,
        service_manager,
        mock_api_client,
        sample_service_data,
        sample_operation_response,
    ):
        """
        Test scale successfully updates only container count.
        """
        service_id = 123
        container_count = 4

        # Setup mocks
        mock_api_client.post.return_value = sample_operation_response
        mock_api_client.wait_for_operation = AsyncMock()

        # Set up the updated service to return
        updated_service_data = sample_service_data.copy()
        updated_service_data["container_count"] = container_count
        updated_service = Service.model_validate(updated_service_data)

        service_manager.get_by_id = AsyncMock(return_value=updated_service)

        # Call the method being tested
        result = await service_manager.scale(service_id, container_count, None)

        # Verify results
        assert result.container_count == container_count
        assert result.container_memory_limit_mb == 1024  # Original value

        # Verify API call was made correctly
        mock_api_client.post.assert_called_once_with(
            f"/services/{service_id}/operations",
            {"type": "scale", "container_count": container_count},
        )

    @pytest.mark.asyncio
    async def test_scale_with_memory_only(
        self,
        service_manager,
        mock_api_client,
        sample_service_data,
        sample_operation_response,
    ):
        """
        Test scale successfully updates only memory.
        """
        service_id = 123
        container_memory_limit_mb = 2048

        # Setup mocks
        mock_api_client.post.return_value = sample_operation_response
        mock_api_client.wait_for_operation = AsyncMock()

        # Set up the updated service to return
        updated_service_data = sample_service_data.copy()
        updated_service_data["container_memory_limit_mb"] = container_memory_limit_mb
        updated_service = Service.model_validate(updated_service_data)

        service_manager.get_by_id = AsyncMock(return_value=updated_service)

        # Call the method being tested
        result = await service_manager.scale(
            service_id, None, container_memory_limit_mb
        )

        # Verify results
        assert result.container_count == 2  # Original value
        assert result.container_memory_limit_mb == container_memory_limit_mb

        # Verify API call was made correctly
        mock_api_client.post.assert_called_once_with(
            f"/services/{service_id}/operations",
            {"type": "scale", "container_size": container_memory_limit_mb},
        )

    @pytest.mark.asyncio
    async def test_scale_service_not_found(
        self, service_manager, mock_api_client, sample_operation_response
    ):
        """
        Test scale raises an exception when service is not found.
        """
        service_id = 999

        # Setup mocks
        mock_api_client.post.return_value = sample_operation_response
        mock_api_client.wait_for_operation = AsyncMock()
        service_manager.get_by_id = AsyncMock(return_value=None)

        # Call the method and verify it raises an exception
        with pytest.raises(Exception) as excinfo:
            await service_manager.scale(service_id, 2, 1024)

        assert f"Service {service_id} not found" in str(excinfo.value)
        service_manager.get_by_id.assert_called_once_with(service_id)

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        service_manager,
        mock_api_client,
        sample_service_data,
        sample_operation_response,
    ):
        """
        Test delete successfully deletes a service.
        """
        service_id = 123

        # Setup mocks
        service = Service.model_validate(sample_service_data)
        service_manager.get_by_id = AsyncMock(return_value=service)

        mock_api_client.post.return_value = sample_operation_response
        mock_api_client.wait_for_operation = AsyncMock()

        # Call the method being tested
        await service_manager.delete(service_id)

        # Verify API calls were made correctly
        service_manager.get_by_id.assert_called_once_with(service_id)
        mock_api_client.post.assert_called_once_with(
            f"/services/{service_id}/operations", {"type": "deprovision"}
        )
        mock_api_client.wait_for_operation.assert_called_once_with(
            sample_operation_response["id"]
        )

    @pytest.mark.asyncio
    async def test_get_settings_returns_present_fields(
        self, service_manager, sample_service_data
    ):
        """
        get_settings returns only the allow-listed fields actually present
        on the fetched Service resource.
        """
        service_data = {
            **sample_service_data,
            "force_zero_downtime": True,
            "stop_timeout": 30,
        }
        service_manager.get_by_id = AsyncMock(
            return_value=Service.model_validate(service_data)
        )

        settings = await service_manager.get_settings(123)

        assert settings == {"force_zero_downtime": True, "stop_timeout": 30}
        service_manager.get_by_id.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_get_settings_service_not_found(self, service_manager):
        service_manager.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(Exception) as excinfo:
            await service_manager.get_settings(999)

        assert "Service 999 not found" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_update_settings_success(
        self, service_manager, mock_api_client, sample_service_data
    ):
        updated_data = {**sample_service_data, "naive_health_check": True}
        mock_api_client.put.return_value = updated_data

        result = await service_manager.update_settings(123, naive_health_check=True)

        mock_api_client.put.assert_called_once_with(
            "/services/123", {"naive_health_check": True}
        )
        assert isinstance(result, Service)

    @pytest.mark.asyncio
    async def test_update_settings_rejects_unsupported_key(
        self, service_manager, mock_api_client
    ):
        with pytest.raises(ValueError) as excinfo:
            await service_manager.update_settings(123, bogus_setting=True)

        assert "bogus_setting" in str(excinfo.value)
        mock_api_client.put.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_service_not_found(self, service_manager):
        """
        Test delete raises an exception when service is not found.
        """
        service_id = 999

        # Setup mocks
        service_manager.get_by_id = AsyncMock(return_value=None)

        # Call the method and verify it raises an exception
        with pytest.raises(Exception) as excinfo:
            await service_manager.delete(service_id)

        assert f"No service found with id {service_id}" in str(excinfo.value)
        service_manager.get_by_id.assert_called_once_with(service_id)
