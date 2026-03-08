import { describe, expect, test } from "bun:test";
import { issuesToSarif } from "@/writers/sarif";
import type { LintIssue } from "@/models/lint-issue";

function makeIssue(overrides: Partial<LintIssue> = {}): LintIssue {
  return {
    rule: "E501",
    linter: "ruff",
    file: "/project/foo.py",
    line: 10,
    col: 1,
    message: "Line too long",
    severity: "error",
    fingerprint: "abc123",
    ...overrides,
  };
}

describe("issuesToSarif", () => {
  test("produces SARIF 2.1.0 version", () => {
    const sarif = issuesToSarif([]);
    expect(sarif.version).toBe("2.1.0");
  });

  test("includes $schema field", () => {
    const sarif = issuesToSarif([]);
    expect(sarif.$schema).toContain("sarif-schema-2.1.0");
  });

  test("includes one run", () => {
    const sarif = issuesToSarif([]);
    expect(sarif.runs).toHaveLength(1);
  });

  test("tool name is ai-guardrails", () => {
    const sarif = issuesToSarif([]);
    expect(sarif.runs[0]?.tool.driver.name).toBe("ai-guardrails");
  });

  test("produces empty results for no issues", () => {
    const sarif = issuesToSarif([]);
    expect(sarif.runs[0]?.results).toHaveLength(0);
  });

  test("maps issue to SARIF result with correct ruleId", () => {
    const issue = makeIssue({ linter: "ruff", rule: "E501" });
    const sarif = issuesToSarif([issue]);
    const result = sarif.runs[0]?.results[0];
    expect(result?.ruleId).toBe("ruff/E501");
  });

  test("maps severity error to SARIF level error", () => {
    const issue = makeIssue({ severity: "error" });
    const sarif = issuesToSarif([issue]);
    expect(sarif.runs[0]?.results[0]?.level).toBe("error");
  });

  test("maps severity warning to SARIF level warning", () => {
    const issue = makeIssue({ severity: "warning" });
    const sarif = issuesToSarif([issue]);
    expect(sarif.runs[0]?.results[0]?.level).toBe("warning");
  });

  test("includes file URI and line/col in location", () => {
    const issue = makeIssue({ file: "/project/foo.py", line: 42, col: 7 });
    const sarif = issuesToSarif([issue]);
    const location = sarif.runs[0]?.results[0]?.locations[0];
    expect(location?.physicalLocation.artifactLocation.uri).toBe("/project/foo.py");
    expect(location?.physicalLocation.region.startLine).toBe(42);
    expect(location?.physicalLocation.region.startColumn).toBe(7);
  });

  test("includes message text", () => {
    const issue = makeIssue({ message: "Line too long (120 > 88)" });
    const sarif = issuesToSarif([issue]);
    expect(sarif.runs[0]?.results[0]?.message.text).toBe("Line too long (120 > 88)");
  });

  test("handles multiple issues", () => {
    const issues = [makeIssue(), makeIssue({ rule: "F401", message: "Unused import" })];
    const sarif = issuesToSarif(issues);
    expect(sarif.runs[0]?.results).toHaveLength(2);
  });
});
