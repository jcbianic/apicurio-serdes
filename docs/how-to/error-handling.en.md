# Error Handling

`apicurio-serdes` raises specific exception types for each failure mode, plus standard Python exceptions for validation errors.

## Exception Overview

| Exception | When it is raised | Key attributes |
|-----------|-------------------|----------------|
| `SchemaNotFoundError` | The artifact or schema ID does not exist in the registry (HTTP 404) | `group_id`, `artifact_id` or `id_type`, `id_value` |
| `RegistryConnectionError` | The registry is unreachable (network error) | `url` |
| `SerializationError` | The `to_dict` callable raised an exception | `cause` |
| `DeserializationError` | Wire format invalid, Avro decode failure, or `from_dict` hook failure | `cause` |
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

**Recovery pattern — retry with backoff:**

```python
import time
from apicurio_serdes._errors import RegistryConnectionError

max_retries = 3
for attempt in range(max_retries):
    try:
        payload = serializer(data, ctx)
        break
    except RegistryConnectionError:
        if attempt == max_retries - 1:
            raise
        time.sleep(2 ** attempt)
```

Note: this exception is only raised on the **first** serialization call (when the schema is fetched). Once the schema is cached, no further HTTP requests are made, so network errors cannot occur during serialization.

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

Raised by the underlying Avro encoder (fastavro) when the data does not match the schema. This is **not** an `apicurio-serdes` exception — it comes from fastavro directly.

```python
try:
    payload = serializer(data, ctx)
except ValueError as e:
    print(f"Data does not match schema: {e}")
```

If `strict=True` is enabled on the serializer, `ValueError` is also raised when the data contains extra fields not defined in the schema.

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

- **32-bit schema ID overflow**: When using `CONFLUENT_PAYLOAD` wire format, the schema ID must fit in an unsigned 32-bit integer. If the registry-assigned ID exceeds this limit, use `WireFormat.KAFKA_HEADERS` instead.
- **int64 range validation**: When registry response headers contain a `globalId` or `contentId` outside the signed 64-bit integer range.

```python
try:
    payload = serializer(data, ctx)
except ValueError as e:
    if "32-bit" in str(e):
        print("Schema ID too large for CONFLUENT_PAYLOAD — switch to KAFKA_HEADERS")
    else:
        print(f"Data does not match schema: {e}")
```

If `strict=True` is enabled on the serializer, `ValueError` is also raised when the data contains extra fields not defined in the schema.

**Recovery:** Ensure the data dictionary has all required fields with the correct types, or switch wire format for large schema IDs.

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
