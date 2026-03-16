# Plan: Auto-Register Schemas on Serialization (Issue #36) — 2026-03-16

## Summary

Add opt-in schema auto-registration to `AvroSerializer`: when `auto_register=True`
and the registry returns a 404 on first serialize, the serializer calls a new
`register_schema()` method on both `ApicurioRegistryClient` and
`AsyncApicurioRegistryClient` to POST the supplied local schema and cache the
resulting `CachedSchema`. Auto-registration is disabled by default (Constitution
Principle V), requires a `schema` kwarg to be supplied at construction time
(validated eagerly, Constitution Principle III), and is gated by a new
`SchemaRegistrationError` that wraps any 4xx/5xx response from the registration
endpoint. No existing public API signatures are broken.

## Stakes Classification

**Level**: Medium

**Rationale**: Three existing modules are modified (both clients and the serializer),
one new error class is added, and the public API surface grows. The serializer's
lazy-fetch hot path is touched — a regression here breaks all serialization. The
change is fully additive (new parameters default to the current behaviour), so
rollback is a straight revert with no migration concerns. 100% branch coverage and
mypy strict are required throughout.

## Context

**Worktree**: `.worktrees/feat-auto-register-36/` on branch `feat/auto-register-36`

**Affected files**:

- `src/apicurio_serdes/_errors.py` — add `SchemaRegistrationError`
- `src/apicurio_serdes/_base.py` — add `_register_endpoint()` helper and `_process_registration_response()` shared logic
- `src/apicurio_serdes/_client.py` — add `register_schema()` sync method
- `src/apicurio_serdes/_async_client.py` — add `register_schema()` async method
- `src/apicurio_serdes/avro/_serializer.py` — add `schema`, `auto_register`, `if_exists` params; wire auto-register into `serialize()`
- `src/apicurio_serdes/__init__.py` — export `SchemaRegistrationError`
- `tests/conftest.py` — add `_register_route()` and `_register_error_route()` mock helpers
- `tests/test_errors.py` — `SchemaRegistrationError` unit tests (or add to existing)
- `tests/test_client.py` — `register_schema` sync integration tests
- `tests/test_async_client.py` — `register_schema` async integration tests
- `tests/test_serializer.py` — auto-register serializer unit/integration tests

## Success Criteria

- [ ] `SchemaRegistrationError(artifact_id, cause)` is raised on any 4xx/5xx from the registration endpoint
- [ ] `SchemaRegistrationError` is importable from `apicurio_serdes`
- [ ] `ApicurioRegistryClient.register_schema(artifact_id, schema, if_exists)` POSTs to `/groups/{group_id}/artifacts` with correct headers and query param, returns `CachedSchema`, populates `_schema_cache`
- [ ] Second `get_schema()` call after `register_schema()` is a cache hit (zero HTTP calls)
- [ ] `AsyncApicurioRegistryClient.register_schema()` is the async equivalent with identical behaviour
- [ ] `AvroSerializer(auto_register=True)` without `schema` raises `ValueError` at construction time
- [ ] `AvroSerializer(auto_register=False, schema=...)` is accepted without error (schema ignored)
- [ ] On first `serialize()` with `auto_register=True` and a 404: calls `register_schema()`, succeeds, returns framed bytes
- [ ] On first `serialize()` with `auto_register=False` and a 404: `SchemaNotFoundError` propagates unchanged (existing behaviour)
- [ ] `if_exists` default is `"RETURN"`; all four literal values are forwarded as the `ifExists` query param
- [ ] Registration network error raises `RegistryConnectionError`
- [ ] Registration 4xx/5xx raises `SchemaRegistrationError` with `artifact_id` and `cause` attributes
- [ ] 100% branch coverage on all new and modified code
- [ ] `mypy` strict passes with zero new errors

## Implementation Steps

### Phase 1: SchemaRegistrationError

#### Step 1.1 — Write SchemaRegistrationError tests (RED)

- **File**: `tests/test_errors.py` (or existing error test file)
- **Action**: Add a `TestSchemaRegistrationError` class with cases:
  - Constructor stores `artifact_id` attribute
  - Constructor stores `cause` attribute
  - `str()` includes the artifact ID
  - `__cause__` is set to the `cause` argument
  - Instance is catchable as `Exception`
  - Importable from `apicurio_serdes` (will fail until Phase 5 — collect now to drive that phase)
- **Verify**: `uv run pytest tests/test_errors.py -x` — expect failures (class does not exist)
- **Complexity**: Small

