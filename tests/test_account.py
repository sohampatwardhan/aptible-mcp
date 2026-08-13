import pytest
from unittest.mock import MagicMock, AsyncMock
from requests.exceptions import HTTPError

from models.account import Account, AccountManager
from api_client import AptibleApiClient
from models.stack import StackManager


@pytest.fixture
def mock_api_client():
    """
    Fixture providing a mock AptibleApiClient.
    """
    mock_client = MagicMock(spec=AptibleApiClient)
    return mock_client


@pytest.fixture
def account_manager(mock_api_client):
    """
    Fixture providing an AccountManager with a mock API client.
    """
    return AccountManager(mock_api_client)


@pytest.fixture
def stack_manager(mock_api_client):
    """
    Fixture providing a StackManager with a mock API client.
    """
    return StackManager(mock_api_client)


@pytest.fixture
def sample_account_data():
    """
    Fixture providing sample account data for testing.
    """
    return {
        "id": 123,
        "handle": "test-account",
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "_links": {
            "self": {"href": "https://api.aptible.com/accounts/123"},
            "stack": {"href": "https://api.aptible.com/stacks/456"},
        },
    }


@pytest.fixture
def sample_accounts_data():
    """
    Fixture providing sample data for multiple accounts.
    """
    return [
        {
            "id": 123,
            "handle": "test-account-1",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "_links": {
                "self": {"href": "https://api.aptible.com/accounts/123"},
                "stack": {"href": "https://api.aptible.com/stacks/456"},
            },
        },
        {
            "id": 789,
            "handle": "test-account-2",
            "created_at": "2023-01-02T12:00:00Z",
            "updated_at": "2023-01-02T12:00:00Z",
            "_links": {
                "self": {"href": "https://api.aptible.com/accounts/789"},
                "stack": {"href": "https://api.aptible.com/stacks/456"},
            },
        },
        {
            "id": 101,
            "handle": "test-account-3",
            "created_at": "2023-01-03T12:00:00Z",
            "updated_at": "2023-01-03T12:00:00Z",
            "_links": {
                "self": {"href": "https://api.aptible.com/accounts/101"},
                "stack": {"href": "https://api.aptible.com/stacks/789"},
            },
        },
    ]


@pytest.fixture
def sample_stack_data():
    """
    Fixture providing sample stack data for testing.
    """
    return {
        "id": 456,
        "name": "test-stack",
        "organization_id": None,
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "_links": {},
    }


class TestAccount:
    """
    Tests for the Account model.
    """

    def test_account_init(self, sample_account_data):
        """
        Test that Account can be initialized from valid data.
        """
        account = Account.model_validate(sample_account_data)

        assert account.id == 123
        assert account.handle == "test-account"
        assert account.created_at == "2023-01-01T12:00:00Z"
        assert account.updated_at == "2023-01-01T12:00:00Z"
        assert account.links == {
            "self": {"href": "https://api.aptible.com/accounts/123"},
            "stack": {"href": "https://api.aptible.com/stacks/456"},
        }

    def test_transform_links(self, sample_account_data):
        """
        Test that _links is transformed to links during initialization.
        """
        account = Account.model_validate(sample_account_data)

        assert "_links" not in sample_account_data
        assert "links" in sample_account_data
        assert account.links == {
            "self": {"href": "https://api.aptible.com/accounts/123"},
            "stack": {"href": "https://api.aptible.com/stacks/456"},
        }

    def test_stack_id_computed_field(self, sample_account_data):
        """
        Test that the stack_id computed field works correctly.
        """
        account = Account.model_validate(sample_account_data)

        assert account.stack_id == 456

    def test_stack_id_missing(self):
        """
        Test that stack_id returns None when stack is missing from links.
        """
        account_data = {
            "id": 123,
            "handle": "test-account",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "links": {},
        }

        account = Account.model_validate(account_data)

        assert account.stack_id is None

    def test_stack_id_missing_href(self):
        """
        Test that stack_id returns None when stack href is missing.
        """
        account_data = {
            "id": 123,
            "handle": "test-account",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "links": {"stack": {}},
        }

        account = Account.model_validate(account_data)

        assert account.stack_id is None


