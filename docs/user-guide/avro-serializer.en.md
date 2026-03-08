# Avro Serializer

`AvroSerializer` serializes Python data to Confluent-framed Avro bytes, fetching the schema from Apicurio Registry on the first call.

## Basic usage

```python
from apicurio_serdes import ApicurioRegistryClient
from apicurio_serdes.avro import AvroSerializer
from apicurio_serdes.serialization import SerializationContext, MessageField

client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)
serializer = AvroSerializer(registry_client=client, artifact_id="UserEvent")

ctx = SerializationContext(topic="user-events", field=MessageField.VALUE)
payload = serializer({"userId": "abc-123", "country": "FR"}, ctx)
```

## Custom to_dict hook

When your application data is not already a plain dict, pass a `to_dict` callable. It receives `(data, ctx)` and must return a dict conforming to the schema.

**With dataclasses:**

```python
from dataclasses import dataclass, asdict

@dataclass
class UserEvent:
    userId: str
    country: str

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    to_dict=lambda obj, ctx: asdict(obj),
)

event = UserEvent(userId="abc-123", country="FR")
payload = serializer(event, ctx)
```

**With Pydantic models:**

```python
from pydantic import BaseModel

class UserEvent(BaseModel):
    userId: str
    country: str

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    to_dict=lambda obj, ctx: obj.model_dump(),
)
```

**With a context-aware hook** — `ctx` carries the topic name and field (KEY or VALUE), useful when a single hook needs to behave differently per topic:

```python
def to_dict(obj, ctx):
    d = obj.model_dump()
    if ctx.field == MessageField.KEY:
        return {"userId": d["userId"]}
    return d
```

If the `to_dict` callable raises any exception, `AvroSerializer` wraps it in a `SerializationError` with the original exception preserved as `__cause__`.

## Wire format and schema ID

By default the serializer embeds the **globalId** in the wire format header, which is Apicurio's default for the Confluent wire format. You can switch to **contentId** if your consumer expects it:

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    use_id="contentId",   # or "globalId" (default)
)
```

The wire format layout is:

```
Byte 0:    0x00  (magic byte, Confluent convention)
Bytes 1-4: schema ID as 4-byte big-endian unsigned integer
Bytes 5+:  Avro binary payload (schemaless encoding)
```

## Strict mode

By default, extra fields in the input dict that are not in the schema are silently ignored by fastavro. Enable `strict=True` to reject them with a `ValueError`:

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    strict=True,
)

# Raises ValueError: Extra fields not in schema: internalFlag
serializer({"userId": "abc", "country": "FR", "internalFlag": True}, ctx)
```

## Schema caching

`AvroSerializer` fetches the schema once and caches it for the lifetime of the client. Two serializers sharing the same `ApicurioRegistryClient` instance also share the cache:

```python
# Only one HTTP request is made, regardless of how many messages are serialized
for event in events:
    payload = serializer(event, ctx)
```

The cache is keyed by `(group_id, artifact_id)` and is thread-safe.

## Error reference

| Exception | When |
|---|---|
| `SchemaNotFoundError` | The `artifact_id` does not exist in the registry (HTTP 404). |
| `RegistryConnectionError` | The registry is unreachable (network error). |
| `SerializationError` | The `to_dict` callable raised an exception. |
| `ValueError` | The data does not conform to the Avro schema, or strict mode rejected extra fields. |

```python
from apicurio_serdes._errors import SchemaNotFoundError, RegistryConnectionError, SerializationError

try:
    payload = serializer(data, ctx)
except SchemaNotFoundError as e:
    # e.group_id, e.artifact_id
    logger.error("Schema not found: %s / %s", e.group_id, e.artifact_id)
except RegistryConnectionError as e:
    # e.url
    logger.error("Registry unreachable: %s", e.url)
except SerializationError as e:
    # e.cause is the original exception from to_dict
    logger.error("to_dict failed: %s", e.cause)
except ValueError as e:
    logger.error("Schema validation failed: %s", e)
```
