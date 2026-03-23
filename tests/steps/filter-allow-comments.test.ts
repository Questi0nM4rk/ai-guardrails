import { describe, expect, test } from "bun:test";
import type { LintIssue } from "@/models/lint-issue";
import { filterAllowComments } from "@/steps/filter-allow-comments";
import { FakeFileManager } from "../fakes/fake-file-manager";

function makeIssue(overrides: Partial<LintIssue> = {}): LintIssue {
  return {
    rule: "biome/noConsole",
    linter: "biome",
    file: "/project/src/foo.ts",
    line: 3,
    col: 1,
    message: "Unexpected console statement",
    severity: "warning",
    fingerprint: "fp-abc",
    ...overrides,
  };
}

describe("filterAllowComments", () => {
  test("returns empty array when no issues", async () => {
    const fm = new FakeFileManager();
    const result = await filterAllowComments([], fm);
    expect(result).toHaveLength(0);
  });

  test("returns all issues when no allow comments in file", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/src/foo.ts", "const x = 1;\nconsole.log(x);\n");
    const issues = [makeIssue({ line: 2 })];

    const result = await filterAllowComments(issues, fm);
    expect(result).toHaveLength(1);
  });

  test("same-line comment suppresses issue on that line", async () => {
    const fm = new FakeFileManager();
    // Issue is on line 2, comment also on line 2
    fm.seed(
      "/project/src/foo.ts",
      'const x = 1;\nconsole.log(x); // ai-guardrails-allow biome/noConsole "CLI tool uses console"\n'
    );
    const issues = [makeIssue({ line: 2 })];

    const result = await filterAllowComments(issues, fm);
    expect(result).toHaveLength(0);
  });

  test("next-line comment suppresses issue on the following line", async () => {
    const fm = new FakeFileManager();
    // Comment on line 1, issue on line 2
    fm.seed(
      "/project/src/foo.ts",
      '// ai-guardrails-allow biome/noConsole "CLI tool uses console"\nconsole.log("hi");\n'
    );
    const issues = [makeIssue({ line: 2 })];

    const result = await filterAllowComments(issues, fm);
    expect(result).toHaveLength(0);
  });

  test("mismatched rule is not suppressed", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      "/project/src/foo.ts",
      '// ai-guardrails-allow ruff/E501 "URL too long"\nconsole.log("hi");\n'
    );
    const issues = [makeIssue({ rule: "biome/noConsole", line: 2 })];

    const result = await filterAllowComments(issues, fm);
    expect(result).toHaveLength(1);
  });

  test("comment two lines above does not suppress issue", async () => {
    const fm = new FakeFileManager();
    // Comment on line 1, issue on line 3 — gap of 2 lines, not suppressed
    fm.seed(
      "/project/src/foo.ts",
      '// ai-guardrails-allow biome/noConsole "reason"\nconst x = 1;\nconsole.log(x);\n'
    );
    const issues = [makeIssue({ line: 3 })];

    const result = await filterAllowComments(issues, fm);
    expect(result).toHaveLength(1);
  });

  test("missing file handled gracefully — issues returned unchanged", async () => {
    const fm = new FakeFileManager();
    // /project/src/missing.ts is not seeded
    const issues = [makeIssue({ file: "/project/src/missing.ts", line: 1 })];

    const result = await filterAllowComments(issues, fm);
    expect(result).toHaveLength(1);
  });

  test("multiple allow comments in one file", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      "/project/src/foo.ts",
      [
        '// ai-guardrails-allow biome/noConsole "reason1"',
        "console.log(1);",
        "const x = 1;",
        '// ai-guardrails-allow ruff/E501 "reason2"',
        "const longLine = 1;",
      ].join("\n")
    );
    const issues = [
      makeIssue({ rule: "biome/noConsole", line: 2 }),
      makeIssue({ rule: "ruff/E501", line: 5, fingerprint: "fp-xyz" }),
    ];

    const result = await filterAllowComments(issues, fm);
    expect(result).toHaveLength(0);
  });

  test("only matching issues suppressed when multiple issues in file", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      "/project/src/foo.ts",
      [
        '// ai-guardrails-allow biome/noConsole "reason"',
        "console.log(1);",
        "const x = reallyLongVariableNameThatExceedsTheLineLengthLimit;",
      ].join("\n")
    );
    const issues = [
      makeIssue({ rule: "biome/noConsole", line: 2 }),
      makeIssue({ rule: "ruff/E501", line: 3, fingerprint: "fp-2" }),
    ];

    const result = await filterAllowComments(issues, fm);
    expect(result).toHaveLength(1);
    expect(result[0]?.rule).toBe("ruff/E501");
  });

  test("hash-style comment suppresses issue", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      "/project/src/foo.py",
      '# ai-guardrails-allow ruff/E501 "URL too long to wrap"\nsome_long_url_line = "https://example.com/very/long/path"\n'
    );
    const issues = [
      makeIssue({
        rule: "ruff/E501",
        file: "/project/src/foo.py",
        line: 2,
        linter: "ruff",
      }),
    ];

    const result = await filterAllowComments(issues, fm);
    expect(result).toHaveLength(0);
  });

  test("lua-style comment suppresses issue", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      "/project/src/foo.lua",
      '-- ai-guardrails-allow selene/shadowing "intentional shadowing"\nlocal x = 1\n'
    );
    const issues = [
      makeIssue({
        rule: "selene/shadowing",
        file: "/project/src/foo.lua",
        line: 2,
        linter: "selene",
      }),
    ];

    const result = await filterAllowComments(issues, fm);
    expect(result).toHaveLength(0);
  });

  test("issues in different files handled independently", async () => {
    const fm = new FakeFileManager();
    // File A has allow comment; File B does not
    fm.seed(
      "/project/src/a.ts",
      '// ai-guardrails-allow biome/noConsole "reason"\nconsole.log(1);\n'
    );
    fm.seed("/project/src/b.ts", "console.log(2);\n");

    const issues = [
      makeIssue({ file: "/project/src/a.ts", line: 2, fingerprint: "fp-a" }),
      makeIssue({ file: "/project/src/b.ts", line: 1, fingerprint: "fp-b" }),
    ];

    const result = await filterAllowComments(issues, fm);
    expect(result).toHaveLength(1);
    expect(result[0]?.file).toBe("/project/src/b.ts");
  });
});
