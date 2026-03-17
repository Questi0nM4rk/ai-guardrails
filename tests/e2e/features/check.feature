Feature: Lint checking

  Scenario: Check runs on initialized typescript project
    Given a bare "typescript" fixture project
    And ai-guardrails has been initialized
    When I run ai-guardrails check
    Then the output should contain at least 1 violation

  Scenario: Check finds ruff violations in python project
    Given a bare "python" fixture project
    And ai-guardrails has been initialized
    When I run ai-guardrails check
    Then the exit code should not be 0
