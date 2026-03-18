Feature: Parse ai-guardrails-allow comments

  Scenario Outline: Parses allow comments in various comment styles
    When I parse allow comments from lines:
      | <line> |
    Then there should be 1 allow comment
    And allow comment 1 should have rule "<rule>"
    And allow comment 1 should have reason "<reason>"
    And allow comment 1 should be on line 1

    Examples:
      | line                                                                           | rule                 | reason                    |
      | x = 1  # ai-guardrails-allow: ruff/E501 "URL cannot be shortened"             | ruff/E501            | URL cannot be shortened   |
      | const x = 1; // ai-guardrails-allow: biome/noExplicitAny "external API type"  | biome/noExplicitAny  | external API type         |
      | local x = val -- ai-guardrails-allow: luacheck/W311 "loop variable shadowing" | luacheck/W311        | loop variable shadowing   |

  Scenario: Returns empty array for lines with no allow comments
    When I parse allow comments from lines:
      | x = 1                  |
      | y = 2                  |
      | # just a regular comment |
    Then there should be 0 allow comments

  Scenario: Returns empty array for empty input
    When I parse allow comments from no lines
    Then there should be 0 allow comments

  Scenario: Handles multiple allow comments in the same file
    When I parse allow comments from lines:
      | x = 1                                              |
      | # ai-guardrails-allow: ruff/E501 "long URL"        |
      | y = 2                                              |
      | // ai-guardrails-allow: biome/noAny "external"     |
    Then there should be 2 allow comments
    And allow comment 1 should have rule "ruff/E501"
    And allow comment 1 should be on line 2
    And allow comment 2 should have rule "biome/noAny"
    And allow comment 2 should be on line 4

  Scenario: Extracts rule and reason correctly
    When I parse allow comments from lines:
      | code  # ai-guardrails-allow: shellcheck/SC2086 "word splitting intentional" |
    Then allow comment 1 should have rule "shellcheck/SC2086"
    And allow comment 1 should have reason "word splitting intentional"

  Scenario: Returns correct 1-indexed line numbers
    When I parse allow comments from lines:
      | line 1                                      |
      | line 2                                      |
      | # ai-guardrails-allow: ruff/E501 "test"     |
      | line 4                                      |
    Then allow comment 1 should be on line 3

  Scenario: Skips allow comment without a quoted reason
    When I parse allow comments from lines:
      | # ai-guardrails-allow: ruff/E501 |
    Then there should be 0 allow comments

  Scenario: Handles allow comment as standalone comment line
    When I parse allow comments from lines:
      | # ai-guardrails-allow: ruff/T201 "CLI tool" |
    Then there should be 1 allow comment
    And allow comment 1 should have rule "ruff/T201"

  Scenario: Trims whitespace around rule and reason
    When I parse allow comments from lines:
      | x = 1  #  ai-guardrails-allow:  ruff/E501  "reason here" |
    Then there should be 1 allow comment
    And allow comment 1 should have rule "ruff/E501"
    And allow comment 1 should have reason "reason here"
