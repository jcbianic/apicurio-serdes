# ADR-010: Keep SchemaNotFoundError dual-constructor pattern

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 review item 10 — "SchemaNotFoundError.from_id() creates half-initialized objects"

## Context

The review flagged that `SchemaNotFoundError` has two construction paths:
`__init__(group_id, artifact_id)` for artifact lookups and
`from_id(id_type, id_value)` for ID-based lookups. The `from_id()` classmethod
uses `cls.__new__()` to bypass `__init__`, creating instances with different
attributes depending on construction path. A generic exception handler
accessing the wrong attributes gets `AttributeError`.

## Decision

Keep the dual-constructor pattern. Do not unify the two construction paths.

## Rationale

- The two construction paths correspond to genuinely different failure modes
  (artifact lookup vs. ID lookup). They carry different diagnostic data
  because the caller has different context in each case.
- Unifying into a single constructor with optional parameters would make
  every attribute optional, forcing callers to check for `None` — worse
  ergonomics, not better.
- Using a base class with two subclasses (`ArtifactNotFoundError`,
  `SchemaIdNotFoundError`) was considered but rejected as over-engineering
  for two construction sites. The `from_id()` pattern is a well-known
  Python idiom (see `datetime.fromtimestamp()`, `dict.fromkeys()`).
- In practice, exception handlers either catch `SchemaNotFoundError`
  generically (using only `str(exc)`, which works for both) or are
  co-located with the code that raised it and know which attributes exist.

## Consequences

- Callers who catch `SchemaNotFoundError` generically should use `str(exc)`
  or check `hasattr()` before accessing path-specific attributes.
- The docstring documents both construction paths and their attributes.
