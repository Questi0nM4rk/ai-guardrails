Feature: noConsole level detection

  # ─── CLI detection (bin field) ─────────────────────────────────────────────

  Scenario: bin field as string → off
    Given a package.json with bin field as string
    When noConsole level is detected
    Then the noConsole level should be "off"

  Scenario: bin field as object → off
    Given a package.json with bin field as object
    When noConsole level is detected
    Then the noConsole level should be "off"

  # ─── Browser framework detection ──────────────────────────────────────────

  Scenario Outline: <dep> in dependencies → error
    Given a package.json with dependency "<dep>"
    When noConsole level is detected
    Then the noConsole level should be "error"

    Examples:
      | dep          |
      | react        |
      | vue          |
      | svelte       |
      | next         |
      | nuxt         |
      | solid-js     |
      | preact       |
      | @angular/core |
      | qwik         |

  Scenario Outline: <dep> in devDependencies → error
    Given a package.json with devDependency "<dep>"
    When noConsole level is detected
    Then the noConsole level should be "error"

    Examples:
      | dep          |
      | react        |
      | vue          |
      | @angular/core |

  # ─── Browser wins over CLI ─────────────────────────────────────────────────

  Scenario: bin field + react dependency → error (browser wins)
    Given a package.json with bin and dependency "react"
    When noConsole level is detected
    Then the noConsole level should be "error"

  Scenario: bin field + vue dependency → error (browser wins)
    Given a package.json with bin and dependency "vue"
    When noConsole level is detected
    Then the noConsole level should be "error"

  # ─── Default fallthrough ───────────────────────────────────────────────────

  Scenario: express (server-side only) → warn
    Given a package.json with dependency "express"
    When noConsole level is detected
    Then the noConsole level should be "warn"

  Scenario: minimal package.json with no bin or framework → warn
    Given a minimal package.json
    When noConsole level is detected
    Then the noConsole level should be "warn"

  Scenario: null input → warn
    Given no package.json content
    When noConsole level is detected
    Then the noConsole level should be "warn"

  Scenario: non-object input (number) → warn
    Given a non-object package.json with value 42
    When noConsole level is detected
    Then the noConsole level should be "warn"

  Scenario: non-object input (string) → warn
    Given a non-object package.json with value "not-an-object"
    When noConsole level is detected
    Then the noConsole level should be "warn"
