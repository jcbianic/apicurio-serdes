# Addressing Model

Apicurio Registry organizes schemas in a three-level hierarchy: **group**, **artifact**, and **version**. This page explains Apicurio's three-level schema hierarchy and how it differs from Confluent Schema Registry's flat namespace.

## The Hierarchy

```text
Registry
 └── Group (e.g., "com.example.schemas")
      ├── Artifact: "UserEvent"
      │    ├── Version 1  (schema v1)
      │    └── Version 2  (schema v2, latest)
      └── Artifact: "OrderEvent"
           └── Version 1  (schema v1, latest)
```

### Group

A logical namespace for a set of related schemas. Groups are similar to packages in Java or modules in Python: they prevent name collisions and provide organisational structure.

Examples:

- `com.example.schemas` — all schemas for one team or domain
- `payments` — schemas related to the payments service
- `default` — the fallback group when none is specified

### Artifact

A named schema within a group. Each artifact has a unique `artifact_id` within its group. An artifact can have multiple versions as the schema evolves.

### Version

A specific revision of an artifact. Versions are numbered sequentially (`1`, `2`, `3`, ...). The `latest` alias always points to the most recent version.

## Why `group_id` Is Required

In `apicurio-serdes`, the `group_id` is a **required parameter** on `ApicurioRegistryClient`:

```python
client = ApicurioRegistryClient(
    url="http://registry:8080/apis/registry/v3",
    group_id="com.example.schemas",  # Required
)
```

This is because Apicurio's v3 REST API includes the group in every artifact URL:

```text
GET /groups/{groupId}/artifacts/{artifactId}/versions/latest/content
```

Without a group, the API call cannot be constructed. Every schema lookup needs to know which group to search in.

## Comparison with Confluent Schema Registry

Confluent Schema Registry uses a flat namespace with no group concept:

| Concept | Confluent Schema Registry | Apicurio Registry |
|---------|--------------------------|-------------------|
| Namespace | None (flat) | Group |
| Schema identifier | Subject (e.g., `user-events-value`) | Group + Artifact (e.g., `com.example.schemas` / `UserEvent`) |
| Naming convention | `<topic>-<key\|value>` | Free-form within a group |
| Multi-tenancy | Separate registries | Groups within one registry |

### Mapping Confluent Subjects to Apicurio

When migrating from Confluent Schema Registry to Apicurio, you need to decide:

1. **Which group** to place your schemas in (e.g., `com.example.schemas`)
2. **What artifact ID** to use for each schema

Common mapping patterns:

| Confluent subject | Apicurio group | Apicurio artifact |
|-------------------|---------------|-------------------|
| `user-events-value` | `com.example.schemas` | `UserEvent` |
| `order-events-value` | `com.example.schemas` | `OrderEvent` |
| `user-events-key` | `com.example.schemas` | `UserEventKey` |

In Confluent, the subject name encodes both the schema identity and the topic binding in one string. In Apicurio, these are separate concepts: the artifact ID is the schema identity, and the topic binding happens at the application level.

## How `apicurio-serdes` Uses the Hierarchy

When you create a serializer:

```python
serializer = AvroSerializer(
    registry_client=client,       # client knows group_id
    artifact_id="UserEvent",      # artifact within that group
)
```

The serializer resolves the schema by calling:

```text
GET /groups/com.example.schemas/artifacts/UserEvent/versions/latest/content
```

The response includes both a `globalId` and a `contentId` in the HTTP headers. The serializer uses one of these (configurable via `use_id`) in the [wire format](wire-format.md) header.
