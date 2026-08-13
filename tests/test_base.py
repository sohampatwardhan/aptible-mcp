import pytest
from unittest.mock import AsyncMock, MagicMock

from models.base import ResourceBase, ResourceManager
from api_client import AptibleApiClient


class DummyResource(ResourceBase):
    handle: str


class DummyManager(ResourceManager[DummyResource, str]):
    resource_name = "dummies"
    resource_model = DummyResource
    resource_url = "/dummies"


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
