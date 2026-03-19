Feature: Config file generation

  # ─── biome generator ───────────────────────────────────────────────────────

  Scenario: biomeGenerator has correct id
    Given the biome generator
    Then the generator id should be "biome"

  Scenario: biomeGenerator has correct configFile
    Given the biome generator
    Then the generator configFile should be "biome.jsonc"

  Scenario: biomeGenerator output matches snapshot
    Given the biome generator
    When I generate with default config
    Then the output should match the snapshot

  Scenario: biomeGenerator output starts with JSONC hash header
    Given the biome generator
    When I generate with default config
    Then the output should start with a JSONC hash header

  Scenario: biomeGenerator respects lineWidth from config
    Given the biome generator
    When I generate with line_length 120
    Then the output should contain '"lineWidth": 120'

  Scenario: biomeGenerator output has schema reference when biome_version set
    Given the biome generator
    When I generate with biome_version "2.4.8"
    Then the output should contain "biomejs.dev/schemas/2.4.8/schema.json"

  Scenario: biomeGenerator omits schema when biome_version absent
    Given the biome generator
    When I generate with default config
    Then the output should not contain "$schema"

  Scenario: biomeGenerator noExplicitAny is error
    Given the biome generator
    When I generate with default config
    Then the output should contain '"noExplicitAny": "error"'

  Scenario: biomeGenerator no files section when ignorePaths is empty
    Given the biome generator
    When I generate with default config
    Then the output should not contain '"files"'

  Scenario: biomeGenerator emits files.includes with negated globs when ignorePaths set
    Given the biome generator
    When I generate with ignorePaths containing "tests/e2e/fixtures/**"
    Then the output should contain '"files"'
    And the output should contain '"includes"'
    And the output should contain '"!tests/e2e/fixtures/**"'

  Scenario: biomeGenerator all negated ignore paths present
    Given the biome generator
    When I generate with ignorePaths "tests/e2e/fixtures/**" and "vendor/**"
    Then the output should contain '"!tests/e2e/fixtures/**"'
    And the output should contain '"!vendor/**"'

  # ─── ruff generator ────────────────────────────────────────────────────────

  Scenario: ruffGenerator has correct id
    Given the ruff generator
    Then the generator id should be "ruff"

  Scenario: ruffGenerator has correct configFile
    Given the ruff generator
    Then the generator configFile should be "ruff.toml"

  Scenario: ruffGenerator output matches snapshot
    Given the ruff generator
    When I generate with default config
    Then the output should match the snapshot

  Scenario: ruffGenerator output has valid hash header
    Given the ruff generator
    When I generate with default config
    Then the output should have a valid TOML hash header

  Scenario: ruffGenerator respects line-length from config
    Given the ruff generator
    When I generate with line_length 120
    Then the output should contain "line-length = 120"

  Scenario: ruffGenerator respects indent-width from config
    Given the ruff generator
    When I generate with indent_width 2
    Then the output should contain "indent-width = 2"

  Scenario: ruffGenerator output contains select all
    Given the ruff generator
    When I generate with default config
    Then the output should contain 'select = ["ALL"]'

  # ─── lefthook generator ────────────────────────────────────────────────────

  Scenario: lefthookGenerator has correct id
    Given the lefthook generator
    Then the generator id should be "lefthook"

  Scenario: lefthookGenerator has correct configFile
    Given the lefthook generator
    Then the generator configFile should be "lefthook.yml"

  Scenario: lefthookGenerator.generate throws directly
    Given the lefthook generator
    When I call generate directly on the lefthook generator
    Then it should throw "lefthookGenerator.generate() must not be called directly"

  Scenario: generateLefthookConfig contains pre-commit section
    When I generate lefthook config with no plugins
    Then the output should contain "pre-commit:"

  Scenario: generateLefthookConfig contains commit-msg section
    When I generate lefthook config with no plugins
    Then the output should contain "commit-msg:"

  Scenario: generateLefthookConfig contains gitleaks
    When I generate lefthook config with no plugins
    Then the output should contain "gitleaks"

  Scenario: generateLefthookConfig contains codespell
    When I generate lefthook config with no plugins
    Then the output should contain "codespell"

  Scenario: no-commits-to-main blocks main branch
    When I generate lefthook config with no plugins
    Then the output should contain '"main"'

  Scenario: no-commits-to-main blocks master branch
    When I generate lefthook config with no plugins
    Then the output should contain '"master"'

  Scenario: no-commits-to-main check uses OR condition
    When I generate lefthook config with no plugins
    Then the output should match the main-or-master OR pattern

  Scenario: no exclude lines when ignorePaths is empty
    When I generate lefthook config with typescript plugin and no ignorePaths
    Then the biome-fix section should not contain "exclude:"

  Scenario: exclude line added when ignorePaths set
    When I generate lefthook config with typescript plugin and ignorePaths "tests/e2e/fixtures/**"
    Then the biome-fix section should contain "exclude:"
    And the biome-fix section should contain "tests/e2e/fixtures/"

  Scenario: codespell merges ignorePaths with default fixture pattern
    When I generate lefthook config with no plugins and ignorePaths "tests/e2e/fixtures/**"
    Then the codespell section should contain "tests/fixtures/.*"
    And the codespell section should contain "tests/e2e/fixtures/"

  Scenario: includes python section when python plugin active
    When I generate lefthook config with python plugin
    Then the output should contain "ruff"

  Scenario: includes typescript section when typescript plugin active
    When I generate lefthook config with typescript plugin
    Then the output should contain "biome"

  Scenario: lefthook output matches snapshot for python and typescript plugins
    When I generate lefthook config with python and typescript plugins
    Then the output should match the snapshot

  Scenario: lefthook output matches snapshot for no plugins
    When I generate lefthook config with no plugins
    Then the output should match the snapshot

  # ─── claude-settings generator ─────────────────────────────────────────────

  Scenario: claudeSettingsGenerator has correct id
    Given the claude-settings generator
    Then the generator id should be "claude-settings"

  Scenario: claudeSettingsGenerator has correct configFile
    Given the claude-settings generator
    Then the generator configFile should be ".claude/settings.json"

  Scenario: claudeSettingsGenerator generates valid JSON
    Given the claude-settings generator
    When I generate with default config
    Then the output should be valid JSON

  Scenario: claudeSettingsGenerator output matches snapshot
    Given the claude-settings generator
    When I generate with default config
    Then the output should match the snapshot

  Scenario: claudeSettingsGenerator includes dangerous-cmd hook for Bash
    Given the claude-settings generator
    When I generate with default config
    Then the output should contain "dangerous-cmd"
    And the output should contain '"Bash"'

  Scenario: claudeSettingsGenerator includes protect-configs hook
    Given the claude-settings generator
    When I generate with default config
    Then the output should contain "protect-configs"
    And the output should contain "Edit|Write|NotebookEdit"

  Scenario: claudeSettingsGenerator includes protect-reads hook for Read
    Given the claude-settings generator
    When I generate with default config
    Then the output should contain "protect-reads"
    And the output should contain '"Read"'

  Scenario: claudeSettingsGenerator includes DANGEROUS_DENY_GLOBS in permissions.deny
    Given the claude-settings generator
    When I generate with default config
    Then the permissions.deny array should be non-empty

  # ─── agent-rules generator ─────────────────────────────────────────────────

  Scenario: detectAgentTools detects claude from .claude directory
    Given a project with file ".claude/settings.json"
    When I detect agent tools
    Then claude should be detected

  Scenario: detectAgentTools detects cursor from .cursorrules
    Given a project with file ".cursorrules"
    When I detect agent tools
    Then cursor should be detected

  Scenario: detectAgentTools detects cursor from .cursor/rules directory
    Given a project with file ".cursor/rules/base.md"
    When I detect agent tools
    Then cursor should be detected

  Scenario: detectAgentTools detects windsurf from .windsurfrules
    Given a project with file ".windsurfrules"
    When I detect agent tools
    Then windsurf should be detected

  Scenario: detectAgentTools detects copilot from .github/copilot-instructions.md
    Given a project with file ".github/copilot-instructions.md"
    When I detect agent tools
    Then copilot should be detected

  Scenario: detectAgentTools detects cline from .clinerules
    Given a project with file ".clinerules"
    When I detect agent tools
    Then cline should be detected

  Scenario: detectAgentTools detects aider from .aider.conf.yml
    Given a project with file ".aider.conf.yml"
    When I detect agent tools
    Then aider should be detected

  Scenario: detectAgentTools returns all false for empty project
    Given an empty project
    When I detect agent tools
    Then no agent tools should be detected

  Scenario: buildAgentRules for claude contains Claude Code Specific section
    When I build agent rules for "claude"
    Then the rules should contain "Claude Code Specific"

  Scenario: buildAgentRules for cursor contains Cursor Specific section
    When I build agent rules for "cursor"
    Then the rules should contain "Cursor Specific"

  Scenario Outline: buildAgentRules all tools contain Core Principles
    When I build agent rules for "<tool>"
    Then the rules should contain "Core Principles"

    Examples:
      | tool     |
      | claude   |
      | cursor   |
      | windsurf |
      | copilot  |
      | cline    |
      | aider    |

  Scenario: AGENT_SYMLINKS cursor maps to .cursorrules
    Then AGENT_SYMLINKS cursor should be ".cursorrules"

  Scenario: AGENT_SYMLINKS windsurf maps to .windsurfrules
    Then AGENT_SYMLINKS windsurf should be ".windsurfrules"

  Scenario: agentRulesGenerator has correct id
    Given the agent-rules generator
    Then the generator id should be "agent-rules"

  Scenario: agentRulesGenerator output contains Core Principles
    Given the agent-rules generator
    When I generate with default config
    Then the output should contain "Core Principles"

  Scenario: agentRulesGenerator output starts with hash header
    Given the agent-rules generator
    When I generate with default config
    Then the output should start with "<!-- ai-guardrails:sha256="
