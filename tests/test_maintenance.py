import pytest
from unittest.mock import MagicMock

from models.maintenance import MaintenanceEntry, MaintenanceManager
from api_client import AptibleApiClient


@pytest.fixture
def mock_api_client():
    return MagicMock(spec=AptibleApiClient)


@pytest.fixture
def maintenance_manager(mock_api_client):
    return MaintenanceManager(mock_api_client)


def _entry(entry_id, account_id):
    return {
        "id": entry_id,
        "handle": f"handle-{entry_id}",
        "status": "scheduled",
        "_links": {
            "account": {"href": f"https://api.aptible.com/accounts/{account_id}"}
        },
    }


class TestMaintenanceEntryModel:
    def test_account_id_computed_field(self):
        entry = MaintenanceEntry.model_validate(
            {**_entry(1, 5), "resource_type": "app"}
        )
        assert entry.account_id == 5

    def test_account_id_missing_link(self):
        entry = MaintenanceEntry.model_validate(
            {"id": 1, "handle": "h", "status": "scheduled", "resource_type": "app"}
        )
        assert entry.account_id is None


class TestMaintenanceManager:
    @pytest.mark.asyncio
    async def test_list_for_account_merges_and_filters(
        self, maintenance_manager, mock_api_client
    ):
        def fake_get(path):
            if path == "/maintenances/apps?per_page=5000&no_embed=true":
                return {"_embedded": {"apps": [_entry(1, 5), _entry(2, 6)]}}
            if path == "/maintenances/databases?per_page=5000&no_embed=true":
                return {"_embedded": {"databases": [_entry(3, 5)]}}
            raise AssertionError(f"unexpected path {path}")

        mock_api_client.get.side_effect = fake_get

        entries = await maintenance_manager.list_for_account(5)

        assert {e.id for e in entries} == {1, 3}
        by_id = {e.id: e for e in entries}
        assert by_id[1].resource_type == "app"
        assert by_id[3].resource_type == "database"

    @pytest.mark.asyncio
    async def test_list_for_account_empty(self, maintenance_manager, mock_api_client):
        mock_api_client.get.return_value = {}

        entries = await maintenance_manager.list_for_account(5)

        assert entries == []
