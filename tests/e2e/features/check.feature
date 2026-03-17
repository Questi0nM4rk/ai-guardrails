Feature: Lint checking

  Scenario Outline: Check catches violations in <lang>
    Given a bare "<lang>" fixture project
    And ai-guardrails has been initialized
    When I run ai-guardrails check
    Then the exit code should not be 0
    And the output should contain at least 1 violation

    Examples:
      | lang       |
      | typescript |
      | python     |
