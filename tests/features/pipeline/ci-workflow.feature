Feature: CI workflow generation

  Scenario: Workflow contains actions/checkout@v4
    Given a project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "actions/checkout@v4"

  Scenario: Workflow contains oven-sh/setup-bun@v2
    Given a project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "oven-sh/setup-bun@v2"

  Scenario: Workflow contains bun install --frozen-lockfile
    Given a project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "bun install --frozen-lockfile"

  Scenario: Workflow contains hashFiles condition
    Given a project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "hashFiles"

  Scenario: Workflow contains bunx ai-guardrails check
    Given a project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "bunx ai-guardrails check"

  Scenario: Workflow is written to .github/workflows/ai-guardrails.yml
    Given a project for CI setup
    When the CI workflow is generated
    Then the workflow should be written to ".github/workflows/ai-guardrails.yml"

  Scenario: checkout comes before setup-bun in the workflow
    Given a project for CI setup
    When the CI workflow is generated
    Then "actions/checkout@v4" should come before "oven-sh/setup-bun@v2" in the workflow

  Scenario: setup-bun comes before bun install in the workflow
    Given a project for CI setup
    When the CI workflow is generated
    Then "oven-sh/setup-bun@v2" should come before "bun install --frozen-lockfile" in the workflow

  Scenario: bun install comes before ai-guardrails check in the workflow
    Given a project for CI setup
    When the CI workflow is generated
    Then "bun install --frozen-lockfile" should come before "bunx ai-guardrails check" in the workflow

  Scenario: Workflow result status is ok
    Given a project for CI setup
    When the CI workflow is generated
    Then the CI step result status should be "ok"

  Scenario: Workflow triggers on push
    Given a project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "push"

  Scenario: Workflow triggers on pull_request
    Given a project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "pull_request"

  Scenario: Workflow uses ubuntu-latest
    Given a project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "ubuntu-latest"

  Scenario: Workflow has jobs section
    Given a project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "jobs:"

  Scenario: Workflow has steps section
    Given a project for CI setup
    When the CI workflow is generated
    Then the workflow should contain "steps:"
