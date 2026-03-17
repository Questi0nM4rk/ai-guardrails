Feature: Init with existing configs

  Scenario: Merge preserves user ruff settings
    Given a preconfigured "python" fixture project
    When I run ai-guardrails init with merge strategy
    Then the exit code should be 0
    And "ruff.toml" should exist
    And "ruff.toml" should contain "line-length = 120"
    And "ruff.toml" should contain "select"

  Scenario: Replace overwrites existing ruff config
    Given a preconfigured "python" fixture project
    When I run ai-guardrails init with replace strategy
    Then the exit code should be 0
    And "ruff.toml" should exist
    And "ruff.toml" should not contain "line-length = 120"

  Scenario: Skip leaves existing config untouched
    Given a preconfigured "python" fixture project
    When I run ai-guardrails init with skip strategy
    Then the exit code should be 0
    And "ruff.toml" should exist
    And "ruff.toml" should contain "line-length = 120"
    And "ruff.toml" should contain "target-version = \"py310\""
