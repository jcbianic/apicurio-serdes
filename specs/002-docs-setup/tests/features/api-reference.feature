# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-003
Feature: Developer finds the exact API details they need
  As a developer integrating apicurio-serdes in a production system,
  I want a complete API reference listing every public class, method,
  parameter, return value, and exception, so that I can look up any
  detail without reading source code.

  @TS-007 @FR-005 @SC-004 @P3 @acceptance
  Scenario: AvroSerializer is fully documented in the API reference
    Given the API reference
    When a developer looks up AvroSerializer
    Then they find its constructor signature, every optional parameter with its default value, a short description of what the class does, and a minimal usage example

  @TS-008 @FR-005 @FR-014 @SC-004 @P3 @validation
  Scenario: All public symbols are fully documented with no warnings
    Given the API reference
    When a developer looks up any public class or method
    Then they find a description, all parameters with name, type, default if applicable, and description, the return type and description, and all exceptions that may be raised with an explanation of when each is raised

  @TS-009 @FR-005 @P3 @acceptance
  Scenario: Runtime exceptions are documented with actionable context
    Given a developer who encounters a SchemaNotFoundError at runtime
    When they look it up in the API reference
    Then they understand what triggered it, which attributes it carries including group_id and artifact_id, and how to handle it in their code
