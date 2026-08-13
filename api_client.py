import asyncio
import json
import jwt
import os
import httpx
from pathlib import Path
from time import monotonic
from typing import Any, Dict, Optional, cast
from urllib.parse import ParseResult, urlparse


class AptibleApiClient:
    """
    Aptible API client for making authenticated requests to the API.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        auth_url: Optional[str] = None,
        request_timeout_seconds: float = 30.0,
        operation_timeout_seconds: float = 1800.0,
        operation_poll_interval_seconds: float = 1.0,
    ) -> None:
        self.api_url: str = (
            api_url
            or os.environ.get("APTIBLE_API_ROOT_URL")
            or "https://api.aptible.com"
        )
        self.auth_url: str = (
            auth_url
            or os.environ.get("APTIBLE_AUTH_ROOT_URL")
            or "https://auth.aptible.com"
        )
        self.request_timeout_seconds = request_timeout_seconds
        self.operation_timeout_seconds = operation_timeout_seconds
        self.operation_poll_interval_seconds = operation_poll_interval_seconds
        self._token: Optional[str] = os.environ.get("APTIBLE_TOKEN", None)
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(request_timeout_seconds),
            follow_redirects=False,
        )

    async def close(self) -> None:
        """Close the reusable asynchronous connection pool."""
        await self._http.aclose()

    def get_token(self) -> str:
        """
        Get authentication token.
        """
        if self._token:
            return self._token

        # Try to get from ~/.aptible/tokens.json file
        home = Path.home()
        try:
            with open(home / ".aptible" / "tokens.json") as f:
                data = json.load(f)
                self._token = data[self.auth_url]
        except (FileNotFoundError, KeyError):
            raise Exception(
                "Authentication token not found. Please login to Aptible CLI first."
            )

        if not self._token:
            raise Exception("You are not logged in")

        return self._token

    async def fetch_public_key(self) -> str:
        """
        Gets the public key used for signing JWTs
        from the Aptible Auth API.
        """
        if not self.auth_url:
            raise ValueError("Auth URL is not set")
        response = await self._http.get(self.auth_url)
        response.raise_for_status()
        public_key = response.json()["public_key"]
        return public_key

    async def parsed_token(self) -> Dict[str, Any]:
        """
        Parse the authentication token.
        """
        token = self.get_token()
        public_key = await self.fetch_public_key()
        return jwt.decode(
            token,
            public_key,
            algorithms=["RS256", "RS512"],
            options={
                "verify_signature": True,
                "verify_exp": True,
            },
            leeway=0,
        )

    async def organization_id(self) -> str:
        """
        Get the organization ID for the logged in user.
        Since users may be a member of multiple orgs (but basically none are), we always choose
        the first organization ID.

        This function doesn't really belong with this client,
        it's just here right now because that's where the token is.
        If a better place for this arises, please move it!
        """
        response = await self._http.get(
            f"{self.auth_url}/organizations",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        orgs = response.json()["_embedded"]["organizations"]
        if orgs == 0:
            raise Exception("Logged in user is not a member of any organizations.")
        return orgs[0]["id"]

    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests
        """
        return {
            "Content-Type": "application/hal+json",
            "Authorization": f"Bearer {self.get_token()}",
        }

    def _build_url(self, path: str) -> str:
        """
        Build the full API URL while preventing bearer-token forwarding to a
        different origin through an absolute HAL link.
        """
        base = cast(ParseResult, urlparse(self.api_url))
        candidate = cast(ParseResult, urlparse(path))

        if candidate.netloc and not candidate.scheme:
            raise ValueError("Protocol-relative API URLs are not allowed")

        if candidate.scheme or candidate.netloc:
            if (
                candidate.scheme.lower() not in {"http", "https"}
                or not candidate.netloc
            ):
                raise ValueError(f"Invalid absolute API URL: {path}")
            if self._origin(candidate) != self._origin(base):
                raise ValueError(
                    f"Refusing to send Aptible credentials to a different origin: {path}"
                )
            return path

        return f"{self.api_url.rstrip('/')}/{path.lstrip('/')}"

    @staticmethod
    def _origin(parsed: ParseResult) -> tuple[str, str, int | None]:
        """Return a normalized URL origin, including an effective default port."""
        if not parsed.hostname:
            raise ValueError("API URL must include a hostname")
        port = parsed.port
        if port is None:
            port = {"http": 80, "https": 443}.get(parsed.scheme.lower())
        return parsed.scheme.lower(), parsed.hostname.lower(), port

    async def get(self, path: str) -> Any:
        """
        Make a GET request to Aptible API.
        """
        url = self._build_url(path)
        response = await self._http.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def get_text(self, path: str, *, authenticated: bool = True) -> str:
        """Fetch text, allowing external HTTPS URLs only when credentials are omitted."""
        if authenticated:
            url = self._build_url(path)
            headers = self._get_headers()
        else:
            parsed = cast(ParseResult, urlparse(path))
            if parsed.scheme.lower() != "https" or not parsed.netloc:
                raise ValueError("Unauthenticated external URLs must use HTTPS")
            url = path
            headers = None
        response = await self._http.get(url, headers=headers)
        response.raise_for_status()
        return response.text

    async def post(self, path: str, data: Any) -> Any:
        """
        Make a POST request to Aptible API.
        """
        url = self._build_url(path)
        response = await self._http.post(
            url,
            headers=self._get_headers(),
            json=data,
        )
        response.raise_for_status()
        return response.json()

    async def put(self, path: str, data: Any) -> Any:
        """
        Make a PUT request to Aptible API.
        """
        url = self._build_url(path)
        response = await self._http.put(
            url,
            headers=self._get_headers(),
            json=data,
        )
        response.raise_for_status()
        return response.json()

    async def delete(self, path: str) -> Any:
        """
        Make a DELETE request to Aptible API.
        """
        url = self._build_url(path)
        response = await self._http.delete(url, headers=self._get_headers())
        response.raise_for_status()

        # Some DELETE responses may not return content
        if response.status_code == 204 or not response.content:
            return None

        return response.json()

    async def wait_for_operation(self, operation_id: str) -> None:
        """
        Waits on the operation to reach a completed state
        OR for the operation to be deleted (from a deprovision).
        """
        done_states = ["succeeded", "failed"]
        deadline = monotonic() + self.operation_timeout_seconds
        while True:
            if monotonic() >= deadline:
                raise TimeoutError(
                    f"Operation {operation_id} did not complete within "
                    f"{self.operation_timeout_seconds:g} seconds"
                )
            try:
                response = await self.get(f"/operations/{operation_id}")
            except httpx.HTTPStatusError as e:
                if e.response is not None and e.response.status_code == 404:
                    return None
                raise

            status = response.get("status", "unknown")
            if status in done_states:
                if status == "failed":
                    raise Exception(
                        f"Operation {operation_id} failed: {response.get('message', 'No error message')}"
                    )
                return None

            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Operation {operation_id} did not complete within "
                    f"{self.operation_timeout_seconds:g} seconds"
                )
            await asyncio.sleep(min(self.operation_poll_interval_seconds, remaining))
