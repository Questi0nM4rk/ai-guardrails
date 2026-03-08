import { describe, expect, test } from "bun:test";
import { statusStep } from "@/steps/status-step";
import { FakeFileManager } from "../fakes/fake-file-manager";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { buildResolvedConfig, MachineConfigSchema, ProjectConfigSchema } from "@/config/schema";
import type { LanguagePlugin } from "@/languages/types";
import type { LinterRunner, RunOptions } from "@/runners/types";
import type { LintIssue } from "@/models/lint-issue";
import type { BaselineEntry } from "@/models/baseline";

function makeConfig() {
  const machine = MachineConfigSchema.parse({});
  const project = ProjectConfigSchema.parse({});
  return buildResolvedConfig(machine, project);
}

function makeIssue(overrides: Partial<LintIssue> = {}): LintIssue {
  return {
    rule: "ruff/E501",
    linter: "ruff",
    file: "/project/foo.py",
    line: 1,
    col: 1,
    message: "Line too long",
    severity: "error",
    fingerprint: "fp-001",
    ...overrides,
  };
}

function makeRunner(issues: LintIssue[]): LinterRunner {
  return {
    id: "test-runner",
    name: "Test Runner",
    configFile: null,
    installHint: {
      description: "Test tool",
    },
    async isAvailable() {
      return true;
    },
    async run(_opts: RunOptions): Promise<LintIssue[]> {
      return issues;
    },
    generateConfig() {
      return null;
    },
  };
}

function makePlugin(issues: LintIssue[]): LanguagePlugin {
  return {
    id: "test",
    name: "Test",
    async detect() {
      return true;
    },
    runners() {
      return [makeRunner(issues)];
    },
  };
}

function makeBaselineEntry(fingerprint: string): BaselineEntry {
  return {
    fingerprint,
    rule: "ruff/E501",
    linter: "ruff",
    file: "/project/foo.py",
    line: 1,
    message: "Line too long",
    capturedAt: new Date().toISOString(),
  };
}

describe("statusStep", () => {
  test("returns ok when no issues and no baseline", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const cons = new FakeConsole();
    const config = makeConfig();

    const output = await statusStep("/project", [makePlugin([])], config, cr, fm, cons);

    expect(output.result.status).toBe("ok");
    expect(output.newIssues).toHaveLength(0);
    expect(output.fixedCount).toBe(0);
  });

  test("identifies new issues not in baseline", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const cons = new FakeConsole();
    const config = makeConfig();

    const baselineEntries = [makeBaselineEntry("fp-baseline")];
    fm.seed("/project/.ai-guardrails/baseline.json", JSON.stringify(baselineEntries));

    const newIssue = makeIssue({ fingerprint: "fp-new" });
    const output = await statusStep("/project", [makePlugin([newIssue])], config, cr, fm, cons);

    expect(output.result.status).toBe("ok");
    expect(output.newIssues).toHaveLength(1);
    expect(output.baselineCount).toBe(1);
  });

  test("counts fixed issues when baseline has more than current", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const cons = new FakeConsole();
    const config = makeConfig();

    const baselineEntries = [makeBaselineEntry("fp-001"), makeBaselineEntry("fp-002")];
    fm.seed("/project/.ai-guardrails/baseline.json", JSON.stringify(baselineEntries));

    // Current scan finds no issues
    const output = await statusStep("/project", [makePlugin([])], config, cr, fm, cons);

    expect(output.fixedCount).toBe(2);
    expect(output.baselineCount).toBe(2);
  });

  test("logs status message to console", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const cons = new FakeConsole();
    const config = makeConfig();

    await statusStep("/project", [makePlugin([])], config, cr, fm, cons);

    expect(cons.infos.length).toBeGreaterThan(0);
    expect(cons.infos[0]).toContain("Status:");
  });
});
