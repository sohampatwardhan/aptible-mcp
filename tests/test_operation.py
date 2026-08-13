import pytest
from unittest.mock import MagicMock, AsyncMock, call

from models.operation import Operation, OperationManager
from api_client import AptibleApiClient


@pytest.fixture
def mock_api_client():
    return MagicMock(spec=AptibleApiClient)


@pytest.fixture
def operation_manager(mock_api_client):
    return OperationManager(mock_api_client)


def _operation_data(status, operation_id=1):
    return {
        "id": operation_id,
        "resource_id": 99,
        "resource_type": "app",
        "type": "deploy",
        "status": status,
    }


class TestOperationManager:
    @pytest.mark.asyncio
    async def test_logs_apply_timeouts_to_api_and_signed_url_requests(
        self, operation_manager, mock_api_client
    ):
        mock_api_client.get_text.side_effect = [
            "https://logs.example/signed",
            "operation output",
        ]

        result = await operation_manager.logs(123)

        assert result == "operation output"
        assert mock_api_client.get_text.call_args_list == [
            call("/operations/123/logs"),
            call("https://logs.example/signed", authenticated=False),
        ]

    def test_operation_defaults_missing_status_to_unknown(self):
        data = _operation_data("queued")
        del data["status"]

        operation = Operation.model_validate(data)

        assert operation.status == "unknown"

    @pytest.mark.asyncio
    async def test_cancel_running_operation(self, operation_manager, mock_api_client):
        running = Operation.model_validate(_operation_data("running"))
        operation_manager.get_by_id = AsyncMock(return_value=running)
        mock_api_client.put.return_value = _operation_data("running", 1) | {
            "cancelled": True
        }

        result = await operation_manager.cancel(1)

        mock_api_client.put.assert_called_once_with(
            "/operations/1", {"cancelled": True}
        )
        assert isinstance(result, Operation)
        assert result.cancelled is True

    @pytest.mark.asyncio
    async def test_cancel_rejects_succeeded_operation(
        self, operation_manager, mock_api_client
    ):
        succeeded = Operation.model_validate(_operation_data("succeeded"))
        operation_manager.get_by_id = AsyncMock(return_value=succeeded)

        with pytest.raises(Exception) as excinfo:
            await operation_manager.cancel(1)

        assert "already succeeded" in str(excinfo.value)
        mock_api_client.put.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_unknown_operation(self, operation_manager):
        operation_manager.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(Exception) as excinfo:
            await operation_manager.cancel(999)

        assert "Operation 999 not found" in str(excinfo.value)
