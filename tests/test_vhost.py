import pytest
from unittest.mock import MagicMock, AsyncMock

from models.vhost import Vhost, VhostManager
from api_client import AptibleApiClient


@pytest.fixture
def mock_api_client():
    """
    Fixture providing a mock AptibleApiClient.
    """
    mock_client = MagicMock(spec=AptibleApiClient)
    return mock_client


@pytest.fixture
def vhost_manager(mock_api_client):
    """
    Fixture providing a VhostManager with a mock API client.
    """
    return VhostManager(mock_api_client)


@pytest.fixture
def sample_vhost_data():
    """
    Fixture providing sample vhost data for testing.
    """
    return {
        "id": 1,
        "virtual_domain": None,
        "external_host": "app-12345.aptible.com",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "status": "provisioned",
        "_links": {"service": {"href": "https://api.aptible.com/services/42"}},
    }


@pytest.fixture
def sample_operation_response():
    """
    Fixture providing a sample operation response.
    """
    return {"id": "operation-123"}


class TestVhostModel:
    """
    Tests for the Vhost model.
    """

    def test_vhost_init(self, sample_vhost_data):
        """
        Test that Vhost can be initialized from valid data.
        """
        vhost = Vhost.model_validate(sample_vhost_data)

        assert vhost.id == 1
        assert vhost.virtual_domain is None
        assert vhost.external_host == "app-12345.aptible.com"
        assert vhost.created_at == "2023-01-01T12:00:00Z"
        assert vhost.updated_at == "2023-01-01T12:00:00Z"
        assert vhost.status == "provisioned"
        assert vhost.links == {
            "service": {"href": "https://api.aptible.com/services/42"}
        }

    def test_transform_links(self, sample_vhost_data):
        """
        Test that _links is transformed to links during initialization.
        """
        # Data already has _links which should be transformed
        vhost = Vhost.model_validate(sample_vhost_data)

        assert "_links" not in sample_vhost_data
        assert "links" in sample_vhost_data
        assert vhost.links == {
            "service": {"href": "https://api.aptible.com/services/42"}
        }

    def test_service_id_computed_field(self, sample_vhost_data):
        """
        Test that the service_id computed field works correctly.
        """
        vhost = Vhost.model_validate(sample_vhost_data)

        assert vhost.service_id == 42

    def test_service_id_missing_service(self):
        """
        Test that service_id raises an exception when service is missing from links.
        """
        vhost_data = {
            "id": 1,
            "external_host": "app-12345.aptible.com",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "status": "provisioned",
            "links": {},
        }

        vhost = Vhost.model_validate(vhost_data)

        with pytest.raises(Exception) as excinfo:
            _ = vhost.service_id

        assert "Service is missing from links" in str(excinfo.value)

    def test_service_id_missing_href(self):
        """
        Test that service_id raises an exception when service href is missing.
        """
        vhost_data = {
            "id": 1,
            "external_host": "app-12345.aptible.com",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "status": "provisioned",
            "links": {"service": {}},
        }

        vhost = Vhost.model_validate(vhost_data)

        with pytest.raises(Exception) as excinfo:
            _ = vhost.service_id

        assert "Service link is missing href" in str(excinfo.value)

    def test_vhost_extended_fields(self, sample_vhost_data):
        """
        Test that Vhost extended fields (type, user_domain, container_ports) parse properly.
        """
        data = {
            **sample_vhost_data,
            "type": "http",
            "user_domain": "app.example.com",
            "container_ports": [80, 443],
        }
        vhost = Vhost.model_validate(data)
        assert vhost.type == "http"
        assert vhost.user_domain == "app.example.com"
        assert vhost.container_ports == [80, 443]


