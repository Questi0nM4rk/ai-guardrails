Feature: Fresh project initialization

  Scenario Outline: Init on bare <lang> project
    Given a bare "<lang>" fixture project
    When I run ai-guardrails init
    Then the exit code should be 0
    And ".lefthook.yml" should exist
    And ".claude/settings.json" should exist

    Examples:
      | lang       |
      | typescript |
      | python     |
      | rust       |
      | go         |
      | shell      |
      | cpp        |
      | lua        |
