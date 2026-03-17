Feature: Multi-language monorepo

  Scenario: Two languages in monorepo
    Given a monorepo combining bare "typescript" and bare "python"
    When I run ai-guardrails init
    Then "biome.jsonc" should exist
    And "ruff.toml" should exist

  Scenario: Random 3-language monorepo
    Given a monorepo with 3 random bare languages
    When I run ai-guardrails init
    Then all detected languages should have configs
