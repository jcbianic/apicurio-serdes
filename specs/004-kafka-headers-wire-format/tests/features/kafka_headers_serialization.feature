# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-001
Feature: Serialize using KAFKA_HEADERS wire format
  As a Python data engineer working with an Apicurio Registry deployment
  configured for KAFKA_HEADERS wire format, I want to serialize Avro messages
  where the schema identifier is placed in Kafka message headers rather than
  embedded in the message bytes, so that my Kafka messages remain
  payload-clean and interoperate with other producers and consumers using
  the same Apicurio KAFKA_HEADERS convention.

  Background:
    Given an AvroSerializer configured with WireFormat.KAFKA_HEADERS

  @TS-001 @FR-005 @SC-001 @P1 @acceptance
  Scenario: Payload contains no framing bytes in KAFKA_HEADERS mode
    Given a schema artifact exists in the registry
    When the serialize() method is called with a valid dict and a SerializationContext
    Then the returned payload contains only raw Avro binary
    And the returned payload does not begin with magic byte 0x00
    And the returned payload does not contain a 4-byte schema identifier prefix

  @TS-002 @FR-006 @SC-002 @P1 @acceptance
  Scenario Outline: Schema identifier header uses Apicurio native naming convention
    Given a schema artifact exists in the registry
    And the AvroSerializer is configured with use_id "<use_id>"
    And the SerializationContext field is "<field>"
    When the serialize() method is called with a valid dict and a SerializationContext
    Then the SerializedMessage headers contain exactly the key "<header_name>"

    Examples:
      | use_id    | field | header_name              |
      | globalId  | VALUE | apicurio.value.globalId  |
      | globalId  | KEY   | apicurio.key.globalId    |
      | contentId | VALUE | apicurio.value.contentId |
      | contentId | KEY   | apicurio.key.contentId   |

  @TS-003 @FR-005 @FR-008 @P1 @acceptance
  Scenario: Error raised for invalid data before any bytes or headers produced
    Given a schema artifact exists in the registry
    When the serialize() method is called with a dict that is missing a required schema field
    Then an error is raised before any bytes are produced
    And no headers are set

  @TS-004 @FR-005 @FR-006 @P1 @acceptance
  Scenario: KAFKA_HEADERS payload decodes correctly when schema is taken from headers
    Given a schema artifact exists in the registry
    When the serialize() method is called with a valid dict and a SerializationContext
    And the raw payload bytes are decoded by an Avro binary reader using the schema from the registry
    Then the decoded record is identical to the original input data

  @TS-005 @FR-007 @SC-002 @P1 @contract
  Scenario: Header value is encoded as 8-byte big-endian signed long
    Given a schema artifact exists in the registry
    When the serialize() method is called with a valid dict and a SerializationContext
    Then the SerializedMessage headers contain exactly one entry
    And the header value is exactly 8 bytes long
    And the header value bytes equal struct.pack(">q", schema_identifier)

  @TS-006 @FR-009 @P2 @acceptance
  Scenario: use_id=contentId places the content identifier in the header for KAFKA_HEADERS mode
    Given a schema artifact exists in the registry
    And the AvroSerializer is configured with use_id "contentId"
    When the serialize() method is called with a valid dict and a SerializationContext
    Then the SerializedMessage headers contain a key ending with ".contentId"
    And the header value encodes the content identifier assigned by the registry

  @TS-007 @FR-008 @P1 @acceptance
  Scenario: SchemaNotFoundError raised when artifact is missing — no bytes or headers returned
    Given no schema artifact exists in the registry for the configured artifact ID
    When the serialize() method is called with a valid dict and a SerializationContext
    Then a SchemaNotFoundError is raised
    And no SerializedMessage is returned

  @TS-008 @NFR-001 @SC-005 @P2 @contract
  Scenario: Schema caching preserved — 1000 consecutive serializations use exactly 1 HTTP call
    Given a schema artifact exists in the registry
    When the serialize() method is called 1000 consecutive times with the same artifact
    Then exactly 1 HTTP call is made to the schema registry
