import pytest
from unittest.mock import AsyncMock, MagicMock

from models.base import ResourceBase, ResourceManager
from api_client import AptibleApiClient


class DummyResource(ResourceBase):
    handle: str
    drain_configuration: object | None = None
    metadata: object | None = None


class DummyManager(ResourceManager[DummyResource, str]):
    resource_name = "dummies"
    resource_model = DummyResource
    resource_url = "/dummies"


def test_resource_serialization_redacts_secrets_and_omits_embedded_resources():
    resource = DummyResource.model_validate(
        {
            "id": 1,
            "handle": "example",
            "password": "top-level-password",
            "drain_configuration": {
                "api_key": "nested-api-key",
                "host": "logs.example.com",
            },
            "metadata": [
                {
                    "access-token": "nested-access-token",
                    "authToken": "camel-case-token",
                    "certificate_fingerprint": "AA:BB:CC",
                    "callback_url": (
                        "https://alice:url-password@logs.example.com:8443/callback"
                        "?accessKey=query-secret&region=us-east-1#fragment"
                    ),
                    "malformed_port_url": (
                        "https://alice:malformed-secret@logs.example.com:bad/path"
                    ),
                    "malformed_ipv6_url": "https://alice:ipv6-secret@[::1/path",
                    "ipv6_url": "https://alice:ipv6-password@[::1]:8443/path",
                    "nested": {
                        "safe": "kept",
                        "_embedded": {"log_drains": [{"password": "hidden"}]},
                        7: "non-string-key",
                    },
                    "tuple_values": ({"privateKey": "tuple-secret"}, "safe"),
                }
            ],
            "_embedded": {
                "log_drains": [{"password": "embedded-password"}],
                "certificates": [
                    {
                        "certificate_body": "certificate-material",
                        "private_key": "private-key-material",
                    }
                ],
            },
        }
    )

    result = resource.model_dump()

    assert "password" not in result
    assert result["drain_configuration"] == "[REDACTED]"
    metadata = result["metadata"][0]
    assert metadata["access-token"] == "[REDACTED]"
    assert metadata["authToken"] == "[REDACTED]"
    assert metadata["certificate_fingerprint"] == "AA:BB:CC"
    assert metadata["callback_url"] == (
        "https://logs.example.com:8443/callback"
        "?accessKey=%5BREDACTED%5D&region=us-east-1"
    )
    assert metadata["malformed_port_url"] == "[REDACTED]"
    assert metadata["malformed_ipv6_url"] == "[REDACTED]"
    assert metadata["ipv6_url"] == "https://[::1]:8443/path"
    assert metadata["nested"] == {"safe": "kept", 7: "non-string-key"}
    assert metadata["tuple_values"] == ({"privateKey": "[REDACTED]"}, "safe")
    assert "_embedded" not in result
    serialized = str(result)
    assert "top-level-password" not in serialized
    assert "nested-api-key" not in serialized
    assert "nested-access-token" not in serialized
    assert "camel-case-token" not in serialized
    assert "url-password" not in serialized
    assert "query-secret" not in serialized
    assert "malformed-secret" not in serialized
    assert "ipv6-secret" not in serialized
    assert "ipv6-password" not in serialized
    assert "embedded-password" not in serialized
    assert "certificate-material" not in serialized
    assert "private-key-material" not in serialized

    json_result = resource.model_dump_json()
    assert "top-level-password" not in json_result
    assert "url-password" not in json_result
    assert "tuple-secret" not in json_result


@pytest.fixture
def mock_api_client():
    return MagicMock(spec=AptibleApiClient)


@pytest.fixture
def manager(mock_api_client):
    return DummyManager(mock_api_client)


@pytest.mark.asyncio
async def test_list_follows_hal_next_links(manager, mock_api_client):
    mock_api_client.get.side_effect = [
        {
            "_embedded": {"dummies": [{"id": 1, "handle": "first"}]},
            "_links": {"next": {"href": "/dummies?page=2"}},
        },
        {
            "_embedded": {"dummies": [{"id": 2, "handle": "second"}]},
            "_links": {},
        },
    ]

    resources = await manager.list()

    assert [resource.id for resource in resources] == [1, 2]
    assert [call.args[0] for call in mock_api_client.get.call_args_list] == [
        "/dummies?per_page=5000&no_embed=true",
        "/dummies?page=2",
    ]


@pytest.mark.asyncio
async def test_list_rejects_pagination_cycles(manager, mock_api_client):
    mock_api_client.get.return_value = {
        "_embedded": {"dummies": []},
        "_links": {"next": {"href": "/dummies?per_page=5000&no_embed=true"}},
    }

    with pytest.raises(RuntimeError, match="Pagination cycle"):
        await manager.list()


@pytest.mark.asyncio
async def test_list_does_not_follow_cross_origin_hal_links():
    client = AptibleApiClient(api_url="https://api.aptible.com")
    client._token = "test-token"
    client._http.get = AsyncMock()
    response = MagicMock()
    response.json.return_value = {
        "_embedded": {"dummies": []},
        "_links": {"next": {"href": "https://attacker.example/dummies?page=2"}},
    }
    manager = DummyManager(client)

    client._http.get.return_value = response
    with pytest.raises(ValueError, match="different origin"):
        await manager.list()

    client._http.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_operation_refetches_by_default(manager, mock_api_client):
    mock_api_client.post.return_value = {"id": 42}
    mock_api_client.get.return_value = {"id": 7, "handle": "refetched"}

    result = await manager._run_operation(7, "/dummies/7/operations", "restart")

    mock_api_client.post.assert_called_once_with(
        "/dummies/7/operations", {"type": "restart"}
    )
    mock_api_client.wait_for_operation.assert_called_once_with(42)
    assert result is not None
    assert result.handle == "refetched"


@pytest.mark.asyncio
async def test_run_operation_with_extra_fields(manager, mock_api_client):
    mock_api_client.post.return_value = {"id": 43}
    mock_api_client.get.return_value = {"id": 7, "handle": "resized"}

    await manager._run_operation(
        7, "/dummies/7/operations", "restart", extra={"container_size": 2048}
    )

    mock_api_client.post.assert_called_once_with(
        "/dummies/7/operations", {"type": "restart", "container_size": 2048}
    )


@pytest.mark.asyncio
async def test_run_operation_no_refetch_returns_none(manager, mock_api_client):
    mock_api_client.post.return_value = {"id": 44}

    result = await manager._run_operation(
        7, "/dummies/7/operations", "deprovision", refetch=False
    )

    mock_api_client.wait_for_operation.assert_called_once_with(44)
    mock_api_client.get.assert_not_called()
    assert result is None


@pytest.mark.asyncio
async def test_run_operation_propagates_failure(manager, mock_api_client):
    mock_api_client.post.return_value = {"id": 45}
    mock_api_client.wait_for_operation.side_effect = Exception(
        "Operation 45 failed: boom"
    )

    with pytest.raises(Exception, match="Operation 45 failed: boom"):
        await manager._run_operation(7, "/dummies/7/operations", "restart")


@pytest.mark.asyncio
async def test_run_operation_awaits_non_blocking_polling(manager, mock_api_client):
    mock_api_client.post.return_value = {"id": 46}
    mock_api_client.get.return_value = {"id": 7, "handle": "refetched"}

    await manager._run_operation(7, "/dummies/7/operations", "restart")

    mock_api_client.wait_for_operation.assert_awaited_once_with(46)
