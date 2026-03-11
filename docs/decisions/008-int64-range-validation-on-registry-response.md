# ADR-008: Validate int64 range on registry response IDs

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 commit `894ad7c`

## Context

Apicurio returns `globalId` and `contentId` as HTTP header values (strings
parsed to int). These are specified as signed 64-bit integers. Out-of-range
values could silently propagate through the cache and into wire format
encoding, causing corruption downstream.

## Decision

Validate that `globalId` and `contentId` fit in signed 64-bit range
immediately after parsing the registry response, in the shared base class.

## Alternatives Considered

- **Trust the registry:** Rejected — defensive validation at system boundaries
  is a standard practice. Registry bugs or misconfigurations should not
  silently corrupt client state.
- **Validate only at serialization time:** Rejected — by then the value is
  already cached and may have been used elsewhere.
- **Use Python's arbitrary precision integers without validation:** Rejected —
  downstream consumers (struct packing, Kafka headers) have fixed-width
  expectations. Catching the problem early produces a clearer error.

## Consequences

- Invalid IDs are caught immediately with a clear `ValueError`.
- Validation lives in the base class, so both sync and async clients enforce it.
- Negligible performance impact (two integer comparisons per response).
