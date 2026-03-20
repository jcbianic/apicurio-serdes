# Error Handling

`apicurio-serdes` raises specific exception types for each failure mode, plus standard
Python exceptions for validation errors.

## Exception Overview

| Exception | When it is raised | Key attributes |
|-----------|-------------------|----------------|
| `SchemaNotFoundError` | The artifact or schema ID does not exist in the registry (HTTP 404) | `group_id`, `artifact_id` or `id_type`, `id_value` |
| `RegistryConnectionError` | The registry is unreachable (network error) | `url` |
| `SchemaRegistrationError` | The registry rejected a schema registration request (4xx/5xx or bad response body) | `artifact_id`, `cause` |
| `SerializationError` | The `to_dict` callable raised an exception | `cause` |
| `ResolverError` | The `artifact_resolver` callable raised an exception or returned a non-string | `cause` |
| `DeserializationError` | Wire format invalid, Avro decode failure, or `from_dict` hook failure | `cause` |
| `AuthenticationError` | The token endpoint is unreachable, returned a non-200 response, or the response body is malformed | — |
| `RuntimeError` | The registry client has been closed | — |
| `ValueError` | Schema ID exceeds 32-bit limit (CONFLUENT_PAYLOAD), or registry response IDs outside int64 range | — |

All custom exceptions are importable from `apicurio_serdes._errors`.

## Handling `SchemaNotFoundError`

Raised when the `artifact_id` does not exist in the specified group.

```python
from apicurio_serdes._errors import SchemaNotFoundError

try:
    payload = serializer(data, ctx)
except SchemaNotFoundError as e:
    print(f"Schema not found: group={e.group_id}, artifact={e.artifact_id}")
```

**Common causes:**

- The artifact ID is misspelled or has the wrong case (`UserEvent` vs `userevent`)
- The schema is in a different group than the one configured on the client
- The schema has not been registered yet

**Recovery:** Verify the artifact exists in the registry:

```bash
curl "http://localhost:8080/apis/registry/v3/groups/com.example.schemas/artifacts"
```

## Handling `RegistryConnectionError`

Raised when the registry is unreachable — the HTTP request failed before getting a response.

```python
from apicurio_serdes._errors import RegistryConnectionError

try:
    payload = serializer(data, ctx)
except RegistryConnectionError as e:
    print(f"Registry unreachable at {e.url}")
    # e.__cause__ is the underlying httpx.ConnectError
```

**Common causes:**

- The registry is down or not yet started
- The URL is wrong (missing `/apis/registry/v3` path)
- A firewall or network issue is blocking the connection

**Built-in retry:** Both clients retry automatically on transient failures — no
manual retry loop is needed. Configure the retry behaviour at construction time:

```python
from apicurio_serdes import ApicurioRegistryClient

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="my-group",
    max_retries=3,               # default — set to 0 to disable
    retry_backoff_ms=1000,       # base delay for the first retry (ms)
    retry_max_backoff_ms=20000,  # maximum backoff cap (ms)
)
```

Retry covers `httpx.TransportError` (network-level failure) and HTTP responses
with status 429, 502, 503, and 504 (transient server errors). After all retries
are exhausted, `RegistryConnectionError` is raised.

**Do not** wrap calls in an additional retry loop — that would multiply the
effective retry count and interfere with the built-in backoff.

Note: this exception is only raised on the **first** serialization call (when the schema
is fetched). Once the schema is cached, no further HTTP requests are made, so network
errors cannot occur during serialization.

## Handling `SerializationError`

Raised when the `to_dict` callable raises an exception during conversion.

```python
from apicurio_serdes._errors import SerializationError

try:
    payload = serializer(data, ctx)
except SerializationError as e:
    print(f"to_dict conversion failed: {e.cause}")
    # e.cause is the original exception from your to_dict callable
    # e.__cause__ is also set for traceback chaining
```

**Common causes:**

- The `to_dict` callable received an unexpected input type
- The callable tried to access an attribute that doesn't exist on the input object
- A Pydantic validation error occurred inside `model_dump()`

**Recovery:** Fix the `to_dict` implementation or validate input data before serialization.

## Handling `ValueError`

Raised by the underlying Avro encoder (fastavro) when the data does not match the schema.
This is **not** an `apicurio-serdes` exception — it comes from fastavro directly.

```python
try:
    payload = serializer(data, ctx)
except ValueError as e:
    print(f"Data does not match schema: {e}")
```

