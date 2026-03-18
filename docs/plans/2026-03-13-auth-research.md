# Research: Client Authentication (2026-03-13)

## Problem Statement

The registry clients (`ApicurioRegistryClient` and `AsyncApicurioRegistryClient`)
make unauthenticated HTTP calls. The first production deployment requires writing
to a Kafka topic on a GCP staging cluster from Airflow DAGs. The Apicurio registry
may be secured behind Keycloak OIDC. Two auth patterns are needed:

- **Bearer token** — static string or dynamic callable (GCP OIDC identity token)
- **Keycloak OAuth2** — client credentials flow with automatic token refresh

## Requirements

| ID   | Requirement |
|------|-------------|
| R-1  | `auth=` kwarg on both `ApicurioRegistryClient` and `AsyncApicurioRegistryClient` |
| R-2  | `BearerAuth(token="...")` for static tokens |
| R-3  | `BearerAuth(token_provider=callable)` for dynamic tokens (e.g., GCP OIDC) |
| R-4  | `KeycloakAuth(token_url, client_id, client_secret)` for client credentials flow |
| R-5  | `KeycloakAuth` auto-refreshes when token nears expiry (threshold-based) |
| R-6  | Both auth classes work with sync and async clients |
| R-7  | No new runtime dependencies |
| R-8  | 100% test coverage maintained |
| R-9  | Exported from top-level `apicurio_serdes` package |

## Findings

### Relevant Files

| File | Purpose | Key Lines |
|------|---------|-----------|
| `src/apicurio_serdes/_base.py` | Base class: `url`, `group_id`, caches, response parsing | 40–49 |
| `src/apicurio_serdes/_client.py` | Sync client; constructs `httpx.Client(base_url=url)` | 44–46 |
| `src/apicurio_serdes/_async_client.py` | Async client; constructs `httpx.AsyncClient(base_url=url)` | 31–34 |
| `src/apicurio_serdes/__init__.py` | Public exports — needs `BearerAuth`, `KeycloakAuth` added | 17–26 |
| `tests/conftest.py` | `mock_registry` fixture via `respx`; route helpers | 135–139 |
| `tests/test_client.py` | Sync client tests; constructor validation pattern | 264+ |
| `tests/test_async_client.py` | Async client tests; `TestInterfaceParity` at line 196 | 196+ |

### Client Construction Extension Points

Both clients are minimal wrappers: `__init__` calls `super().__init__(url, group_id)`
then constructs the httpx client. Auth needs to be threaded through here:

```python
# _client.py — current
self._http_client = httpx.Client(base_url=url)

# _client.py — after change
self._http_client = httpx.Client(base_url=url, auth=auth)
```

The base class (`_RegistryClientBase`) does **not** need to change. It holds no
HTTP client; auth is purely a transport-layer concern of the subclasses.

### httpx Auth Protocol

httpx provides a generator-based `httpx.Auth` protocol with three methods:

```python
class httpx.Auth:
    def auth_flow(self, request) -> Generator[Request, Response, None]: ...
    def sync_auth_flow(self, request) -> Generator[Request, Response, None]: ...
    async def async_auth_flow(self, request) -> AsyncGenerator[Request, Response]: ...
```

- `sync_auth_flow` is called by `httpx.Client`
- `async_auth_flow` is called by `httpx.AsyncClient`
- By default, both delegate to `auth_flow` if only `auth_flow` is overridden
- **Key**: when `auth_flow` does no I/O (just injects a header), one class serves both clients

**Simple Bearer injection (no I/O, single class works for sync + async):**

```python
class BearerAuth(httpx.Auth):
    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self._get_token()}"
        yield request
```

### Keycloak Token Flow

Endpoint: `POST {token_url}` where `token_url` is the full URL, e.g.
`https://keycloak.example.com/realms/myrealm/protocol/openid-connect/token`.

Request body (`application/x-www-form-urlencoded`):

```text
grant_type=client_credentials&client_id=<id>&client_secret=<secret>
```

Response JSON:

```json
{
  "access_token": "eyJhbGci...",
  "expires_in": 300,
  "token_type": "Bearer"
}
```

No refresh token is issued for client credentials grants — a new token must be
fetched on expiry.

### Token Refresh Pattern

Confluent's production implementation uses a **threshold-based expiry window**:
refresh when less than 20% of the TTL remains (`expires_at - now < 0.2 * expires_in`).
This avoids clock-skew races where a token expires mid-request.

Pattern with double-checked locking:

```python
def _is_expired(self) -> bool:
    if not self._token:
        return True
    return self._expires_at < time.monotonic() + (self._expires_in * 0.2)

def _ensure_token(self) -> None:
    if self._is_expired():
        with self._lock:
            if self._is_expired():   # second check inside lock
                self._fetch_token()
```

### Sync vs Async Duality for KeycloakAuth

`BearerAuth` has no I/O in `auth_flow` → single class with `auth_flow` works.

`KeycloakAuth` must perform an HTTP POST to fetch a token. This creates a duality:

