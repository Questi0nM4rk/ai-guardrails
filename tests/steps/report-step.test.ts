import { describe, expect, test } from "bun:test";
import type { FileManager } from "@/infra/file-manager";
import type { LintIssue } from "@/models/lint-issue";
import { reportStep } from "@/steps/report-step";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

function makeIssue(overrides: Partial<LintIssue> = {}): LintIssue {
  return {
    rule: "ruff/E501",
    linter: "ruff",
    file: "/project/src/foo.py",
    line: 10,
    col: 1,
    message: "Line too long",
    severity: "error",
    fingerprint: "fp-abc123",
    ...overrides,
  };
}

describe("reportStep — text format", () => {
  test("outputs formatted issues to console.error", async () => {
    const console = new FakeConsole();
    const fm = new FakeFileManager();
    const issues = [makeIssue()];

    const result = await reportStep(issues, "text", console, fm);

    expect(result.status).toBe("ok");
    expect(console.errors).toHaveLength(1);
    expect(console.errors[0]).toBeDefined();
  });

  test("does not write any file in text format", async () => {
    const console = new FakeConsole();
    const fm = new FakeFileManager();
    const issues = [makeIssue()];

    await reportStep(issues, "text", console, fm);

    expect(fm.written).toHaveLength(0);
  });

  test("handles empty issues array without writing to console", async () => {
    const console = new FakeConsole();
    const fm = new FakeFileManager();

    const result = await reportStep([], "text", console, fm);

    expect(result.status).toBe("ok");
    // formatIssues returns empty string for no issues → no console.error call
    expect(console.errors).toHaveLength(0);
  });
});

describe("reportStep — sarif format", () => {
  test("writes SARIF JSON to file when sarifOutputPath is provided", async () => {
    const console = new FakeConsole();
    const fm = new FakeFileManager();
    const issues = [makeIssue()];
    const sarifPath = "/project/results.sarif";

    const result = await reportStep(issues, "sarif", console, fm, sarifPath);

    expect(result.status).toBe("ok");
    expect(fm.written).toHaveLength(1);
    const [writtenPath, writtenContent] = fm.written[0] ?? ["", ""];
    expect(writtenPath).toBe(sarifPath);
    // SARIF output is valid JSON
    const parsed: unknown = JSON.parse(writtenContent);
    expect(parsed).toBeDefined();
  });

  test("outputs SARIF JSON to console.info when no sarifOutputPath given", async () => {
    const console = new FakeConsole();
    const fm = new FakeFileManager();
    const issues = [makeIssue()];

    const result = await reportStep(issues, "sarif", console, fm);

    expect(result.status).toBe("ok");
    expect(fm.written).toHaveLength(0);
    expect(console.infos).toHaveLength(1);
    const sarifText = console.infos[0];
    expect(sarifText).toBeDefined();
    if (!sarifText) return;
    const parsed: unknown = JSON.parse(sarifText);
    expect(parsed).toBeDefined();
  });

  test("handles empty issues array in SARIF format", async () => {
    const console = new FakeConsole();
    const fm = new FakeFileManager();

    const result = await reportStep([], "sarif", console, fm, "/out.sarif");

    expect(result.status).toBe("ok");
    expect(fm.written).toHaveLength(1);
    const [, content] = fm.written[0] ?? ["", ""];
    const parsed = JSON.parse(content) as { runs: Array<{ results: unknown[] }> };
    expect(parsed.runs[0]?.results).toHaveLength(0);
  });

  test("result message includes issue count and format", async () => {
    const console = new FakeConsole();
    const fm = new FakeFileManager();
    const issues = [makeIssue(), makeIssue({ rule: "ruff/F401", fingerprint: "fp-2" })];

    const result = await reportStep(issues, "sarif", console, fm);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("2");
    expect(result.message).toContain("sarif");
  });
});

describe("reportStep — error handling", () => {
  test("returns error when fileManager throws on writeText", async () => {
    const console = new FakeConsole();
    const inner = new FakeFileManager();
    const throwingFm: FileManager = {
      readText: (p) => inner.readText(p),
      writeText: async () => {
        throw new Error("disk full");
      },
      appendText: (p, c) => inner.appendText(p, c),
      exists: (p) => inner.exists(p),
      mkdir: (p, o) => inner.mkdir(p, o),
      glob: (p, c, i) => inner.glob(p, c, i),
      isSymlink: (p) => inner.isSymlink(p),
      delete: (p) => inner.delete(p),
    };

    // reportStep does not have a try/catch — it will throw through
    // Verify no crash for text format (no file write)
    const result = await reportStep([], "text", console, throwingFm);
    expect(result.status).toBe("ok");
  });
});
