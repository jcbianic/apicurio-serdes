# Feature Specification: Async Registry Client

**Feature Branch**: `003-async-registry-client`
**Created**: 2026-03-06
**Status**: Draft
**Input**: User description: "003 — ApicurioRegistryClient (async variant). The intent doc calls out sync-first, async-friendly as a design principle. The sync client already underpins the serializer, but the async variant is a first-class MVP deliverable — needed for asyncio-based producers/consumers (FastAPI, etc.). This would expose the same interface backed by an async HTTP client."

## User Stories *(mandatory)*

### User Story 1 - Retrieve a schema asynchronously from the registry (Priority: P1)

As a Python developer building an asyncio-based Kafka producer or consumer (e.g., using FastAPI), I want an async registry client that retrieves Avro schemas from Apicurio Registry without blocking the event loop, so that I can integrate schema-validated serialization into my async application without thread-pool workarounds.

**Why this priority**: This is the core capability. Without async schema retrieval, there is no async client. All other stories depend on this one.

**Independent Test**: Can be fully tested by configuring an async client against a stubbed registry endpoint, calling `await client.get_schema(artifact_id)`, and verifying the returned schema, globalId, and contentId match the expected values.

**Acceptance Scenarios**:

1. **Given** a configured `AsyncApicurioRegistryClient` pointing at a registry that holds a known Avro schema for a given artifact, **When** `await client.get_schema(artifact_id)` is called, **Then** the returned `CachedSchema` contains the parsed schema, the correct `global_id`, and the correct `content_id`.

2. **Given** a configured async client, **When** `get_schema` is called with an artifact ID that does not exist in the registry, **Then** a `SchemaNotFoundError` is raised identifying the missing artifact and group.

3. **Given** a configured async client, **When** `get_schema` is called and the registry is unreachable, **Then** a `RegistryConnectionError` is raised wrapping the underlying network exception and including the registry URL.

---

### User Story 2 - Async schema caching prevents redundant registry lookups (Priority: P2)

As a Python developer running a high-throughput async Kafka producer, I want the async client to cache schemas after the first fetch, so that subsequent serialization calls do not incur additional HTTP round-trips or event-loop stalls.

**Why this priority**: An async client that contacts the registry on every call is unusable in production. Caching is required for real-world viability.

**Independent Test**: Can be fully tested by calling `get_schema` twice for the same artifact and asserting the registry was contacted exactly once.

**Acceptance Scenarios**:

1. **Given** a configured `AsyncApicurioRegistryClient`, **When** `get_schema` is called twice for the same artifact ID, **Then** the registry is contacted exactly once for that schema.

2. **Given** an async client that has already fetched schema A, **When** `get_schema` is called for a different artifact B, **Then** the registry is contacted once for schema B, and schema A is not re-fetched.

---

### User Story 3 - Async client mirrors the sync client interface (Priority: P2)

As a Python developer migrating from the sync client to the async variant, I want the async client to accept the same constructor parameters and expose the same method names as the sync client, so that switching requires only adding `await` and changing the class name.

**Why this priority**: Interface consistency reduces adoption friction and learning curve. Users already familiar with `ApicurioRegistryClient` should feel at home.

**Independent Test**: Can be verified by comparing constructor signatures and method signatures side-by-side and confirming identical parameter names, types, and return types (modulo `Awaitable` wrapping).

**Acceptance Scenarios**:

1. **Given** a developer already using `ApicurioRegistryClient(url=..., group_id=...)`, **When** they switch to `AsyncApicurioRegistryClient(url=..., group_id=...)`, **Then** the constructor accepts the same parameters with the same semantics.

2. **Given** a developer calling `client.get_schema(artifact_id)`, **When** they switch to the async client, **Then** the only change required is `await client.get_schema(artifact_id)`.

---

### User Story 4 - Async client supports context-manager lifecycle (Priority: P3)