#### Step 1.2 — Implement SchemaRegistrationError (GREEN)

- **File**: `src/apicurio_serdes/_errors.py`
- **Action**: Append following the `RegistryConnectionError` pattern:
  ```python
  class SchemaRegistrationError(Exception):
      def __init__(self, artifact_id: str, cause: Exception) -> None:
          self.artifact_id = artifact_id
          self.cause = cause
          super().__init__(
              f"Failed to register schema for artifact '{artifact_id}': {cause}"
          )
          self.__cause__ = cause
  ```
- **Verify**: `uv run pytest tests/test_errors.py -x` — all Step 1.1 tests pass
- **Complexity**: Small

---

### Phase 2: `register_schema` on sync client

#### Step 2.1 — Write sync client tests (RED)

- **File**: `tests/conftest.py` + `tests/test_client.py`
- **Action**:
  - Add `_register_route()` helper to `conftest.py` — mocks `POST .../groups/{group_id}/artifacts`
    with `ifExists` query param, responds 200 with `X-Registry-GlobalId` and
    `X-Registry-ContentId` headers
  - Add `_register_error_route()` helper for 4xx/5xx responses
  - Test cases:
    - Happy path: `register_schema("UserEvent", schema)` returns `CachedSchema` with correct IDs
    - Cache populated: subsequent `get_schema("UserEvent")` makes zero HTTP calls (GET route call_count == 0)
    - `if_exists` forwarded: parametrize over `["FAIL", "RETURN", "RETURN_OR_UPDATE", "UPDATE"]`
    - 4xx response (409) raises `SchemaRegistrationError` with `artifact_id` set
    - 5xx response (500) raises `SchemaRegistrationError`
    - Network error raises `RegistryConnectionError`
    - Closed client raises `RuntimeError`
- **Verify**: `uv run pytest tests/test_client.py -x` — expect failures (method does not exist)
- **Complexity**: Small

#### Step 2.2 — Implement `register_schema` on sync client (GREEN)

- **File**: `src/apicurio_serdes/_base.py` + `src/apicurio_serdes/_client.py`
- **Action**:
  - Add `_register_endpoint(self) -> str` to `_base.py`:
    ```python
    def _register_endpoint(self) -> str:
        return f"/groups/{self.group_id}/artifacts"
    ```
  - Add `_process_registration_response(response, artifact_id)` to `_base.py` — raises
    `SchemaRegistrationError(artifact_id, exc)` on non-2xx; parses `X-Registry-GlobalId`
    and `X-Registry-ContentId` headers on success; returns `CachedSchema`
  - Add `register_schema()` to `ApicurioRegistryClient`, lock-guarded (no fast-path cache
    check — registration is a write; caller has established schema is absent):
    ```python
    def register_schema(
        self,
        artifact_id: str,
        schema: dict[str, Any],
        if_exists: Literal["FAIL", "RETURN", "RETURN_OR_UPDATE", "UPDATE"] = "RETURN",
    ) -> CachedSchema:
        self._check_closed()
        with self._lock:
            try:
                response = self._http_client.post(
                    self._register_endpoint(),
                    json=schema,
                    headers={
                        "X-Registry-ArtifactId": artifact_id,
                        "X-Registry-ArtifactType": "AVRO",
                    },
                    params={"ifExists": if_exists},
                )
            except httpx.TransportError as exc:
                raise RegistryConnectionError(self.url, exc) from exc
            cached = self._process_registration_response(response, artifact_id)
            self._schema_cache[(self.group_id, artifact_id)] = cached
            return cached
    ```
- **Verify**: `uv run pytest tests/test_client.py -x` — all Phase 2 tests pass
- **Complexity**: Medium

---

### Phase 3: `register_schema` on async client

#### Step 3.1 — Write async client tests (RED)

- **File**: `tests/test_async_client.py`
- **Action**: Mirror every Step 2.1 test case as `async def`. The `_register_route()` helper
  from `conftest.py` is reused unchanged. Additional case:
  - Interface parity: assert `AsyncApicurioRegistryClient.register_schema` signature
    matches sync counterpart (same param names, same defaults)
- **Verify**: `uv run pytest tests/test_async_client.py -x` — expect failures
- **Complexity**: Small

#### Step 3.2 — Implement `register_schema` on async client (GREEN)

