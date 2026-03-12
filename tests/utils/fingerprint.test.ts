import { describe, expect, test } from "bun:test";
import { fingerprintIssue } from "@/utils/fingerprint";

describe("fingerprintIssue", () => {
  const sourceLines = [
    "def foo():", // line 1
    "  x = 1", // line 2
    "  y = very_long_name", // line 3 — the flagged line
    "  return y", // line 4
    "", // line 5
  ];

  test("same issue produces same fingerprint", () => {
    const issue = {
      rule: "ruff/E501",
      linter: "ruff",
      file: "src/foo.py",
      line: 3,
      col: 1,
      message: "Line too long",
      severity: "error" as const,
    };
    const a = fingerprintIssue(issue, sourceLines);
    const b = fingerprintIssue(issue, sourceLines);
    expect(a).toBe(b);
  });

  test("different file produces different fingerprint", () => {
    const base = {
      rule: "ruff/E501",
      linter: "ruff",
      line: 3,
      col: 1,
      message: "Line too long",
      severity: "error" as const,
    };
    const a = fingerprintIssue({ ...base, file: "src/foo.py" }, sourceLines);
    const b = fingerprintIssue({ ...base, file: "src/bar.py" }, sourceLines);
    expect(a).not.toBe(b);
  });

  test("different rule produces different fingerprint", () => {
    const base = {
      linter: "ruff",
      file: "src/foo.py",
      line: 3,
      col: 1,
      message: "Line too long",
      severity: "error" as const,
    };
    const a = fingerprintIssue({ ...base, rule: "ruff/E501" }, sourceLines);
    const b = fingerprintIssue({ ...base, rule: "ruff/E302" }, sourceLines);
    expect(a).not.toBe(b);
  });

  test("different line content produces different fingerprint", () => {
    const issue = {
      rule: "ruff/E501",
      linter: "ruff",
      file: "src/foo.py",
      line: 3,
      col: 1,
      message: "Line too long",
      severity: "error" as const,
    };
    const altLines = [...sourceLines];
    altLines[2] = "  z = different_content";
    const a = fingerprintIssue(issue, sourceLines);
    const b = fingerprintIssue(issue, altLines);
    expect(a).not.toBe(b);
  });

  test("returns a 64-char hex string", () => {
    const issue = {
      rule: "ruff/E501",
      linter: "ruff",
      file: "src/foo.py",
      line: 3,
      col: 1,
      message: "Line too long",
      severity: "error" as const,
    };
    const fp = fingerprintIssue(issue, sourceLines);
    expect(fp).toMatch(/^[0-9a-f]{64}$/);
  });

  test("handles line at beginning of file (no contextBefore)", () => {
    const issue = {
      rule: "ruff/E501",
      linter: "ruff",
      file: "src/foo.py",
      line: 1,
      col: 1,
      message: "Line too long",
      severity: "error" as const,
    };
    // Should not throw
    const fp = fingerprintIssue(issue, sourceLines);
    expect(fp).toMatch(/^[0-9a-f]{64}$/);
  });

  test("handles line at end of file (no contextAfter)", () => {
    const issue = {
      rule: "ruff/E501",
      linter: "ruff",
      file: "src/foo.py",
      line: 5,
      col: 1,
      message: "Line too long",
      severity: "error" as const,
    };
    const fp = fingerprintIssue(issue, sourceLines);
    expect(fp).toMatch(/^[0-9a-f]{64}$/);
  });

  test("handles empty source lines", () => {
    const issue = {
      rule: "ruff/E501",
      linter: "ruff",
      file: "src/foo.py",
      line: 1,
      col: 1,
      message: "Line too long",
      severity: "error" as const,
    };
    const fp = fingerprintIssue(issue, []);
    expect(fp).toMatch(/^[0-9a-f]{64}$/);
  });
});
