# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-002
Feature: Schema caching prevents redundant registry lookups on deserialization
  As a Python data engineer running a high-throughput Kafka consumer, I want
  schemas resolved during deserialization to be cached, so that processing a
  stream of messages sharing the same schema does not incur an HTTP round-trip
  per message.

  Background:
    Given a configured ApicurioRegistryClient pointing at a registry that holds schemas with contentId 42 ("SchemaA") and contentId 43 ("SchemaB")

  @TS-010 @FR-007 @SC-003 @P2 @acceptance
  Scenario: Registry is contacted exactly once when the same schema identifier is deserialized multiple times
    Given an AvroDeserializer configured with the client
    And a SerializationContext for topic "events" and field VALUE
    When 1000 Confluent-framed messages all referencing contentId 42 are deserialized in sequence
    Then the registry is contacted exactly once for contentId 42

  @TS-011 @FR-007 @P2 @acceptance
  Scenario: A new schema identifier triggers one registry call without re-fetching a previously cached schema
    Given an AvroDeserializer configured with the client
    And a message referencing contentId 42 has already been deserialized and contentId 42 is cached
    And a SerializationContext for topic "events" and field VALUE
    When a message referencing contentId 43 is deserialized for the first time
    Then the registry is contacted exactly once for contentId 43
    And the registry is not contacted again for contentId 42

  @TS-012 @NFR-001 @P1 @acceptance
  Scenario: Concurrent deserialization of the same schema identifier results in exactly one registry HTTP request
    Given an ApicurioRegistryClient pointing at a registry that holds a schema with contentId 42
    And an AvroDeserializer configured with that client
    When many messages all referencing contentId 42 are deserialized concurrently from multiple threads
    Then the registry is contacted exactly once for contentId 42
    And all deserialized results are correct Python dicts
