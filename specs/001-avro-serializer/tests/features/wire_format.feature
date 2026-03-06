# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

Feature: Confluent wire format framing and API contract
  Byte-level verification of the Confluent wire format encoding and
  validation that the public API mirrors confluent-kafka conventions.

  Background:
    Given a configured ApicurioRegistryClient pointing at a registry that returns globalId 42 and contentId 7 for artifact "UserEvent"
    And a valid dict conforming to the "UserEvent" schema
    And a SerializationContext for topic "users" and field VALUE

  @TS-016 @FR-003 @FR-010 @SC-002 @P1 @contract
  Scenario: Default wire format embeds globalId as the 4-byte schema identifier
    Given an AvroSerializer configured with use_id="globalId" and artifact_id "UserEvent"
    When the serializer is called with the valid dict
    Then output byte 0 is 0x00
    And bytes 1 through 4 contain the value 42 encoded as a big-endian unsigned 32-bit integer

  @TS-017 @FR-010 @P2 @contract
  Scenario: Wire format embeds contentId when use_id is set to contentId
    Given an AvroSerializer configured with use_id="contentId" and artifact_id "UserEvent"
    When the serializer is called with the valid dict
    Then output byte 0 is 0x00
    And bytes 1 through 4 contain the value 7 encoded as a big-endian unsigned 32-bit integer

  @TS-018 @FR-005 @SC-004 @P1 @contract
  Scenario: AvroSerializer callable interface mirrors the confluent-kafka serializer convention
    Given an AvroSerializer instance bound to artifact_id "UserEvent"
    When the serializer is called as serializer(data, ctx) with a valid dict and SerializationContext
    Then the return value is of type bytes
    And the return value begins with magic byte 0x00
