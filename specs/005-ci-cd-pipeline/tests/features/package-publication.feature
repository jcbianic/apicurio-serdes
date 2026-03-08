# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-003
Feature: Automated Package Publication
  As a maintainer, I want an automated publication process that publishes the
  package to a staging registry first and then to the production registry so that
  releases reach end users reliably without manual packaging steps.

  @TS-011 @FR-008 @SC-004 @P1 @acceptance
  Scenario: Package is published to the staging registry first
    Given a maintainer triggers a release
    When the publication pipeline runs
    Then the package is first published to the staging package registry (TestPyPI)

  @TS-012 @FR-008 @FR-010 @SC-004 @P1 @acceptance
  Scenario: Package is promoted to production after successful staging validation
    Given the package is successfully published to the staging registry
    When the staging validation succeeds
    Then the package is automatically published to the production registry (PyPI)

  @TS-013 @FR-009 @SC-006 @P1 @acceptance
  Scenario: Pipeline fails when package version does not match the release identifier
    Given a release is triggered
    When the package version does not match the release identifier
    Then the pipeline fails with a clear error message before any publication occurs

  @TS-014 @FR-010 @SC-006 @P1 @acceptance
  Scenario: Staging failure prevents production publication
    Given publication to the staging registry fails
    When the pipeline evaluates the result
    Then it does not proceed to publish to the production registry
    And it reports the failure

  @TS-015 @FR-012 @SC-007 @P1 @acceptance
  Scenario: Pipeline fails gracefully when version has already been published
    Given the release pipeline is triggered
    When the package version has already been published to the registry
    Then the pipeline detects the conflict and fails gracefully without overwriting the existing release

  @TS-016 @FR-011 @SC-004 @P1 @contract
  Scenario: Publication authenticates using OIDC trusted publishing without stored secrets
    Given a release is triggered and OIDC trusted publishing is configured
    When the publication pipeline authenticates to the registry
    Then authentication uses OIDC identity tokens
    And no stored API secrets are required

  @TS-017 @FR-008 @SC-006 @P1 @contract
  Scenario: Publish workflow jobs execute sequentially with hard gates
    Given a GitHub Release is published
    When the publish workflow runs
    Then the validate-version, build, publish-testpypi, validate-testpypi, and publish-pypi jobs execute in sequence
    And each job only starts after the previous job succeeds
