Feature: Agent instructions generation

  Scenario: Init generates AGENTS.md
    Given a project for agent instructions testing
    When agent instructions step runs
    Then the agent file "AGENTS.md" should be written

  Scenario: AGENTS.md contains base rules
    Given a project for agent instructions testing
    When agent instructions step runs
    Then the agent file "AGENTS.md" should contain "Core Principles"

  Scenario: Init creates CLAUDE.md when absent
    Given a project without CLAUDE.md
    When agent instructions step runs
    Then the agent file "CLAUDE.md" should be written
    And the agent file "CLAUDE.md" should contain "AI Guardrails"

  Scenario: Init preserves user-authored CLAUDE.md by default (BUG-006)
    Given a project with existing CLAUDE.md
    When agent instructions step runs
    Then "CLAUDE.md" should contain the original content
    And the agent file "CLAUDE.md" should not contain "AI Guardrails"

  Scenario: Init appends guardrails to CLAUDE.md when --force is set
    Given a project with existing CLAUDE.md
    When agent instructions step runs with force
    Then the agent file "CLAUDE.md" should contain "AI Guardrails"
    And "CLAUDE.md" should contain the original content

  Scenario: Init does not duplicate guardrails section
    Given a project with CLAUDE.md containing "AI Guardrails"
    When agent instructions step runs
    Then "CLAUDE.md" should contain exactly one "AI Guardrails" section
