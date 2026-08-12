from typing import List, Optional

from pydantic import Field, computed_field

from models.base import ResourceBase, ResourceManager


class MaintenanceEntry(ResourceBase):
    """
    Aptible scheduled maintenance entry, for either an app or a database.
    """

    handle: str = Field(..., description="Handle of the resource under maintenance")
    status: str = Field(..., description="Maintenance status")
    resource_type: str = Field(
        ..., description="Which collection this entry came from: 'app' or 'database'"
    )

    @computed_field
    def account_id(self) -> Optional[int]:
        """
        Extract account_id from _links.account.href, matching App.account_id's
        convention, so MaintenanceManager can filter both global collections
        client-side by environment.
        """
        if not self.links or "account" not in self.links:
            return None

        href = self.links.get("account", {}).get("href")
        if not href:
            return None

        return int(href.split("/")[-1])


class MaintenanceManager(ResourceManager[MaintenanceEntry, str]):
    """
    Manager for scheduled maintenance entries. There is no per-environment
    endpoint for these; both /maintenances/apps and /maintenances/databases
    are global collections that must be filtered client-side by account.
    """

    resource_name = "maintenances"
    resource_model = MaintenanceEntry
    resource_url = "/maintenances"

    async def list_for_account(self, account_id: int) -> List[MaintenanceEntry]:
        """
        List scheduled maintenance entries (app and database) for an
        environment, tagging each with which collection it came from.

        Both /maintenances/apps and /maintenances/databases are global
        collections (no per-environment endpoint exists), so filtering by
        account_id happens client-side here rather than server-side. The
        embedded collection key for each endpoint is assumed to match its
        last path segment ("apps"/"databases"), following the same
        HAL convention every other custom list method in this codebase
        relies on (e.g. GET /accounts/{id}/backups -> _embedded.backups) —
        confirm live and adjust if either endpoint's actual key differs.
        """
        entries: List[MaintenanceEntry] = []
        for path, embedded_key, resource_type in (
            ("/maintenances/apps", "apps", "app"),
            ("/maintenances/databases", "databases", "database"),
        ):
            response = self.api_client.get(f"{path}?per_page=5000&no_embed=true")
            items = response.get("_embedded", {}).get(embedded_key, [])
            for item in items:
                entry = self.resource_model.model_validate(
                    {**item, "resource_type": resource_type}
                )
                if entry.account_id == account_id:
                    entries.append(entry)
        return entries