- **Sync client path**: `sync_auth_flow` must use `threading.Lock` and `httpx.Client`
- **Async client path**: `async_auth_flow` must use `asyncio.Lock` and avoid blocking

**Recommended approach — separate `sync_auth_flow` and `async_auth_flow`**:

```python
class KeycloakAuth(httpx.Auth):
    def __init__(self, token_url, client_id, client_secret, scope=None):
        ...
        self._sync_lock = threading.Lock()
        self._async_lock: asyncio.Lock | None = None  # lazily created

    def sync_auth_flow(self, request):
        self._sync_ensure_token()
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request

    async def async_auth_flow(self, request):
        await self._async_ensure_token()
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request
```

`_sync_ensure_token` uses `threading.Lock` + opens a short-lived `httpx.Client`
for the token POST.

`_async_ensure_token` uses `asyncio.Lock` (created lazily on first call to stay
event-loop-safe) + opens a short-lived `httpx.AsyncClient` for the token POST.

**Why lazy async lock?** Although Python ≥ 3.10 allows creating `asyncio.Lock()`
without a running loop, creating it lazily inside `_async_ensure_token` is
the safest pattern and avoids any edge cases when the object is used across
different event loops in tests.

**Alternative — `asyncio.to_thread`**: Run `_sync_fetch_token` in a thread pool
from `_async_ensure_token`. Simpler, but introduces thread-pool overhead on every
token refresh and still requires careful lock handling.

### Test Patterns

The project uses `respx` for HTTP mocking. Auth tests need to:

1. Verify `Authorization: Bearer` header is sent on registry requests
2. For `KeycloakAuth`: mock the token endpoint POST + the registry GET
3. Verify auto-refresh: set `expires_at` in the past, confirm a new token fetch

`respx` can assert on request headers:

```python
route = router.get(url).mock(...)
assert route.calls[0].request.headers["authorization"] == "Bearer test-token"
```

For `KeycloakAuth`, mock the token endpoint separately:

```python
router.post("https://keycloak/token").mock(
    return_value=Response(200, json={"access_token": "tok", "expires_in": 300})
)
```

### External Research Summary

| Topic | Finding | Source |
|-------|---------|--------|
| httpx `auth_flow` | Generator protocol; `sync_auth_flow`/`async_auth_flow` wrap it | httpx docs + source |
| Single class for sync+async | Works when `auth_flow` has no I/O | httpx source `_auth.py` |
| Keycloak endpoint | `POST /realms/{realm}/protocol/openid-connect/token` | Keycloak official docs |
| Token response | `access_token` + `expires_in` (no refresh token) | RFC 6749 §4.4 |
| Threshold refresh | 20% TTL remaining; double-checked lock | Confluent source |
| CUSTOM bearer source | User-supplied callable; Confluent `_CustomOAuthClient` | Confluent source |

### Technical Constraints

- **No new dependencies** — httpx is already a dependency; token fetch uses httpx directly
- **Python ≥ 3.10** — `asyncio.Lock()` safe without running loop; `asyncio.to_thread` available
- **100% coverage** — every branch in both `sync_auth_flow` and `async_auth_flow` must be tested,
  including the token-expired refresh path
- **mypy strict** — `httpx.Auth` subclasses must be properly typed; `token_provider` typed as
  `Callable[[], str]`; async lock typed as `asyncio.Lock | None`
- **Thread-safe sync, coroutine-safe async** — double-checked locking pattern required

## Open Questions

1. Does the staging Apicurio registry actually require auth, or only Kafka does?
   (If registry is open, Bearer/Keycloak support is still correct to ship but not blocking.)
2. What realm name does the backend team use in Keycloak? (Needed for `token_url` in docs/examples.)
3. Should `KeycloakAuth` accept an optional `scope` parameter? (Default: no scope sent.)
4. Should auth errors (e.g., 401 from token endpoint) raise a new `AuthenticationError`,
   or wrap into `RegistryConnectionError`?

## Recommendations

### New module: `src/apicurio_serdes/_auth.py`

```python
class BearerAuth(httpx.Auth):
    def __init__(
        self,
        token: str | None = None,
        token_provider: Callable[[], str] | None = None,
    ) -> None: ...

    def auth_flow(self, request: httpx.Request) -> Generator[...]: ...


class KeycloakAuth(httpx.Auth):
    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str | None = None,
    ) -> None: ...

    def sync_auth_flow(self, request: httpx.Request) -> Generator[...]: ...
    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[...]: ...
```

### Changes to `_client.py` and `_async_client.py`

Add `auth: httpx.Auth | None = None` parameter; pass to `httpx.Client`/`httpx.AsyncClient`.

### Changes to `__init__.py`

Export `BearerAuth` and `KeycloakAuth` from top-level package.

### Test files

- `tests/test_auth.py` — unit tests for `BearerAuth` and `KeycloakAuth` in isolation
  (no real HTTP, mock token endpoint with respx)
- `tests/test_client.py` — add constructor test for `auth=BearerAuth(...)` passed through
- `tests/test_async_client.py` — same parity test
