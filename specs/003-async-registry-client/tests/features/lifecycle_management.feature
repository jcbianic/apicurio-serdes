# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-004
Feature: Async client supports context-manager lifecycle
  As a Python developer using structured resource management in asyncio,
  I want to use the async client as an async context manager, so that the
  underlying HTTP connection pool is properly closed when my application
  shuts down.

  @TS-031 @FR-009 @P3 @acceptance
  Scenario: async with block closes the HTTP connection pool on exit
    Given an AsyncApicurioRegistryClient instance
    When it is used as "async with AsyncApicurioRegistryClient(...) as client:"
    And the async with block exits normally
    Then the underlying httpx.AsyncClient is closed

  @TS-032 @FR-009 @P3 @acceptance
  Scenario: async with block closes the HTTP connection pool when an exception is raised
    Given an AsyncApicurioRegistryClient instance
    When it is used as "async with AsyncApicurioRegistryClient(...) as client:"
    And an exception is raised inside the async with block
    Then the underlying httpx.AsyncClient is closed before the exception propagates

  @TS-033 @FR-010 @P3 @acceptance
  Scenario: aclose() closes the HTTP connection pool explicitly
    Given an AsyncApicurioRegistryClient instance created without a context manager
    When await client.aclose() is called
    Then the underlying httpx.AsyncClient is closed
