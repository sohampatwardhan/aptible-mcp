import pytest
from unittest.mock import MagicMock
from requests.exceptions import HTTPError

from models.certificate import Certificate, CertificateManager
from api_client import AptibleApiClient


@pytest.fixture
def mock_api_client():
    return MagicMock(spec=AptibleApiClient)


@pytest.fixture
def certificate_manager(mock_api_client):
    return CertificateManager(mock_api_client)


@pytest.fixture
def sample_certificate_data():
    return {
        "id": 1,
        "common_name": "example.com",
        "fingerprint": "AA:BB:CC",
    }


class TestCertificateModel:
    def test_certificate_init(self, sample_certificate_data):
        certificate = Certificate.model_validate(sample_certificate_data)
        assert certificate.common_name == "example.com"
        assert certificate.fingerprint == "AA:BB:CC"

    def test_certificate_defaults_to_none(self):
        certificate = Certificate.model_validate({"id": 1})
        assert certificate.common_name is None
        assert certificate.fingerprint is None


class TestCertificateManager:
    @pytest.mark.asyncio
    async def test_upload(
        self, certificate_manager, mock_api_client, sample_certificate_data
    ):
        mock_api_client.post.return_value = sample_certificate_data

        certificate = await certificate_manager.upload(
            5, "-----BEGIN CERTIFICATE-----...", "-----BEGIN PRIVATE KEY-----..."
        )

        mock_api_client.post.assert_called_once_with(
            "/accounts/5/certificates",
            {
                "certificate_body": "-----BEGIN CERTIFICATE-----...",
                "private_key": "-----BEGIN PRIVATE KEY-----...",
            },
        )
        assert certificate.common_name == "example.com"

    @pytest.mark.asyncio
    async def test_upload_propagates_http_error(
        self, certificate_manager, mock_api_client
    ):
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_api_client.post.side_effect = HTTPError(response=mock_response)

        with pytest.raises(HTTPError):
            await certificate_manager.upload(5, "bad-cert", "bad-key")

    @pytest.mark.asyncio
    async def test_list_for_account(
        self, certificate_manager, mock_api_client, sample_certificate_data
    ):
        mock_api_client.get.return_value = {
            "_embedded": {"certificates": [sample_certificate_data]}
        }

        certificates = await certificate_manager.list_for_account(5)

        mock_api_client.get.assert_called_once_with(
            "/accounts/5/certificates?per_page=5000&no_embed=true"
        )
        assert len(certificates) == 1
        assert certificates[0].common_name == "example.com"

    @pytest.mark.asyncio
    async def test_list_for_account_empty(self, certificate_manager, mock_api_client):
        mock_api_client.get.return_value = {}

        certificates = await certificate_manager.list_for_account(5)

        assert certificates == []
