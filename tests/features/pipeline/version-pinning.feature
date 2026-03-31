Feature: Version pinning

  Scenario: Init writes min_version to config
    Given a project for version pin testing
    When init runs with version pinning enabled
    Then config.toml should contain "min_version"

  Scenario: Status warns when installed version is older than pinned
    Given a project pinned to version "99.0.0"
    When version status is checked
    Then a version mismatch warning should be emitted

  Scenario: Status shows no warning when version matches
    Given a project pinned to version "0.0.1"
    When version status is checked
    Then no version mismatch warning should be emitted

  Scenario: Init preserves higher existing pin on re-run
    Given a project pinned to version "99.0.0"
    When init runs with version pinning enabled
    Then config.toml should contain "99.0.0"

  Scenario: --min-version flag overrides installed version
    Given a project for version pin testing
    When init runs with --min-version "5.0.0"
    Then config.toml should contain "5.0.0"
