# ADR-012: Keep explicit __cause__ assignment on DeserializationError

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 review item 13 — "DeserializationError.__init__ redundantly sets __cause__"

## Context

The review flagged that `DeserializationError.__init__` sets
`self.__cause__ = cause` explicitly, but every raise site also uses
`raise ... from exc`, which sets `__cause__` again. The explicit assignment
is technically redundant.

## Decision

Keep the explicit `self.__cause__ = cause` in the constructor.

## Rationale

- The constructor also exposes `self.cause` as a public attribute for
  programmatic access. Setting `__cause__` in the same place ensures both
  attributes are always consistent, regardless of how the exception is raised.
- If a caller constructs `DeserializationError(msg, cause=exc)` without
  using `raise ... from`, the `__cause__` would not be set without the
  explicit assignment. Defensive construction ensures correctness regardless
  of the raise pattern.
- The cost is one attribute assignment — negligible, and the intent is clear.
- Removing it would save zero runtime cost and create a subtle bug if anyone
  constructs the exception without `from`.
