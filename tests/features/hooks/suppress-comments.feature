Feature: Scan files for suppression comments

  Scenario Outline: Detects shellcheck disable in shell files
    When I scan "<filename>" with content "# shellcheck disable=SC2086\necho $var\n"
    Then the findings count should be 1
    And finding at line 1 should exist

    Examples:
      | filename    |
      | script.sh   |
      | script.bash |
      | config.zsh  |
      | script.ksh  |

  Scenario: Returns no findings for ksh file without suppressions
    When I scan "script.ksh" with content "echo hello\n"
    Then the findings count should be 0

  Scenario: Returns no findings for unknown extension
    When I scan "data.csv" with content "# noqa\n"
    Then the findings count should be 0

  Scenario: Skips lines containing ai-guardrails-allow
    When I scan "script.sh" with content "# shellcheck disable=SC2086  # ai-guardrails-allow: shellcheck/SC2086 \"intentional\"\n"
    Then the findings count should be 0

  Scenario: Detects noqa in Python files
    When I scan "module.py" with content "x = 1  # noqa\n"
    Then the findings count should be 1

  Scenario: Detects type ignore in Python files
    When I scan "module.py" with content "x: int = 'bad'  # type: ignore\n"
    Then the findings count should be 1

  Scenario: Detects nosemgrep in TypeScript files
    When I scan "file.ts" with content "new RegExp(x); // nosemgrep: some-rule\n"
    Then the findings count should be 1
    And finding pattern should contain "nosemgrep"

  Scenario: Generic scanner catches NOLINT in TypeScript comment
    When I scan "file.ts" with content "code(); // NOLINT\n"
    Then the findings count should be 1
    And finding pattern should be "generic-suppression-keyword"

  Scenario: Generic scanner does not flag keywords in code
    When I scan "file.ts" with content "const suppressWarning = true;\n"
    Then the findings count should be 0

  Scenario: Generic scanner does not flag suppress as ordinary English word
    When I scan "file.ts" with content "// suppress compiler noise from generated proto\n"
    Then the findings count should be 0

  Scenario: Generic scanner flags nolint in comment
    When I scan "file.ts" with content "code(); // nolint: SA1000\n"
    Then the findings count should be 1
    And finding pattern should be "generic-suppression-keyword"

  Scenario: Generic scanner ignores URLs with double slash
    When I scan "file.ts" with content "const url = \"http://nolint.io/api\";\n"
    Then the findings count should be 0

  Scenario: Generic scanner skips lines with ai-guardrails-allow
    When I scan "file.ts" with content "// nosemgrep: rule // ai-guardrails-allow: semgrep/rule \"justified\"\n"
    Then the findings count should be 0

  Scenario: Generic scanner does not double-flag explicit pattern hits
    When I scan "file.ts" with content "new RegExp(x); // nosemgrep: rule\n"
    Then the findings count should be 1
    And finding pattern should contain "nosemgrep"

  Scenario: extractComment extracts inline double-slash comment in TypeScript
    When I extract comment from "const x = 1; // some comment" for language "typescript"
    Then the extracted comment should start with " some comment"

  Scenario: extractComment extracts hash comment in Python
    When I extract comment from "x = 1  # noqa" for language "python"
    Then the extracted comment should start with " noqa"

  Scenario: extractComment does not treat hash as comment in TypeScript
    When I extract comment from "this.#privateField = 1" for language "typescript"
    Then the extracted comment should be ""

  Scenario: extractComment extracts double-dash comment in Lua
    When I extract comment from "local x = 1 -- luacheck: ignore" for language "lua"
    Then the extracted comment should start with " luacheck: ignore"

  Scenario: extractComment does not treat double-dash as comment in TypeScript
    When I extract comment from "x--" for language "typescript"
    Then the extracted comment should be ""

  Scenario: extractComment returns empty for code-only line
    When I extract comment from "const x = 1;" for language "typescript"
    Then the extracted comment should be ""

  Scenario: extractComment extracts block comment
    When I extract comment from "x = 1; /* suppress */" for language "typescript"
    Then the extracted comment should start with " suppress"

  Scenario: extractComment skips URL and finds real comment after
    When I extract comment from url-test line 1 for language "typescript"
    Then the extracted comment should start with " real comment"

  Scenario: extractComment returns empty for line with only URL
    When I extract comment from url-test line 2 for language "typescript"
    Then the extracted comment should be ""

  Scenario: extractComment finds double-slash comment after block comment
    When I extract comment from "code; /* innocuous */ // NOLINT" for language "typescript"
    Then the extracted comment should start with " NOLINT"

  Scenario: extractComment skips URL after block comment on same line
    When I extract comment from "code; /* block */ http://nolint.io/api" for language "typescript"
    Then the extracted comment should start with " block"
