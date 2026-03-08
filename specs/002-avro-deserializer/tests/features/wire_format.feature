# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

Feature: Confluent wire format framing and deserializer API contract
  Byte-level verification of Confluent wire format decoding and validation
  that the public API mirrors confluent-kafka consumer conventions.

  Background:
    Given a configured ApicurioRegistryClient pointing at a registry that returns globalId 7 and contentId 42 for artifact "UserEvent"
    And a SerializationContext for topic "users" and field VALUE

  @TS-016 @FR-003 @FR-006 @SC-004 @P1 @contract
  Scenario: Default use_id is contentId — 4-byte field is interpreted as a contentId
    Given an AvroDeserializer configured with use_id="contentId" and the client
    And bytes whose magic byte is 0x00 and whose 4-byte field encodes the value 42 as big-endian uint32
    And a valid Avro payload appended after the 5-byte header
    When the deserializer is called with those bytes and the context
    Then the registry is queried for contentId 42
    And the decoded result is a Python dict

  @TS-017 @FR-006 @P2 @contract
  Scenario: use_id="globalId" causes the 4-byte field to be interpreted as a globalId
    Given an AvroDeserializer configured with use_id="globalId" and the client
    And bytes whose magic byte is 0x00 and whose 4-byte field encodes the value 7 as big-endian uint32
    And a valid Avro payload appended after the 5-byte header
    When the deserializer is called with those bytes and the context
    Then the registry is queried for globalId 7
    And the decoded result is a Python dict

  @TS-018 @FR-002 @SC-004 @P1 @contract
  Scenario: AvroDeserializer callable interface mirrors the confluent-kafka deserializer convention
    Given an AvroDeserializer instance bound to the client
    And valid Confluent-framed Avro bytes for artifact "UserEvent"
    When the deserializer is called as deserializer(data, ctx) with those bytes and the SerializationContext
    Then the return value is a Python dict
