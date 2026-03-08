import { describe, expect, test } from "bun:test";
import { checkPrerequisites } from "@/steps/check-prerequisites";
import type { LanguagePlugin } from "@/languages/types";
import type { LinterRunner, RunOptions, InstallHint } from "@/runners/types";
import type { LintIssue } from "@/models/lint-issue";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";

function makeHint(description: string, overrides?: Partial<InstallHint>): InstallHint {
  return { description, ...overrides };
}

function makeRunner(id: string, available: boolean, hint?: Partial<InstallHint>): LinterRunner {
  return {
    id,
    name: id,
    configFile: null,
    installHint: makeHint(`${id} tool`, hint),
    async isAvailable() {
      return available;
    },
    async run(_opts: RunOptions): Promise<LintIssue[]> {
      return [];
    },
    generateConfig() {
      return null;
    },
  };
}

function makePlugin(runners: LinterRunner[]): LanguagePlugin {
  return {
    id: "test",
    name: "Test",
    async detect() {
      return true;
    },
    runners() {
      return runners;
    },
  };
}

describe("checkPrerequisites", () => {
  test("reports all available when every runner is present", async () => {
    const cr = new FakeCommandRunner();
    const cons = new FakeConsole();
    const plugin = makePlugin([makeRunner("ruff", true), makeRunner("pyright", true)]);

    const { report } = await checkPrerequisites(cons, cr, [plugin]);

    expect(report.missing).toHaveLength(0);
    expect(report.available).toContain("ruff");
    expect(report.available).toContain("pyright");
    expect(cons.successes.length).toBeGreaterThan(0);
  });

  test("reports missing runners when tools are unavailable", async () => {
    const cr = new FakeCommandRunner();
    const cons = new FakeConsole();
    const plugin = makePlugin([
      makeRunner("shellcheck", false, { brew: "brew install shellcheck" }),
      makeRunner("shfmt", true),
    ]);

    const { report } = await checkPrerequisites(cons, cr, [plugin]);

    expect(report.missing).toHaveLength(1);
    expect(report.missing[0]?.runnerId).toBe("shellcheck");
    expect(report.available).toContain("shfmt");
    expect(cons.warnings.length).toBeGreaterThan(0);
  });

  test("deduplicates runners appearing in multiple plugins", async () => {
    const cr = new FakeCommandRunner();
    const cons = new FakeConsole();
    const sharedRunner = makeRunner("codespell", false, { pip: "pip install codespell" });
    const plugin1 = makePlugin([sharedRunner]);
    const plugin2 = makePlugin([sharedRunner]);

    const { report } = await checkPrerequisites(cons, cr, [plugin1, plugin2]);

    expect(report.missing).toHaveLength(1);
    expect(report.missing[0]?.runnerId).toBe("codespell");
  });

  test("returns ok step result regardless of missing tools", async () => {
    const cr = new FakeCommandRunner();
    const cons = new FakeConsole();
    const plugin = makePlugin([makeRunner("clippy", false)]);

    const { result } = await checkPrerequisites(cons, cr, [plugin]);

    expect(result.status).toBe("ok");
  });

  test("handles empty plugin list", async () => {
    const cr = new FakeCommandRunner();
    const cons = new FakeConsole();

    const { report } = await checkPrerequisites(cons, cr, []);

    expect(report.missing).toHaveLength(0);
    expect(report.available).toHaveLength(0);
  });
});
