"""Authentication classes for Apicurio registry clients."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import AsyncGenerator, Callable, Generator
from urllib.parse import urlparse, urlunparse

import httpx

from apicurio_serdes._errors import AuthenticationError

__all__ = ["BearerAuth", "KeycloakAuth"]

_REFRESH_THRESHOLD = 0.2  # refresh when < 20% of TTL remains


class BearerAuth(httpx.Auth):
    """Bearer token authentication for Apicurio registry clients.

    Exactly one of *token* or *token_provider* must be supplied.

    Args:
        token: Static Bearer token string.
        token_provider: Zero-argument callable that returns a token string.
            Called on every request, so it can return fresh tokens (e.g.
            GCP OIDC identity tokens retrieved via ``google-auth``).

    Raises:
        ValueError: If neither or both of *token* and *token_provider* are given.

    Example:
        ```python
        # Static token
        auth = BearerAuth(token="my-static-token")

        # Dynamic token (GCP OIDC)
        auth = BearerAuth(token_provider=lambda: get_google_id_token())

        client = ApicurioRegistryClient(url="...", group_id="...", auth=auth)
        ```
    """

    def __init__(
        self,
        token: str | None = None,
        token_provider: Callable[[], str] | None = None,
    ) -> None:
        if (token is None) == (token_provider is None):
            raise ValueError(
                "BearerAuth requires exactly one of 'token' or 'token_provider'."
            )
        self._token = token
        self._token_provider = token_provider

    def _get_token(self) -> str:
        if self._token_provider is not None:
            return self._token_provider()
        return self._token  # type: ignore[return-value]

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        """Inject Authorization header; works for both sync and async clients."""
        request.headers["Authorization"] = f"Bearer {self._get_token()}"
        yield request


class KeycloakAuth(httpx.Auth):
    """OAuth2 client credentials auth against a Keycloak token endpoint.

    Fetches a token on first use and automatically refreshes it when
    less than 20% of its TTL remains (threshold-based refresh).

    Implements separate ``sync_auth_flow`` / ``async_auth_flow`` so that
    async callers never block the event loop.

    Args:
        token_url: Full URL of the Keycloak token endpoint, e.g.
            ``"https://keycloak.example.com/realms/myrealm/protocol/openid-connect/token"``.
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret.
        scope: Optional OAuth2 scope string (e.g. ``"openid"``).

    Raises:
        AuthenticationError: If the token endpoint is unreachable or returns
            a non-200 response.

    Example:
        ```python
        auth = KeycloakAuth(
            token_url="https://keycloak.example.com/realms/myrealm/protocol/openid-connect/token",
            client_id="my-client",
            client_secret="secret",
        )
        client = ApicurioRegistryClient(url="...", group_id="...", auth=auth)
        ```
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str | None = None,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope

        self._token: str = ""
        self._expires_at: float = 0.0
        self._expires_in: float = 0.0

        self._sync_lock = threading.Lock()
        self._async_lock: asyncio.Lock | None = None

    def __repr__(self) -> str:
        return (
            f"KeycloakAuth(token_url={self._token_url!r}, "
            f"client_id={self._client_id!r}, client_secret=***)"
        )

    # ── Shared helpers ──

    def _is_expired(self) -> bool:
        if not self._token:
            return True
        return (
            self._expires_at < time.monotonic() + self._expires_in * _REFRESH_THRESHOLD
        )

    def _build_token_data(self) -> dict[str, str]:
        data: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        if self._scope is not None:
            data["scope"] = self._scope
        return data

    @staticmethod
    def _safe_url(url: str) -> str:
        """Strip userinfo from a URL to avoid leaking embedded credentials."""
        parsed = urlparse(url)
        return urlunparse(parsed._replace(netloc=parsed.hostname or ""))

    def _parse_token_response(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Limit error text to avoid leaking secrets from non-standard IdP responses
            try:
                error_detail = response.json().get("error", response.status_code)
            except Exception:
                error_detail = response.status_code
            raise AuthenticationError(
                f"Token endpoint returned {response.status_code}: {error_detail}"
            ) from exc
        try:
            payload = response.json()
            self._token = payload["access_token"]
            self._expires_in = float(payload["expires_in"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError(
                f"Unexpected token endpoint response (missing access_token or expires_in): {exc}"
            ) from exc
        self._expires_at = time.monotonic() + self._expires_in

    # ── Sync path ──

    def _sync_fetch_token(self) -> None:
        try:
            with httpx.Client() as client:
                response = client.post(self._token_url, data=self._build_token_data())
        except httpx.TransportError as exc:
            raise AuthenticationError(
                f"Could not reach token endpoint {self._safe_url(self._token_url)}: {exc}"
            ) from exc
        self._parse_token_response(response)

    def _sync_ensure_token(self) -> None:
        if self._is_expired():
            with self._sync_lock:
                if self._is_expired():
                    self._sync_fetch_token()

    def sync_auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        """Sync auth flow: ensure token, inject header."""
        self._sync_ensure_token()
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request

    # ── Async path ──

    def _get_async_lock(self) -> asyncio.Lock:
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    async def _async_fetch_token(self) -> None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._token_url, data=self._build_token_data()
                )
        except httpx.TransportError as exc:
            raise AuthenticationError(
                f"Could not reach token endpoint {self._safe_url(self._token_url)}: {exc}"
            ) from exc
        self._parse_token_response(response)

    async def _async_ensure_token(self) -> None:
        if self._is_expired():
            async with self._get_async_lock():
                if self._is_expired():
                    await self._async_fetch_token()

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        """Async auth flow: ensure token without blocking, inject header."""
        await self._async_ensure_token()
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request
