# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-001
Feature: Deserialize Confluent-framed Avro bytes to a Python dict
  As a Python data engineer consuming Kafka messages, I want to deserialize
  Avro bytes into a Python dict using a schema resolved from the Apicurio
  Registry, so that my Kafka consumer receives structured, schema-validated
  data with no custom decoding or registry code at the call site.

  Background:
    Given a configured ApicurioRegistryClient pointing at a registry that holds a known Avro schema with contentId 42 for artifact "UserEvent"
    And an AvroDeserializer created with that client

  @TS-001 @FR-001 @FR-002 @FR-005 @SC-001 @SC-002 @P1 @acceptance
  Scenario: Valid Confluent-framed Avro bytes deserialize to the original dict
    Given Confluent-framed Avro bytes produced by serializing a known dict with schema "UserEvent"
    And a SerializationContext for topic "users" and field VALUE
    When the deserializer is called with those bytes and the context
    Then the returned value is a Python dict
    And the dict contents match the original data that was serialized

  @TS-002 @FR-005 @P1 @acceptance
  Scenario: Schema is resolved from the registry using the identifier in the wire frame
    Given valid Confluent-framed Avro bytes whose 4-byte field encodes contentId 42
    And a SerializationContext for topic "users" and field VALUE
    When the deserializer is called with those bytes and the context
    Then the registry is queried for contentId 42
    And the schema returned for that identifier is used to decode the payload

  @TS-003 @FR-003 @P1 @acceptance
  Scenario: Bytes not starting with magic byte 0x00 raise a DeserializationError immediately
    Given bytes that begin with 0x01 instead of the expected magic byte 0x00
    And a SerializationContext for topic "users" and field VALUE
    When the deserializer is called with those bytes and the context
    Then a DeserializationError is raised
    And no registry lookup is attempted

  @TS-004 @FR-010 @P1 @acceptance
  Scenario: Valid framing with an unknown schema identifier raises a descriptive error
    Given valid Confluent-framed Avro bytes whose 4-byte field encodes contentId 9999
    And the registry has no schema corresponding to contentId 9999
    And a SerializationContext for topic "users" and field VALUE
    When the deserializer is called with those bytes and the context
    Then a descriptive error is raised
    And the error message identifies the unresolved identifier 9999

  @TS-005 @FR-004 @P1 @acceptance
  Scenario: Empty input raises a DeserializationError before any registry lookup
    Given an empty byte string
    And a SerializationContext for topic "users" and field VALUE
    When the deserializer is called with those bytes and the context
    Then a DeserializationError is raised
    And no registry lookup is attempted

  @TS-006 @FR-004 @P1 @acceptance
  Scenario: Input shorter than 5 bytes raises a DeserializationError before any registry lookup
    Given bytes that contain the magic byte 0x00 followed by only 3 bytes
    And a SerializationContext for topic "users" and field VALUE
    When the deserializer is called with those bytes and the context
    Then a DeserializationError is raised
    And no registry lookup is attempted

  @TS-007 @FR-011 @P1 @acceptance
  Scenario: Corrupt Avro payload raises a DeserializationError identifying the decoding failure
    Given valid Confluent framing with magic byte and contentId 42
    And a payload that cannot be decoded with the resolved schema
    And a SerializationContext for topic "users" and field VALUE
    When the deserializer is called with those bytes and the context
    Then a DeserializationError is raised
    And the error message identifies the decoding failure

  @TS-008 @FR-012 @P1 @acceptance
  Scenario: Unreachable registry during schema resolution raises a RegistryConnectionError
    Given an ApicurioRegistryClient configured with an unreachable registry URL
    And an AvroDeserializer using that client
    And valid Confluent-framed Avro bytes referencing contentId 42
    And a SerializationContext for topic "users" and field VALUE
    When the deserializer is called with those bytes and the context
    Then a RegistryConnectionError is raised
    And the error message includes the registry URL

  @TS-009 @SC-002 @SC-005 @P1 @acceptance
  Scenario: Round-trip — bytes from AvroSerializer deserialize back to the original dict
    Given an AvroSerializer configured with the same client and artifact_id "UserEvent"
    And a plain dict conforming to the "UserEvent" schema
    And a SerializationContext for topic "users" and field VALUE
    When the dict is serialized with the AvroSerializer
    And the resulting bytes are deserialized with the AvroDeserializer
    Then the deserialized dict equals the original dict
    And no manual registry interaction occurred between the two steps
