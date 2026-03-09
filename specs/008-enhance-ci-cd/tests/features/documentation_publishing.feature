# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-003
Feature: Publish Documentation to ReadTheDocs on PR and Release
  As a user, I want documentation to be automatically built and published so
  that I can review API docs for any PR and access them for stable releases.

  @TS-012 @FR-006 @SC-003 @P1 @acceptance
  Scenario: ReadTheDocs builds documentation and provides preview link on PR
    Given a PR is opened
    When CI completes successfully
    Then ReadTheDocs builds documentation and provides a preview link

  @TS-013 @FR-006 @SC-003 @P1 @acceptance
  Scenario: Documentation preview reflects PR changes
    Given documentation changes are made in a PR
    When the preview is generated
    Then the preview correctly reflects the changes

  @TS-014 @FR-007 @SC-003 @P1 @acceptance
  Scenario: Documentation published to primary site on release
    Given a release tag is created
    When the release workflow completes
    Then documentation is published to the primary ReadTheDocs site

  @TS-015 @FR-008 @P1 @contract
  Scenario: ReadTheDocs uses webhook-based authentication
    Given ".readthedocs.yaml" exists in the repository
    When ReadTheDocs integration is configured
    Then authentication is webhook-based with no GitHub secret required

  @TS-016 @FR-006 @P1 @contract
  Scenario: CI validates documentation build independently
    Given the CI workflow defines a "docs-build" job
    When the job runs "mkdocs build --strict"
    Then documentation build errors are caught before ReadTheDocs builds
