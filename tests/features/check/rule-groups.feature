Feature: Rule groups structure and toggling

  Scenario: All rule groups count
    Given all rule groups
    Then there should be 6 groups

  Scenario: Each group has a unique id
    Given all rule groups
    Then each group should have a unique id

  Scenario: Each group has at least one command rule
    Given all rule groups
    Then each group should have at least one command rule

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

  Scenario: collectCommandRules aggregates all group rules
    Given all rule groups
    Then collectCommandRules should return all rules from all groups

  Scenario: collectCommandRules returns empty for empty input
    When I collect command rules from no groups
    Then the result should be empty

  Scenario: collectCommandRules returns only rules from selected groups
    Given all rule groups
    When I collect command rules from the "destructive-rm" group only
    Then the result should have 1 rule
    And the first rule should have cmd "rm"

  Scenario: collectDenyGlobs aggregates all group globs
    Given all rule groups
    Then collectDenyGlobs should return all globs from all groups

  Scenario: collectDenyGlobs returns empty for empty input
    When I collect deny globs from no groups
    Then the result should be empty

  Scenario: COMMAND_RULES does not contain a RecurseRule
    Given the COMMAND_RULES export
    Then it should not contain a recurse rule

  Scenario: COMMAND_RULES contains rm CallRule
    Given the COMMAND_RULES export
    Then it should contain an rm call rule with --recursive and --force

  Scenario: DANGEROUS_DENY_GLOBS matches collectDenyGlobs output
    Given all rule groups
    Then DANGEROUS_DENY_GLOBS should equal collectDenyGlobs output

  Scenario: DEFAULT_PATH_RULES has .env write rule
    Given the default path rules
    Then there should be a write rule matching ".env"

  Scenario: DEFAULT_PATH_RULES has .ssh read rule
    Given the default path rules
    Then there should be a read rule matching "/home/user/.ssh/id_rsa"

  Scenario: buildRuleSet returns default rules with empty config
    Given a ruleset built with empty config
    Then the ruleset should have command rules
    And the ruleset should have path rules

  Scenario: buildRuleSet injects recurse rule
    Given a ruleset built with empty config
    Then the first command rule should be a recurse rule

  Scenario: buildRuleSet adds protectWrite for custom managedFiles
    Given a ruleset built with managedFiles containing "custom.lock"
    Then the path rules should match "custom.lock" for write

  Scenario: buildRuleSet with empty config returns all rules
    Given a ruleset built with empty config
    Then the command rule count should equal 1 plus the total domain rules

  Scenario: Disabling destructive-rm removes its rules
    Given a ruleset built with disabledGroups "destructive-rm"
    Then the command rule count should be reduced by the "destructive-rm" group size

  Scenario: Disabling multiple groups removes their rules
    Given a ruleset built with disabledGroups "destructive-rm" and "chmod-world-writable"
    Then the command rule count should be reduced by those groups combined

  Scenario: Recurse rule always present when all groups disabled
    Given a ruleset built with all groups disabled
    Then the command rule count should be 1
    And the first command rule should be a recurse rule

  Scenario: Unknown group names do not break buildRuleSet
    Given a ruleset built with disabledGroups "nonexistent"
    Then the command rule count should equal 1 plus the total domain rules

  Scenario: Empty disabledGroups enables all groups
    Given a ruleset built with empty disabledGroups
    Then the command rule count should equal 1 plus the total domain rules

  Scenario: Path rules unaffected by disabledGroups
    Given a ruleset built with disabledGroups "destructive-rm"
    Then both rulesets should have the same number of path rules
