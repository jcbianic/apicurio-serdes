# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-002
Feature: Open-Source Quality Signaling
  As a maintainer, I want the pipeline to integrate with quality signaling
  services that offer free tiers for open-source projects so that the repository
  publicly communicates code quality, coverage, and health through badges and
  dashboards that build trust with potential adopters.

  @TS-007 @FR-005 @SC-002 @SC-003 @P1 @acceptance
  Scenario: Coverage results are uploaded to external coverage reporting service
    Given the CI pipeline completes successfully
    When coverage results are produced
    Then the results are uploaded to an external coverage reporting service
    And the service provides a public dashboard and embeddable badge

  @TS-008 @FR-005 @SC-003 @P1 @acceptance
  Scenario: Pull request displays coverage change compared to base branch
    Given a pull request is opened
    When the coverage reporting service receives the results
    Then the PR displays a coverage summary showing coverage change compared to the base branch

  @TS-009 @FR-007 @SC-002 @P1 @acceptance
  Scenario: Repository displays up-to-date quality signal badges in README
    Given the repository has quality signaling configured
    When a potential adopter visits the repository
    Then they can see up-to-date badges for CI status and coverage percentage in the README

  @TS-010 @FR-005 @SC-001 @P1 @acceptance
  Scenario: Coverage service unavailability does not block the CI pipeline
    Given the CI pipeline runs and coverage results are produced
    When the external coverage reporting service is unavailable
    Then the pipeline still passes or fails based on local coverage enforcement
    And the upload failure is logged as a warning but is non-blocking
