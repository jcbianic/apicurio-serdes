# ADR-001: Base class extraction over mixin for sync/async client deduplication

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 (`fix/client-hardening-and-dedup`)

## Context

The sync `ApicurioRegistryClient` and async `AsyncApicurioRegistryClient` had
nearly identical logic for endpoint building, response processing, int64
validation, closed-client guards, and caching. This duplication caused
divergence bugs: the async client lacked int64 validation, the sync client
lacked the closed-client guard.

## Decision

Extract shared logic into a non-public abstract base class `_RegistryClientBase`
in `src/apicurio_serdes/_base.py`. Both clients inherit from it and only
implement their transport-specific methods (HTTP calls with httpx sync vs async,
lock type selection).

## Alternatives Considered

- **Mixin approach:** Rejected because the shared logic represents core state
  and behavior (cache, closed flag, validation), not orthogonal utility methods.
  A base class better models the "is-a" relationship.
- **Keep duplication, enforce via review:** Rejected because review-time
  enforcement already failed — the divergence bugs were the proof.
- **Composition / delegate object:** Considered but rejected as over-engineering
  for two subclasses. Would add indirection without meaningful benefit.

## Consequences

- Both clients stay in sync by construction, not by discipline.
- New shared behavior goes in one place (`_base.py`).
- Subclass contract is documented: subclasses must set `_http_client` and
  `_lock` in their `__init__` after calling `super().__init__()`.
