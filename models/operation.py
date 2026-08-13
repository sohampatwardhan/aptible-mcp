from pydantic import Field
from typing import Dict, List, Any

from models.base import ResourceBase, ResourceManager


class Operation(ResourceBase):
    """
    Aptible Operation model.
    """

    resource_id: int = Field(
        ..., description="ID of the resource the operation was run against."
    )
    resource_type: str = Field(
        ..., description="Type of the resource the operation was run against."
    )
    type: str = Field(..., description="The type of operation run.")
    status: str = Field("unknown", description="Current status of the operation.")
    cancelled: bool = Field(
        False, description="Whether the operation has been cancelled."
    )


class OperationManager(ResourceManager[Operation, str]):
    """
    Manager for Operations.
    """

    resource_name = "operations"
    resource_model = Operation
    resource_url = "/operations"

    async def logs(self, operation_id: int) -> str:
        """
        Get logs for an operation by fetching from the S3 URL endpoint.
        Returns the actual log content as a string.
        """
        redirect_url = await self.api_client.get_text(
            f"/operations/{operation_id}/logs"
        )
        if not redirect_url:
            return f"No logs available for operation {operation_id} (empty response)"
        log_content = await self.api_client.get_text(redirect_url, authenticated=False)
        if not log_content:
            return f"No logs available for operation {operation_id} (empty content from redirect URL)"
        return log_content

    async def get_operations_for_app(self, app_id: int) -> List[Dict[str, Any]]:
        """
        Get recent operations for an app with ID, type, and status.
        """
        response = await self.api_client.get(f"/apps/{app_id}/operations")
        operations = response.get("_embedded", {}).get("operations", [])
        return [
            {
                "id": op["id"],
                "type": op.get("type", "unknown"),
                "status": op.get("status", "unknown"),
            }
            for op in operations
        ]

    async def get_operations_for_database(
        self, database_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get recent operations for a database with ID, type, and status.
        """
        response = await self.api_client.get(f"/databases/{database_id}/operations")
        operations = response.get("_embedded", {}).get("operations", [])
        return [
            {
                "id": op["id"],
                "type": op.get("type", "unknown"),
                "status": op.get("status", "unknown"),
            }
            for op in operations
        ]

    async def cancel(self, operation_id: int) -> Operation:
        """
        Cancel a running operation. Cancellation is a PUT with
        cancelled: true against the operation itself, not a DELETE or a
        sub-resource. An operation already in a terminal state (succeeded
        or failed) can't be cancelled; this raises before making that call.
        """
        operation = await self.get_by_id(operation_id)
        if not operation:
            raise Exception(f"Operation {operation_id} not found")
        if operation.status in ("succeeded", "failed"):
            raise Exception(
                f"Operation {operation_id} is already {operation.status} and cannot be cancelled"
            )

        response = await self.api_client.put(
            f"/operations/{operation_id}", {"cancelled": True}
        )
        return self.resource_model.model_validate(response)

    async def get_operations_for_vhost(self, vhost_id: int) -> List[Dict[str, Any]]:
        """
        Get recent operations for a vhost with ID, type, and status.
        """
        response = await self.api_client.get(f"/vhosts/{vhost_id}/operations")
        operations = response.get("_embedded", {}).get("operations", [])
        return [
            {
                "id": op["id"],
                "type": op.get("type", "unknown"),
                "status": op.get("status", "unknown"),
            }
            for op in operations
        ]
