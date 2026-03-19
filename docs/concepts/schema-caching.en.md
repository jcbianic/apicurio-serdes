# Schema Caching

`apicurio-serdes` caches schemas after the first fetch so that subsequent serialization calls do not make HTTP
requests. This page explains how schema caching works and what to expect from its behaviour.

## How the Cache Works

When you call a serializer for the first time, it asks the `ApicurioRegistryClient` to fetch the schema from the
registry. The client stores the result as a `CachedSchema` — a frozen (immutable) dataclass — in an in-memory cache
keyed by `(group_id, artifact_id)`. Freezing the cached entry prevents accidental mutation of shared schema data.

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

The cache lives for the lifetime of the `ApicurioRegistryClient` instance. By default there is no TTL (time-to-live)
or expiration — once a schema is cached, it stays cached until the client is garbage-collected or the entry is evicted
by the LRU policy.

Artifact-based lookups (`get_schema`, `register_schema`) can be given a configurable TTL via `cache_ttl_seconds`.
After the TTL elapses, the next call re-fetches from the registry and picks up any new schema version automatically.

ID-based lookups (`get_schema_by_global_id`, `get_schema_by_content_id`) are content-addressed and immutable — a
`globalId` or `contentId` always refers to the same schema content. These entries never expire regardless of
`cache_ttl_seconds`.

This means:

- **Within a long-running process** (e.g., a Kafka consumer loop), schemas are fetched once at startup and never
  again (unless TTL is set or they are evicted by the LRU policy).
- **If a schema changes in the registry** and no TTL is configured, the running client will not see the new version
  until restarted. With `cache_ttl_seconds` set, the client picks up new versions automatically after each TTL window.

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

## Cache Eviction and Size Limits

Two constructor parameters control cache behaviour:

- `cache_max_size` (default `1000`): maximum number of entries in each cache. When the limit is reached, the
  least-recently-used entry is evicted to make room for new entries (LRU policy). Applies to both the schema cache
  and the ID cache.
- `cache_ttl_seconds` (default `None`): optional TTL in seconds for artifact-based schema cache entries. After this
  duration, the cached entry is treated as a miss and the registry is re-fetched. ID-based cache entries never expire.

```python
from apicurio_serdes import ApicurioRegistryClient

# Limit both caches to 500 entries and re-fetch artifact schemas every 5 minutes
client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",
    cache_max_size=500,
    cache_ttl_seconds=300,
)
```

Both parameters raise `ValueError` on invalid values: `cache_max_size` must be at least `1`;
`cache_ttl_seconds` must be `None` or strictly positive.

## Cache Sharing

Multiple serializers that share the same `ApicurioRegistryClient` instance also share the cache. If two serializers
use the same `artifact_id`, the schema is fetched once:

```python
# Same client → same cache → one HTTP request for "UserEvent"
ser1 = AvroSerializer(registry_client=client, artifact_id="UserEvent")
ser2 = AvroSerializer(registry_client=client, artifact_id="UserEvent")
```

If you create separate `ApicurioRegistryClient` instances, each has its own independent cache.

## Thread Safety

The cache is protected by a reentrant lock (`threading.RLock`). Multiple threads can safely call `get_schema`
concurrently:

- If two threads request the same schema simultaneously, only one makes the HTTP request; the other waits on the lock
  and then reads from the cache.
- Read operations on an already-cached schema do not acquire the lock (fast path).

This means you can safely share a single `ApicurioRegistryClient` and its serializers across threads in a
multi-threaded producer.

## When to Create a New Client

Create a new `ApicurioRegistryClient` when:

- **The schema has been updated in the registry** and you need the new version, and no `cache_ttl_seconds` is
  configured. With `cache_ttl_seconds` set, the running client picks up new schema versions automatically after each
  TTL window.
- **You are connecting to a different registry** or switching groups.
- **You want to reset the cache** (e.g., in tests).

In most production scenarios, a single client instance per application is sufficient.
