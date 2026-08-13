from typing import Optional, Any
from pydantic import Field, computed_field

from models.base import ResourceBase, ResourceManager

_SETTINGS_FIELDS = (
    "force_zero_downtime",
    "naive_health_check",
    "restart_free_scaling",
    "stop_timeout",
)


class Service(ResourceBase):
    """
    Aptible Service model.
    """

    handle: str = Field(..., description="Service handle (name)")
    process_type: str = Field(..., description="Type of service process")
    container_count: int = Field(
        ..., description="Number of containers running this service"
    )
    container_memory_limit_mb: int = Field(
        ..., description="Size of containers running this service in MB"
    )
    created_at: str = Field(..., description="Service creation timestamp")
    updated_at: str = Field(..., description="Service last update timestamp")

    @computed_field
    def app_id(self) -> int:
        """
        Extract app_id from links.app.href
        """
        if not self.links or "app" not in self.links:
            raise Exception("App is missing from links")

        href = self.links.get("app", {}).get("href")
        if not href:
            raise Exception("App link is missing href")

        return int(href.split("/")[-1])


class ServiceManager(ResourceManager[Service, str]):
    """
    Manager for Service resources.
    """

    resource_name = "services"
    resource_model = Service
    resource_url = "/services"

    async def list_by_app(self, app_id: int) -> list[Service]:
        """
        List all services for a specific app.
        """
        response = await self.api_client.get(
            f"/apps/{app_id}/services?per_page=5000&no_embed=true"
        )
        items = response["_embedded"][self.resource_name]
        return [self.resource_model.model_validate(item) for item in items]

    async def get_by_handle_and_app(
        self, handle: str, app_id: int
    ) -> Optional[Service]:
        """
        Get a service by handle within a specific app.
        """
        services = await self.list_by_app(app_id)
        for service in services:
            if service.handle == handle:
                return service
        return None

    async def scale(
        self,
        service_id: int,
        container_count: int | None,
        container_memory_limit_mb: int | None,
    ) -> Service:
        """
        Scale a service to a given container count and/or memory limit.
        If neither is passed in, this will still trigger a scale operation, which
        in turn will trigger a new release of the service.
        """
        operation_data: dict[str, Any] = {"type": "scale"}

        if container_count is not None:
            operation_data["container_count"] = container_count
        if container_memory_limit_mb is not None:
            operation_data["container_size"] = container_memory_limit_mb

        response = await self.api_client.post(
            f"/services/{service_id}/operations", operation_data
        )
        await self.api_client.wait_for_operation(response["id"])

        refreshed_service = await self.get_by_id(service_id)
        if not refreshed_service:
            raise Exception(f"Service {service_id} not found")
        return refreshed_service

    async def get_settings(self, service_id: int) -> dict[str, Any]:
        """
        Return whichever of force_zero_downtime, naive_health_check,
        restart_free_scaling, stop_timeout are present on the current Service
        resource. These aren't declared Service fields (the API may omit
        them entirely rather than returning null), so they're read from the
        model's extra-field passthrough rather than typed attributes.
        """
        service = await self.get_by_id(service_id)
        if not service:
            raise Exception(f"Service {service_id} not found")

        extra = service.model_extra or {}
        return {field: extra[field] for field in _SETTINGS_FIELDS if field in extra}

    async def update_settings(self, service_id: int, **settings: Any) -> Service:
        """
        Update one or more service settings. The --simple-health-check CLI
        flag corresponds to the naive_health_check field name. Every key is
        validated against the four-name allow-list before any HTTP call, so
        a typo never reaches the API as a silently-ignored extra field.
        """
        for key in settings:
            if key not in _SETTINGS_FIELDS:
                raise ValueError(f"Unsupported service setting: {key}")

        response = await self.api_client.put(f"/services/{service_id}", settings)
        return self.resource_model.model_validate(response)

    async def delete(self, service_id: int) -> None:
        """
        Delete a service by ID.
        """
        service = await self.get_by_id(service_id)
        if not service:
            raise Exception(f"No service found with id {service_id}")

        operation_data = {"type": "deprovision"}
        response = await self.api_client.post(
            f"/services/{service_id}/operations", operation_data
        )
        await self.api_client.wait_for_operation(response["id"])