If `strict=True` is enabled on the serializer, `ValueError` is also raised when the data
contains extra fields not defined in the schema.

**Recovery:** Ensure the data dictionary has all required fields with the correct types.

## Handling `RuntimeError` (Closed Client)

Raised when you call a method on a registry client that has already been closed.

```python
try:
    payload = serializer(data, ctx)
except RuntimeError as e:
    if "closed" in str(e):
        print("Client was closed — create a new client instance")
```

**Common causes:**

- Calling `close()` or exiting a context manager, then reusing the same client
- Sharing a client across threads/coroutines where one path closes it prematurely

**Recovery:** Create a new `ApicurioRegistryClient` or `AsyncApicurioRegistryClient` instance.

## Handling `ValueError` (Validation)

In addition to Avro schema validation errors from fastavro, `ValueError` is raised in two new situations:

- **32-bit schema ID overflow**: When using `CONFLUENT_PAYLOAD` wire format, the schema
  ID must fit in an unsigned 32-bit integer. If the registry-assigned ID exceeds this
  limit, use `WireFormat.KAFKA_HEADERS` instead.
- **int64 range validation**: When registry response headers contain a `globalId` or
  `contentId` outside the signed 64-bit integer range.

```python
try:
    payload = serializer(data, ctx)
except ValueError as e:
    if "32-bit" in str(e):
        print("Schema ID too large for CONFLUENT_PAYLOAD — switch to KAFKA_HEADERS")
    else:
        print(f"Data does not match schema: {e}")
```

If `strict=True` is enabled on the serializer, `ValueError` is also raised when the data
contains extra fields not defined in the schema.

**Recovery:** Ensure the data dictionary has all required fields with the correct types,
or switch wire format for large schema IDs.

## Handling `SchemaRegistrationError`

Raised when `auto_register=True` and the registry rejects the registration request
(4xx or 5xx response, or the response body is missing the expected IDs).

```python
from apicurio_serdes._errors import SchemaRegistrationError

try:
    payload = serializer(data, ctx)
except SchemaRegistrationError as e:
    print(f"Registration failed for '{e.artifact_id}': {e.cause}")
    # e.__cause__ is also set for traceback chaining
```

**Common causes:**

- `if_exists="FAIL"` and the artifact already exists in the registry
- The registry rejected the schema content (schema validation error)
- The registry returned an unexpected response body

**Recovery:** Check `e.cause` for the registry error message. If the artifact already
exists and `FAIL` is too strict, switch to `if_exists="FIND_OR_CREATE_VERSION"`.

## Handling `ResolverError`

Raised when `artifact_resolver` raises an exception or returns something other than
a non-empty string.

```python
from apicurio_serdes._errors import ResolverError

try:
    payload = serializer(data, ctx)
except ResolverError as e:
    print(f"Resolver failed: {e}")
    if e.cause:
        print(f"Caused by: {e.cause}")
```

**Common causes:**

- The resolver raised an unhandled exception
- The resolver returned `None` or `""` instead of an artifact ID

**Recovery:** Fix the resolver implementation to always return a non-empty string.

## Handling `AuthenticationError`

Raised by `KeycloakAuth` when the token endpoint is unreachable, returns a non-200
response, or returns a body missing `access_token` or `expires_in`.

```python
from apicurio_serdes._errors import AuthenticationError

try:
    payload = serializer(data, ctx)
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
```

**Common causes:**

- The `token_url` is incorrect or the Keycloak realm does not exist
- The `client_id` or `client_secret` are wrong (non-200 response from the token endpoint)
- The token endpoint returned JSON without `access_token` or `expires_in`

**Recovery:** Double-check the `token_url`, `client_id`, and `client_secret` in
`KeycloakAuth`. See [Authentication](../how-to/authentication.md) for examples.

## Putting It All Together

```python
from apicurio_serdes._errors import (
    SchemaNotFoundError,
    RegistryConnectionError,
    SerializationError,
)

try:
    payload = serializer(data, ctx)
except SchemaNotFoundError as e:
    logger.error("Schema %s not found in group %s", e.artifact_id, e.group_id)
    raise
except RegistryConnectionError as e:
    logger.error("Registry unreachable at %s", e.url)
    raise
except SerializationError as e:
    logger.error("to_dict hook failed: %s", e.cause)
    raise
except RuntimeError as e:
    logger.error("Client is closed: %s", e)
    raise
except ValueError as e:
    logger.error("Validation failed: %s", e)
    raise
```
