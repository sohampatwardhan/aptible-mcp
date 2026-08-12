import pytest
from unittest.mock import MagicMock

from models.backup import Backup, BackupManager
from api_client import AptibleApiClient


@pytest.fixture
def mock_api_client():
    return MagicMock(spec=AptibleApiClient)


@pytest.fixture
def backup_manager(mock_api_client):
    return BackupManager(mock_api_client)


@pytest.fixture
def sample_backup_data():
    return {
        "id": 1,
        "created_at": "2026-08-01T00:00:00Z",
        "_links": {
            "database": {"href": "https://api.aptible.com/databases/99"},
        },
    }


class TestBackupModel:
    def test_database_id_computed_field(self, sample_backup_data):
        backup = Backup.model_validate(sample_backup_data)
        assert backup.database_id == 99

    def test_database_id_missing_link(self):
        backup = Backup.model_validate({"id": 1, "created_at": "2026-08-01T00:00:00Z"})
        assert backup.database_id is None


class TestBackupManager:
    @pytest.mark.asyncio
    async def test_list_for_database(
        self, backup_manager, mock_api_client, sample_backup_data
    ):
        mock_api_client.get.return_value = {
            "_embedded": {"backups": [sample_backup_data]}
        }

        backups = await backup_manager.list_for_database(99)

        mock_api_client.get.assert_called_once_with(
            "/databases/99/backups?per_page=5000&no_embed=true"
        )
        assert len(backups) == 1
        assert backups[0].database_id == 99

    @pytest.mark.asyncio
    async def test_list_for_database_empty(self, backup_manager, mock_api_client):
        mock_api_client.get.return_value = {}

        backups = await backup_manager.list_for_database(99)

        assert backups == []

    @pytest.mark.asyncio
    async def test_list_for_database_filters_by_max_age(
        self, backup_manager, mock_api_client
    ):
        old_backup = {
            "id": 1,
            "created_at": "2000-01-01T00:00:00+00:00",
            "_links": {"database": {"href": "https://api.aptible.com/databases/99"}},
        }
        recent_backup = {
            "id": 2,
            "created_at": "2099-01-01T00:00:00+00:00",
            "_links": {"database": {"href": "https://api.aptible.com/databases/99"}},
        }
        mock_api_client.get.return_value = {
            "_embedded": {"backups": [old_backup, recent_backup]}
        }

        backups = await backup_manager.list_for_database(99, max_age="1w")

        assert len(backups) == 1
        assert backups[0].id == 2

    @pytest.mark.asyncio
    async def test_list_orphaned(
        self, backup_manager, mock_api_client, sample_backup_data
    ):
        mock_api_client.get.return_value = {
            "_embedded": {"backups": [sample_backup_data]}
        }

        backups = await backup_manager.list_orphaned(5)

        mock_api_client.get.assert_called_once_with(
            "/accounts/5/backups?orphaned=true&per_page=5000&no_embed=true"
        )
        assert len(backups) == 1

    @pytest.mark.asyncio
    async def test_restore_without_destination_account(
        self, backup_manager, mock_api_client
    ):
        mock_api_client.post.return_value = {"id": 500}

        await backup_manager.restore(1, "new-db")

        mock_api_client.post.assert_called_once_with(
            "/backups/1/operations", {"type": "restore", "handle": "new-db"}
        )
        mock_api_client.wait_for_operation.assert_called_once_with(500)

    @pytest.mark.asyncio
    async def test_restore_with_destination_account(
        self, backup_manager, mock_api_client
    ):
        mock_api_client.post.return_value = {"id": 501}

        await backup_manager.restore(1, "new-db", destination_account_id=7)

        mock_api_client.post.assert_called_once_with(
            "/backups/1/operations",
            {"type": "restore", "handle": "new-db", "destination_account_id": 7},
        )

    @pytest.mark.asyncio
    async def test_purge(self, backup_manager, mock_api_client):
        mock_api_client.post.return_value = {"id": 600}

        await backup_manager.purge(1)

        mock_api_client.post.assert_called_once_with(
            "/backups/1/operations", {"type": "purge"}
        )
        mock_api_client.wait_for_operation.assert_called_once_with(600)
