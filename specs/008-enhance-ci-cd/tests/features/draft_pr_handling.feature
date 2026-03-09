# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-006
Feature: Create PRs as Draft with Conditional CI Triggering
  As a maintainer, I want PRs to be created as draft and CI to only run when
  marked as "Ready for Review" so that work-in-progress changes don't consume
  CI resources.

  @TS-027 @FR-011 @P2 @acceptance
  Scenario: PR creation guidance defaults to draft
    Given a PR is opened
    When it is created
    Then it defaults to draft status

  @TS-028 @FR-012 @SC-006 @P2 @acceptance
  Scenario: Draft PR skips full CI suite
    Given a PR is in draft status
    When CI workflows are checked
    Then no full CI suite runs

  @TS-029 @FR-013 @SC-006 @P2 @acceptance
  Scenario: Full CI suite runs on ready for review
    Given a PR is marked "Ready for Review"
    When the status changes
    Then full CI suite runs immediately

  @TS-030 @FR-012 @SC-006 @P2 @contract
  Scenario: Lint job runs on draft PRs for quick feedback
    Given a PR is in draft status
    When the CI workflow triggers
    Then only the "lint" job executes
    And "typecheck", "test", "docs-build", and "publish-testpypi" jobs are skipped

  @TS-031 @FR-013 @P2 @contract
  Scenario: CI workflow triggers on ready_for_review event
    Given the CI workflow trigger configuration
    When the pull_request event types are inspected
    Then "ready_for_review" is included as a trigger type

  @TS-032 @FR-012 @P2 @validation
  Scenario: Draft condition uses correct GitHub event property
    Given the CI workflow job conditions
    When the draft-skip condition is inspected
    Then it checks "github.event.pull_request.draft == false"
