# ADR-007: Closed-client guard on every public method

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 commit `4b23fd3`

## Context

After `close()` (or `aclose()`), the underlying httpx client is shut down.
Without a guard, subsequent operations produce confusing httpx transport errors
(e.g., `httpx.PoolTimeout`, connection refused). The async client had a
closed-client guard, but the sync client did not.

## Decision

Add a `_check_closed()` guard at the entry of every public method in the base
class. It raises `RuntimeError("client is closed")` if the client has been
closed.

## Alternatives Considered

- **Let httpx errors propagate:** Rejected — the errors are confusing and
  don't tell the user they are using a closed client.
- **Silently reconnect:** Rejected — implicit reconnection violates the
  explicit lifecycle contract (context manager pattern) and could mask bugs.
- **Guard only on `close()` method:** Rejected — the bug surfaces on
  subsequent calls, not on `close()` itself.

## Consequences

- Clear, predictable error when using a closed client.
- Small per-call overhead (one boolean check) — negligible.
- Consistent behavior between sync and async clients via the shared base class.
