Feature: Rule groups structure and toggling

  Scenario: All rule groups count
    Given all rule groups
    Then there should be 6 groups

  Scenario: Each group has a unique id
    Given all rule groups
    Then each group should have a unique id

  Scenario: Each group has at least one deny glob
    Given all rule groups
    Then each group should have at least one deny glob

  Scenario: Expected group ids are present
    Given all rule groups
    Then the group ids should include "destructive-rm"
    And the group ids should include "git-force-push"
    And the group ids should include "git-destructive"
    And the group ids should include "git-bypass-hooks"
    And the group ids should include "chmod-world-writable"
    And the group ids should include "remote-code-exec"

  Scenario: DANGEROUS_DENY_GLOBS matches collectDenyGlobs output
    Given all rule groups
    Then DANGEROUS_DENY_GLOBS should equal collectDenyGlobs output

  Scenario: buildAllModules with empty config catches dangerous rm
    Given a ruleset built with empty config
    When I evaluate bash command "rm -rf /tmp/scratch"
    Then the decision should be "ask"

  Scenario: buildAllModules with managedFiles protects custom file
    Given a ruleset built with managedFiles containing "custom.lock"
    When I evaluate write to path "/repo/custom.lock"
    Then the decision should be "ask"

  Scenario: Disabling destructive-rm removes its rule
    Given a ruleset built with disabledGroups "destructive-rm"
    When I evaluate bash command "rm -rf /tmp/scratch"
    Then the decision should be "allow"

  Scenario: Other groups still fire when destructive-rm is disabled
    Given a ruleset built with disabledGroups "destructive-rm"
    When I evaluate bash command "git push --force origin main"
    Then the decision should be "ask"

  Scenario: Disabling all groups produces a permissive bash ruleset
    Given a ruleset built with all groups disabled
    When I evaluate bash command "rm -rf /tmp/scratch"
    Then the decision should be "allow"

  Scenario: Unknown group names do not break buildAllModules
    Given a ruleset built with disabledGroups "nonexistent"
    When I evaluate bash command "rm -rf /tmp/scratch"
    Then the decision should be "ask"

  Scenario: Empty disabledGroups enables all groups
    Given a ruleset built with empty disabledGroups
    When I evaluate bash command "rm -rf /tmp/scratch"
    Then the decision should be "ask"

  Scenario: Path rules unaffected by disabledGroups
    Given a ruleset built with disabledGroups "destructive-rm"
    When I evaluate write to path "/tmp/.env"
    Then the decision should be "ask"
