Feature: Protect sensitive files from reads

  Background:
    Given the default ruleset

  Scenario Outline: Blocks read of sensitive files
    When I evaluate read of path "<path>"
    Then the decision should not be "allow"

    Examples:
      | path                        |
      | /home/user/.ssh/id_rsa      |
      | /home/user/.gnupg/secring.gpg |
      | .env                        |

  Scenario: Allows read of non-sensitive file
    When I evaluate read of path "README.md"
    Then the decision should be "allow"
