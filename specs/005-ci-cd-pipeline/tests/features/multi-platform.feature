# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-006
Feature: Multi-Platform Compatibility Verification
  As a contributor, I want the test suite to run across multiple supported Python
  versions so that compatibility claims are verified automatically rather than
  assumed.

  @TS-025 @FR-017 @SC-008 @P3 @acceptance
  Scenario: Tests execute on all Python versions declared as supported
    Given a pull request is opened
    When the CI pipeline runs
    Then tests execute on all Python versions declared as supported in the project configuration

  @TS-026 @FR-017 @SC-008 @P3 @acceptance
  Scenario: Version-specific test failure is clearly attributed to the failing version
    Given a test fails on one Python version but passes on others
    When the CI pipeline reports results
    Then the failure is clearly attributed to the specific version
