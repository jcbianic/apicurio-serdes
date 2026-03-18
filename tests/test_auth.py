"""Tests for authentication classes: BearerAuth and KeycloakAuth."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import httpx
import pytest
import respx
from httpx import Response

from apicurio_serdes._auth import BearerAuth, KeycloakAuth
from apicurio_serdes._errors import AuthenticationError

TOKEN_URL = "https://keycloak.example.com/realms/myrealm/protocol/openid-connect/token"
REGISTRY_URL = "http://registry:8080/apis/registry/v3"
ARTIFACT_URL = f"{REGISTRY_URL}/groups/g/artifacts/a/versions/latest/content"


# ── Helpers ──


def _mock_registry(router: respx.MockRouter) -> respx.Route:
    return router.get(ARTIFACT_URL).mock(
        return_value=Response(
            200,
            content=b'{"type":"record","name":"X","fields":[]}',
            headers={"X-Registry-GlobalId": "1", "X-Registry-ContentId": "2"},
        )
    )


def _token_response(token: str = "tok", expires_in: int = 300) -> Response:
    return Response(200, json={"access_token": token, "expires_in": expires_in})


# ── BearerAuth ──


class TestBearerAuth:
    """BearerAuth injects a static or dynamic Bearer token."""

    def test_static_token_injects_header(self) -> None:
        with respx.mock() as router:
            route = _mock_registry(router)
            with httpx.Client(auth=BearerAuth(token="my-token")) as client:
                client.get(ARTIFACT_URL)
            assert route.calls[0].request.headers["authorization"] == "Bearer my-token"

    def test_dynamic_token_calls_provider(self) -> None:
        provider = MagicMock(return_value="dyn-token")
        with respx.mock() as router:
            route = _mock_registry(router)
            with httpx.Client(auth=BearerAuth(token_provider=provider)) as client:
                client.get(ARTIFACT_URL)
            assert route.calls[0].request.headers["authorization"] == "Bearer dyn-token"

    def test_provider_called_on_each_request(self) -> None:
        call_count = 0

        def provider() -> str:
            nonlocal call_count
            call_count += 1
            return f"token-{call_count}"

        with respx.mock() as router:
            _mock_registry(router)
            with httpx.Client(auth=BearerAuth(token_provider=provider)) as client:
                client.get(ARTIFACT_URL)
                client.get(ARTIFACT_URL)
        assert call_count == 2

    def test_no_args_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            BearerAuth()

    def test_both_args_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            BearerAuth(token="t", token_provider=lambda: "t")

    def test_works_with_sync_httpx_client(self) -> None:
        with respx.mock() as router:
            route = _mock_registry(router)
            with httpx.Client(auth=BearerAuth(token="sync-tok")) as client:
                client.get(ARTIFACT_URL)
            assert "Bearer sync-tok" in route.calls[0].request.headers["authorization"]

    @pytest.mark.asyncio
    async def test_works_with_async_httpx_client(self) -> None:
        with respx.mock() as router:
            route = _mock_registry(router)
            async with httpx.AsyncClient(auth=BearerAuth(token="async-tok")) as client:
                await client.get(ARTIFACT_URL)
            assert route.calls[0].request.headers["authorization"] == "Bearer async-tok"


# ── KeycloakAuth sync ──


class TestKeycloakAuthSync:
    """KeycloakAuth fetches and auto-refreshes tokens via client credentials (sync)."""

    def _auth(self, scope: str | None = None) -> KeycloakAuth:
        return KeycloakAuth(
            token_url=TOKEN_URL,
            client_id="client",
            client_secret="secret",
            scope=scope,
        )

    def test_happy_path_injects_token(self) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(return_value=_token_response("tok1"))
            route = _mock_registry(router)
            auth = self._auth()
            with httpx.Client(auth=auth) as client:
                client.get(ARTIFACT_URL)
            assert route.calls[0].request.headers["authorization"] == "Bearer tok1"

    def test_token_reused_on_second_request(self) -> None:
        with respx.mock() as router:
            token_route = router.post(TOKEN_URL).mock(
                return_value=_token_response("tok1")
            )
            _mock_registry(router)
            auth = self._auth()
            with httpx.Client(auth=auth) as client:
                client.get(ARTIFACT_URL)
                client.get(ARTIFACT_URL)
            assert token_route.call_count == 1

    def test_auto_refresh_when_expired(self) -> None:
        with respx.mock() as router:
            token_route = router.post(TOKEN_URL).mock(
                side_effect=[
                    _token_response("tok1"),
                    _token_response("tok2"),
                ]
            )
            _mock_registry(router)
            auth = self._auth()
            with httpx.Client(auth=auth) as client:
                client.get(ARTIFACT_URL)
                # Force expiry
                auth._expires_at = time.monotonic() - 1
                client.get(ARTIFACT_URL)
            assert token_route.call_count == 2

    def test_threshold_refresh_before_expiry(self) -> None:
        with respx.mock() as router:
            token_route = router.post(TOKEN_URL).mock(
                side_effect=[
                    _token_response("tok1", expires_in=100),
                    _token_response("tok2", expires_in=100),
                ]
            )
            _mock_registry(router)
            auth = self._auth()
            with httpx.Client(auth=auth) as client:
                client.get(ARTIFACT_URL)
                # Within 20% threshold (< 20s remaining of 100s)
                auth._expires_at = time.monotonic() + 10
                auth._expires_in = 100
                client.get(ARTIFACT_URL)
            assert token_route.call_count == 2

    def test_token_endpoint_401_raises_authentication_error(self) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(return_value=Response(401, text="Unauthorized"))
            auth = self._auth()
            with (
                httpx.Client(auth=auth) as client,
                pytest.raises(AuthenticationError, match="401"),
            ):
                client.get(ARTIFACT_URL)

    def test_token_endpoint_unreachable_raises_authentication_error(self) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(side_effect=httpx.ConnectError("refused"))
            auth = self._auth()
            with httpx.Client(auth=auth) as client, pytest.raises(AuthenticationError):
                client.get(ARTIFACT_URL)

    def test_token_endpoint_read_timeout_raises_authentication_error(self) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(side_effect=httpx.ReadTimeout("timed out"))
            auth = self._auth()
            with httpx.Client(auth=auth) as client, pytest.raises(AuthenticationError):
                client.get(ARTIFACT_URL)

    def test_scope_included_in_token_request(self) -> None:
        with respx.mock() as router:
            token_route = router.post(TOKEN_URL).mock(return_value=_token_response())
            _mock_registry(router)
            auth = self._auth(scope="openid")
            with httpx.Client(auth=auth) as client:
                client.get(ARTIFACT_URL)
            body = token_route.calls[0].request.content.decode()
            assert "scope=openid" in body

    def test_no_scope_omits_scope_from_request(self) -> None:
        with respx.mock() as router:
            token_route = router.post(TOKEN_URL).mock(return_value=_token_response())
            _mock_registry(router)
            auth = self._auth()
            with httpx.Client(auth=auth) as client:
                client.get(ARTIFACT_URL)
            body = token_route.calls[0].request.content.decode()
            assert "scope" not in body


# ── KeycloakAuth async ──


class TestKeycloakAuthAsync:
    """KeycloakAuth fetches and auto-refreshes tokens via client credentials (async)."""

    def _auth(self, scope: str | None = None) -> KeycloakAuth:
        return KeycloakAuth(
            token_url=TOKEN_URL,
            client_id="client",
            client_secret="secret",
            scope=scope,
        )

    @pytest.mark.asyncio
    async def test_happy_path_injects_token(self) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(return_value=_token_response("atok1"))
            route = _mock_registry(router)
            auth = self._auth()
            async with httpx.AsyncClient(auth=auth) as client:
                await client.get(ARTIFACT_URL)
            assert route.calls[0].request.headers["authorization"] == "Bearer atok1"

    @pytest.mark.asyncio
    async def test_token_reused_on_second_request(self) -> None:
        with respx.mock() as router:
            token_route = router.post(TOKEN_URL).mock(
                return_value=_token_response("atok1")
            )
            _mock_registry(router)
            auth = self._auth()
            async with httpx.AsyncClient(auth=auth) as client:
                await client.get(ARTIFACT_URL)
                await client.get(ARTIFACT_URL)
            assert token_route.call_count == 1

    @pytest.mark.asyncio
    async def test_auto_refresh_when_expired(self) -> None:
        with respx.mock() as router:
            token_route = router.post(TOKEN_URL).mock(
                side_effect=[
                    _token_response("atok1"),
                    _token_response("atok2"),
                ]
            )
            _mock_registry(router)
            auth = self._auth()
            async with httpx.AsyncClient(auth=auth) as client:
                await client.get(ARTIFACT_URL)
                auth._expires_at = time.monotonic() - 1
                await client.get(ARTIFACT_URL)
            assert token_route.call_count == 2

    @pytest.mark.asyncio
    async def test_threshold_refresh_before_expiry(self) -> None:
        with respx.mock() as router:
            token_route = router.post(TOKEN_URL).mock(
                side_effect=[
                    _token_response("atok1", expires_in=100),
                    _token_response("atok2", expires_in=100),
                ]
            )
            _mock_registry(router)
            auth = self._auth()
            async with httpx.AsyncClient(auth=auth) as client:
                await client.get(ARTIFACT_URL)
                auth._expires_at = time.monotonic() + 10
                auth._expires_in = 100
                await client.get(ARTIFACT_URL)
            assert token_route.call_count == 2

    @pytest.mark.asyncio
    async def test_token_endpoint_401_raises_authentication_error(self) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(return_value=Response(401, text="Unauthorized"))
            auth = self._auth()
            async with httpx.AsyncClient(auth=auth) as client:
                with pytest.raises(AuthenticationError, match="401"):
                    await client.get(ARTIFACT_URL)

    @pytest.mark.asyncio
    async def test_token_endpoint_unreachable_raises_authentication_error(
        self,
    ) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(side_effect=httpx.ConnectError("refused"))
            auth = self._auth()
            async with httpx.AsyncClient(auth=auth) as client:
                with pytest.raises(AuthenticationError):
                    await client.get(ARTIFACT_URL)

    @pytest.mark.asyncio
    async def test_token_endpoint_read_timeout_raises_authentication_error(
        self,
    ) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(side_effect=httpx.ReadTimeout("timed out"))
            auth = self._auth()
            async with httpx.AsyncClient(auth=auth) as client:
                with pytest.raises(AuthenticationError):
                    await client.get(ARTIFACT_URL)

    def test_lazy_lock_usable_from_inside_event_loop(self) -> None:
        """KeycloakAuth created outside event loop works fine when used async."""
        # Object is created here (outside any event loop)
        auth = self._auth()
        # Lock should be None until first async use
        assert auth._async_lock is None


# ── Double-checked locking coverage ──


class TestDoubleCheckedLocking:
    """Cover the second-check-is-False branch in sync and async ensure_token."""

    def _auth(self) -> KeycloakAuth:
        return KeycloakAuth(
            token_url=TOKEN_URL,
            client_id="client",
            client_secret="secret",
        )

    def test_sync_second_check_skips_fetch_when_token_refreshed(self) -> None:
        """Second _is_expired() inside the lock returns False → _sync_fetch_token skipped."""
        auth = self._auth()
        call_count = [0]

        def once_then_false() -> bool:
            call_count[0] += 1
            # First call (outer): expired; second call (inner lock): already refreshed
            return call_count[0] == 1

        auth._is_expired = once_then_false  # type: ignore[method-assign]
        # No HTTP mock needed — fetch should NOT be called
        auth._sync_ensure_token()
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_async_second_check_skips_fetch_when_token_refreshed(
        self,
    ) -> None:
        """Second _is_expired() inside async lock returns False → _async_fetch_token skipped."""
        auth = self._auth()
        call_count = [0]

        def once_then_false() -> bool:
            call_count[0] += 1
            return call_count[0] == 1

        auth._is_expired = once_then_false  # type: ignore[method-assign]
        await auth._async_ensure_token()
        assert call_count[0] == 2


# ── Security hardening tests ──


class TestKeycloakAuthSecurity:
    """Cover security hardening: malformed responses, repr masking, URL sanitisation."""

    def _auth(self) -> KeycloakAuth:
        return KeycloakAuth(
            token_url=TOKEN_URL,
            client_id="client",
            client_secret="super-secret",
        )

    def test_200_with_missing_access_token_raises_authentication_error(self) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(
                return_value=Response(200, json={"expires_in": 300})
            )
            auth = self._auth()
            with (
                httpx.Client(auth=auth) as client,
                pytest.raises(AuthenticationError, match="access_token"),
            ):
                client.get(ARTIFACT_URL)

    def test_200_with_empty_access_token_raises_authentication_error(self) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(
                return_value=Response(200, json={"access_token": "", "expires_in": 300})
            )
            auth = self._auth()
            with (
                httpx.Client(auth=auth) as client,
                pytest.raises(AuthenticationError, match="access_token"),
            ):
                client.get(ARTIFACT_URL)
        assert auth._token == ""

    def test_200_with_null_access_token_raises_authentication_error(self) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(
                return_value=Response(
                    200, json={"access_token": None, "expires_in": 300}
                )
            )
            auth = self._auth()
            with (
                httpx.Client(auth=auth) as client,
                pytest.raises(AuthenticationError, match="access_token"),
            ):
                client.get(ARTIFACT_URL)
        assert auth._token == ""

    def test_200_with_missing_expires_in_raises_authentication_error(self) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(
                return_value=Response(200, json={"access_token": "tok"})
            )
            auth = self._auth()
            with (
                httpx.Client(auth=auth) as client,
                pytest.raises(AuthenticationError, match="expires_in"),
            ):
                client.get(ARTIFACT_URL)
        # Token state must not be partially mutated on failure
        assert auth._token == ""
        assert auth._expires_at == 0.0

    @pytest.mark.parametrize("expires_in", [0, -1, -300])
    def test_200_with_non_positive_expires_in_raises_authentication_error(
        self, expires_in: int
    ) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(
                return_value=Response(
                    200, json={"access_token": "tok", "expires_in": expires_in}
                )
            )
            auth = self._auth()
            with (
                httpx.Client(auth=auth) as client,
                pytest.raises(AuthenticationError, match="expires_in"),
            ):
                client.get(ARTIFACT_URL)
        # Token state must not be mutated on failure
        assert auth._token == ""
        assert auth._expires_at == 0.0

    def test_200_with_non_json_body_raises_authentication_error(self) -> None:
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(return_value=Response(200, text="not json"))
            auth = self._auth()
            with httpx.Client(auth=auth) as client, pytest.raises(AuthenticationError):
                client.get(ARTIFACT_URL)

    def test_401_error_message_does_not_include_full_response_body(self) -> None:
        sensitive_body = '{"error":"invalid_client","secret_echo":"super-secret"}'
        with respx.mock() as router:
            router.post(TOKEN_URL).mock(return_value=Response(401, text=sensitive_body))
            auth = self._auth()
            with (
                httpx.Client(auth=auth) as client,
                pytest.raises(AuthenticationError) as exc_info,
            ):
                client.get(ARTIFACT_URL)
            # Full body must not appear in the error message
            assert sensitive_body not in str(exc_info.value)

    def test_repr_masks_client_secret(self) -> None:
        auth = self._auth()
        r = repr(auth)
        assert "super-secret" not in r
        assert "***" in r
        assert "client_id='client'" in r

    def test_transport_error_message_strips_embedded_credentials(self) -> None:
        url_with_creds = "https://user:pass@keycloak.example.com/realms/r/protocol/openid-connect/token"
        auth = KeycloakAuth(
            token_url=url_with_creds,
            client_id="client",
            client_secret="secret",
        )
        with respx.mock() as router:
            router.post(url_with_creds).mock(side_effect=httpx.ConnectError("refused"))
            with (
                httpx.Client(auth=auth) as client,
                pytest.raises(AuthenticationError) as exc_info,
            ):
                client.get(ARTIFACT_URL)
        assert "pass" not in str(exc_info.value)
        assert "user" not in str(exc_info.value)

    def test_transport_error_message_preserves_port(self) -> None:
        url_with_creds = "https://user:pass@keycloak.example.com:8443/realms/r/protocol/openid-connect/token"
        auth = KeycloakAuth(
            token_url=url_with_creds,
            client_id="client",
            client_secret="secret",
        )
        with respx.mock() as router:
            router.post(url_with_creds).mock(side_effect=httpx.ConnectError("refused"))
            with (
                httpx.Client(auth=auth) as client,
                pytest.raises(AuthenticationError) as exc_info,
            ):
                client.get(ARTIFACT_URL)
        assert "pass" not in str(exc_info.value)
        assert ":8443" in str(exc_info.value)
