Feature: Install pipeline — machine-level setup only

  Background: install does not mutate the project or global Claude settings

  Scenario: Returns ok when hook-kit is available
    Given a default install project
    When the install pipeline runs
    Then the result status should be "ok"

  Scenario: Does not write any project files
    Given a default install project
    When the install pipeline runs
    Then no project files should be written

  Scenario: Does not invoke lefthook install
    Given a default install project
    When the install pipeline runs
    Then lefthook install should not have been called

  Scenario: Does not mutate ~/.claude/settings.json
    Given a default install project
    When the install pipeline runs
    Then no file ending with ".claude/settings.json" should be written

  Scenario: Install exit code 0 on success
    Given an install result with status "ok"
    Then the install exit code should be 0

  Scenario: Install exit code 2 on error
    Given an install result with status "error"
    Then the install exit code should be 2
