# Authentication

Pass an `auth` argument to either client to connect to a protected registry.
Two handlers are built in: `BearerAuth` for static or provider-supplied tokens,
and `KeycloakAuth` for OAuth2 client credentials against a Keycloak endpoint.

The `auth` parameter is mutually exclusive with `http_client` — if you supply
your own httpx client, configure auth on it directly.

## `BearerAuth` — static or dynamic token

### Static token

```python
from apicurio_serdes import ApicurioRegistryClient, BearerAuth

auth = BearerAuth(token="my-static-token")

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
    auth=auth,
)
```

### Dynamic token (refreshed per request)

Pass a zero-argument callable via `token_provider` instead. It is called on every
request, so it can return a fresh token each time — useful for short-lived credentials
like GCP OIDC identity tokens or Vault leases:

```python
from apicurio_serdes import BearerAuth

auth = BearerAuth(token_provider=lambda: fetch_oidc_token())
```

`token` and `token_provider` are mutually exclusive; exactly one must be supplied.

## `KeycloakAuth` — OAuth2 client credentials

For Keycloak-protected registries, `KeycloakAuth` handles the client credentials
flow including token refresh. Give it a token URL, a client ID, and a secret:

```python
from apicurio_serdes import ApicurioRegistryClient, KeycloakAuth

auth = KeycloakAuth(
    token_url="https://keycloak.example.com/realms/myrealm/protocol/openid-connect/token",
    client_id="my-client",
    client_secret="secret",
    scope="openid",          # optional
)

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
    auth=auth,
)
```

The token is fetched on the first request. After that, `KeycloakAuth` refreshes it
automatically when less than 20% of its TTL remains. The async client gets its own
non-blocking refresh path so it never blocks the event loop.

## Using with `AsyncApicurioRegistryClient`

Both `BearerAuth` and `KeycloakAuth` work unchanged with the async client:

```python
from apicurio_serdes import AsyncApicurioRegistryClient, KeycloakAuth

auth = KeycloakAuth(
    token_url="https://keycloak.example.com/realms/myrealm/protocol/openid-connect/token",
    client_id="my-client",
    client_secret="secret",
)

async with AsyncApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
    auth=auth,
) as client:
    ...
```

## Using a custom `httpx` client (escape hatch)

Neither handler fits? Supply a pre-configured `httpx.Client` via `http_client` instead.
The client is used as-is and `close()` won't touch it:

```python
import httpx
from apicurio_serdes import ApicurioRegistryClient

http_client = httpx.Client(
    headers={"X-Api-Key": "my-api-key"},
    verify="/path/to/custom-ca.pem",
)

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
    http_client=http_client,
)
```

## Error handling

Authentication failures raise `AuthenticationError`:

```python
from apicurio_serdes._errors import AuthenticationError

try:
    payload = serializer(data, ctx)
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
```

See [Error Handling](./error-handling.md#handling-authenticationerror) for
common causes and recovery steps.
