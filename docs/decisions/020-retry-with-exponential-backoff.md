# ADR-020: Retry with Exponential Backoff and httpx Escape Hatch

**Status:** Accepted
**Date:** 2026-03-18
**Supersedes:** ADR-014 (No timeout or retry configuration on HTTP clients)

## Context

ADR-014 rejected built-in retry logic on the grounds that retry policy is
application-specific and baking it in forces opinions on callers. However, both
reference implementations disagree:

- **Confluent Python** (`SchemaRegistryClient`): built-in retry with
  `max.retries=3`, `retries.wait.ms=1000`, `retries.max.wait.ms=20000`,
  exponential backoff with full jitter, retrying on 408/429/5xx.
- **Apicurio Java** (`SchemaResolverConfig`): built-in retry with
  `apicurio.registry.retry-count=3`, `apicurio.registry.retry-backoff-ms=300`.

Additionally, the "delegate to the user" escape hatch proposed in ADR-014
(pass a pre-configured `httpx.Client`) does not actually cover the transient
HTTP status code case: `httpx.HTTPTransport(retries=N)` only retries on
connection errors, not on 429/5xx responses. Users who need full retry
coverage would have to implement the retry loop themselves — a significant
burden for a trivially common operational concern.

The set of retryable events (transport errors, 429, 502, 503, 504) is
uncontroversial, well-established, and safe regardless of caller SLA. A user
who wants no retries can set `max_retries=0`.

## Decision

1. Add `max_retries`, `retry_backoff_ms`, and `retry_max_backoff_ms`
   keyword-only parameters to both `ApicurioRegistryClient` and
   `AsyncApicurioRegistryClient`, with defaults matching Confluent Python
   (`max_retries=3`, `retry_backoff_ms=1000`, `retry_max_backoff_ms=20000`).

2. Implement exponential backoff with full jitter:
   `delay = random.uniform(0, min(retry_backoff_ms * 2^attempt, retry_max_backoff_ms)) / 1000`.

3. Retry on: `httpx.TransportError` (any), HTTP 429, 502, 503, 504.
   Do **not** retry on: 4xx other than 429, 500 (ambiguous for mutations).

4. Also accept an `http_client` keyword-only parameter (`httpx.Client` for
   sync, `httpx.AsyncClient` for async) as a power-user escape hatch for
   custom transports, connection pools, auth, and mTLS. When a user-provided
   client is given, the library does not close it on `close()` / `aclose()`.

## Rationale

- Aligns with both reference implementations.
- Retryable events are infrastructure noise, not business logic — the
  right policy is uncontroversial for this class of errors.
- `httpx.HTTPTransport(retries=N)` is insufficient for production use
  (covers only connection errors, not 5xx/429).
- `max_retries=0` fully disables retry for callers who prefer to manage
  it themselves.
- The `http_client` escape hatch preserves the power-user path from ADR-014's
  revisit trigger.

## Consequences

- Existing clients get 3 retries by default where they previously had none.
  On persistent registry outages, failure takes up to ~3× longer to surface.
  This is acceptable and matches the behaviour users expect from the reference
  implementations.
- The `http_client` parameter enables advanced scenarios (mTLS, custom proxies,
  service-mesh-aware auth) without the library needing to expose every knob.
