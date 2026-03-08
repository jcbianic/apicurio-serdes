# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-002
Feature: CONFLUENT_PAYLOAD remains the default, unaffected by KAFKA_HEADERS addition
  As a Python data engineer already using AvroSerializer with Confluent wire format,
  I want my existing code to continue working without any changes after the
  KAFKA_HEADERS option is introduced, so that adopting the new version does not
  require a migration.

  @TS-010 @FR-003 @FR-004 @SC-003 @P2 @acceptance
  Scenario: Default serialization produces Confluent framing bytes
    Given an AvroSerializer configured without an explicit wire_format parameter
    And a schema artifact exists in the registry
    When the serializer is called with a valid dict and a SerializationContext
    Then the returned bytes begin with magic byte 0x00
    And the returned bytes contain a 4-byte big-endian schema identifier at offset 1

  @TS-011 @FR-004 @SC-003 @P2 @acceptance
  Scenario: Explicit CONFLUENT_PAYLOAD output is identical to default output
    Given an AvroSerializer configured with WireFormat.CONFLUENT_PAYLOAD
    And a schema artifact exists in the registry
    When the serializer is called with the same valid dict as the default serializer
    Then the output bytes are identical to the output produced with no wire_format argument

  @TS-012 @FR-010 @P2 @contract
  Scenario: serialize() returns SerializedMessage with empty headers for CONFLUENT_PAYLOAD
    Given an AvroSerializer configured with WireFormat.CONFLUENT_PAYLOAD
    And a schema artifact exists in the registry
    When the serialize() method is called with a valid dict and a SerializationContext
    Then the returned SerializedMessage.payload contains the Confluent-framed bytes
    And the returned SerializedMessage.headers is an empty dict

  @TS-013 @FR-004 @FR-010 @P2 @contract
  Scenario: __call__ return type is unchanged — returns bytes only
    Given an AvroSerializer configured with WireFormat.CONFLUENT_PAYLOAD
    And a schema artifact exists in the registry
    When __call__ is invoked with a valid dict and a SerializationContext
    Then the return value is of type bytes
    And the return value is identical to SerializedMessage.payload from serialize()

  @TS-014 @FR-010 @P2 @validation
  Scenario: SerializedMessage is immutable — mutation raises an error
    Given an AvroSerializer configured with WireFormat.CONFLUENT_PAYLOAD
    And a schema artifact exists in the registry
    When the serialize() method is called with a valid dict and a SerializationContext
    And an attempt is made to mutate the returned SerializedMessage.payload field
    Then a FrozenInstanceError is raised
