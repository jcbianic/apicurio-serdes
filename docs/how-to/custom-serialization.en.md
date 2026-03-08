# Custom Serialization with `to_dict`

By default, `AvroSerializer` expects a plain Python `dict` as input. If your application uses dataclasses, Pydantic models, or other domain objects, pass a `to_dict` callable to convert them before Avro encoding.

## The `to_dict` Signature

```python
def to_dict(data: Any, ctx: SerializationContext) -> dict[str, Any]:
    ...
```

The callable receives two arguments:

- **`data`** — the object you passed to the serializer
- **`ctx`** — the `SerializationContext` with `topic` and `field` metadata

It must return a plain `dict` whose keys and values match the Avro schema.

## With Dataclasses

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

## With Pydantic Models

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

event = UserEvent(userId="abc-123", country="FR")
payload = serializer(event, ctx)
```

## Context-Aware Hooks

The `ctx` parameter carries the topic name and field type (`KEY` or `VALUE`). Use it when a single hook needs to behave differently depending on the context:

```python
from apicurio_serdes.serialization import MessageField

def to_dict(obj, ctx):
    d = obj.model_dump()
    if ctx.field == MessageField.KEY:
        # For message keys, only include the identifier
        return {"userId": d["userId"]}
    return d

serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    to_dict=to_dict,
)
```

## When to Use It

Use `to_dict` when:

- Your data is not already a `dict` (dataclasses, Pydantic models, attrs classes)
- You need to transform or filter fields before serialization
- You need different serialization logic for keys vs values

Skip `to_dict` when your data is already a plain `dict` that matches the schema.

## Error Handling

If the `to_dict` callable raises any exception, `AvroSerializer` wraps it in a `SerializationError` with the original exception preserved as `__cause__`:

```python
from apicurio_serdes._errors import SerializationError

try:
    payload = serializer(bad_data, ctx)
except SerializationError as e:
    print(f"to_dict failed: {e.cause}")
    # e.__cause__ is the original exception
```

This distinguishes hook failures from Avro schema validation errors (which raise `ValueError`).