- **File**: `src/apicurio_serdes/_async_client.py`
- **Action**: Add async method following the existing async lock pattern:
  ```python
  async def register_schema(
      self,
      artifact_id: str,
      schema: dict[str, Any],
      if_exists: Literal["FAIL", "RETURN", "RETURN_OR_UPDATE", "UPDATE"] = "RETURN",
  ) -> CachedSchema:
      self._check_closed()
      async with self._lock:
          try:
              response = await self._http_client.post(
                  self._register_endpoint(),
                  json=schema,
                  headers={
                      "X-Registry-ArtifactId": artifact_id,
                      "X-Registry-ArtifactType": "AVRO",
                  },
                  params={"ifExists": if_exists},
              )
          except httpx.TransportError as exc:
              raise RegistryConnectionError(self.url, exc) from exc
          cached = self._process_registration_response(response, artifact_id)
          self._schema_cache[(self.group_id, artifact_id)] = cached
          return cached
  ```
- **Verify**: `uv run pytest tests/test_async_client.py -x` — all Phase 3 tests pass
- **Complexity**: Medium

---

### Phase 4: Wire auto-register into `AvroSerializer`

#### Step 4.1 — Write serializer auto-register tests (RED)

- **File**: `tests/test_serializer.py`
- **Action**: Add `TestAutoRegister` class using `_not_found_route()` for GET 404 and
  `_register_route()` for POST 200. Test cases:
  - `auto_register=True` without `schema` → `ValueError` at construction
  - `auto_register=False` with `schema` supplied → constructs without error
  - GET 404 + POST 200 → serialize succeeds, returns framed bytes
  - Second serialize → cache hit, zero additional HTTP requests
  - `auto_register=False` + GET 404 → `SchemaNotFoundError` propagates unchanged
  - GET 404 + POST 409 → `SchemaRegistrationError` raised
  - GET 404 + POST network error → `RegistryConnectionError` raised
  - `if_exists="FAIL"` forwarded in POST query param
  - `if_exists` default is `"RETURN"`
  - `auto_register=True` with `artifact_resolver` → resolver returns ID, GET 404, POST 200 → success
- **Verify**: `uv run pytest tests/test_serializer.py -x` — expect failures
- **Complexity**: Small

#### Step 4.2 — Implement auto-register in `AvroSerializer` (GREEN)

- **File**: `src/apicurio_serdes/avro/_serializer.py`
- **Action**:
  1. Add three constructor params after the existing params:
     ```python
     schema: dict[str, Any] | None = None,
     auto_register: bool = False,
     if_exists: Literal["FAIL", "RETURN", "RETURN_OR_UPDATE", "UPDATE"] = "RETURN",
     ```
  2. Add constructor validation after the `use_id` guard:
     ```python
     if auto_register and schema is None:
         raise ValueError("schema must be provided when auto_register=True")
     ```
  3. Store: `self._local_schema = schema`, `self.auto_register = auto_register`,
     `self.if_exists = if_exists`
  4. In `serialize()` lazy-fetch block, replace the `get_schema` call:
     ```python
     try:
         cached = self.registry_client.get_schema(effective_id)
     except SchemaNotFoundError:
         if not self.auto_register or self._local_schema is None:
             raise
         cached = self.registry_client.register_schema(
             effective_id, self._local_schema, self.if_exists
         )
     self._schema = cached
     self._parsed_schema = fastavro.parse_schema(cached.schema)
     ```
  5. Add `SchemaNotFoundError` to imports from `apicurio_serdes._errors` if not explicit
- **Verify**: `uv run pytest tests/test_serializer.py -x` — all Phase 4 tests pass
- **Complexity**: Medium

---

### Phase 5: Public API exports and coverage gate

#### Step 5.1 — Export `SchemaRegistrationError` (GREEN)

- **File**: `src/apicurio_serdes/__init__.py`
- **Action**: Add `SchemaRegistrationError` to import from `._errors` and to `__all__`
- **Verify**: `python -c "from apicurio_serdes import SchemaRegistrationError; print('OK')"`
- **Complexity**: Small

#### Step 5.2 — Full suite and coverage gate

- **Files**: all test files
- **Action**: Run full suite with coverage
- **Verify**:
  - `uv run pytest --tb=short` — 0 failures
  - 100% branch coverage on `_errors.py`, `_base.py`, `_client.py`, `_async_client.py`,
    `avro/_serializer.py`, `__init__.py`
  - `uv run mypy src/` — 0 errors
- **Complexity**: Small

---

## Test Strategy

