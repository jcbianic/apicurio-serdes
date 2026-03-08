# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-001
Feature: New visitor understands the problem and gets started
  As a Python data engineer who discovers apicurio-serdes for the first time,
  I want to immediately understand what problem this library solves and get
  my first Kafka message serialized end-to-end in a single reading,
  so that I can evaluate the library and start using it without consulting
  external resources.

  @TS-001 @FR-001 @SC-001 @P1 @acceptance
  Scenario: Homepage communicates problem clearly to a first-time visitor
    Given a developer who has never seen the library arrives at the documentation homepage
    When they read the homepage
    Then they can articulate in one sentence what problem apicurio-serdes solves, who it is for, and what makes it different from existing approaches

  @TS-002 @FR-002 @SC-002 @P1 @acceptance
  Scenario: Quickstart guide leads to a working serialization example
    Given a developer following the quickstart guide from the first line
    When they complete every step in sequence
    Then they have a working Python script that successfully serializes a Python dict to Confluent-framed Avro bytes using their Apicurio Registry instance or a documented local alternative

  @TS-003 @FR-003 @P1 @acceptance
  Scenario Outline: Quickstart troubleshooting covers common setup errors
    Given a developer following the quickstart who encounters a setup error
    When they encounter a "<error_type>" error and consult the troubleshooting section
    Then they find a description of the error, its root cause, and a corrective action without leaving the quickstart page

    Examples:
      | error_type            |
      | wrong registry URL    |
      | non-existent artifact |
      | invalid input data    |
