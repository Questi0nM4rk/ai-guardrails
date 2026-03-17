Feature: Lint checking

  Scenario: Check completes on initialized typescript project
    Given a bare "typescript" fixture project
    And ai-guardrails has been initialized
    When I run ai-guardrails check
    Then the check should complete without config error

  Scenario: Check completes on initialized python project
    Given a bare "python" fixture project
    And ai-guardrails has been initialized
    When I run ai-guardrails check
    Then the check should complete without config error
