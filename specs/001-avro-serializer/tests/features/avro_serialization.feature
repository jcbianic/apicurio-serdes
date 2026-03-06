# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-001
Feature: Serialize Python dict to Confluent-framed Avro bytes
  As a Python data engineer producing Kafka messages, I want to serialize a
  Python dict to Avro bytes using a schema stored in Apicurio Registry, so
  that my Kafka producer can send type-safe, schema-validated messages with
  no custom registry or encoding code at the call site.

  Background:
    Given a configured ApicurioRegistryClient pointing at a registry that holds a known Avro schema for artifact "UserEvent"
    And an AvroSerializer created with that client and artifact_id "UserEvent"

  @TS-001 @FR-002 @FR-003 @FR-005 @SC-001 @P1 @acceptance
  Scenario: Serialize valid dict produces Confluent wire format bytes
    Given a SerializationContext for topic "users" and field VALUE
    When the serializer is called with a valid dict conforming to the schema
    Then the returned bytes begin with magic byte 0x00
    And bytes at offset 1 through 4 contain a 4-byte big-endian schema identifier
    And the remaining bytes are a valid Avro binary payload

  @TS-002 @FR-003 @P1 @acceptance
  Scenario: Two valid dicts serialized from the same schema share the same 4-byte identifier prefix
    Given a SerializationContext for topic "users" and field VALUE
    When two different valid dicts conforming to the same schema are serialized
    Then both outputs share the same 4-byte schema identifier prefix

  @TS-003 @FR-002 @P1 @acceptance
  Scenario: Dict missing a required field raises an error before any bytes are produced
    Given a SerializationContext for topic "users" and field VALUE
    When the serializer is called with a dict that is missing a field required by the schema
    Then a ValueError is raised
    And no bytes are produced

  @TS-004 @FR-008 @P1 @acceptance
  Scenario: Artifact not found in the registry raises a SchemaNotFoundError
    Given an AvroSerializer configured with artifact_id "NonExistentSchema"
    And the registry returns HTTP 404 for that artifact
    When the serializer is called with a valid dict and a SerializationContext
    Then a SchemaNotFoundError is raised
    And the error message identifies the missing artifact and the group

  @TS-005 @FR-011 @P1 @acceptance
  Scenario: Registry unreachable raises a RegistryConnectionError wrapping the cause
    Given an ApicurioRegistryClient configured with an unreachable registry URL
    And an AvroSerializer using that client with artifact_id "UserEvent"
    When the serializer is called with a valid dict and a SerializationContext
    Then a RegistryConnectionError is raised
    And the error message includes the registry URL

  @TS-006 @FR-012 @P2 @acceptance
  Scenario: Extra fields in input dict are silently dropped when strict mode is disabled
    Given an AvroSerializer configured with strict=False and artifact_id "UserEvent"
    And a SerializationContext for topic "users" and field VALUE
    When the serializer is called with a dict containing extra fields not present in the schema
    Then valid Confluent-framed Avro bytes are returned
    And no error is raised

  @TS-007 @FR-012 @P2 @acceptance
  Scenario: Extra fields in input dict raise ValueError when strict mode is enabled
    Given an AvroSerializer configured with strict=True and artifact_id "UserEvent"
    And a SerializationContext for topic "users" and field VALUE
    When the serializer is called with a dict containing extra fields not present in the schema
    Then a ValueError is raised before any bytes are produced

  @TS-008 @FR-001 @FR-009 @P1 @validation
  Scenario: group_id is a required parameter for ApicurioRegistryClient
    When an ApicurioRegistryClient is constructed without providing a group_id
    Then a ValueError is raised indicating that group_id is required

  @TS-009 @FR-004 @P1 @validation
  Scenario: SerializationContext carries the Kafka topic name and field type
    Given a SerializationContext constructed with topic "orders" and field KEY
    Then the context exposes topic "orders"
    And the context exposes field KEY
