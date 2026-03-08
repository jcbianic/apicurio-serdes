# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-003
Feature: Custom dict-to-object transformation via from_dict hook
  As a Python developer whose application works with typed domain objects
  rather than plain dicts, I want to provide a custom conversion callable to
  AvroDeserializer, so that deserialized data is automatically transformed
  into my domain objects without extra conversion code at every consumer
  call site.

  Background:
    Given a configured ApicurioRegistryClient pointing at a registry that holds a known Avro schema with contentId 42 for artifact "UserEvent"
    And valid Confluent-framed Avro bytes produced for that schema

  @TS-013 @FR-008 @P3 @acceptance
  Scenario: Provided from_dict callable is applied to the decoded dict before returning
    Given an AvroDeserializer configured with a from_dict callable that constructs a UserEvent dataclass
    And a SerializationContext for topic "users" and field VALUE
    When the deserializer is called with the valid Avro bytes and the context
    Then the from_dict callable is applied to the decoded dict
    And the returned value is a UserEvent dataclass instance, not a plain dict

  @TS-014 @FR-008 @P3 @acceptance
  Scenario: Absent from_dict callable returns the decoded dict directly with no transformation
    Given an AvroDeserializer configured without a from_dict callable
    And a SerializationContext for topic "users" and field VALUE
    When the deserializer is called with the valid Avro bytes and the context
    Then the returned value is a plain Python dict
    And no transformation is applied

  @TS-015 @FR-009 @P2 @acceptance
  Scenario: from_dict callable raising an exception is wrapped as a DeserializationError
    Given an AvroDeserializer configured with a from_dict callable that raises a RuntimeError
    And a SerializationContext for topic "users" and field VALUE
    When the deserializer is called with the valid Avro bytes and the context
    Then a DeserializationError is raised
    And the DeserializationError includes the original RuntimeError as its cause
    And the error message identifies the failed conversion
