Feature: Hook binary resolution

  Scenario: Generated hooks use command -v guard
    Given generated claude settings
    Then all hook commands should contain "command -v ai-guardrails"

  Scenario: Generated hooks do not reference ./dist/
    Given generated claude settings
    Then no hook command should contain "./dist/"

  Scenario: Hooks use ai-guardrails as binary name
    Given generated claude settings
    Then hook commands should use "ai-guardrails" not "./dist/ai-guardrails"
