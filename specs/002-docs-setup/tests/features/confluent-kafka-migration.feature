# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-002
Feature: Confluent-kafka migrant identifies all differences and adapts their code
  As a Python developer currently using confluent-kafka's schema registry serializers,
  I want a migration guide that puts the two APIs side by side with a complete map
  of differences, so that I can update my existing producer code and know exactly
  what will change in behavior without surprises.

  @TS-004 @FR-004 @SC-003 @P2 @acceptance
  Scenario: Migration guide enumerates every API and behavioral difference
    Given a developer using confluent-kafka's AvroSerializer
    When they read the migration guide
    Then they can enumerate every class name, parameter name, and behavioral difference between the two libraries from a single reading, including the required group_id parameter that has no direct counterpart in Confluent's client

  @TS-005 @FR-004 @P2 @acceptance
  Scenario: Migration requires only import and configuration changes for the common case
    Given a developer who has read the migration guide
    When they update their existing producer code
    Then they need to touch no more than the import lines and the client configuration to achieve a working migration for the common case

  @TS-006 @FR-004 @P2 @acceptance
  Scenario: Migration guide explains group_id and schema naming mapping
    Given a developer whose schemas are organized under a non-default group
    When they read the migration guide
    Then they understand what group_id represents in Apicurio, why it is required, and how to map their existing schema naming to Apicurio's group/artifact model
