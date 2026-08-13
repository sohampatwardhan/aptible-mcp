"""
MetricDrain model and MetricDrainManager implementation.
"""

from typing import Any, Dict, List, Optional
from httpx import HTTPStatusError
from pydantic import Field, computed_field
from requests.exceptions import HTTPError

from models.base import ResourceBase, ResourceManager


VALID_DRAIN_TYPES = {"influxdb_database", "influxdb", "influxdb2", "datadog"}


class MetricDrain(ResourceBase):
    """
    Aptible MetricDrain model.
    """

    handle: str = Field(..., description="Metric drain handle (name)")
    drain_type: str = Field(..., description="Metric drain destination type")
    status: str = Field(..., description="Current status of the metric drain")
    drain_configuration: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Metric drain configuration parameters. Unlike log drains' flat fields, "
            "drain_configuration is a nested object for most types."
        ),
    )

    @computed_field
    def account_id(self) -> Optional[int]:
        """
        Extract account_id from links.account.href.
        """
        if not self.links or "account" not in self.links:
            return None

        href = self.links.get("account", {}).get("href")
        if not href:
            return None

        return int(href.split("/")[-1])


class MetricDrainManager(ResourceManager[MetricDrain, str]):
    """
    Manager for MetricDrain resources.
    """

    resource_name = "metric_drains"
    resource_model = MetricDrain
    resource_url = "/metric_drains"

    async def create(  # type: ignore[override]
        self,
        account_id: int,
        handle: str,
        drain_type: str,
        drain_configuration: Optional[Dict[str, Any]] = None,
        **type_fields: Any,
    ) -> MetricDrain:
        """
        Provision a metric drain in an environment. Validate drain_type against
        allowed set before provisioning. drain_configuration is a nested object for
        most metric drain types.
        """
        if drain_type not in VALID_DRAIN_TYPES:
            raise ValueError(
                f"Unsupported metric drain type: '{drain_type}'. Supported types: {sorted(list(VALID_DRAIN_TYPES))}"
            )

        config = dict(drain_configuration or {})
        config.update(type_fields)

        payload: Dict[str, Any] = {
            "handle": handle,
            "drain_type": drain_type,
        }
        if config:
            payload["drain_configuration"] = config

        response = await self.api_client.post(
            f"/accounts/{account_id}/metric_drains", payload
        )
        drain = self.resource_model.model_validate(response)

        result = await self._run_operation(
            drain.id,
            f"/metric_drains/{drain.id}/operations",
            "provision",
        )
        return result if result is not None else drain

    async def list_for_account(self, account_id: int) -> List[MetricDrain]:
        """
        List metric drains provisioned in an environment.
        Attempts nested path GET /accounts/{id}/metric_drains, and falls back to global
        GET /metric_drains filtered client-side by account link if nested path 404s.
        """
        try:
            response = await self.api_client.get(
                f"/accounts/{account_id}/metric_drains?per_page=5000&no_embed=true"
            )
            if "_embedded" in response:
                items = response["_embedded"].get(self.resource_name, [])
                return [self.resource_model.model_validate(item) for item in items]
            return []
        except (HTTPError, HTTPStatusError) as err:
            if err.response is not None and err.response.status_code == 404:
                return await self._list_global_filtered_by_account(account_id)
            raise

    async def _list_global_filtered_by_account(
        self, account_id: int
    ) -> List[MetricDrain]:
        """
        Fallback path for listing metric drains by account.
        """
        response = await self.api_client.get(
            f"{self.resource_url}?per_page=5000&no_embed=true"
        )
        if "_embedded" not in response:
            return []
        items = response["_embedded"].get(self.resource_name, [])
        drains = [self.resource_model.model_validate(item) for item in items]
        return [d for d in drains if d.account_id == account_id]

    async def deprovision(self, drain_id: int) -> None:
        """
        Deprovision a metric drain by identifier.
        """
        try:
            await self._run_operation(
                drain_id,
                f"/metric_drains/{drain_id}/operations",
                "deprovision",
                refetch=False,
            )
        except (HTTPError, HTTPStatusError) as err:
            if err.response is not None and err.response.status_code == 404:
                raise Exception(f"Metric drain {drain_id} not found.") from err
            raise
