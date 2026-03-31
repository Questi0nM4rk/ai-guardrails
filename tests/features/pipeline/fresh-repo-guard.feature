Feature: Fresh repo guard in lefthook

  Scenario: Lefthook config includes fresh repo guard
    Given a generated lefthook config
    Then the config should contain "git rev-list --count HEAD"

  Scenario: Fresh repo guard comes before branch check
    Given a generated lefthook config
    Then "rev-list" should come before "rev-parse" in the no-commits-to-main section

  Scenario: No-commits-to-main blocks commits on main after first commit
    Given a generated lefthook config
    Then the config should contain "Direct commits to main are not allowed"
