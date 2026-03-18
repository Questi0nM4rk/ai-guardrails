Feature: Check pipeline

  Scenario: No issues returns ok
    Given a project with no lint issues
    When the check pipeline runs
    Then the result status should be "ok"

  Scenario: No issues returns zero issue count
    Given a project with no lint issues
    When the check pipeline runs
    Then the result issue count should be 0

  Scenario: Issues found returns error
    Given a project with 1 lint issue
    When the check pipeline runs
    Then the result status should be "error"

  Scenario: Issues found returns non-zero issue count
    Given a project with 1 lint issue
    When the check pipeline runs
    Then the result issue count should be greater than 0

  Scenario: Reports steps to console
    Given a project with no lint issues
    When the check pipeline runs
    Then the console should have recorded steps

  Scenario: Exit code 0 for no issues
    Given a project with no lint issues
    When the check pipeline runs
    Then the check exit code should be 0

  Scenario: Exit code 1 for lint issues
    Given a project with 3 lint issues
    When the check pipeline runs
    Then the check exit code should be 1

  Scenario: Exit code 2 for config error
    Given a check pipeline result with status "error" and issue count 0
    Then the check exit code for that result should be 2

  Scenario: Format flag passes through context
    Given a project with no lint issues and format flag "sarif"
    When the check pipeline runs
    Then the result status should be "ok"
