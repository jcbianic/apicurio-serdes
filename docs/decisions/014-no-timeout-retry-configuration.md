# ADR-014: No timeout or retry configuration on HTTP clients

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 review item 15 — "No timeout/retry configuration on HTTP clients"

## Context

The review flagged that `httpx.Client(base_url=url)` uses httpx's default
timeouts (5s connect, 5s read, 5s write, 5s pool) with no user override
and no retry logic. A single transient 503 fails the operation permanently.

## Decision

Do not add timeout configuration or retry logic to the client.

## Rationale

- **Timeouts:** httpx's defaults (5s each) are reasonable for a local or
  near-network registry. Exposing timeout configuration adds API surface
  that must be maintained. If a user needs custom timeouts, they can pass
  a pre-configured `httpx.Client` (this pattern should be added before
  timeout params — see revisit trigger).
- **Retries:** Retry logic is application-specific. The right retry policy
  depends on the caller's SLA, deployment topology, and error budget.
  Baking retry logic into a library forces opinions that may conflict
  with the caller's own retry/circuit-breaker middleware (e.g., Tenacity,
  Stamina, or a service mesh sidecar).
- **Constitution Principle V (Simplicity):** "The library must do one thing
  well: serialize and deserialize." Retry logic is infrastructure, not
  serialization.
- Users who need retries can wrap calls with their own retry decorator
  or use httpx's event hooks / transport layer.

## Revisit Trigger

- Accept a user-provided `httpx.Client` / `httpx.AsyncClient` in the
  constructor. This gives users full control over timeouts, retries,
  connection pooling, and auth without the library needing to expose
  every knob. This is the preferred path if users request configurability.
