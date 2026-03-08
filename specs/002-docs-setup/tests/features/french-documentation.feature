# DO NOT MODIFY SCENARIOS
# These .feature files define expected behavior derived from requirements.
# During implementation:
#   - Write step definitions to match these scenarios
#   - Fix code to pass tests, don't modify .feature files
#   - If requirements change, re-run /iikit-04-testify

@US-004
Feature: French-speaking developer reads the complete documentation in French
  As a French-speaking data engineer at a European organization using Apicurio Registry,
  I want to read the entire documentation in French — including the homepage, quickstart,
  user guide, conceptual explanations, and migration guide — so that I can understand
  and use the library fully without a language barrier.

  @TS-010 @FR-009 @FR-011 @SC-005 @P4 @acceptance
  Scenario: Language switch displays all content in French
    Given a French-speaking developer arrives at the documentation site
    When they switch the interface to French
    Then all navigation labels, headings, and narrative content appear in correct, natural French

  @TS-011 @FR-009 @SC-005 @P4 @acceptance
  Scenario: French documentation page tree has parity with English
    Given the French documentation
    When a developer reads the homepage, quickstart, user guide, conceptual pages, and migration guide in French
    Then every section present in the English version is also present in French with equivalent depth and no untranslated fragments

  @TS-012 @FR-009 @P4 @acceptance
  Scenario: French quickstart is complete and functional end-to-end
    Given a developer browsing in French who follows the quickstart end-to-end
    When they complete every step
    Then the guide is complete and fully functional without needing to switch to English at any point

  @TS-013 @FR-010 @SC-006 @P4 @validation
  Scenario Outline: Search returns relevant results for common terms in both languages
    Given the documentation site with full-text search enabled
    When a user searches for "<search_term>" in "<language>"
    Then at least one relevant result is returned

    Examples:
      | search_term | language |
      | serializer  | en       |
      | group_id    | en       |
      | wire format | en       |
      | caching     | en       |
      | migration   | en       |
      | error       | en       |
      | serializer  | fr       |
      | group_id    | fr       |
      | wire format | fr       |
      | caching     | fr       |
      | migration   | fr       |
      | error       | fr       |
