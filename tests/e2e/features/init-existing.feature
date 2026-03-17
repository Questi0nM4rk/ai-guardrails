Feature: Init with existing configs

  Scenario: Merge preserves user settings in tsconfig
    Given a preconfigured "typescript" fixture project
    When I run ai-guardrails init with merge strategy
    Then "tsconfig.json" should contain "\"strict\": true"
    And "tsconfig.json" should contain "\"baseUrl\""
    And "tsconfig.json" should contain "exactOptionalPropertyTypes"

  Scenario: Replace overwrites existing config
    Given a preconfigured "python" fixture project
    When I run ai-guardrails init with replace strategy
    Then the exit code should be 0
    And "ruff.toml" should exist

  Scenario: Skip leaves existing config untouched
    Given a preconfigured "typescript" fixture project
    When I run ai-guardrails init with skip strategy
    Then "tsconfig.json" should contain "\"strict\": false"
