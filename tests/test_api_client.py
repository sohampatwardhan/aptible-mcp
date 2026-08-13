from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api_client import AptibleApiClient


def _client(**kwargs) -> AptibleApiClient:
    client = AptibleApiClient(
        api_url="https://api.aptible.com",
        auth_url="https://auth.aptible.com",
        **kwargs,
    )
    client._token = "test-token"
    return client


def test_build_url_accepts_relative_and_same_origin_absolute_urls():
    client = _client()

    assert client._build_url("/apps") == "https://api.aptible.com/apps"
    assert (
        client._build_url("https://api.aptible.com/databases/1/vhosts")
        == "https://api.aptible.com/databases/1/vhosts"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://attacker.example/vhosts",
        "http://api.aptible.com/vhosts",
        "https://api.aptible.com.evil.example/vhosts",
        "//attacker.example/vhosts",
    ],
)
def test_build_url_rejects_cross_origin_and_protocol_relative_urls(url):
    client = _client()

    with pytest.raises(ValueError):
        client._build_url(url)


@pytest.mark.asyncio
async def test_get_uses_async_client_with_configured_request_timeout():
    client = _client(request_timeout_seconds=7.5)
    client._http.get = AsyncMock()
    response = MagicMock()
    response.json.return_value = {"id": 1}
    client._http.get.return_value = response

    assert await client.get("/apps/1") == {"id": 1}

    client._http.get.assert_awaited_once_with(
        "https://api.aptible.com/apps/1",
        headers={
            "Content-Type": "application/hal+json",
            "Authorization": "Bearer test-token",
        },
    )
    assert client._http.timeout.read == 7.5


@pytest.mark.asyncio
async def test_wait_for_operation_times_out_instead_of_polling_forever():
    client = _client(
        operation_timeout_seconds=5,
        operation_poll_interval_seconds=1,
    )
    client.get = AsyncMock(return_value={"status": "running"})

    with (
        patch("api_client.monotonic", side_effect=[0, 0, 5]),
        patch("api_client.asyncio.sleep", new=AsyncMock()) as sleep,
        pytest.raises(TimeoutError, match="Operation op-1 did not complete within 5"),
    ):
        await client.wait_for_operation("op-1")

    sleep.assert_not_awaited()
    client.get.assert_awaited_once_with("/operations/op-1")


@pytest.mark.asyncio
async def test_get_text_never_sends_credentials_to_external_log_url():
    client = _client()
    client._http.get = AsyncMock()
    response = MagicMock(text="logs")
    client._http.get.return_value = response

    assert (
        await client.get_text("https://logs.example/signed", authenticated=False)
        == "logs"
    )

    client._http.get.assert_awaited_once_with(
        "https://logs.example/signed", headers=None
    )
