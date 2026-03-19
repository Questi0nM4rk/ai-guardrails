Feature: Language detection

  Scenario Outline: Detects <language> by marker file
    Given a project with file "<marker>"
    When languages are detected
    Then "<language>" should be detected

    Examples:
      | language   | marker                |
      | python     | pyproject.toml        |
      | python     | src/app.py            |
      | typescript | package.json          |
      | typescript | src/index.ts          |
      | typescript | index.js              |
      | rust       | Cargo.toml            |
      | go         | go.mod                |
      | shell      | scripts/build.sh      |
      | cpp        | CMakeLists.txt        |
      | dotnet     | MyApp.csproj          |
      | lua        | src/main.lua          |

  Scenario: Universal plugin always included for empty project
    Given an empty project
    When languages are detected
    Then "universal" should be detected

  Scenario: Universal plugin always included with other languages
    Given a project with file "pyproject.toml"
    When languages are detected
    Then "universal" should be detected
    And "python" should be detected

  Scenario: Multiple languages detected simultaneously
    Given a project with files "pyproject.toml" and "package.json"
    When languages are detected
    Then "python" should be detected
    And "typescript" should be detected

  Scenario: Returns only universal for empty project
    Given an empty project
    When languages are detected
    Then only "universal" should be detected

  Scenario: ALL_PLUGINS contains 9 plugins
    When the plugin registry is inspected
    Then it should contain 9 plugins

  Scenario: Universal plugin is last in registry
    When the plugin registry is inspected
    Then the last plugin id should be "universal"

  Scenario: All plugin IDs are unique
    When the plugin registry is inspected
    Then all plugin ids should be unique

  Scenario: Plugins returned in priority order
    Given a project with files "pyproject.toml" and "Cargo.toml"
    When languages are detected
    Then "python" should appear before "rust"

  Scenario: detectLanguagesStep returns ok with detected languages
    Given a project with file "pyproject.toml"
    When the detect-languages step runs
    Then the step result status should be "ok"
    And "python" should be in the step languages
    And "universal" should be in the step languages

  Scenario: detectLanguagesStep result message contains Detected
    Given a project with file "package.json"
    When the detect-languages step runs
    Then the step result status should be "ok"
    And the step result message should contain "Detected"

  Scenario: detectLanguagesStep detects multiple languages
    Given a project with files "pyproject.toml" and "Cargo.toml"
    When the detect-languages step runs
    Then "python" should be in the step languages
    And "rust" should be in the step languages

  Scenario: Python plugin returns ruff and pyright runners
    When the "python" plugin runners are inspected
    Then the runner ids should include "ruff"
    And the runner ids should include "pyright"

  Scenario: Python plugin returns exactly 2 runners
    When the "python" plugin runners are inspected
    Then there should be 2 runners

  Scenario: TypeScript plugin returns biome and tsc runners
    When the "typescript" plugin runners are inspected
    Then the runner ids should include "biome"
    And the runner ids should include "tsc"

  Scenario: TypeScript plugin returns exactly 2 runners
    When the "typescript" plugin runners are inspected
    Then there should be 2 runners

  # Ignore path scenarios — files in dependency dirs must NOT trigger detection

  Scenario Outline: Files in ignored dirs do not trigger detection
    Given a project with only a file at ignored path "<path>"
    When languages are detected
    Then "<language>" should not be detected

    Examples:
      | language   | path                                       |
      | python     | node_modules/pkg/helper.py                 |
      | python     | .venv/lib/python3.11/site.py               |
      | typescript | node_modules/react/index.js                |
      | typescript | dist/bundle.js                             |
      | shell      | vendor/scripts/build.sh                    |
      | cpp        | build/generated/foo.cpp                    |
      | lua        | vendor/libs/module.lua                     |

  Scenario: src/app.py still triggers Python detection
    Given a project with file "src/app.py"
    When languages are detected
    Then "python" should be detected

  Scenario: pyproject.toml at root always triggers Python (marker not filtered)
    Given a project with only a file at ignored path "node_modules/pkg/helper.py"
    When languages are detected
    Then "python" should not be detected
