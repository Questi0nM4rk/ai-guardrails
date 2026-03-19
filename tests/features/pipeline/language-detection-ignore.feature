Feature: Language detection ignore paths

  # ─── DEFAULT_IGNORE constant ───────────────────────────────────────────────

  Scenario: DEFAULT_IGNORE contains node_modules
    When the DEFAULT_IGNORE list is inspected
    Then it should contain the pattern "node_modules/**"

  Scenario: DEFAULT_IGNORE contains .venv
    When the DEFAULT_IGNORE list is inspected
    Then it should contain the pattern ".venv/**"

  Scenario: DEFAULT_IGNORE contains venv
    When the DEFAULT_IGNORE list is inspected
    Then it should contain the pattern "venv/**"

  Scenario: DEFAULT_IGNORE contains vendor
    When the DEFAULT_IGNORE list is inspected
    Then it should contain the pattern "vendor/**"

  Scenario: DEFAULT_IGNORE contains dist
    When the DEFAULT_IGNORE list is inspected
    Then it should contain the pattern "dist/**"

  Scenario: DEFAULT_IGNORE contains build
    When the DEFAULT_IGNORE list is inspected
    Then it should contain the pattern "build/**"

  Scenario: DEFAULT_IGNORE contains target
    When the DEFAULT_IGNORE list is inspected
    Then it should contain the pattern "target/**"

  Scenario: DEFAULT_IGNORE contains __pycache__
    When the DEFAULT_IGNORE list is inspected
    Then it should contain the pattern "__pycache__/**"

  # ─── Marker-file detection wins over ignored globs ─────────────────────────

  Scenario: pyproject.toml at root triggers Python despite .py only in node_modules
    Given a project with files "pyproject.toml" and "node_modules/dep/helper.py"
    When languages are detected
    Then "python" should be detected

  Scenario: package.json at root triggers TypeScript despite .ts only in dist
    Given a project with files "package.json" and "dist/bundle.ts"
    When languages are detected
    Then "typescript" should be detected

  # ─── go.mod and Cargo.toml are marker files (not glob-detected) ───────────

  Scenario: go.mod at root triggers Go detection
    Given a project with file "go.mod"
    When languages are detected
    Then "go" should be detected

  Scenario: Cargo.toml at root triggers Rust detection
    Given a project with file "Cargo.toml"
    When languages are detected
    Then "rust" should be detected

  # ─── Source files in non-ignored dirs are detected ────────────────────────

  Scenario: Python file in src/ triggers detection
    Given a project with file "src/app.py"
    When languages are detected
    Then "python" should be detected

  Scenario: TypeScript file in lib/ triggers detection
    Given a project with file "lib/helper.ts"
    When languages are detected
    Then "typescript" should be detected

  Scenario: Shell file in scripts/ triggers detection
    Given a project with file "scripts/build.sh"
    When languages are detected
    Then "shell" should be detected

  # ─── Files in multiple ignored dirs at once ────────────────────────────────

  Scenario Outline: File only in <dir> does not trigger <language>
    Given a project with only a file at ignored path "<path>"
    When languages are detected
    Then "<language>" should not be detected

    Examples:
      | language   | path                            | dir             |
      | python     | .venv/lib/site-packages/x.py    | .venv           |
      | python     | venv/lib/python3.11/x.py        | venv            |
      | python     | __pycache__/cache.py            | __pycache__     |
      | typescript | build/output.ts                 | build           |
      | shell      | target/release/build.sh         | target          |

  # ─── Universal plugin is always detected ──────────────────────────────────

  Scenario: Universal plugin detected even when all source files are in ignored dirs
    Given a project with only a file at ignored path "node_modules/pkg/helper.py"
    When languages are detected
    Then "universal" should be detected