| Test case | Type | Input | Expected output |
| --------- | ---- | ----- | --------------- |
| `SchemaRegistrationError` stores `artifact_id` | Unit | `SchemaRegistrationError("art", exc)` | `.artifact_id == "art"` |
| `SchemaRegistrationError` stores `cause` | Unit | `SchemaRegistrationError("art", exc)` | `.cause is exc`, `.__cause__ is exc` |
| `SchemaRegistrationError` message includes artifact ID | Unit | `str(err)` | `"art"` in message |
| `SchemaRegistrationError` importable | Unit | `from apicurio_serdes import SchemaRegistrationError` | no `ImportError` |
| Sync `register_schema` happy path | Integration | POST mock 200 | `CachedSchema` with correct IDs |
| Sync cache populated after register | Integration | POST 200, then `get_schema` | GET route call_count == 0 |
| Sync `if_exists` forwarded (×4 values) | Integration | `if_exists=` each value | `ifExists=` in POST query |
| Sync 4xx → `SchemaRegistrationError` | Integration | POST mock 409 | `SchemaRegistrationError` with `artifact_id` |
| Sync 5xx → `SchemaRegistrationError` | Integration | POST mock 500 | `SchemaRegistrationError` |
| Sync network error → `RegistryConnectionError` | Integration | POST raises `ConnectError` | `RegistryConnectionError` |
| Sync closed client → `RuntimeError` | Unit | `close()` then `register_schema` | `RuntimeError` |
| Async `register_schema` happy path | Integration | POST mock 200, async | `CachedSchema` |
| Async cache populated after register | Integration | POST 200, then async `get_schema` | GET call_count == 0 |
| Async 4xx → `SchemaRegistrationError` | Integration | POST mock 409, async | `SchemaRegistrationError` |
| Async network error → `RegistryConnectionError` | Integration | POST `ConnectError`, async | `RegistryConnectionError` |
| Async interface parity | Unit | Inspect signatures | param names and defaults match sync |
| Serializer: `auto_register=True` no schema | Unit | Constructor | `ValueError` at construction |
| Serializer: `auto_register=False` with schema | Unit | Constructor | no error |
| Serializer: GET 404 + POST 200 | Integration | 404 then 200 | framed bytes returned |
| Serializer: second serialize is cache hit | Integration | 404+200, then second call | zero additional HTTP requests |
| Serializer: `auto_register=False` + GET 404 | Integration | 404 | `SchemaNotFoundError` propagates |
| Serializer: GET 404 + POST 409 | Integration | 404 GET, 409 POST | `SchemaRegistrationError` |
| Serializer: GET 404 + POST network error | Integration | 404 GET, `ConnectError` POST | `RegistryConnectionError` |
| Serializer: `if_exists` default is `"RETURN"` | Integration | no `if_exists` kwarg | `ifExists=RETURN` in POST |
| Serializer: `if_exists="FAIL"` forwarded | Integration | `if_exists="FAIL"` | `ifExists=FAIL` in POST |
| Serializer: `auto_register=True` with `artifact_resolver` | Integration | resolver + 404 + 200 | serialize succeeds |

## Risks and Mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| `_process_registration_response` duplicates `_process_schema_response` logic | Drift between paths | Extract shared header parsing into a private `_parse_schema_headers()` base method; both processors call it |
| `_local_schema: dict | None` mypy inference | mypy strict failure | Annotate explicitly; the `auto_register and schema is None` guard narrows type at call site |
| `Literal[...]` annotation needs `Literal` in scope | mypy error | `from __future__ import annotations` already present; import `Literal` under `TYPE_CHECKING` |
| POST body double-encoded | Malformed schema in registry | Use `json=schema` kwarg (httpx serializes once); test with nested schema |
| Wrong POST URL path | Silent 404 | Unit test asserts route `call_count == 1` on exact URL pattern |
| Schema mismatch when using `artifact_resolver` | Silent wrong schema registered | Document that callers supply the schema dict matching the expected artifact; add docstring note |
| `auto_register=False` re-raise branch uncovered after refactor | Coverage gap | Confirm existing 404 scenario still exercises the re-raise branch |

## Rollback Strategy

All changes are additive. New constructor parameters all have defaults that reproduce
current behaviour (`auto_register=False`, `schema=None`, `if_exists` unused when
`auto_register=False`). No database or configuration changes. Rollback: `git revert`
the feature branch commits.

## Status

- [ ] Plan approved
- [ ] Implementation started
- [ ] Implementation complete
