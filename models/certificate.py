from typing import List, Optional

from pydantic import Field

from models.base import ResourceBase, ResourceManager


class Certificate(ResourceBase):
    """
    Aptible Certificate model.
    """

    common_name: Optional[str] = Field(None, description="Certificate common name")
    fingerprint: Optional[str] = Field(None, description="Certificate fingerprint")


class CertificateManager(ResourceManager[Certificate, str]):
    """
    Manager for Certificate resources.
    """

    resource_name = "certificates"
    resource_model = Certificate
    resource_url = "/certificates"

    async def upload(
        self, account_id: int, certificate_body: str, private_key: str
    ) -> Certificate:
        """
        Upload a certificate to an environment. Named `upload` rather than
        `create` because it takes different arguments than the inherited
        ResourceManager.create(data: dict), which would otherwise be an
        incompatible method override. There is no separate chain field in
        the Aptible API — any intermediate certificates must be concatenated
        into certificate_body by the caller. Rejection of an invalid PEM or
        mismatched key pair surfaces as an HTTPError from the API; this
        method does not attempt client-side PEM/key-pair validation.
        """
        response = await self.api_client.post(
            f"/accounts/{account_id}/certificates",
            {"certificate_body": certificate_body, "private_key": private_key},
        )
        return Certificate.model_validate(response)

    async def list_for_account(self, account_id: int) -> List[Certificate]:
        """
        List certificates uploaded to an environment.
        """
        response = await self.api_client.get(
            f"/accounts/{account_id}/certificates?per_page=5000&no_embed=true"
        )
        if "_embedded" not in response:
            return []
        items = response["_embedded"][self.resource_name]
        return [self.resource_model.model_validate(item) for item in items]
