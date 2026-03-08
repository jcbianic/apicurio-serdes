# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-005
Feature: Developer understands key concepts through dedicated conceptual pages
  As a data engineer new to Apicurio Registry and the Confluent wire format,
  I want dedicated conceptual explanation pages covering the wire format byte layout,
  schema caching behaviour, and Apicurio's group/artifact/version addressing model,
  so that I understand not just how to call the API but why the library works the
  way it does.

  @TS-014 @FR-006 @P5 @acceptance
  Scenario: Wire format conceptual page explains byte layout and identifier choices
    Given a conceptual page on the Confluent wire format
    When a developer reads it
    Then they understand the byte layout of a serialized message including the magic byte, 4-byte schema identifier, and Avro payload, the purpose of each field, and the difference between globalId and contentId identifiers

  @TS-015 @FR-006 @P5 @acceptance
  Scenario: Schema caching conceptual page explains cache lifecycle and safety guarantees
    Given a conceptual page on schema caching
    When a developer reads it
    Then they understand when the cache is populated, how long it persists, when to create a new client instance, and what thread-safety guarantees the cache provides

  @TS-016 @FR-006 @P5 @acceptance
  Scenario: Addressing model conceptual page explains Apicurio group/artifact/version hierarchy
    Given a conceptual page on Apicurio's addressing model
    When a developer reads it
    Then they understand the group to artifact to version hierarchy, why group_id is required in apicurio-serdes, and how to map an existing Confluent schema naming convention to Apicurio's model
