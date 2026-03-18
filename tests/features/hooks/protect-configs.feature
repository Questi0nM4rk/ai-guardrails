Feature: Protect config files from writes

  Background:
    Given the default ruleset

  Scenario Outline: Blocks write to protected config files
    When I evaluate write to path "<path>"
    Then the decision should not be "allow"

    Examples:
      | path                   |
      | .env                   |
      | biome.jsonc            |
      | .claude/settings.json  |
      | package.json           |

  Scenario: Allows write to regular source file
    When I evaluate write to path "src/main.ts"
    Then the decision should be "allow"

  Scenario: Blocks bash redirect to .env
    When I evaluate bash command "cat secret > .env"
    Then the decision should not be "allow"

  Scenario: Allows safe bash command
    When I evaluate bash command "echo hello"
    Then the decision should be "allow"
