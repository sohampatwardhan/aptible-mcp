from typing import List, Any
from pydantic import Field, computed_field

from models.base import ResourceBase, ResourceManager


class Vhost(ResourceBase):
    """
    Aptible Vhost model.
    """

    virtual_domain: str | None = Field(None, description="Virtual domain for the vhost")
    external_host: str | None = Field(..., description="External host for the vhost")
    created_at: str = Field(..., description="VHost creation timestamp")
    updated_at: str = Field(..., description="VHost last update timestamp")
    status: str = Field(..., description="Current status of the vhost")
    type: str | None = Field(
        None, description="Endpoint type (e.g. http, tcp, tls, grpc)"
    )
    user_domain: str | None = Field(
        None, description="User custom domain for the vhost"
    )
    container_ports: list[int] | None = Field(
        None, description="Container ports for the vhost"
    )

    @computed_field
    def service_id(self) -> int:
        """
        Extract service_id from links.service.href
        """
        if not self.links or "service" not in self.links:
            raise Exception("Service is missing from links")

        href = self.links.get("service", {}).get("href")
        if not href:
            raise Exception("Service link is missing href")

        return int(href.split("/")[-1])


class VhostManager(ResourceManager[Vhost, str]):
    """
    Manager for Vhost resources.
    """

    resource_name = "vhosts"
    resource_model = Vhost
    resource_url = "/vhosts"

    async def create(self, data: dict[str, Any]) -> Vhost:
        """
        Create a new Vhost (aka Endpoint) for a service.
        """
        service_id = data["service_id"]
        if not service_id:
            raise Exception("A service_id is required.")

        data = {
            "service_id": service_id,
            "type": "http",
            "platform": "alb",
            "load_balancing_algorithm_type": "round_robin",
            "default": True,
            "acme": False,
            "internal": False,
        }

        response = self.api_client.post(f"/services/{service_id}/vhosts", data)
        vhost = self.resource_model.model_validate(response)

        operation_data = {"type": "provision"}
        response = self.api_client.post(
            f"/vhosts/{vhost.id}/operations", operation_data
        )
        self.api_client.wait_for_operation(response["id"])

        return vhost

    async def create_custom_domain(
        self,
        service_id: int,
        domain: str,
        managed_tls: bool = True,
        certificate_fingerprint: str | None = None,
        endpoint_type: str = "http",
        container_ports: list[int] | None = None,
    ) -> Vhost:
        """
        Create a custom domain endpoint for a service with managed TLS or custom cert.
        """
        if not service_id:
            raise ValueError("A service_id is required.")

        if managed_tls:
            clean_domain = domain.strip().lower()
            parts = clean_domain.split(".")
            if clean_domain.startswith("*") or len(parts) <= 2:
                raise ValueError(
                    f"Managed TLS is not supported for apex or wildcard domains: {domain}"
                )

        if endpoint_type == "tls" and not certificate_fingerprint:
            raise ValueError(
                "A certificate reference (certificate_fingerprint) is required for TLS endpoints."
            )

        payload: dict[str, Any] = {
            "service_id": service_id,
            "type": endpoint_type,
            "platform": "alb" if endpoint_type in ("http", "grpc") else "elb",
            "user_domain": domain,
        }

        if managed_tls:
            payload["acme"] = True
        else:
            payload["acme"] = False
            if certificate_fingerprint:
                payload["certificate_fingerprint"] = certificate_fingerprint

        if container_ports is not None:
            payload["container_ports"] = container_ports

        response = self.api_client.post(f"/services/{service_id}/vhosts", payload)
        vhost = self.resource_model.model_validate(response)

        res = await self._run_operation(
            vhost.id, f"/vhosts/{vhost.id}/operations", "provision"
        )
        return res or vhost

    async def create_database_endpoint(
        self,
        database_id: int,
        internal: bool = False,
        ip_whitelist: list[str] | None = None,
    ) -> Vhost:
        """
        Create a database endpoint.
        """
        if not database_id:
            raise ValueError("A database_id is required.")

        database_data = self.api_client.get(f"/databases/{database_id}")
        vhosts_href = None
        if isinstance(database_data, dict):
            links = database_data.get("_links") or database_data.get("links", {})
            if isinstance(links, dict) and "vhosts" in links:
                vhosts_href = links["vhosts"].get("href")

        if not vhosts_href:
            raise ValueError(
                f"Database {database_id} does not expose the required vhosts relation."
            )

        payload: dict[str, Any] = {
            "type": "tcp",
            "platform": "elb",
            "internal": internal,
        }
        if ip_whitelist is not None:
            payload["ip_whitelist"] = ip_whitelist

        response = self.api_client.post(vhosts_href, payload)
        vhost = self.resource_model.model_validate(response)

        res = await self._run_operation(
            vhost.id, f"/vhosts/{vhost.id}/operations", "provision"
        )
        return res or vhost

    async def modify(self, vhost_id: int, **fields: Any) -> Vhost:
        """
        Modify an existing endpoint.
        """
        response = self.api_client.put(f"/vhosts/{vhost_id}", fields)
        return self.resource_model.model_validate(response)

    async def renew(self, vhost_id: int) -> Vhost:
        """
        Trigger a TLS renewal for a managed-TLS app endpoint.
        """
        res = await self._run_operation(
            vhost_id, f"/vhosts/{vhost_id}/operations", "renew"
        )
        if res is None:
            res = await self.get_by_id(vhost_id)
        if res is None:
            raise Exception(f"No vhost found with id {vhost_id}")
        return res

    async def list_by_service(self, service_id: int) -> List[Vhost]:
        """
        List all vhosts for a specific service.
        """
        response = self.api_client.get(
            f"/services/{service_id}/vhosts?per_page=5000&no_embed=true"
        )
        items = response["_embedded"][self.resource_name]
        return [self.resource_model.model_validate(item) for item in items]

    async def delete_vhost(self, vhost_id: int) -> None:
        """
        Delete a vhost by ID.
        """
        vhost = await self.get_by_id(vhost_id)
        if not vhost:
            raise Exception(f"No vhost found with id {vhost_id}")

        operation_data = {"type": "deprovision"}
        response = self.api_client.post(
            f"/vhosts/{vhost_id}/operations", operation_data
        )
        self.api_client.wait_for_operation(response["id"])
