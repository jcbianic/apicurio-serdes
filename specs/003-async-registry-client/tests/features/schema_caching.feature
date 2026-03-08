# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-002
Feature: Async schema caching prevents redundant registry lookups
  As a Python developer running a high-throughput async Kafka producer,
  I want the async client to cache schemas after the first fetch, so that
  subsequent serialization calls do not incur additional HTTP round-trips
  or event-loop stalls.

  Background:
    Given a configured AsyncApicurioRegistryClient pointing at a stubbed registry

  @TS-011 @FR-004 @SC-003 @P2 @acceptance
  Scenario: Same artifact fetched twice contacts the registry exactly once
    Given the registry holds a schema for artifact "UserEvent"
    When await client.get_schema("UserEvent") is called
    And await client.get_schema("UserEvent") is called a second time
    Then the registry received exactly 1 HTTP request for "UserEvent"
    And both calls returned the same CachedSchema

  @TS-012 @FR-004 @P2 @acceptance
  Scenario: Fetching a different artifact does not re-fetch a cached schema
    Given the registry holds schemas for artifacts "SchemaA" and "SchemaB"
    When await client.get_schema("SchemaA") is called
    And await client.get_schema("SchemaB") is called
    Then the registry received exactly 1 HTTP request for "SchemaA"
    And the registry received exactly 1 HTTP request for "SchemaB"

  @TS-013 @NFR-001 @P1 @acceptance
  Scenario: Concurrent coroutines fetching the same uncached schema result in one HTTP request
    Given the registry holds a schema for artifact "UserEvent"
    When 10 coroutines concurrently call await client.get_schema("UserEvent") for the first time
    Then the registry received exactly 1 HTTP request for "UserEvent"
    And all coroutines received an identical CachedSchema
