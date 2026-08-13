from typing import Optional, List, Any
from pydantic import Field, computed_field

from models.base import ResourceBase, ResourceManager
from models.stack import StackManager


class Account(ResourceBase):
    """
    Aptible Account (aka Environment) model
    """

    handle: str = Field(..., description="Resource handle (name)")
    created_at: str = Field(..., description="Account creation timestamp")
    updated_at: str = Field(..., description="Account last update timestamp")

    @computed_field
    def stack_id(self) -> Optional[int]:
        """
        Extract stack_id from _links.stack.href

        Example: _links.stack.href = "https://api.aptible.com/stacks/1234"
        """
        if not self.links or "stack" not in self.links:
            return None

        href = self.links.get("stack", {}).get("href")
        if not href:
            return None

        return int(href.split("/")[-1])


class AccountManager(ResourceManager[Account, str]):
    """
    Manager for Account (aka Environment) resources
    """

    resource_name = "accounts"
    resource_model = Account
    resource_url = "/accounts"
    stack_manager: Optional[StackManager] = None

    async def list(self, **kwargs) -> List[Account]:
        """
        Override list method to match test expectations
        """
        response = await self.api_client.get(self.resource_url)
        if "_embedded" not in response:
            return []
        items = response["_embedded"][self.resource_name]
        return [self.resource_model.model_validate(item) for item in items]

    async def get_by_id(self, obj_id: int, **kwargs) -> Optional[Account]:
        """
        Override get_by_id to use direct URL lookup for account tests
        """
        try:
            response = await self.api_client.get(f"{self.resource_url}/{obj_id}")
            return self.resource_model.model_validate(response)
        except Exception:
            return await super().get_by_id(obj_id, with_params=False, **kwargs)

    async def create(self, data: dict[str, Any]) -> Account:
        """
        Create a new account/environment
        """
        handle = data.get("handle")
        if not handle:
            raise Exception("A handle is required.")
        stack_id = data.get("stack_id")
        if not stack_id:
            raise Exception("A stack_id is required.")

        if not self.stack_manager:
            self.stack_manager = StackManager(self.api_client)

        stack = await self.stack_manager.get_by_id(stack_id)
        if stack is None:
            raise Exception(f"Stack {stack_id} not found")

        account_type = "development" if not stack.organization_id else "production"

        create_data = {
            "handle": handle,
            "stack_id": stack.id,
            "type": account_type,
            "organization_id": await self.api_client.organization_id(),
        }
        return await super().create(create_data)

    async def rename(self, account_id: int, new_handle: str) -> Account:
        """
        Rename an environment. A handle that's already taken elsewhere in
        the organization surfaces as the API's own HTTPError, unhandled here,
        exactly like existing handle-uniqueness behavior elsewhere.
        """
        response = await self.api_client.put(
            f"{self.resource_url}/{account_id}", {"handle": new_handle}
        )
        return self.resource_model.model_validate(response)

    async def get_ca_certificate(self, account_id: int) -> Optional[str]:
        """
        Return the environment's configured CA certificate body, or None if
        none is configured. The write path for setting this is intentionally
        not implemented here (unconfirmed against the real API).
        """
        response = await self.api_client.get(f"{self.resource_url}/{account_id}")
        return response.get("ca_body")

    async def get_by_stack_id(self, stack_id: int) -> List[Account]:
        """
        Get accounts/environments for a stack by stack ID.
        """
        accounts = await self.list(with_params=False)
        return [account for account in accounts if account.stack_id == stack_id]
