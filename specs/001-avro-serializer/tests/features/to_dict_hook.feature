# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-003
Feature: Custom object-to-dict transformation via to_dict hook
  As a Python developer whose message payloads are domain objects rather
  than plain dicts, I want to provide a custom conversion callable to
  AvroSerializer, so that I can serialize my existing objects without
  manually converting them at every call site.

  @TS-013 @FR-007 @P3 @acceptance
  Scenario: Provided to_dict callable is applied to the input before Avro encoding
    Given an AvroSerializer configured with a to_dict callable and artifact_id "UserEvent"
    And the to_dict callable converts the input object to a valid dict
    And a SerializationContext for topic "users" and field VALUE
    When the serializer is called with a non-dict domain object
    Then the to_dict callable is applied to the input first
    And the resulting dict is Avro-encoded identically to serializing that dict directly

  @TS-014 @FR-007 @P3 @acceptance
  Scenario: Absent to_dict callable means the plain dict is passed directly to the encoder
    Given an AvroSerializer configured without a to_dict callable and artifact_id "UserEvent"
    And a SerializationContext for topic "users" and field VALUE
    When the serializer is called with a plain dict conforming to the schema
    Then the dict is used directly for Avro encoding with no transformation applied

  @TS-015 @FR-013 @P2 @acceptance
  Scenario: to_dict callable raising an exception is wrapped as a SerializationError
    Given an AvroSerializer configured with a to_dict callable that raises a RuntimeError
    And a SerializationContext for topic "users" and field VALUE
    When the serializer is called with an input object
    Then a SerializationError is raised
    And the SerializationError includes the original RuntimeError as its cause
    And the error message identifies the failed conversion