class TestAccountManager:
    """
    Tests for the AccountManager class.
    """

    @pytest.mark.asyncio
    async def test_list(self, account_manager, mock_api_client, sample_accounts_data):
        """
        Test that the list method correctly returns accounts.
        """

        mock_api_client.get.return_value = {
            "_embedded": {"accounts": sample_accounts_data}
        }

        accounts = await account_manager.list()

        assert len(accounts) == 3
        assert all(isinstance(account, Account) for account in accounts)
        assert [account.id for account in accounts] == [123, 789, 101]
        assert [account.handle for account in accounts] == [
            "test-account-1",
            "test-account-2",
            "test-account-3",
        ]

        mock_api_client.get.assert_called_once_with("/accounts")

    @pytest.mark.asyncio
    async def test_get_by_id(
        self, account_manager, mock_api_client, sample_account_data
    ):
        """
        Test that get_by_id correctly returns an account by ID.
        """

        mock_api_client.get.return_value = sample_account_data
        account_id = 123

        account = await account_manager.get_by_id(account_id)

        assert isinstance(account, Account)
        assert account.id == 123
        assert account.handle == "test-account"

        mock_api_client.get.assert_called_once_with(f"/accounts/{account_id}")

    @pytest.mark.asyncio
    async def test_get(self, account_manager, mock_api_client, sample_accounts_data):
        """
        Test that get correctly returns an account by handle.
        """

        mock_api_client.get.return_value = {
            "_embedded": {"accounts": sample_accounts_data}
        }
        handle = "test-account-2"

        account = await account_manager.get(handle)

        assert isinstance(account, Account)
        assert account.id == 789
        assert account.handle == "test-account-2"

        mock_api_client.get.assert_called_once_with("/accounts")

    @pytest.mark.asyncio
    async def test_get_not_found(
        self, account_manager, mock_api_client, sample_accounts_data
    ):
        """
        Test that get returns None when account is not found.
        """

        mock_api_client.get.return_value = {
            "_embedded": {"accounts": sample_accounts_data}
        }
        handle = "nonexistent-account"

        account = await account_manager.get(handle)

        assert account is None

        mock_api_client.get.assert_called_once_with("/accounts")

    @pytest.mark.asyncio
    async def test_get_by_stack_id(
        self, account_manager, mock_api_client, sample_accounts_data
    ):
        """
        Test that get_by_stack_id correctly returns accounts by stack ID.
        """

        mock_api_client.get.return_value = {
            "_embedded": {"accounts": sample_accounts_data}
        }
        stack_id = 456

        accounts = await account_manager.get_by_stack_id(stack_id)

        assert len(accounts) == 2
        assert all(isinstance(account, Account) for account in accounts)
        assert [account.id for account in accounts] == [123, 789]
        assert [account.handle for account in accounts] == [
            "test-account-1",
            "test-account-2",
        ]

        mock_api_client.get.assert_called_once_with("/accounts")

    @pytest.mark.asyncio
    async def test_get_by_stack_id_not_found(
        self, account_manager, mock_api_client, sample_accounts_data
    ):
        """
        Test that get_by_stack_id returns an empty list when no accounts match.
        """

        mock_api_client.get.return_value = {
            "_embedded": {"accounts": sample_accounts_data}
        }
        stack_id = 999

        accounts = await account_manager.get_by_stack_id(stack_id)

        assert len(accounts) == 0

        mock_api_client.get.assert_called_once_with("/accounts")

    @pytest.mark.asyncio
    async def test_create(
        self,
        monkeypatch,
        account_manager,
        mock_api_client,
        sample_account_data,
        sample_stack_data,
    ):
        """
        Test that the create method successfully creates an account.
        """

        mock_stack_manager = MagicMock()
        mock_stack_model = MagicMock()
        mock_stack_model.id = 456
        mock_stack_model.organization_id = None
        mock_stack_manager.get_by_id = AsyncMock(return_value=mock_stack_model)

        monkeypatch.setattr(account_manager, "stack_manager", mock_stack_manager)

        mock_api_client.organization_id = AsyncMock(return_value="org-123")
        mock_api_client.post.return_value = sample_account_data

        account = await account_manager.create(
            {"handle": "test-account", "stack_id": 456}
        )

        assert isinstance(account, Account)
        assert account.id == 123
        assert account.handle == "test-account"

        mock_stack_manager.get_by_id.assert_called_once_with(456)
        mock_api_client.organization_id.assert_called_once()
        mock_api_client.post.assert_called_once_with(
            "/accounts",
            {
                "handle": "test-account",
                "stack_id": 456,
                "type": "development",
                "organization_id": "org-123",
            },
        )

    @pytest.mark.asyncio
    async def test_create_production_account(
        self, monkeypatch, account_manager, mock_api_client, sample_account_data
    ):
        """
        Test creating a production account when stack has an organization_id.
        """
        mock_stack_manager = MagicMock()
        mock_stack_model = MagicMock()
        mock_stack_model.id = 456
        mock_stack_model.organization_id = "org-123"
        mock_stack_manager.get_by_id = AsyncMock(return_value=mock_stack_model)

        monkeypatch.setattr(account_manager, "stack_manager", mock_stack_manager)

        mock_api_client.organization_id = AsyncMock(return_value="org-123")
        mock_api_client.post.return_value = sample_account_data

        account = await account_manager.create(
            {"handle": "test-account", "stack_id": 456}
        )

        assert isinstance(account, Account)

        mock_api_client.post.assert_called_once_with(
            "/accounts",
            {
                "handle": "test-account",
                "stack_id": 456,
                "type": "production",
                "organization_id": "org-123",
            },
        )

    @pytest.mark.asyncio
    async def test_create_missing_handle(self, account_manager):
        """
        Test create raises an exception when handle is missing.
        """
        with pytest.raises(Exception) as excinfo:
            await account_manager.create({"handle": None, "stack_id": 456})

        assert "A handle is required" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_create_missing_stack_id(self, account_manager):
        """
        Test create raises an exception when stack_id is missing.
        """
        with pytest.raises(Exception) as excinfo:
            await account_manager.create({"handle": "test-account", "stack_id": None})

        assert "A stack_id is required" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_create_stack_not_found(self, monkeypatch, account_manager):
        """
        Test create raises an exception when stack_id is not found.
        """

        mock_stack_manager = MagicMock()
        mock_stack_manager.get_by_id = AsyncMock(return_value=None)

        monkeypatch.setattr(account_manager, "stack_manager", mock_stack_manager)

        with pytest.raises(Exception) as excinfo:
            await account_manager.create({"handle": "test-account", "stack_id": 999})

        assert "Stack 999 not found" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_rename_success(
        self, account_manager, mock_api_client, sample_account_data
    ):
        renamed_data = {**sample_account_data, "handle": "renamed-account"}
        mock_api_client.put.return_value = renamed_data

        account = await account_manager.rename(123, "renamed-account")

        mock_api_client.put.assert_called_once_with(
            "/accounts/123", {"handle": "renamed-account"}
        )
        assert isinstance(account, Account)
        assert account.handle == "renamed-account"

    @pytest.mark.asyncio
    async def test_rename_duplicate_handle_propagates(
        self, account_manager, mock_api_client
    ):
        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_api_client.put.side_effect = HTTPError(response=mock_response)

        with pytest.raises(HTTPError):
            await account_manager.rename(123, "already-taken")

    @pytest.mark.asyncio
    async def test_get_ca_certificate_configured(
        self, account_manager, mock_api_client, sample_account_data
    ):
        mock_api_client.get.return_value = {
            **sample_account_data,
            "ca_body": "-----BEGIN CERTIFICATE-----...",
        }

        ca_certificate = await account_manager.get_ca_certificate(123)

        mock_api_client.get.assert_called_once_with("/accounts/123")
        assert ca_certificate == "-----BEGIN CERTIFICATE-----..."

    @pytest.mark.asyncio
    async def test_get_ca_certificate_unconfigured(
        self, account_manager, mock_api_client, sample_account_data
    ):
        mock_api_client.get.return_value = sample_account_data

        ca_certificate = await account_manager.get_ca_certificate(123)

        assert ca_certificate is None
