# ADR-006: Align deserializer use_id default to globalId

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 commit `3810b6e`, Constitution Principle IV (Wire Format Fidelity)

## Context

The serializer defaults to `use_id="globalId"`. Both deserializers
(`AvroDeserializer` and `AsyncAvroDeserializer`) previously defaulted to
`use_id="contentId"`. A user creating both with defaults would serialize
with `globalId` in the wire format header but deserialize interpreting the
same bytes as `contentId` — silently fetching the wrong schema when
`globalId != contentId`.

## Decision

Change the deserializer default from `"contentId"` to `"globalId"` to match
the serializer. This is a breaking change for users relying on the old default.

## Alternatives Considered

- **Keep mixed defaults, document the gotcha:** Rejected — documentation does
  not prevent footguns. The library should be correct by default.
- **Make `use_id` required (no default):** Rejected — would break API
  compatibility for all existing users, not just the small minority using
  `contentId`.
- **Change serializer default to `contentId` instead:** Rejected — `globalId`
  is the more common and safer default in the Apicurio ecosystem.

## Consequences

- Users who explicitly pass `use_id="contentId"` are unaffected.
- Users relying on the old deserializer default (`"contentId"`) will see a
  behavior change. This is acceptable because the old default was silently
  wrong when paired with the serializer default.
- Existing tests were updated to explicitly pass `use_id="contentId"` where
  that behavior was intentional.
