Feature: CI workflow generation

  Scenario: Workflow contains actions/checkout@v4
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "actions/checkout@v4"

  Scenario: Workflow contains oven-sh/setup-bun@v2 for typescript
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "oven-sh/setup-bun@v2"

  Scenario: Workflow contains bun install --frozen-lockfile for typescript
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "bun install --frozen-lockfile"

  Scenario: Workflow contains hashFiles condition for typescript
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "hashFiles"

  Scenario: Workflow does not reference ai-guardrails binary
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should not contain "ai-guardrails"

  Scenario: Workflow contains biome check for typescript
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "bunx biome check ."

  Scenario: Workflow contains tsc --noEmit for typescript
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "bunx tsc --noEmit"

  Scenario: Workflow is written to .github/workflows/ai-guardrails.yml
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should be written to ".github/workflows/ai-guardrails.yml"

  Scenario: checkout comes before setup-bun in the workflow
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then "actions/checkout@v4" should come before "oven-sh/setup-bun@v2" in the workflow

  Scenario: setup-bun comes before bun install in the workflow
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then "oven-sh/setup-bun@v2" should come before "bun install --frozen-lockfile" in the workflow

  Scenario: bun install comes before biome check in the workflow
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then "bun install --frozen-lockfile" should come before "bunx biome check ." in the workflow

  Scenario: Workflow result status is ok
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the CI step result status should be "ok"

  Scenario: Workflow triggers on push
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "push"

  Scenario: Workflow triggers on pull_request
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "pull_request"

  Scenario: Workflow uses ubuntu-latest
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "ubuntu-latest"

  Scenario: Workflow has jobs section
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "jobs:"

  Scenario: Workflow has steps section
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "steps:"

  Scenario: Python workflow contains ruff check
    Given a python project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "ruff check ."

  Scenario: Python workflow contains pyright
    Given a python project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "pyright"

  Scenario: Python workflow contains setup-python
    Given a python project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "actions/setup-python@v5"

  Scenario: Python workflow does not contain biome
    Given a python project for CI setup
    When the CI workflow is generated
    Then the workflow should not contain "biome"

  Scenario: Empty language set contains only universal checks
    Given an empty language project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "codespell"
    And the workflow should contain "markdownlint-cli2"
    And the workflow should contain "gitleaks"

  Scenario: Universal checks always present for typescript
    Given a typescript project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "codespell"
    And the workflow should contain "markdownlint-cli2"
    And the workflow should contain "gitleaks detect --no-banner"
