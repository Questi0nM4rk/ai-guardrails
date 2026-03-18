Feature: Config loading and merging

  Scenario: Load valid machine config from TOML
    Given a file at "/machine.toml" containing:
      """
      profile = "strict"
      [[ignore]]
      rule = "ruff/E501"
      reason = "Too strict"
      """
    When I load the machine config from "/machine.toml"
    Then the profile should be "strict"
    And the ignore list should have 1 entry
    And the first ignore rule should be "ruff/E501"

  Scenario: Machine config defaults when file does not exist
    Given no file at "/nonexistent.toml"
    When I load the machine config from "/nonexistent.toml"
    Then the profile should be "standard"
    And the ignore list should be empty

  Scenario: Machine config defaults for empty TOML file
    Given a file at "/empty.toml" containing ""
    When I load the machine config from "/empty.toml"
    Then the profile should be "standard"

  Scenario: Machine config throws on malformed TOML
    Given a file at "/bad.toml" containing "profile = [unclosed"
    When I load the machine config from "/bad.toml"
    Then it should throw an error

  Scenario: Load valid project config
    Given a file at "/proj/.ai-guardrails/config.toml" containing:
      """
      profile = "minimal"
      [config]
      line_length = 100
      """
    When I load the project config from "/proj"
    Then the profile should be "minimal"
    And the config line_length should be 100

  Scenario: Project config defaults when file does not exist
    Given no file at "/proj/.ai-guardrails/config.toml"
    When I load the project config from "/proj"
    Then the profile should be undefined
    And the ignore list should be empty

  Scenario: Project profile overrides machine profile
    Given a machine config with profile "strict"
    And a project config with profile "minimal"
    When I resolve the config
    Then the resolved profile should be "minimal"

  Scenario: Machine profile used when project has none
    Given a machine config with profile "strict"
    And a project config with no profile
    When I resolve the config
    Then the resolved profile should be "strict"

  Scenario: Ignore lists are merged from machine and project
    Given a machine config ignoring "ruff/E501" with reason "machine"
    And a project config ignoring "ruff/D" with reason "project"
    When I resolve the config
    Then the resolved ignore list should have 2 entries
    And the resolved ignore list should contain "ruff/E501"
    And the resolved ignore list should contain "ruff/D"

  Scenario: Project ignore overrides machine ignore for same rule
    Given a machine config ignoring "ruff/E501" with reason "machine reason"
    And a project config ignoring "ruff/E501" with reason "project reason"
    When I resolve the config
    Then the resolved ignore list should have 1 entry
    And the first ignore entry reason should be "project reason"

  Scenario: isAllowed returns true for globally ignored rule
    Given a resolved config ignoring "ruff/E501"
    Then isAllowed for rule "ruff/E501" on path "src/foo.py" should be true

  Scenario: isAllowed returns false for non-ignored rule
    Given a resolved config with no ignores
    Then isAllowed for rule "ruff/E501" on path "src/foo.py" should be false

  Scenario: isAllowed returns true when rule matches glob allow entry
    Given a resolved config allowing "ruff/ARG002" for glob "tests/**/*.py"
    Then isAllowed for rule "ruff/ARG002" on path "tests/unit/foo.py" should be true
    And isAllowed for rule "ruff/ARG002" on path "src/foo.py" should be false

  Scenario: isAllowed is false for different rule matching allow glob
    Given a resolved config allowing "ruff/ARG002" for glob "tests/**/*.py"
    Then isAllowed for rule "ruff/E501" on path "tests/unit/foo.py" should be false

  Scenario: ignoredRules set contains all globally ignored rules
    Given a machine config ignoring "ruff/E501"
    And a project config ignoring "ruff/D"
    When I resolve the config
    Then ignoredRules should contain "ruff/E501"
    And ignoredRules should contain "ruff/D"
    And ignoredRules should not contain "ruff/W"
