"""
Log Drain model and manager for Aptible log drains.
"""

from typing import Any, List, Optional
from requests.exceptions import HTTPError
from pydantic import Field, computed_field

from models.base import ResourceBase, ResourceManager


VALID_LOG_DRAIN_TYPES = {"syslog_tls_tcp", "https_post", "elasticsearch_database"}


class LogDrain(ResourceBase):
    """
    Aptible Log Drain model.
    """

    handle: str = Field(..., description="Log drain handle (name)")
    drain_type: str = Field(..., description="Type of log drain")
    status: str = Field(..., description="Log drain status")

    @computed_field
    def account_id(self) -> Optional[int]:
        """
        Extract account_id from _links.account.href

        Example: _links.account.href = "https://api.aptible.com/accounts/1234"
        """
        if not self.links or "account" not in self.links:
            return None

        href = self.links.get("account", {}).get("href")
        if not href:
            return None

        return int(href.split("/")[-1])


class LogDrainManager(ResourceManager[LogDrain, str]):
    """
    Manager for Log Drain resources.
    """

    resource_name = "log_drains"
    resource_model = LogDrain
    resource_url = "/log_drains"

    async def create(  # type: ignore[override]
        self, account_id: int, handle: str, drain_type: str, **type_fields: Any
    ) -> LogDrain:
        """
        Create and provision a log drain for an environment.

        Validates that drain_type is supported before making any API calls.
        POSTs to /accounts/{account_id}/log_drains and then triggers a provision operation.
        """
        if drain_type not in VALID_LOG_DRAIN_TYPES:
            raise ValueError(
                f"Unsupported log drain type: '{drain_type}'. "
                f"Supported types: {', '.join(sorted(VALID_LOG_DRAIN_TYPES))}"
            )

        payload = {"handle": handle, "drain_type": drain_type, **type_fields}
        response = self.api_client.post(f"/accounts/{account_id}/log_drains", payload)
        drain = self.resource_model.model_validate(response)

        refreshed = await self._run_operation(
            drain.id, f"/log_drains/{drain.id}/operations", "provision"
        )
        return refreshed or drain

    async def list_for_account(self, account_id: int) -> List[LogDrain]:
        """
        List all log drains for a specific account (environment).

        Tries the nested path `GET /accounts/{account_id}/log_drains?per_page=5000&no_embed=true`
        first. If that endpoint returns a 404 HTTPError (the nested path is unconfirmed against
        the live Aptible API), it falls back to the global `GET /log_drains?per_page=5000&no_embed=true`
        collection and filters client-side by the drain's account link.
        """
        try:
            response = self.api_client.get(
                f"/accounts/{account_id}/log_drains?per_page=5000&no_embed=true"
            )
            if "_embedded" not in response:
                return []
            items = response["_embedded"][self.resource_name]
            return [self.resource_model.model_validate(item) for item in items]
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                all_drains = await self.list()
                return [drain for drain in all_drains if drain.account_id == account_id]
            raise

    async def deprovision(self, drain_id: int) -> None:
        """
        Deprovision a log drain by identifier.

        Triggers a deprovision operation without refetching. If the log drain
        does not exist, raises an exception identifying the log drain ID.
        """
        try:
            await self._run_operation(
                drain_id,
                f"/log_drains/{drain_id}/operations",
                "deprovision",
                refetch=False,
            )
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise Exception(f"Log drain {drain_id} not found") from e
            raise
