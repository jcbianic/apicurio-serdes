# ADR-003: Frozen dataclass for CachedSchema

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 commit `ec601d3`

## Context

`CachedSchema` holds the schema dict, `global_id`, and `content_id` returned
by the registry. It is stored in a shared in-memory cache and returned to
callers. If a caller mutates the schema dict, the mutation silently corrupts
the cached copy for all future callers.

## Decision

Use `@dataclass(frozen=True)` for `CachedSchema`.

## Alternatives Considered

- **Plain `@dataclass`:** Rejected because attribute reassignment would be
  allowed, creating a silent cache corruption vector.
- **Deep copy on every cache retrieval:** Rejected as unnecessarily expensive
  for a hot path. Freezing is cheaper (zero runtime cost on reads) and
  communicates intent.
- **Named tuple:** Rejected because dataclass provides better ergonomics
  (named fields, type annotations, IDE support).

## Consequences

- Attribute reassignment raises `FrozenInstanceError` immediately.
- The `schema` dict inside is still technically mutable (frozen only prevents
  attribute reassignment, not deep mutation). This is an accepted trade-off:
  deep-freezing dicts is expensive and the frozen signal is sufficient to
  communicate "do not mutate."
- If deep immutability becomes necessary, consider wrapping the schema dict
  in `types.MappingProxyType`.
