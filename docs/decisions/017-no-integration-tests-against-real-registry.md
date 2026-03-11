# ADR-017: No integration tests against a real registry (yet)

**Status:** Accepted
**Date:** 2026-03-11
**Context:** PR #32 review item 18 — "No integration tests against a real registry"

## Context

The review flagged that every HTTP call is mocked with respx. No test proves
the client actually works against a real Apicurio Registry. Docker-compose
or testcontainers-based integration tests would catch mismatches between the
mocked API and the real one.

## Decision

Do not add integration tests in this PR. Keep mock-based tests as the
primary test strategy.

## Rationale

- Mock-based tests with 100% coverage validate the library's logic
  thoroughly: wire format encoding, caching, error handling, concurrency.
  These are the areas where bugs actually occur.
- Integration tests require a running Apicurio Registry (Docker), which
  adds CI complexity (Docker-in-Docker, service health checks, port
  allocation) and slows the feedback loop.
- The Apicurio v3 REST API is well-documented and stable. The mocks are
  based on the documented response format, not reverse-engineered. Risk
  of mock drift is low.
- This is a scope decision, not a quality decision. Integration tests are
  valuable but are a separate workstream from client hardening.

## Consequences

- Risk: mocks could diverge from the real API (e.g., header name changes,
  new required fields). Mitigated by tracking Apicurio release notes.
- Integration tests should be added as a follow-up, gated behind a
  `pytest.mark.integration` marker so they don't run on every push.
