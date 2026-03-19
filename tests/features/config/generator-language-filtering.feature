Feature: Generator language filtering

  # ─── Language field assertions ─────────────────────────────────────────────

  Scenario: ruffGenerator has languages field containing python
    When the ruff generator languages are inspected
    Then the generator languages should contain "python"

  Scenario: biomeGenerator has languages field containing typescript
    When the biome generator languages are inspected
    Then the generator languages should contain "typescript"

  Scenario: ruffGenerator languages field has exactly one entry
    When the ruff generator languages are inspected
    Then the generator languages should have length 1

  Scenario: biomeGenerator languages field has exactly one entry
    When the biome generator languages are inspected
    Then the generator languages should have length 1

  Scenario: lefthookGenerator has no languages field
    When the lefthook generator languages are inspected
    Then the generator has no languages field

  Scenario: claudeSettingsGenerator has no languages field
    When the claude-settings generator languages are inspected
    Then the generator has no languages field

  Scenario: editorconfigGenerator has no languages field
    When the editorconfig generator languages are inspected
    Then the generator has no languages field

  Scenario: markdownlintGenerator has no languages field
    When the markdownlint generator languages are inspected
    Then the generator has no languages field

  Scenario: codespellGenerator has no languages field
    When the codespell generator languages are inspected
    Then the generator has no languages field

  Scenario: agentRulesGenerator has no languages field
    When the agent-rules generator languages are inspected
    Then the generator has no languages field

  # ─── Python-only project ───────────────────────────────────────────────────

  Scenario: ruff.toml written for python-only project
    Given a project with detected language "python"
    When configs are generated
    Then "ruff.toml" should be written

  Scenario: biome.jsonc NOT written for python-only project
    Given a project with detected language "python"
    When configs are generated
    Then "biome.jsonc" should not be written

  Scenario: Universal configs written for python-only project
    Given a project with detected language "python"
    When configs are generated
    Then "lefthook.yml" should be written
    And ".editorconfig" should be written

  # ─── TypeScript-only project ───────────────────────────────────────────────

  Scenario: biome.jsonc written for typescript-only project
    Given a project with detected language "typescript"
    When configs are generated
    Then "biome.jsonc" should be written

  Scenario: ruff.toml NOT written for typescript-only project
    Given a project with detected language "typescript"
    When configs are generated
    Then "ruff.toml" should not be written

  Scenario: Universal configs written for typescript-only project
    Given a project with detected language "typescript"
    When configs are generated
    Then "lefthook.yml" should be written
    And ".editorconfig" should be written

  # ─── Non-python/non-ts languages alone ────────────────────────────────────

  Scenario Outline: Neither ruff nor biome written for <language>-only project
    Given a project with detected language "<language>"
    When configs are generated
    Then "ruff.toml" should not be written
    And "biome.jsonc" should not be written
    And "lefthook.yml" should be written

    Examples:
      | language |
      | rust     |
      | go       |
      | shell    |
      | cpp      |
      | dotnet   |
      | lua      |

  # ─── Python + TypeScript ───────────────────────────────────────────────────

  Scenario: Both ruff and biome written for python+typescript project
    Given a project with detected languages "python" and "typescript"
    When configs are generated
    Then "ruff.toml" should be written
    And "biome.jsonc" should be written

  Scenario: Universal configs written for python+typescript project
    Given a project with detected languages "python" and "typescript"
    When configs are generated
    Then "lefthook.yml" should be written

  # ─── Universal generators always run ──────────────────────────────────────

  Scenario Outline: Universal generators run regardless of detected language
    Given a project with detected language "<language>"
    When configs are generated
    Then "lefthook.yml" should be written
    And ".editorconfig" should be written

    Examples:
      | language |
      | python     |
      | typescript |
      | rust       |
      | go         |
