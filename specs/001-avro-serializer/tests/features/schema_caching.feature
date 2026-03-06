# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-002
Feature: Schema caching prevents redundant registry lookups
  As a Python data engineer running a high-throughput Kafka producer, I want
  the Avro schema to be fetched from the registry once and reused for
  subsequent messages, so that my producer does not incur an HTTP round-trip
  on every serialization call.

  Background:
    Given a configured ApicurioRegistryClient pointing at a registry that holds schemas for artifacts "SchemaA" and "SchemaB"

  @TS-010 @FR-006 @SC-003 @P2 @acceptance
  Scenario: Registry is contacted exactly once when the same artifact is serialized multiple times
    Given an AvroSerializer configured for artifact "SchemaA"
    And a SerializationContext for topic "events" and field VALUE
    When the serializer is called twice in sequence with valid dicts
    Then the registry is contacted exactly once for artifact "SchemaA"

  @TS-011 @FR-006 @P2 @acceptance
  Scenario: A new artifact triggers one registry call without re-fetching a previously cached schema
    Given an AvroSerializer for artifact "SchemaA" that has already fetched and cached its schema
    And an AvroSerializer for artifact "SchemaB"
    And a SerializationContext for topic "events" and field VALUE
    When the serializer for "SchemaB" is used for the first time with a valid dict
    Then the registry is contacted exactly once for artifact "SchemaB"
    And the registry is not contacted again for artifact "SchemaA"

  @TS-012 @NFR-001 @P1 @acceptance
  Scenario: Concurrent calls to the same artifact result in exactly one registry HTTP request
    Given an ApicurioRegistryClient pointing at a registry that holds a schema for artifact "SharedSchema"
    And multiple AvroSerializer instances all configured for artifact "SharedSchema"
    When all serializers are called concurrently with valid dicts
    Then the registry is contacted exactly once for artifact "SharedSchema"
    And all serializers return valid Confluent-framed Avro bytes
