import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import type { LanguagePlugin } from "@/languages/types";
import type { LintIssue } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { runLinterCollection } from "@/steps/run-linters";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

function makeConfig() {
  const machine = MachineConfigSchema.parse({});
  const project = ProjectConfigSchema.parse({});
  return buildResolvedConfig(machine, project);
}

function makeIssue(overrides: Partial<LintIssue> = {}): LintIssue {
  return {
    rule: "ruff/E501",
    linter: "ruff",
    file: "/project/src/foo.py",
    line: 1,
    col: 1,
    message: "Line too long",
    severity: "error",
    fingerprint: "fp-abc",
    ...overrides,
  };
}

function makeRunner(issues: LintIssue[], available = true): LinterRunner {
  return {
    id: "test-runner",
    name: "Test Runner",
    configFile: null,
    installHint: { description: "Test tool" },
    async isAvailable(): Promise<boolean> {
      return available;
    },
    async run(_opts: RunOptions): Promise<LintIssue[]> {
      return issues;
    },
  };
}

function makePlugin(id: string, runners: LinterRunner[]): LanguagePlugin {
  return {
    id,
    name: id,
    async detect(): Promise<boolean> {
      return true;
    },
    runners(): LinterRunner[] {
      return runners;
    },
  };
}

describe("runLinterCollection", () => {
  test("returns empty array when no languages given", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const issues = await runLinterCollection("/project", [], config, cr, fm);

    expect(issues).toHaveLength(0);
  });

  test("collects issues from a single available runner", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();
    const issue = makeIssue();
    const plugin = makePlugin("python", [makeRunner([issue])]);

    const issues = await runLinterCollection("/project", [plugin], config, cr, fm);

    expect(issues).toHaveLength(1);
    expect(issues[0]?.rule).toBe("ruff/E501");
  });

  test("collects issues from multiple runners across multiple plugins", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const plugin1 = makePlugin("python", [
      makeRunner([makeIssue({ fingerprint: "fp-1" })]),
    ]);
    const plugin2 = makePlugin("typescript", [
      makeRunner([
        makeIssue({ rule: "biome/lint", fingerprint: "fp-2" }),
        makeIssue({ rule: "biome/style", fingerprint: "fp-3" }),
      ]),
    ]);

    const issues = await runLinterCollection(
      "/project",
      [plugin1, plugin2],
      config,
      cr,
      fm
    );

    expect(issues).toHaveLength(3);
  });

  test("skips unavailable runners gracefully", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const unavailableRunner = makeRunner([makeIssue()], false);
    const plugin = makePlugin("rust", [unavailableRunner]);

    const issues = await runLinterCollection("/project", [plugin], config, cr, fm);

    expect(issues).toHaveLength(0);
  });

  test("collects from available runners while skipping unavailable ones", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const availableRunner = makeRunner([makeIssue({ fingerprint: "fp-ok" })], true);
    const unavailableRunner = makeRunner(
      [makeIssue({ fingerprint: "fp-skip" })],
      false
    );
    const plugin = makePlugin("mixed", [availableRunner, unavailableRunner]);

    const issues = await runLinterCollection("/project", [plugin], config, cr, fm);

    expect(issues).toHaveLength(1);
    expect(issues[0]?.fingerprint).toBe("fp-ok");
  });

  test("returns empty array when all runners have no issues", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const plugin1 = makePlugin("python", [makeRunner([])]);
    const plugin2 = makePlugin("typescript", [makeRunner([])]);

    const issues = await runLinterCollection(
      "/project",
      [plugin1, plugin2],
      config,
      cr,
      fm
    );

    expect(issues).toHaveLength(0);
  });

  test("flattens issues from multiple runners within a single plugin", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const runner1 = makeRunner([makeIssue({ fingerprint: "fp-r1" })]);
    const runner2 = makeRunner([makeIssue({ fingerprint: "fp-r2" })]);
    const plugin = makePlugin("python", [runner1, runner2]);

    const issues = await runLinterCollection("/project", [plugin], config, cr, fm);

    expect(issues).toHaveLength(2);
    const fingerprints = issues.map((i) => i.fingerprint);
    expect(fingerprints).toContain("fp-r1");
    expect(fingerprints).toContain("fp-r2");
  });
});
