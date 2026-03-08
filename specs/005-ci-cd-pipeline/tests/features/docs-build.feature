# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-005
Feature: Documentation Build Validation
  As a maintainer, I want the CI pipeline to validate that documentation builds
  successfully on every pull request so that documentation regressions are caught
  before merge, even if the documentation hosting itself is managed separately.

  @TS-023 @FR-016 @SC-009 @P2 @acceptance
  Scenario: Documentation build is validated on every pull request
    Given a pull request is opened
    When the CI pipeline runs
    Then the documentation build is validated and builds without errors

  @TS-024 @FR-016 @SC-009 @P2 @acceptance
  Scenario: Documentation error causes the CI pipeline to fail
    Given the documentation source contains an error such as a broken reference or syntax error
    When the CI pipeline runs
    Then the build fails
    And the pipeline reports the specific documentation error
