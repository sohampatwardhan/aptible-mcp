from typing import Optional, List, Any
from pydantic import Field, computed_field

from models.base import ResourceBase, ResourceManager


class DatabaseImage(ResourceBase):
    """
    Database Images available for managed databases.
    """

    type: str = Field(..., description="Database type (postgresql, redis, etc)")
    version: str = Field(..., description="Database version")
    description: str = Field(..., description="Database description")


class Database(ResourceBase):
    """
    Aptible Database model.
    """

    handle: str = Field(..., description="Resource handle (name)")
    type: str = Field(..., description="Database type (postgresql, redis, etc)")
    created_at: str = Field(..., description="Database creation timestamp")
    updated_at: str = Field(..., description="Database last update timestamp")
    status: str = Field(..., description="Current status of the database")

    @computed_field
    def account_id(self) -> Optional[int]:
        """
        Extract account_id from _links.account.href

        Example: links.stack.href = "https://api.aptible.com/accounts/1234"
        """
        if not self.links or "account" not in self.links:
            return None

        href = self.links.get("account", {}).get("href")
        if not href:
            return None

        return int(href.split("/")[-1])

    @computed_field
    def database_image_id(self) -> Optional[int]:
        """
        Extract account_id from _links.database_image.href

        Example: links.stack.href = "https://api.aptible.com/database_images/1234"
        """
        if not self.links or "database_image" not in self.links:
            return None

        href = self.links.get("database_image", {}).get("href")
        if not href:
            return None

        return int(href.split("/")[-1])


class DatabaseManager(ResourceManager[Database, str]):
    """
    Manager for Database resources.
    """

    resource_name = "databases"
    resource_model = Database
    resource_url = "/databases"

    async def list_available_types(self) -> List[DatabaseImage]:
        """
        List available database types.
        """
        response = self.api_client.get("/database_images")
        items = response["_embedded"]["database_images"]
        return [DatabaseImage.model_validate(item) for item in items]

    async def create(self, data: dict[str, Any]) -> Database:
        """
        Create a new database.

        Asking for an image ID as an input runs a little bit against the grain
        of the format of other methods, where we use handles/names instead.
        However, the chosen database image is a combination of type and version,
        and asking the AI to consistently and reliably provide both in the
        exact way that they're formatted in our API seemed like too much.
        """
        handle = data["handle"]
        if not handle:
            raise Exception("A handle is required")
        account_id = data["account_id"]
        if not account_id:
            raise Exception("An account_id is required")
        image_id = data["image_id"]
        if not image_id:
            raise Exception("A image_id is required")

        images = await self.list_available_types()
        images = [img for img in images if img.id == image_id]
        if not images:
            raise ValueError(f"No database image found with id {image_id}")
        if len(images) > 1:
            raise ValueError(f"Multiple database images found with id {image_id}")
        image = images[0]
        data = {
            "handle": handle,
            "database_image_id": image_id,
            "type": image.type or "postgresql",
        }
        response = self.api_client.post(f"/accounts/{account_id}/databases", data)
        database = self.resource_model.model_validate(response)

        operation_data = {"type": "provision"}
        response = self.api_client.post(
            f"/databases/{database.id}/operations", operation_data
        )
        self.api_client.wait_for_operation(response["id"])

        return database

    async def replicate(
        self,
        database_id: int,
        replica_handle: str,
        container_size: Optional[int] = None,
        disk_size: Optional[int] = None,
    ) -> None:
        """
        Create a read replica of a database and wait for it to be ready.

        The replica is a new resource, so callers fetch it separately by handle.
        """
        operation_data: dict[str, Any] = {
            "type": "replicate",
            "handle": replica_handle,
        }
        if container_size is not None:
            operation_data["container_size"] = container_size
        if disk_size is not None:
            operation_data["disk_size"] = disk_size

        response = self.api_client.post(
            f"/databases/{database_id}/operations", operation_data
        )
        self.api_client.wait_for_operation(response["id"])

    async def clone(self, database_id: int, new_handle: str) -> None:
        """
        Clone a database into a new resource and wait for it to be ready.

        Callers fetch the newly-created database separately by handle.
        """
        operation_data = {"type": "clone", "handle": new_handle}
        response = self.api_client.post(
            f"/databases/{database_id}/operations", operation_data
        )
        self.api_client.wait_for_operation(response["id"])

    async def modify_iops(
        self,
        database_id: int,
        provisioned_iops: Optional[int] = None,
        ebs_volume_type: Optional[str] = None,
    ) -> Database:
        """Modify a database's provisioned IOPS or EBS volume type."""
        extra: dict[str, Any] = {}
        if provisioned_iops is not None:
            extra["provisioned_iops"] = provisioned_iops
        if ebs_volume_type is not None:
            extra["ebs_volume_type"] = ebs_volume_type

        database = await self._run_operation(
            database_id,
            f"/databases/{database_id}/operations",
            "modify",
            extra=extra if extra else None,
        )
        if not database:
            raise Exception(f"Database {database_id} not found")
        return database

    async def resize(
        self,
        database_id: int,
        container_size: Optional[int] = None,
        disk_size: Optional[int] = None,
        instance_profile: Optional[str] = None,
    ) -> Database:
        """
        Resize a database's container, disk, or instance profile.

        Aptible performs database resize through a ``restart`` operation, not
        a ``modify`` operation; this method preserves that API behavior.
        """
        extra: dict[str, Any] = {}
        if container_size is not None:
            extra["container_size"] = container_size
        if disk_size is not None:
            extra["disk_size"] = disk_size
        if instance_profile is not None:
            extra["instance_profile"] = instance_profile

        database = await self._run_operation(
            database_id,
            f"/databases/{database_id}/operations",
            "restart",
            extra=extra if extra else None,
        )
        if not database:
            raise Exception(f"Database {database_id} not found")
        return database

    async def reload(self, database_id: int) -> Database:
        """Reload a database and return its refreshed resource."""
        database = await self._run_operation(
            database_id, f"/databases/{database_id}/operations", "reload"
        )
        if not database:
            raise Exception(f"Database {database_id} not found")
        return database

    async def rename(self, database_id: int, new_handle: str) -> Database:
        """Rename a database to a new handle."""
        response = self.api_client.put(
            f"/databases/{database_id}", {"handle": new_handle}
        )
        return self.resource_model.model_validate(response)

    async def restart(self, database_id: int) -> Database:
        """Restart a database without changing its size."""
        database = await self._run_operation(
            database_id, f"/databases/{database_id}/operations", "restart"
        )
        if not database:
            raise Exception(f"Database {database_id} not found")
        return database

    async def list_versions_for_type(self, database_type: str) -> List[DatabaseImage]:
        """List available database images for a database type."""
        images = [
            image
            for image in await self.list_available_types()
            if image.type == database_type
        ]
        if not images:
            raise ValueError(f"No database type found named {database_type}")
        return images

    async def delete(self, database_id: int) -> None:
        """
        Delete a database by handle.
        """
        database = await self.get_by_id(database_id)
        if not database:
            raise Exception(f"Database {database_id} not found")

        operation_data = {"type": "deprovision"}
        response = self.api_client.post(
            f"/databases/{database.id}/operations", operation_data
        )
        self.api_client.wait_for_operation(response["id"])
