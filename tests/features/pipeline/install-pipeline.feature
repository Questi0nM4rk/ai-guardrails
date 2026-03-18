Feature: Install pipeline

  Scenario: Returns ok and writes all config files
    Given a default install project
    When the install pipeline runs
    Then the result status should be "ok"
    And at least as many files as generators should be written

  Scenario: Writes lefthook.yml
    Given a default install project
    When the install pipeline runs
    Then a file ending with "lefthook.yml" should be written

  Scenario: Runs lefthook install
    Given a default install project
    When the install pipeline runs
    Then lefthook install should have been called

  Scenario: Writes CI workflow file
    Given a default install project
    When the install pipeline runs
    Then a file containing "ai-guardrails.yml" should be written

  Scenario: Skips hooks when noHooks flag is set
    Given a default install project with noHooks flag
    When the install pipeline runs
    Then lefthook install should not have been called

  Scenario: Skips CI when noCi flag is set
    Given a default install project with noCi flag
    When the install pipeline runs
    Then no file containing "ai-guardrails.yml" should be written

  Scenario: Reports progress steps to console
    Given a default install project
    When the install pipeline runs
    Then the console should have recorded steps
    And the console should have recorded successes

  Scenario: Install exit code 0 on success
    Given an install result with status "ok"
    Then the install exit code should be 0

  Scenario: Install exit code 2 on error
    Given an install result with status "error"
    Then the install exit code should be 2
