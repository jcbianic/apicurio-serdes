# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-001
Feature: Automated Quality Gate on Every Change
  As a contributor, I want every push and pull request to automatically run the
  full test suite with coverage enforcement, static analysis, and type checking so
  that I receive fast feedback on whether my changes meet the project's quality
  standards before review begins.

  @TS-001 @FR-001 @SC-001 @P1 @acceptance
  Scenario: Full test suite runs with branch coverage enforcement on push
    Given a contributor pushes a commit to any branch
    When the CI pipeline is triggered
    Then the full test suite runs with branch coverage enforcement at the threshold defined in the project configuration

  @TS-002 @FR-004 @SC-001 @P1 @acceptance
  Scenario: PR status reflects pipeline result and blocks merge on failure
    Given a contributor opens a pull request
    When the CI pipeline completes
    Then the PR status reflects pass or fail
    And merge is blocked when any quality check fails

  @TS-003 @FR-002 @FR-003 @SC-001 @P1 @acceptance
  Scenario: Static analysis or type checking violations fail the pipeline
    Given a push includes code that fails static analysis or type checking
    When the CI pipeline runs
    Then the pipeline reports the specific violations
    And the check fails

  @TS-004 @FR-001 @SC-001 @P1 @acceptance
  Scenario: Coverage below threshold fails the pipeline
    Given the test suite passes but coverage is below the required threshold
    When the CI pipeline evaluates results
    Then the pipeline fails
    And the pipeline reports the coverage gap

  @TS-005 @FR-001 @FR-002 @FR-003 @FR-016 @SC-001 @P1 @contract
  Scenario: CI workflow executes all quality jobs on push to main
    Given a push event targets the main branch
    When the CI workflow evaluates its trigger configuration
    Then the lint, typecheck, test, and docs jobs all execute

  @TS-006 @FR-006 @SC-001 @P1 @contract
  Scenario: Coverage XML report is available as a downloadable build artifact
    Given the test job completes successfully
    When the CI pipeline uploads artifacts
    Then a coverage XML report artifact is available for download from the workflow run
