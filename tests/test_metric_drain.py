import pytest
from unittest.mock import MagicMock
from requests.exceptions import HTTPError

from models.metric_drain import MetricDrain, MetricDrainManager
from api_client import AptibleApiClient


@pytest.fixture
def mock_api_client():
    client = MagicMock(spec=AptibleApiClient)
    return client


@pytest.fixture
def metric_drain_manager(mock_api_client):
    return MetricDrainManager(mock_api_client)


@pytest.fixture
def sample_metric_drain_data():
    return {
        "id": 1,
        "handle": "test-metric-drain",
        "drain_type": "datadog",
        "status": "provisioned",
        "drain_configuration": {"api_key": "1234567890"},
        "_links": {"account": {"href": "https://api.aptible.com/accounts/10"}},
    }


class TestMetricDrainModel:
    def test_metric_drain_init(self, sample_metric_drain_data):
        drain = MetricDrain.model_validate(sample_metric_drain_data)
        assert drain.id == 1
        assert drain.handle == "test-metric-drain"
        assert drain.drain_type == "datadog"
        assert drain.status == "provisioned"
        assert drain.drain_configuration == {"api_key": "1234567890"}

    def test_account_id_computed_field(self, sample_metric_drain_data):
        drain = MetricDrain.model_validate(sample_metric_drain_data)
        assert drain.account_id == 10

    def test_account_id_missing_links(self):
        drain = MetricDrain.model_validate(
            {
                "id": 1,
                "handle": "drain-1",
                "drain_type": "datadog",
                "status": "provisioned",
            }
        )
        assert drain.account_id is None

    def test_account_id_missing_href(self):
        drain = MetricDrain.model_validate(
            {
                "id": 1,
                "handle": "drain-1",
                "drain_type": "datadog",
                "status": "provisioned",
                "_links": {"account": {}},
            }
        )
        assert drain.account_id is None


class TestMetricDrainManager:
    @pytest.mark.asyncio
    async def test_create_success(
        self, metric_drain_manager, mock_api_client, sample_metric_drain_data
    ):
        mock_api_client.post.side_effect = [
            sample_metric_drain_data,  # Create POST response
            {"id": 100, "status": "queued"},  # Operation POST response
        ]
        mock_api_client.get.return_value = sample_metric_drain_data  # Refetch response

        drain = await metric_drain_manager.create(
            account_id=10,
            handle="test-metric-drain",
            drain_type="datadog",
            drain_configuration={"api_key": "1234567890"},
        )

        assert mock_api_client.post.call_count == 2
        mock_api_client.post.assert_any_call(
            "/accounts/10/metric_drains",
            {
                "handle": "test-metric-drain",
                "drain_type": "datadog",
                "drain_configuration": {"api_key": "1234567890"},
            },
        )
        mock_api_client.post.assert_any_call(
            "/metric_drains/1/operations",
            {"type": "provision"},
        )
        mock_api_client.wait_for_operation.assert_called_once_with(100)
        assert drain.handle == "test-metric-drain"
        assert drain.drain_type == "datadog"

    @pytest.mark.asyncio
    async def test_create_with_type_fields(
        self, metric_drain_manager, mock_api_client, sample_metric_drain_data
    ):
        mock_api_client.post.side_effect = [
            sample_metric_drain_data,
            {"id": 101, "status": "queued"},
        ]
        mock_api_client.get.return_value = sample_metric_drain_data

        await metric_drain_manager.create(
            account_id=10,
            handle="test-metric-drain",
            drain_type="influxdb",
            host="influx.example.com",
            port=8086,
        )

        mock_api_client.post.assert_any_call(
            "/accounts/10/metric_drains",
            {
                "handle": "test-metric-drain",
                "drain_type": "influxdb",
                "drain_configuration": {
                    "host": "influx.example.com",
                    "port": 8086,
                },
            },
        )

    @pytest.mark.asyncio
    async def test_create_unsupported_type(self, metric_drain_manager, mock_api_client):
        with pytest.raises(ValueError) as exc_info:
            await metric_drain_manager.create(
                account_id=10,
                handle="invalid-drain",
                drain_type="unsupported_type",
            )

        assert "unsupported_type" in str(exc_info.value)
        mock_api_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_for_account_nested_success(
        self, metric_drain_manager, mock_api_client, sample_metric_drain_data
    ):
        mock_api_client.get.return_value = {
            "_embedded": {"metric_drains": [sample_metric_drain_data]}
        }

        drains = await metric_drain_manager.list_for_account(10)

        mock_api_client.get.assert_called_once_with(
            "/accounts/10/metric_drains?per_page=5000&no_embed=true"
        )
        assert len(drains) == 1
        assert drains[0].handle == "test-metric-drain"
        assert drains[0].account_id == 10

    @pytest.mark.asyncio
    async def test_list_for_account_fallback_on_404(
        self, metric_drain_manager, mock_api_client, sample_metric_drain_data
    ):
        # Nested endpoint returns 404
        mock_404 = MagicMock()
        mock_404.status_code = 404
        http_error = HTTPError(response=mock_404)

        other_drain_data = {
            "id": 2,
            "handle": "other-account-drain",
            "drain_type": "datadog",
            "status": "provisioned",
            "_links": {"account": {"href": "https://api.aptible.com/accounts/99"}},
        }

        def get_side_effect(url):
            if "/accounts/10/metric_drains" in url:
                raise http_error
            elif url == "/metric_drains?per_page=5000&no_embed=true":
                return {
                    "_embedded": {
                        "metric_drains": [sample_metric_drain_data, other_drain_data]
                    }
                }
            raise ValueError(f"Unexpected GET URL: {url}")

        mock_api_client.get.side_effect = get_side_effect

        drains = await metric_drain_manager.list_for_account(10)

        assert len(drains) == 1
        assert drains[0].id == 1
        assert drains[0].account_id == 10

    @pytest.mark.asyncio
    async def test_list_for_account_empty(self, metric_drain_manager, mock_api_client):
        mock_api_client.get.return_value = {}

        drains = await metric_drain_manager.list_for_account(10)

        assert drains == []

    @pytest.mark.asyncio
    async def test_deprovision_success(self, metric_drain_manager, mock_api_client):
        mock_api_client.post.return_value = {"id": 200, "status": "queued"}

        await metric_drain_manager.deprovision(1)

        mock_api_client.post.assert_called_once_with(
            "/metric_drains/1/operations",
            {"type": "deprovision"},
        )
        mock_api_client.wait_for_operation.assert_called_once_with(200)

    @pytest.mark.asyncio
    async def test_deprovision_not_found(self, metric_drain_manager, mock_api_client):
        mock_404 = MagicMock()
        mock_404.status_code = 404
        mock_api_client.post.side_effect = HTTPError(
            "404 Client Error", response=mock_404
        )

        with pytest.raises(Exception, match="Metric drain 999 not found"):
            await metric_drain_manager.deprovision(999)
