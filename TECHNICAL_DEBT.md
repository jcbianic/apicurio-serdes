# Technical Debt

Minor items deferred from code review. None block correctness in the current usage profile; all are safe to address in a future iteration.

## TD-001 — `httpx.ConnectError` catch too narrow in `ApicurioRegistryClient.get_schema`

**File**: `src/apicurio_serdes/_client.py:89`
**Impact**: `httpx.TimeoutException`, `httpx.ReadError`, and other `httpx.TransportError` subclasses propagate unwrapped instead of being raised as `RegistryConnectionError`. This breaks the FR-011 contract for any network failure beyond a connection refusal (e.g. a slow registry that accepts TCP but times out mid-response).
**Fix**: Change `except httpx.ConnectError` to `except httpx.TransportError`.

## TD-002 — `httpx.Client` has no lifecycle management in `ApicurioRegistryClient`

**File**: `src/apicurio_serdes/_client.py:53`
**Impact**: The `httpx.Client` connection pool is never explicitly closed. Not a problem for the expected long-lived singleton usage, but leaks file descriptors if the client is created and discarded multiple times (e.g. in test suites without proper teardown).
**Fix**: Add a `close()` method and `__enter__`/`__exit__` to support use as a context manager.

## TD-003 — Error classes not re-exported from the package root

**File**: `src/apicurio_serdes/__init__.py`
**Impact**: Callers must write `from apicurio_serdes._errors import RegistryConnectionError` to write `except` clauses, importing from a private module. The contract (`contracts/public-api.md`) does not require top-level re-export, but it is the ergonomic expectation for a public library.
**Fix**: Re-export `RegistryConnectionError`, `SchemaNotFoundError`, and `SerializationError` from `__init__.py`.
