import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import type { LanguagePlugin } from "@/languages/types";
import type { BaselineEntry } from "@/models/baseline";
import type { LintIssue } from "@/models/lint-issue";
import { BASELINE_PATH } from "@/models/paths";
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

function makeBaselineEntry(overrides: Partial<BaselineEntry> = {}): BaselineEntry {
  return {
    fingerprint: "abc123",
    rule: "ruff/E501",
    linter: "ruff",
    file: "foo.py",
    line: 1,
    message: "Line too long",
    capturedAt: "2024-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("checkStep — inline allow comments", () => {
  test("issue with inline allow comment is not counted as new", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    // Allow comment on line 1 covers the issue on line 2
    fm.seed(
      "/project/foo.py",
      '# ai-guardrails-allow ruff/E501 "URL too long"\nsome_very_long_line_here = True\n'
    );

    const issue = makeIssue({
      rule: "ruff/E501",
      file: "/project/foo.py",
      line: 2,
      fingerprint: "fp-allowed",
    });
    const languages = [makePlugin([issue])];

    const { result, newIssueCount } = await checkStep(
      "/project",
      languages,
      config,
      cr,
      fm
    );

    expect(result.status).toBe("ok");
    expect(newIssueCount).toBe(0);
  });

  test("issue without allow comment still counted as new", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    fm.seed("/project/foo.py", "some_very_long_line_here = True\n");

    const issue = makeIssue({
      rule: "ruff/E501",
      file: "/project/foo.py",
      line: 1,
      fingerprint: "fp-not-allowed",
    });
    const languages = [makePlugin([issue])];

    const { result, newIssueCount } = await checkStep(
      "/project",
      languages,
      config,
      cr,
      fm
    );

    expect(result.status).toBe("error");
    expect(newIssueCount).toBe(1);
  });
});

describe("checkStep — baseline", () => {
  test("returns ok when all issue fingerprints are in baseline", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();
    const issue = makeIssue({ fingerprint: "fp-001" });

    fm.seed(
      `/project/${BASELINE_PATH}`,
      JSON.stringify([makeBaselineEntry({ fingerprint: "fp-001" })])
    );

    const { result, issues, newIssueCount } = await checkStep(
      "/project",
      [makePlugin([issue])],
      config,
      cr,
      fm
    );

    expect(result.status).toBe("ok");
    expect(result.message).toContain("baselined");
    expect(issues).toHaveLength(1); // all issues still returned for reporting
    expect(newIssueCount).toBe(0);
  });

  test("returns error when baseline is missing one fingerprint", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    fm.seed(
      `/project/${BASELINE_PATH}`,
      JSON.stringify([makeBaselineEntry({ fingerprint: "fp-001" })])
    );

    const issues = [
      makeIssue({ fingerprint: "fp-001" }),
      makeIssue({ fingerprint: "fp-NEW", rule: "ruff/F401" }),
    ];

    const { result, newIssueCount } = await checkStep(
      "/project",
      [makePlugin(issues)],
      config,
      cr,
      fm
    );

    expect(result.status).toBe("error");
    expect(result.message).toContain("1 new");
    expect(newIssueCount).toBe(1);
  });

  test("treats all issues as new when no baseline file exists", async () => {
    const fm = new FakeFileManager(); // no baseline seeded
    const cr = new FakeCommandRunner();
    const config = makeConfig();
    const issue = makeIssue({ fingerprint: "fp-001" });

    const { result, newIssueCount } = await checkStep(
      "/project",
      [makePlugin([issue])],
      config,
      cr,
      fm
    );

    expect(result.status).toBe("error");
    expect(newIssueCount).toBe(1);
  });

  test("treats all issues as new when baseline is empty array", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    fm.seed(`/project/${BASELINE_PATH}`, JSON.stringify([]));

    const issue = makeIssue({ fingerprint: "fp-001" });

    const { result, newIssueCount } = await checkStep(
      "/project",
      [makePlugin([issue])],
      config,
      cr,
      fm
    );

    expect(result.status).toBe("error");
    expect(newIssueCount).toBe(1);
  });
});
