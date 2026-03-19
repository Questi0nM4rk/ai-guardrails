import { describe, expect, test } from "bun:test";
import { z } from "zod";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import type { LanguagePlugin } from "@/languages/types";
import type { BaselineEntry } from "@/models/baseline";
import { BaselineEntrySchema, loadBaseline } from "@/models/baseline";
import type { LintIssue } from "@/models/lint-issue";
import { BASELINE_PATH } from "@/models/paths";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { checkStep } from "@/steps/check-step";
import { snapshotStep } from "@/steps/snapshot-step";
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
    line: 10,
    col: 1,
    message: "Line too long",
    severity: "error",
    fingerprint: "fp-abc123",
    ...overrides,
  };
}

function makeRunner(issues: LintIssue[], available = true): LinterRunner {
  return {
    id: "test-runner",
    name: "Test Runner",
    configFile: null,
    installHint: { description: "Test tool" },
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

function readBaseline(fm: FakeFileManager, projectDir: string): BaselineEntry[] {
  const written = fm.written.find(
    ([path]) => path === `${projectDir}/${BASELINE_PATH}`
  );
  if (!written) throw new Error("Baseline was not written");
  const parsed: unknown = JSON.parse(written[1]);
  return z.array(BaselineEntrySchema).parse(parsed);
}

describe("snapshotStep — relative paths", () => {
  test("stores relative file paths in baseline entries, not absolute", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();
    const issue = makeIssue({ file: "/project/src/foo.py" });
    const languages = [makePlugin([issue])];

    const result = await snapshotStep("/project", languages, config, cr, fm);

    expect(result.status).toBe("ok");

    const entries = readBaseline(fm, "/project");
    expect(entries).toHaveLength(1);

    const entry = entries[0];
    expect(entry).toBeDefined();
    if (!entry) return;

    // Must be relative — must NOT start with "/"
    expect(entry.file).not.toMatch(/^\//);
    expect(entry.file).toBe("src/foo.py");
  });

  test("stores relative paths for issues in nested subdirectories", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();
    const issues = [
      makeIssue({ file: "/project/src/nested/deep/bar.py", fingerprint: "fp-1" }),
      makeIssue({ file: "/project/tests/test_foo.py", fingerprint: "fp-2" }),
    ];
    const languages = [makePlugin(issues)];

    await snapshotStep("/project", languages, config, cr, fm);

    const entries = readBaseline(fm, "/project");
    expect(entries).toHaveLength(2);

    const paths = entries.map((e) => e.file);
    expect(paths).toContain("src/nested/deep/bar.py");
    expect(paths).toContain("tests/test_foo.py");
  });

  test("snapshot→check round-trip: all issues classified as existing", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const issue = makeIssue({
      file: "/project/src/foo.py",
      fingerprint: "fp-round-trip",
    });
    const languages = [makePlugin([issue])];

    // Phase 1: snapshot captures the baseline
    const snapResult = await snapshotStep("/project", languages, config, cr, fm);
    expect(snapResult.status).toBe("ok");

    // The baseline file must now exist in the fake FS
    const baselinePath = `/project/${BASELINE_PATH}`;
    const written = fm.written.find(([p]) => p === baselinePath);
    expect(written).toBeDefined();

    // Phase 2: check against the same issues — all must be "existing", none new
    const { result, newIssueCount } = await checkStep(
      "/project",
      languages,
      config,
      cr,
      fm
    );

    expect(result.status).toBe("ok");
    expect(newIssueCount).toBe(0);
    expect(result.message).toContain("baselined");
  });

  test("snapshot→check round-trip: new issue introduced after snapshot is detected", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const existingIssue = makeIssue({
      file: "/project/src/foo.py",
      fingerprint: "fp-existing",
    });

    // Snapshot with only the existing issue
    await snapshotStep("/project", [makePlugin([existingIssue])], config, cr, fm);

    // Check with existing + a brand-new issue
    const newIssue = makeIssue({
      file: "/project/src/bar.py",
      fingerprint: "fp-brand-new",
      rule: "ruff/F401",
    });

    const { result, newIssueCount } = await checkStep(
      "/project",
      [makePlugin([existingIssue, newIssue])],
      config,
      cr,
      fm
    );

    expect(result.status).toBe("error");
    expect(newIssueCount).toBe(1);
  });

  test("baseline entry fingerprints match exactly what checkStep uses for lookup", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const fingerprint = "fp-exact-match";
    const issue = makeIssue({ file: "/project/src/foo.py", fingerprint });
    const languages = [makePlugin([issue])];

    await snapshotStep("/project", languages, config, cr, fm);

    const entries = readBaseline(fm, "/project");
    const baseline = loadBaseline(entries);

    // The fingerprint stored in the baseline must be the same value the runner produced
    expect(baseline.has(fingerprint)).toBe(true);
  });

  test("returns ok with zero entries when no issues found", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();
    const languages = [makePlugin([])];

    const result = await snapshotStep("/project", languages, config, cr, fm);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("0 issue(s)");

    const entries = readBaseline(fm, "/project");
    expect(entries).toHaveLength(0);
  });
});
