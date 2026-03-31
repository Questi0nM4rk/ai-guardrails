Feature: Staticcheck config generation

  Scenario: Generates staticcheck.conf for Go projects
    Given a Go project for staticcheck testing
    When the staticcheck config is generated
    Then the staticcheck output should contain "[checks]"
    And the staticcheck output should contain 'enabled = ["all"]'

  Scenario: Skips staticcheck.conf for non-Go projects
    Given a TypeScript project for staticcheck testing
    When staticcheck detection runs
    Then staticcheck should not be applicable
