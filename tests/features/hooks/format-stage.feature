Feature: Format stage configuration

  Scenario Outline: FORMATTERS has entries for common file types
    Then FORMATTERS should match glob for file "<filename>"

    Examples:
      | filename |
      | foo.py   |
      | foo.ts   |
      | foo.rs   |
      | foo.go   |
      | foo.lua  |
      | foo.c    |
      | foo.cpp  |

  Scenario: Each formatter has a non-empty glob
    Then each formatter should have a non-empty glob

  Scenario: Each formatter cmd returns a non-empty array
    Then each formatter cmd should return a non-empty array

  Scenario: getStagedFiles returns an array without throwing
    When I call getStagedFiles
    Then the result should be an array

  Scenario: getStagedFiles filters out empty strings from git output
    When I call getStagedFiles
    Then no file in the result should be an empty string

  Scenario: FORMATTERS cmd entries return non-empty arrays for tryRun
    Then each formatter cmd should return a non-empty array with a truthy first element
