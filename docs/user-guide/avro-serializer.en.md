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

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `registry_client` | `ApicurioRegistryClient` | required | The registry client to fetch schemas from. |
| `artifact_id` | `str` | `None` | Static artifact ID. Mutually exclusive with `artifact_resolver`. |
| `artifact_resolver` | callable | `None` | Callable `(ctx) -> str` that derives the artifact ID from the serialization context. Mutually exclusive with `artifact_id`. |
| `schema` | `dict` | `None` | Avro schema dict to register. Required when `auto_register=True`; ignored otherwise. |
| `auto_register` | `bool` | `False` | Register `schema` with the registry on first serialize if the artifact is not found (HTTP 404). |
| `if_exists` | `str` | `"RETURN"` | Behaviour when the artifact already exists during auto-registration. One of `"FAIL"`, `"RETURN"`, `"RETURN_OR_UPDATE"`, `"UPDATE"`. |
| `to_dict` | callable | `None` | Converts non-dict input to a dict before encoding. See [Custom Serialization](../how-to/custom-serialization.md). |
| `use_id` | `"globalId"` or `"contentId"` | `"globalId"` | Which schema identifier to embed in the wire format header. See [Choosing Between globalId and contentId](../how-to/identifier-selection.md). |
| `strict` | `bool` | `False` | Reject input fields not present in the schema with `ValueError`. |

## Auto-registration

When `auto_register=True` and the artifact is not found in the registry (HTTP
404), the serializer calls `register_schema` to create the artifact before
serializing:

```python
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    schema={
        "type": "record",
        "name": "UserEvent",
        "namespace": "com.example",
        "fields": [
            {"name": "userId", "type": "string"},
            {"name": "country", "type": "string"},
        ],
    },
    auto_register=True,
)
```

The `if_exists` parameter controls what happens if another process already
registered the artifact concurrently. The default `"RETURN"` returns the
existing artifact without error, which is the safest choice in most cases.

## Exceptions

| Exception | When |
|---|---|
| `SchemaNotFoundError` | The `artifact_id` does not exist in the registry and `auto_register=False`. |
| `SchemaRegistrationError` | `auto_register=True` and the registry returned a 4xx or 5xx error, or the response body is missing the expected IDs. |
| `RegistryConnectionError` | The registry is unreachable (network error). |
| `SerializationError` | The `to_dict` callable raised an exception. |
| `ValueError` | The data does not conform to the Avro schema, strict mode rejected extra fields, or the schema ID exceeds the unsigned 32-bit limit for `CONFLUENT_PAYLOAD` wire format (use `WireFormat.KAFKA_HEADERS` for 64-bit ID support). |
| `RuntimeError` | The underlying registry client has been closed. |

See [Error Handling](../how-to/error-handling.md) for recovery patterns and code examples.

## Further reading

- [Custom Serialization](../how-to/custom-serialization.md) — serializing dataclasses, Pydantic models, and domain objects
- [Choosing Between globalId and contentId](../how-to/identifier-selection.md) — when to change the `use_id` parameter
- [Schema Caching](../concepts/schema-caching.md) — cache lifetime, sharing, and thread safety
- [Wire Format](../concepts/wire-format.md) — byte layout of the serialized output
