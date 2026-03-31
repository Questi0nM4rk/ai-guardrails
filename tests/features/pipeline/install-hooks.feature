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

  Scenario: All three matchers are present
    Given no settings.json exists
    When install hooks step runs
    Then hooks should include matcher "Bash"
    And hooks should include matcher "Edit|Write|NotebookEdit"
    And hooks should include matcher "Read"

  Scenario: Hook commands use command -v guard
    Given no settings.json exists
    When install hooks step runs
    Then all hook commands should contain "command -v ai-guardrails"

  Scenario: Handles malformed JSON gracefully
    Given settings.json contains invalid JSON
    When install hooks step runs
    Then the step should succeed
    And settings.json should contain valid hooks
