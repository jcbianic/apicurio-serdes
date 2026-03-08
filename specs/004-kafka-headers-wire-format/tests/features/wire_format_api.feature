# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-003
Feature: WireFormat is an explicit named option at configuration time
  As a Python developer configuring serializers for a Kafka pipeline,
  I want to select the wire format using a named constant rather than a string
  or boolean flag, so that my configuration is self-documenting, discoverable
  by IDE tooling, and protected against typos.

  @TS-020 @FR-001 @FR-002 @SC-004 @P3 @acceptance
  Scenario: WireFormat is importable from the library top-level namespace
    Given the apicurio_serdes package is installed
    When a developer imports WireFormat from apicurio_serdes
    Then the import succeeds without error
    And WireFormat is accessible as apicurio_serdes.WireFormat

  @TS-021 @FR-001 @SC-004 @P3 @acceptance
  Scenario: WireFormat enum exposes CONFLUENT_PAYLOAD and KAFKA_HEADERS members
    Given the WireFormat enum is imported from apicurio_serdes
    When a developer inspects the WireFormat enum members
    Then WireFormat.CONFLUENT_PAYLOAD is a valid member
    And WireFormat.KAFKA_HEADERS is a valid member

  @TS-022 @FR-003 @SC-001 @P3 @acceptance
  Scenario: AvroSerializer accepts wire_format=WireFormat.KAFKA_HEADERS without error
    Given the apicurio_serdes package is installed
    When a developer configures AvroSerializer with wire_format=WireFormat.KAFKA_HEADERS
    Then no TypeError is raised
    And no ValueError is raised
    And the serializer is configured in KAFKA_HEADERS mode

  @TS-023 @FR-003 @P3 @acceptance
  Scenario: AvroSerializer defaults to CONFLUENT_PAYLOAD when no wire_format is specified
    Given the apicurio_serdes package is installed
    When a developer creates AvroSerializer without a wire_format argument
    Then the serializer defaults to WireFormat.CONFLUENT_PAYLOAD mode

  @TS-024 @FR-001 @P3 @validation
  Scenario: Passing an invalid wire_format value raises an error at construction
    Given the apicurio_serdes package is installed
    When a developer creates AvroSerializer with an invalid wire_format value "unsupported"
    Then a ValueError is raised at construction time
