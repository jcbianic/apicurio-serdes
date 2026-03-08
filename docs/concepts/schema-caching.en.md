# Schema Caching

`apicurio-serdes` caches schemas after the first fetch so that subsequent serialization calls do not make HTTP requests. This page explains when the cache is populated, how long it lasts, and what guarantees it provides.

## How the Cache Works

When you call a serializer for the first time, it asks the `ApicurioRegistryClient` to fetch the schema from the registry. The client stores the result in an in-memory cache keyed by `(group_id, artifact_id)`.

```text
First call:

  serializer(data, ctx)
       │
       ▼
  ApicurioRegistryClient.get_schema("UserEvent")
       │
       ├── Cache miss → HTTP GET /groups/.../artifacts/UserEvent/versions/latest/content
       │                  └── Store result in cache
       │
       └── Return CachedSchema (schema dict + globalId + contentId)


Subsequent calls:

  serializer(data, ctx)
       │
       ▼
  ApicurioRegistryClient.get_schema("UserEvent")
       │
       └── Cache hit → Return immediately (no HTTP request)
```

## Cache Lifetime

The cache lives for the lifetime of the `ApicurioRegistryClient` instance. There is no TTL (time-to-live) or expiration — once a schema is cached, it stays cached until the client is garbage-collected.

This means:

- **Within a long-running process** (e.g., a Kafka consumer loop), schemas are fetched once at startup and never again.
- **If a schema changes in the registry**, the running client will not see the new version. To pick up schema changes, create a new `ApicurioRegistryClient` instance.

```python
# Schema cached for the lifetime of this client
client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
)

# All serializers sharing this client share the same cache
serializer_a = AvroSerializer(registry_client=client, artifact_id="UserEvent")
serializer_b = AvroSerializer(registry_client=client, artifact_id="OrderEvent")

# Only 2 HTTP requests total, regardless of how many messages are serialized
for event in events:
    serializer_a(event, ctx)
```

## Cache Sharing

Multiple serializers that share the same `ApicurioRegistryClient` instance also share the cache. If two serializers use the same `artifact_id`, the schema is fetched once:

```python
# Same client → same cache → one HTTP request for "UserEvent"
ser1 = AvroSerializer(registry_client=client, artifact_id="UserEvent")
ser2 = AvroSerializer(registry_client=client, artifact_id="UserEvent")
```

If you create separate `ApicurioRegistryClient` instances, each has its own independent cache.

## Thread Safety

The cache is protected by a reentrant lock (`threading.RLock`). Multiple threads can safely call `get_schema` concurrently:

- If two threads request the same schema simultaneously, only one makes the HTTP request; the other waits on the lock and then reads from the cache.
- Read operations on an already-cached schema do not acquire the lock (fast path).

This means you can safely share a single `ApicurioRegistryClient` and its serializers across threads in a multi-threaded producer.

## When to Create a New Client

Create a new `ApicurioRegistryClient` when:

- **The schema has been updated in the registry** and you need the new version.
- **You are connecting to a different registry** or switching groups.
- **You want to reset the cache** (e.g., in tests).

In most production scenarios, a single client instance per application is sufficient.
