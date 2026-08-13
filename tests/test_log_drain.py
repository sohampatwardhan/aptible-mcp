import pytest
from unittest.mock import MagicMock
from requests.exceptions import HTTPError

from models.log_drain import LogDrain, LogDrainManager
from api_client import AptibleApiClient


@pytest.fixture
def mock_api_client():
    return MagicMock(spec=AptibleApiClient)


@pytest.fixture
def log_drain_manager(mock_api_client):
    return LogDrainManager(mock_api_client)


@pytest.fixture
def sample_log_drain_data():
    return {
        "id": 10,
        "handle": "prod-syslog",
        "drain_type": "syslog_tls_tcp",
        "status": "provisioned",
        "_links": {"account": {"href": "https://api.aptible.com/accounts/101"}},
    }


class TestLogDrainModel:
    def test_log_drain_init(self, sample_log_drain_data):
        drain = LogDrain.model_validate(sample_log_drain_data)
        assert drain.id == 10
        assert drain.handle == "prod-syslog"
        assert drain.drain_type == "syslog_tls_tcp"
        assert drain.status == "provisioned"

    def test_account_id_computed_field(self, sample_log_drain_data):
        drain = LogDrain.model_validate(sample_log_drain_data)
        assert drain.account_id == 101

    def test_account_id_missing(self):
        drain = LogDrain.model_validate(
            {
                "id": 10,
                "handle": "d1",
                "drain_type": "https_post",
                "status": "provisioned",
            }
        )
        assert drain.account_id is None


class TestLogDrainManager:
    @pytest.mark.asyncio
    async def test_create_valid(
        self, log_drain_manager, mock_api_client, sample_log_drain_data
    ):
        mock_api_client.post.side_effect = [
            sample_log_drain_data,  # POST /accounts/101/log_drains
            {"id": 500},  # POST /log_drains/10/operations
        ]
        mock_api_client.get.return_value = (
            sample_log_drain_data  # refetch in _run_operation
        )

        drain = await log_drain_manager.create(
            101, "prod-syslog", "syslog_tls_tcp", url="syslog://example.com:514"
        )

        mock_api_client.post.assert_any_call(
            "/accounts/101/log_drains",
            {
                "handle": "prod-syslog",
                "drain_type": "syslog_tls_tcp",
                "url": "syslog://example.com:514",
            },
        )
        mock_api_client.post.assert_any_call(
            "/log_drains/10/operations",
            {"type": "provision"},
        )
        mock_api_client.wait_for_operation.assert_called_once_with(500)
        assert drain.id == 10
        assert drain.handle == "prod-syslog"

    @pytest.mark.asyncio
    async def test_create_unsupported_type(self, log_drain_manager, mock_api_client):
        with pytest.raises(ValueError, match="Unsupported log drain type"):
            await log_drain_manager.create(101, "bad-drain", "invalid_type")

        mock_api_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_for_account_nested_success(
        self, log_drain_manager, mock_api_client, sample_log_drain_data
    ):
        mock_api_client.get.return_value = {
            "_embedded": {"log_drains": [sample_log_drain_data]}
        }

        drains = await log_drain_manager.list_for_account(101)

        mock_api_client.get.assert_called_once_with(
            "/accounts/101/log_drains?per_page=5000&no_embed=true"
        )
        assert len(drains) == 1
        assert drains[0].id == 10
        assert drains[0].account_id == 101

    @pytest.mark.asyncio
    async def test_list_for_account_fallback_404(
        self, log_drain_manager, mock_api_client, sample_log_drain_data
    ):
        mock_404_resp = MagicMock()
        mock_404_resp.status_code = 404

        other_drain_data = {
            "id": 11,
            "handle": "other-syslog",
            "drain_type": "syslog_tls_tcp",
            "status": "provisioned",
            "_links": {"account": {"href": "https://api.aptible.com/accounts/202"}},
        }

        # First call to /accounts/101/log_drains raises 404, second call to /log_drains returns all drains
        mock_api_client.get.side_effect = [
            HTTPError(response=mock_404_resp),
            {"_embedded": {"log_drains": [sample_log_drain_data, other_drain_data]}},
        ]

        drains = await log_drain_manager.list_for_account(101)

        assert len(drains) == 1
        assert drains[0].id == 10
        assert drains[0].account_id == 101

    @pytest.mark.asyncio
    async def test_list_for_account_other_http_error(
        self, log_drain_manager, mock_api_client
    ):
        mock_500_resp = MagicMock()
        mock_500_resp.status_code = 500
        mock_api_client.get.side_effect = HTTPError(response=mock_500_resp)

        with pytest.raises(HTTPError):
            await log_drain_manager.list_for_account(101)

    @pytest.mark.asyncio
    async def test_deprovision_success(self, log_drain_manager, mock_api_client):
        mock_api_client.post.return_value = {"id": 501}

        await log_drain_manager.deprovision(10)

        mock_api_client.post.assert_called_once_with(
            "/log_drains/10/operations", {"type": "deprovision"}
        )
        mock_api_client.wait_for_operation.assert_called_once_with(501)

    @pytest.mark.asyncio
    async def test_deprovision_unknown_id(self, log_drain_manager, mock_api_client):
        mock_404_resp = MagicMock()
        mock_404_resp.status_code = 404
        mock_api_client.post.side_effect = HTTPError(response=mock_404_resp)

        with pytest.raises(Exception, match="999"):
            await log_drain_manager.deprovision(999)