class TestVhostManager:
    """
    Tests for the VhostManager class.
    """

    @pytest.mark.asyncio
    async def test_list_by_service(
        self, vhost_manager, mock_api_client, sample_vhost_data
    ):
        """
        Test list_by_service correctly returns vhosts for a service.
        """
        # Setup mock response from API client
        service_id = 42
        mock_api_client.get.return_value = {
            "_embedded": {"vhosts": [sample_vhost_data]}
        }

        # Call the method being tested
        result = await vhost_manager.list_by_service(service_id)

        # Verify results
        assert len(result) == 1
        assert isinstance(result[0], Vhost)
        assert result[0].id == 1
        assert result[0].service_id == 42

        # Verify API call was made correctly
        mock_api_client.get.assert_called_once_with(
            f"/services/{service_id}/vhosts?per_page=5000&no_embed=true"
        )

    @pytest.mark.asyncio
    async def test_delete_vhost_success(
        self,
        vhost_manager,
        mock_api_client,
        sample_vhost_data,
        sample_operation_response,
    ):
        """
        Test delete_vhost successfully deletes a vhost.
        """
        # Setup mocks
        vhost_id = 42
        mock_api_client.post.return_value = sample_operation_response

        # Mock get_by_id method
        vhost = Vhost.model_validate(sample_vhost_data)
        vhost_manager.get_by_id = AsyncMock(return_value=vhost)

        # Mock wait_for_operation method
        mock_api_client.wait_for_operation = MagicMock()

        # Call the method being tested
        await vhost_manager.delete_vhost(vhost_id)

        # Verify API calls were made correctly
        vhost_manager.get_by_id.assert_called_once_with(vhost_id)
        mock_api_client.post.assert_called_once_with(
            f"/vhosts/{vhost_id}/operations", {"type": "deprovision"}
        )
        mock_api_client.wait_for_operation.assert_called_once_with(
            sample_operation_response["id"]
        )

    @pytest.mark.asyncio
    async def test_delete_vhost_not_found(self, vhost_manager):
        """
        Test delete_vhost raises an exception when vhost is not found.
        """
        # Mock get_by_id method to return None
        vhost_manager.get_by_id = AsyncMock(return_value=None)

        # Call the method and verify it raises an exception
        with pytest.raises(Exception) as excinfo:
            await vhost_manager.delete_vhost(999)

        assert "No vhost found with id 999" in str(excinfo.value)
        vhost_manager.get_by_id.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        vhost_manager,
        mock_api_client,
        sample_vhost_data,
        sample_operation_response,
    ):
        """
        Test that the create method successfully creates a vhost and provisions it.
        """
        # Set up mocks
        service_id = 42
        mock_api_client.post.side_effect = [
            sample_vhost_data,  # Response for creating the vhost
            sample_operation_response,  # Response for provisioning operation
        ]

        # Mock the wait_for_operation method
        mock_api_client.wait_for_operation = MagicMock()

        # Call the method being tested
        result = await vhost_manager.create({"service_id": service_id})

        # Check the result is as expected
        assert isinstance(result, Vhost)
        assert result.id == 1
        assert result.external_host == "app-12345.aptible.com"
        assert result.service_id == 42

        # Verify API calls were made correctly
        mock_api_client.post.assert_any_call(
            f"/services/{service_id}/vhosts",
            {
                "service_id": service_id,
                "type": "http",
                "platform": "alb",
                "load_balancing_algorithm_type": "round_robin",
                "default": True,
                "acme": False,
                "internal": False,
            },
        )
        mock_api_client.post.assert_any_call(
            f"/vhosts/{result.id}/operations", {"type": "provision"}
        )
        mock_api_client.wait_for_operation.assert_called_once_with(
            sample_operation_response["id"]
        )

    @pytest.mark.asyncio
    async def test_create_missing_service_id(self, vhost_manager):
        """
        Test that create raises an exception when service_id is missing.
        """
        with pytest.raises(Exception) as excinfo:
            await vhost_manager.create({"service_id": None})

        assert "A service_id is required." in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_create_custom_domain_managed_tls_success(
        self,
        vhost_manager,
        mock_api_client,
        sample_vhost_data,
        sample_operation_response,
    ):
        """
        Test create_custom_domain with managed TLS.
        """
        service_id = 42
        mock_api_client.post.side_effect = [
            {**sample_vhost_data, "user_domain": "sub.example.com"},
            sample_operation_response,
        ]
        mock_api_client.get.return_value = {
            **sample_vhost_data,
            "user_domain": "sub.example.com",
        }
        mock_api_client.wait_for_operation = MagicMock()

        result = await vhost_manager.create_custom_domain(
            service_id=service_id,
            domain="sub.example.com",
            managed_tls=True,
        )

        assert isinstance(result, Vhost)
        assert result.id == 1
        mock_api_client.post.assert_any_call(
            f"/services/{service_id}/vhosts",
            {
                "service_id": service_id,
                "type": "http",
                "platform": "alb",
                "user_domain": "sub.example.com",
                "acme": True,
            },
        )
        mock_api_client.post.assert_any_call(
            "/vhosts/1/operations", {"type": "provision"}
        )

    @pytest.mark.asyncio
    async def test_create_custom_domain_apex_domain_rejection(self, vhost_manager):
        """
        Test create_custom_domain rejects apex domain when managed_tls is True.
        """
        with pytest.raises(ValueError) as excinfo:
            await vhost_manager.create_custom_domain(
                service_id=42, domain="example.com", managed_tls=True
            )
        assert "Managed TLS is not supported for apex" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_create_custom_domain_wildcard_domain_rejection(self, vhost_manager):
        """
        Test create_custom_domain rejects wildcard domain when managed_tls is True.
        """
        with pytest.raises(ValueError) as excinfo:
            await vhost_manager.create_custom_domain(
                service_id=42, domain="*.example.com", managed_tls=True
            )
        assert "Managed TLS is not supported for apex or wildcard" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_create_custom_domain_custom_cert_success(
        self,
        vhost_manager,
        mock_api_client,
        sample_vhost_data,
        sample_operation_response,
    ):
        """
        Test create_custom_domain with custom certificate fingerprint.
        """
        service_id = 42
        mock_api_client.post.side_effect = [
            {**sample_vhost_data, "user_domain": "example.com"},
            sample_operation_response,
        ]
        mock_api_client.get.return_value = {
            **sample_vhost_data,
            "user_domain": "example.com",
        }
        mock_api_client.wait_for_operation = MagicMock()

        result = await vhost_manager.create_custom_domain(
            service_id=service_id,
            domain="example.com",
            managed_tls=False,
            certificate_fingerprint="fp12345",
        )

        assert isinstance(result, Vhost)
        mock_api_client.post.assert_any_call(
            f"/services/{service_id}/vhosts",
            {
                "service_id": service_id,
                "type": "http",
                "platform": "alb",
                "user_domain": "example.com",
                "acme": False,
                "certificate_fingerprint": "fp12345",
            },
        )

    @pytest.mark.asyncio
    async def test_create_custom_domain_tls_missing_cert_rejection(self, vhost_manager):
        """
        Test create_custom_domain raises error if endpoint_type is tls and cert fingerprint is missing.
        """
        with pytest.raises(ValueError) as excinfo:
            await vhost_manager.create_custom_domain(
                service_id=42,
                domain="sub.example.com",
                managed_tls=False,
                endpoint_type="tls",
                certificate_fingerprint=None,
            )
        assert "certificate reference" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_create_database_endpoint_success(
        self,
        vhost_manager,
        mock_api_client,
        sample_vhost_data,
        sample_operation_response,
    ):
        """
        Test create_database_endpoint resolves database HAL relation and provisions.
        """
        database_id = 10
        mock_api_client.get.side_effect = [
            {
                "id": database_id,
                "_links": {
                    "vhosts": {
                        "href": f"https://api.aptible.com/databases/{database_id}/vhosts"
                    }
                },
            },
            sample_vhost_data,
        ]
        mock_api_client.post.side_effect = [
            sample_vhost_data,
            sample_operation_response,
        ]
        mock_api_client.wait_for_operation = MagicMock()

        result = await vhost_manager.create_database_endpoint(
            database_id=database_id,
            internal=True,
            ip_whitelist=["10.0.0.0/8"],
        )

        assert isinstance(result, Vhost)
        mock_api_client.post.assert_any_call(
            f"https://api.aptible.com/databases/{database_id}/vhosts",
            {
                "type": "tcp",
                "platform": "elb",
                "internal": True,
                "ip_whitelist": ["10.0.0.0/8"],
            },
        )

    @pytest.mark.asyncio
    async def test_create_database_endpoint_requires_hal_relation(
        self,
        vhost_manager,
        mock_api_client,
    ):
        """Reject database resources that do not advertise endpoint creation."""
        mock_api_client.get.return_value = {"id": 10, "_links": {}}

        with pytest.raises(ValueError, match="required vhosts relation"):
            await vhost_manager.create_database_endpoint(database_id=10)

        mock_api_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_modify_vhost_success(
        self, vhost_manager, mock_api_client, sample_vhost_data
    ):
        """
        Test modify method sends PUT request to vhost endpoint.
        """
        vhost_id = 1
        updated_data = {**sample_vhost_data, "container_ports": [8080]}
        mock_api_client.put.return_value = updated_data

        result = await vhost_manager.modify(vhost_id, container_ports=[8080])

        assert isinstance(result, Vhost)
        assert result.container_ports == [8080]
        mock_api_client.put.assert_called_once_with(
            f"/vhosts/{vhost_id}", {"container_ports": [8080]}
        )

    @pytest.mark.asyncio
    async def test_renew_vhost_success(
        self,
        vhost_manager,
        mock_api_client,
        sample_vhost_data,
        sample_operation_response,
    ):
        """
        Test renew method triggers renew operation and refetches vhost.
        """
        vhost_id = 1
        mock_api_client.post.return_value = sample_operation_response
        mock_api_client.get.return_value = sample_vhost_data
        mock_api_client.wait_for_operation = MagicMock()

        result = await vhost_manager.renew(vhost_id)

        assert isinstance(result, Vhost)
        mock_api_client.post.assert_called_once_with(
            f"/vhosts/{vhost_id}/operations", {"type": "renew"}
        )
        mock_api_client.wait_for_operation.assert_called_once_with(
            sample_operation_response["id"]
        )
