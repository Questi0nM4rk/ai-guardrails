import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import type { LanguagePlugin } from "@/languages/types";
import type { LintIssue } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { checkStep } from "@/steps/check-step";
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
    file: "/project/foo.py",
    line: 1,
    col: 1,
    message: "Line too long",
    severity: "error",
    fingerprint: "abc123",
    ...overrides,
  };
}

function makeRunner(issues: LintIssue[], available = true): LinterRunner {
  return {
    id: "test-runner",
    name: "Test Runner",
    configFile: null,
    installHint: {
      description: "Test tool",
    },
    async isAvailable() {
      return available;
    },
    async run(_opts: RunOptions): Promise<LintIssue[]> {
      return issues;
    },
  };
}

function makePlugin(issues: LintIssue[], available = true): LanguagePlugin {
  return {
    id: "test",
    name: "Test",
    async detect() {
      return true;
    },
    runners() {
      return [makeRunner(issues, available)];
    },
  };
}

describe("checkStep", () => {
  test("returns ok when no issues found", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();
    const languages = [makePlugin([])];

    const { result, issues } = await checkStep("/project", languages, config, cr, fm);

    expect(result.status).toBe("ok");
    expect(issues).toHaveLength(0);
  });

  test("returns error when issues found", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();
    const languages = [makePlugin([makeIssue()])];

    const { result, issues } = await checkStep("/project", languages, config, cr, fm);

    expect(result.status).toBe("error");
    expect(issues).toHaveLength(1);
  });

  test("filters allowed rules from results", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const machine = MachineConfigSchema.parse({
      ignore: [{ rule: "ruff/E501", reason: "allowed" }],
    });
    const project = ProjectConfigSchema.parse({});
    const config = buildResolvedConfig(machine, project);

    const languages = [makePlugin([makeIssue({ rule: "ruff/E501" })])];

    const { result, issues } = await checkStep("/project", languages, config, cr, fm);

    expect(result.status).toBe("ok");
    expect(issues).toHaveLength(0);
  });

  test("aggregates issues from multiple runners", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const plugin1 = makePlugin([makeIssue({ rule: "ruff/E501" })]);
    const plugin2 = makePlugin([makeIssue({ rule: "ruff/F401" })]);

    const { issues } = await checkStep("/project", [plugin1, plugin2], config, cr, fm);

    expect(issues).toHaveLength(2);
  });

  test("filters out issues in ignored paths", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const project = ProjectConfigSchema.parse({
      ignore_paths: ["tests/fixtures/**"],
    });
    const config = buildResolvedConfig(MachineConfigSchema.parse({}), project);

    const languages = [
      makePlugin([
        makeIssue({ file: "/project/tests/fixtures/bad.py" }),
        makeIssue({ file: "/project/src/good.py" }),
      ]),
    ];

    const { result, issues } = await checkStep("/project", languages, config, cr, fm);

    // Only the issue outside the ignored path should remain
    expect(issues).toHaveLength(1);
    expect(issues[0]?.file).toBe("/project/src/good.py");
    expect(result.status).toBe("error");
  });

  test("keeps issues outside ignored paths", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const project = ProjectConfigSchema.parse({
      ignore_paths: ["tests/e2e/fixtures/**"],
    });
    const config = buildResolvedConfig(MachineConfigSchema.parse({}), project);

    const languages = [makePlugin([makeIssue({ file: "/project/src/main.py" })])];

    const { issues } = await checkStep("/project", languages, config, cr, fm);

    expect(issues).toHaveLength(1);
  });

  test("ignorePaths empty array disables path filtering", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig(); // ignorePaths defaults to []

    const languages = [
      makePlugin([makeIssue({ file: "/project/tests/fixtures/bad.py" })]),
    ];

    const { issues } = await checkStep("/project", languages, config, cr, fm);

    // Without ignorePaths, nothing is filtered by path
    expect(issues).toHaveLength(1);
  });
});
