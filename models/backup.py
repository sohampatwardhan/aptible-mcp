from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Optional
from pydantic import Field, computed_field

from models.base import ResourceBase, ResourceManager


class Backup(ResourceBase):
    """
    Aptible Backup model.
    """

    created_at: str = Field(..., description="Backup creation timestamp")

    @computed_field
    def account_id(self) -> Optional[int]:
        """Extract the owning account ID when the backup exposes that link."""
        if not self.links or "account" not in self.links:
            return None

        href = self.links.get("account", {}).get("href")
        if not href:
            return None

        return int(href.split("/")[-1])

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
        response = await self.api_client.get(
            f"/databases/{database_id}/backups?per_page=5000&no_embed=true"
        )
        if "_embedded" not in response:
            return []
        items = response["_embedded"][self.resource_name]
        backups = [self.resource_model.model_validate(item) for item in items]

        if max_age is not None:
            cutoff = self._parse_relative_age(max_age)
            backups = [
                backup
                for backup in backups
                if self._parse_timestamp(backup.created_at) >= cutoff
            ]

        return backups

    @staticmethod
    def _parse_relative_age(max_age: str, now: Optional[datetime] = None) -> datetime:
        """
        Convert a relative duration string ("1w", "1y", "30d") into an
        aware UTC cutoff timestamp.
        """
        match = re.fullmatch(r"(\d+)([dwy])", max_age)
        if not match:
            raise ValueError(f"Invalid max_age format: {max_age}")
        amount, unit = int(match.group(1)), match.group(2)
        days = {"d": 1, "w": 7, "y": 365}[unit] * amount
        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        return reference.astimezone(timezone.utc) - timedelta(days=days)

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        """Parse an ISO 8601 API timestamp into an aware UTC datetime."""
        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
        timestamp = datetime.fromisoformat(normalized)
        if timestamp.tzinfo is None:
            raise ValueError(f"Backup timestamp must include a timezone: {value}")
        return timestamp.astimezone(timezone.utc)

    async def list_orphaned(self, account_id: int) -> List[Backup]:
        """
        List orphaned backups (backups whose source database has been deleted)
        for an environment.
        """
        response = await self.api_client.get(
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

        response = await self.api_client.post(
            f"/backups/{backup_id}/operations", operation_data
        )
        await self.api_client.wait_for_operation(response["id"])

    async def purge(self, backup_id: int) -> None:
        """
        Purge a backup by ID.
        """
        operation_data = {"type": "purge"}
        response = await self.api_client.post(
            f"/backups/{backup_id}/operations", operation_data
        )
        await self.api_client.wait_for_operation(response["id"])
