Feature: GitHub init modules

  # PR Template
  Scenario: Generates PR template when absent
    Given a GitHub project for PR template testing
    When the github-pr-template module executes
    Then the github module should write ".github/pull_request_template.md"
    And the template should contain "## Summary"
    And the template should contain "## Test plan"

  Scenario: Skips PR template when file already exists
    Given a GitHub project with existing PR template
    When the github-pr-template module executes
    Then the module should return status "skipped"

  # CodeRabbit Reviewer
  Scenario: Generates .coderabbit.yaml when absent
    Given a GitHub project with authentication
    When the github-cc-reviewer module executes
    Then the github module should write ".coderabbit.yaml"
    And the config should contain "enable_free_tier: true"
    And the config should contain "profile: \"auto\""

  Scenario: Skips .coderabbit.yaml when file exists
    Given a GitHub project with existing .coderabbit.yaml
    When the github-cc-reviewer module executes
    Then the module should return status "skipped"

  Scenario: Skips cc-reviewer when not authenticated
    Given a GitHub project without authentication
    When the github-cc-reviewer module executes
    Then the module should return status "skipped"

  # Branch Protection
  Scenario: Calls gh API for branch protection
    Given a GitHub project with authentication and workflows
    When the github-branch-protection module executes
    Then gh api should be called with "branches/main/protection"
    And the call should include "required_pull_request_reviews"

  Scenario: Skips branch protection when not authenticated
    Given a GitHub project without authentication
    When the github-branch-protection module executes
    Then the module should return status "skipped"

  Scenario: Includes workflow job names as required status checks
    Given a GitHub project with authentication and a workflow named "Test & Coverage"
    When the github-branch-protection module executes
    Then the call should include "Test & Coverage" in required status checks

  # Protected Patterns
  Scenario: Creates ruleset for release branches
    Given a GitHub project with authentication and branch protection
    When the github-protected-patterns module executes
    Then gh api should be called with "rulesets"
    And the call should include "release/*"

  Scenario: Skips rulesets when not authenticated
    Given a GitHub project without authentication
    When the github-protected-patterns module executes
    Then the module should return status "skipped"
