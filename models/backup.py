from typing import Any, Dict, List, Optional
from pydantic import Field, computed_field

from models.base import ResourceBase, ResourceManager


class Backup(ResourceBase):
    """
    Aptible Backup model.
    """

    created_at: str = Field(..., description="Backup creation timestamp")

    @computed_field
    def database_id(self) -> Optional[int]:
        """
        Extract database_id from _links.database.href

        Example: links.database.href = "https://api.aptible.com/databases/1234"
        """
        if not self.links or "database" not in self.links:
            return None

        href = self.links.get("database", {}).get("href")
        if not href:
            return None

        return int(href.split("/")[-1])


class BackupManager(ResourceManager[Backup, str]):
    """
    Manager for Backup resources.
    """

    resource_name = "backups"
    resource_model = Backup
    resource_url = "/backups"

    async def list_for_database(
        self, database_id: int, max_age: Optional[str] = None
    ) -> List[Backup]:
        """
        List backups for a database, optionally excluding backups older than
        max_age (a relative duration string like "1w"/"1y"). The API has no
        confirmed server-side filter for this, so filtering happens client-side.
        """
        response = self.api_client.get(
            f"/databases/{database_id}/backups?per_page=5000&no_embed=true"
        )
        if "_embedded" not in response:
            return []
        items = response["_embedded"][self.resource_name]
        backups = [self.resource_model.model_validate(item) for item in items]

        if max_age is not None:
            cutoff = self._parse_relative_age(max_age)
            backups = [b for b in backups if b.created_at >= cutoff]

        return backups

    @staticmethod
    def _parse_relative_age(max_age: str) -> str:
        """
        Convert a relative duration string ("1w", "1y", "30d") into an ISO 8601
        cutoff timestamp string, comparable against created_at's ISO format.
        """
        import re
        from datetime import datetime, timedelta, timezone

        match = re.fullmatch(r"(\d+)([dwy])", max_age)
        if not match:
            raise ValueError(f"Invalid max_age format: {max_age}")
        amount, unit = int(match.group(1)), match.group(2)
        days = {"d": 1, "w": 7, "y": 365}[unit] * amount
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return cutoff.isoformat()

    async def list_orphaned(self, account_id: int) -> List[Backup]:
        """
        List orphaned backups (backups whose source database has been deleted)
        for an environment.
        """
        response = self.api_client.get(
            f"/accounts/{account_id}/backups?orphaned=true&per_page=5000&no_embed=true"
        )
        if "_embedded" not in response:
            return []
        items = response["_embedded"][self.resource_name]
        return [self.resource_model.model_validate(item) for item in items]

    async def restore(
        self,
        backup_id: int,
        new_handle: str,
        destination_account_id: Optional[int] = None,
    ) -> None:
        """
        Restore a backup into a new database. This always creates a new
        database rather than restoring in place; the caller composes with
        DatabaseManager.get(new_handle, ...) afterward to fetch the result.
        """
        operation_data: Dict[str, Any] = {"type": "restore", "handle": new_handle}
        if destination_account_id is not None:
            operation_data["destination_account_id"] = destination_account_id

        response = self.api_client.post(
            f"/backups/{backup_id}/operations", operation_data
        )
        self.api_client.wait_for_operation(response["id"])

    async def purge(self, backup_id: int) -> None:
        """
        Purge a backup by ID.
        """
        operation_data = {"type": "purge"}
        response = self.api_client.post(
            f"/backups/{backup_id}/operations", operation_data
        )
        self.api_client.wait_for_operation(response["id"])
