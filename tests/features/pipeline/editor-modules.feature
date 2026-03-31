Feature: Editor on-save modules

  # VS Code
  Scenario: Generates VS Code settings for TypeScript project
    Given a TypeScript project for vscode on-save testing
    When the vscode-on-save module executes
    Then the editor module should write ".vscode/settings.json"
    And the settings should contain "biomejs.biome"

  Scenario: Generates VS Code settings for Python project
    Given a Python project for vscode on-save testing
    When the vscode-on-save module executes
    Then the editor module should write ".vscode/settings.json"
    And the settings should contain "charliermarsh.ruff"

  Scenario: VS Code merges without overwriting existing settings
    Given a TypeScript project with existing VS Code settings
    When the vscode-on-save module executes
    Then existing settings keys should be preserved

  Scenario: VS Code generates extensions.json
    Given a TypeScript project for vscode on-save testing
    When the vscode-on-save module executes
    Then the editor module should write ".vscode/extensions.json"
    And extensions should recommend "biomejs.biome"

  Scenario: VS Code skips when no supported languages
    Given a project with no supported languages for vscode
    When the vscode-on-save module executes
    Then the editor module should return status "skipped"

  # Helix
  Scenario: Generates Helix config for TypeScript
    Given a TypeScript project for helix on-save testing
    When the helix-on-save module executes
    Then the editor module should write ".helix/languages.toml"
    And the editor config should contain "biome"

  Scenario: Helix skips when file exists
    Given a project with an existing helix languages config
    When the helix-on-save module executes
    Then the editor module should return status "skipped"

  Scenario: Helix skips when no supported languages
    Given a project with no supported languages for helix
    When the helix-on-save module executes
    Then the editor module should return status "skipped"

  # Neovim
  Scenario: Generates nvim config for TypeScript
    Given a TypeScript project for nvim on-save testing
    When the nvim-on-save module executes
    Then the editor module should write ".nvim/conform.lua"
    And the editor config should contain "biome"

  Scenario: Nvim skips when file exists
    Given a project with an existing nvim conform config
    When the nvim-on-save module executes
    Then the editor module should return status "skipped"

  # Zed
  Scenario: Generates Zed settings for TypeScript
    Given a TypeScript project for zed on-save testing
    When the zed-on-save module executes
    Then the editor module should write ".zed/settings.json"
    And the settings should contain "biome"

  Scenario: Zed merges without overwriting existing settings
    Given a TypeScript project with existing Zed settings
    When the zed-on-save module executes
    Then existing Zed settings keys should be preserved

  Scenario: Zed skips when no supported languages
    Given a project with no supported languages for zed
    When the zed-on-save module executes
    Then the editor module should return status "skipped"
