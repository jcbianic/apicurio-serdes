# Choosing Between `globalId` and `contentId`

`AvroSerializer` embeds a 4-byte schema identifier in every serialized message. You can choose which identifier to use with the `use_id` parameter. This guide explains the tradeoffs.

## The Two Identifiers

Every schema version in Apicurio Registry has two IDs:

| Identifier | What it is | How it is assigned |
|------------|------------|-------------------|
| **globalId** | A unique, auto-incremented integer assigned when an artifact version is created. | Sequential — `1`, `2`, `3`, ... across the entire registry. |
| **contentId** | A content-addressed integer derived from the schema bytes. | Deterministic — two identical schemas always share the same `contentId`. |

Both are returned by the registry in HTTP response headers (`X-Registry-GlobalId` and `X-Registry-ContentId`) and cached by `ApicurioRegistryClient`.

## How to Choose

```python
# Default: use globalId
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    use_id="globalId",
)

# Alternative: use contentId
serializer = AvroSerializer(
    registry_client=client,
    artifact_id="UserEvent",
    use_id="contentId",
)
```

## When to Use `globalId` (Default)

Use `globalId` when:

- You want the **default behavior** — it matches the most common Confluent wire format convention
- Your consumers resolve schemas by version history (most Apicurio and Confluent setups)
- Each schema version should have a **distinct** ID, even if the schema content is identical to a previous version

`globalId` is the safe default. Choose this unless you have a specific reason to use `contentId`.

## When to Use `contentId`

Use `contentId` when:

- Your consumers are configured to resolve schemas by **content hash** rather than version ID
- You want **identical schemas** registered in different groups or as different artifacts to share the same ID in the wire format
- You are using Apicurio's content-based deduplication features

## Producer and consumer must agree

The identifier type is **not encoded in the wire format**. Both `globalId` and `contentId` occupy the same 4 bytes in the message header. The consumer must know which type to expect.

If the producer embeds a `contentId` but the consumer interprets it as a `globalId` (or vice versa), the consumer will fetch the wrong schema or fail to find one at all.

Make sure your producer and consumer configurations agree on which ID type is in use.

## Registry Behavior

When the `ApicurioRegistryClient` fetches a schema, the registry returns **both** IDs in the response headers. The client caches both. The `use_id` parameter only controls which one the serializer writes into the wire format header — it does not affect what the registry returns or how caching works.