As a Python developer using structured resource management in asyncio, I want to use the async client as an async context manager, so that the underlying HTTP connection pool is properly closed when my application shuts down.

**Why this priority**: Context-manager support is a best practice for async resource management and prevents connection leaks in long-running services.

**Independent Test**: Can be fully tested by using `async with AsyncApicurioRegistryClient(...) as client:` and verifying the underlying HTTP client is closed on exit.

**Acceptance Scenarios**:

1. **Given** an `AsyncApicurioRegistryClient`, **When** used with `async with`, **Then** the underlying HTTP connection pool is closed when the block exits.

2. **Given** an `AsyncApicurioRegistryClient` created without a context manager, **When** `await client.aclose()` is called, **Then** the underlying HTTP connection pool is closed.

---

### Edge Cases

- What happens when two concurrent coroutines request the same uncached schema simultaneously? (Cache stampede)
- What happens when the async client is used after its connection pool has been closed?
- What happens when the registry returns an unexpected status code (e.g., 500)?
- What happens when `url` or `group_id` is empty?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The library MUST provide an `AsyncApicurioRegistryClient` that accepts a registry base URL and a `group_id`, and can retrieve Avro schema definitions from the registry by `artifact_id` using async I/O.

- **FR-002**: `AsyncApicurioRegistryClient.get_schema(artifact_id)` MUST be an async method returning a `CachedSchema` containing the parsed schema, `global_id`, and `content_id`.

- **FR-003**: The async client MUST reuse the same `CachedSchema` dataclass as the sync client so that schemas fetched by either client variant are interchangeable.

- **FR-004**: The async client MUST cache retrieved schemas so that repeated calls with the same `artifact_id` do not produce more than one registry request for that schema.

- **FR-005**: When the referenced `artifact_id` is not found in the registry (HTTP 404), the async client MUST raise a `SchemaNotFoundError` identifying the missing artifact and group.

- **FR-006**: When the Apicurio Registry is unreachable due to a network error, the async client MUST raise a `RegistryConnectionError` that wraps the underlying exception and includes the registry URL.

- **FR-007**: The `group_id` MUST be a required configuration parameter of the async client and MUST be applied to every schema lookup.

- **FR-008**: The async client MUST validate that `url` and `group_id` are non-empty at construction time, raising `ValueError` if either is empty.

- **FR-009**: The async client MUST support usage as an async context manager (`async with`) that closes the underlying HTTP connection pool on exit.

- **FR-010**: The async client MUST provide an explicit `aclose()` async method for closing the underlying HTTP connection pool outside of a context manager.

- **FR-011**: The async client MUST be importable from the top-level package alongside the sync client (e.g., `from apicurio_serdes import AsyncApicurioRegistryClient`).

### Non-Functional Requirements

- **NFR-001**: The async client MUST be safe for concurrent use from multiple coroutines within the same event loop. Specifically, concurrent cache population for the same `artifact_id` MUST NOT result in duplicate HTTP requests or cache corruption.

### Key Entities

- **AsyncApicurioRegistryClient**: Async registry accessor. Holds connection configuration (URL, group_id) and a schema cache. Responsible for all asynchronous communication with the registry and for returning schema definitions by artifact identifier.

- **CachedSchema**: Shared value object (same as sync client) holding a resolved schema and registry metadata (schema dict, global_id, content_id).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can retrieve a schema from Apicurio Registry in an async context using `await client.get_schema(artifact_id)` with no blocking calls or thread-pool delegation.

- **SC-002**: The async client reuses the same `CachedSchema` type as the sync client, allowing serializers and deserializers to work with either client variant without modification.

- **SC-003**: Fetching the same schema 1,000 times from the async client results in exactly 1 registry HTTP call (cache hit on all subsequent calls).

- **SC-004**: Constructor parameters, method names, and error types are identical between the sync and async clients, differing only in the async/await calling convention and resource cleanup method names.
