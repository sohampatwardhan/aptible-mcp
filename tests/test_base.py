import pytest
from unittest.mock import MagicMock

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
