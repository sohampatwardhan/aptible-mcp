from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from api_client import AptibleApiClient

T = TypeVar("T", bound=BaseModel)
ID = TypeVar("ID")


class ResourceBase(BaseModel):
    """
    Base model for all API resources.
    """

    id: int = Field(..., description="Resource unique identifier")
    links: Dict[str, Any] = Field({}, description="Links to related resources")

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def transform_links(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform _links to links for API compatibility.
        """
        if isinstance(data, dict) and "_links" in data:
            data["links"] = data.pop("_links")
        return data


class ResourceManager(Generic[T, ID]):
    """
    Base class for resource managers providing CRUD operations.
    """

    resource_name: str
    resource_model: Type[T]
    resource_url: str

    name_field: str = "handle"

    def __init__(self, api_client: "AptibleApiClient") -> None:
        self.api_client = api_client

    async def list(self, **kwargs) -> List[T]:
        """
        List all resources.
        """
        query_params = "?per_page=5000&no_embed=true"

        response = self.api_client.get(f"{self.resource_url}{query_params}")
        if "_embedded" not in response:
            return []
        items = response["_embedded"][self.resource_name]
        return [self.resource_model.model_validate(item) for item in items]

    async def get(self, identifier: ID, **kwargs) -> Optional[T]:
        """
        Get a specific resource by semi-unique identifier (usually handle).
        """
        items = await self.list(**kwargs)
        for item in items:
            if getattr(item, self.name_field) == identifier:
                return item
        return None

    async def get_by_id(self, obj_id: int, **kwargs) -> Optional[T]:
        """
        Get a specific resource by ID.
        """
        item = self.api_client.get(f"{self.resource_url}/{obj_id}")
        return self.resource_model.model_validate(item)

    async def create(self, data: Dict[str, Any]) -> T:
        """
        Create a new resource.
        """
        response = self.api_client.post(f"{self.resource_url}", data)
        return self.resource_model.model_validate(response)

    async def delete(self, resource_id: int) -> None:
        """
        Delete a resource by ID.
        """
        self.api_client.delete(f"{self.resource_url}/{resource_id}")

    async def _run_operation(
        self,
        resource_id: int,
        operations_path: str,
        operation_type: str,
        extra: Optional[Dict[str, Any]] = None,
        refetch: bool = True,
    ) -> Optional[T]:
        """
        Generalizes the operation-trigger-and-wait pattern hand-written per-method
        elsewhere (e.g. Service.scale, App.deploy): POST an operation, wait for it
        to reach a terminal state, then optionally refetch the resource it acted on.

        Actions that produce a *different* resource than the one they're called on
        (e.g. backup restore, database clone) should not use this — call
        api_client.post + wait_for_operation directly and let the caller compose
        with the target manager instead.
        """
        operation_data: Dict[str, Any] = {"type": operation_type, **(extra or {})}
        response = self.api_client.post(operations_path, operation_data)
        self.api_client.wait_for_operation(response["id"])
        return await self.get_by_id(resource_id) if refetch else None
