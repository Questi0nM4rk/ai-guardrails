Feature: Hook binary resolution

  Scenario: Generated hooks point at the bundled binary
    Given generated claude settings
    Then all hook commands should be "ai-guardrails-hk-cc-tools"

  Scenario: Generated hooks do not reference ./dist/
    Given generated claude settings
    Then no hook command should contain "./dist/"

  Scenario: Generated hooks do not use shell guards (Iron Law 4 covers infra failure)
    Given generated claude settings
    Then no hook command should contain "command -v"
