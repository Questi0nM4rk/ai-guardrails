Feature: Install hooks merge

  Scenario: Creates settings.json when absent
    Given no settings.json exists
    When install hooks step runs
    Then settings.json should be created
    And it should contain PreToolUse hooks

  Scenario: Merges hooks into existing settings
    Given settings.json exists with user permissions
    When install hooks step runs
    Then the existing permissions should be preserved
    And PreToolUse hooks should be added

  Scenario: Does not duplicate hooks on re-run
    Given settings.json exists with guardrails hooks
    When install hooks step runs
    Then PreToolUse hooks should not be duplicated

  Scenario: Unified matcher covers all CC events
    Given no settings.json exists
    When install hooks step runs
    Then hooks should include matcher "Bash|Edit|Write|NotebookEdit|Read"

  Scenario: Hook command points at the bundled binary
    Given no settings.json exists
    When install hooks step runs
    Then all installed hook commands should be "ai-guardrails-hk-cc-tools"

  Scenario: Handles malformed JSON gracefully
    Given settings.json contains invalid JSON
    When install hooks step runs
    Then the step should succeed
    And settings.json should contain valid hooks
