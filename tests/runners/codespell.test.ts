import { describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { codespellRunner, parseCodespellOutput } from "@/runners/codespell";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

const FIXTURE_PATH = resolve(import.meta.dir, "../fixtures/codespell-output.txt");
const PROJECT_DIR = "/project";

const FIXTURE_TEXT = await Bun.file(FIXTURE_PATH).text();

function makeConfig(overrides?: Partial<ResolvedConfig>): ResolvedConfig {
  return {
    profile: "standard",
    ignore: [],
    allow: [],
    values: { line_length: 100, indent_width: 2 },
    ignoredRules: new Set(),
    ignorePaths: [],
    isAllowed: () => false,
    ...overrides,
  };
}

describe("parseCodespellOutput", () => {
  test("returns LintIssue[] from fixture", () => {
    const issues = parseCodespellOutput(FIXTURE_TEXT, PROJECT_DIR);
    expect(issues).toHaveLength(2);

    const first = issues[0];
    expect(first).toBeDefined();
    if (!first) return;
    expect(first.rule).toBe("codespell/spell");
    expect(first.linter).toBe("codespell");
    expect(first.file).toBe("/project/src/utils.py");
    expect(first.line).toBe(5);
    expect(first.col).toBe(1);
    // The message format is "Spelling: <typo> ==> <correction>"
    expect(first.message).toMatch(/^Spelling: .+ ==> .+$/);
    expect(first.severity).toBe("warning");
    expect(first.fingerprint).toHaveLength(64);
  });

  test("strips leading ./ from paths", () => {
    const issues = parseCodespellOutput(FIXTURE_TEXT, PROJECT_DIR);
    for (const issue of issues) {
      expect(issue.file).not.toContain("./");
    }
  });

  test("returns [] for empty output", () => {
    const issues = parseCodespellOutput("", PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("returns [] for output with no matching lines", () => {
    const issues = parseCodespellOutput("Scanning...\nDone.", PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("resolves relative paths to absolute", () => {
    const issues = parseCodespellOutput(FIXTURE_TEXT, "/my/project");
    const first = issues[0];
    expect(first).toBeDefined();
    if (!first) return;
    expect(first.file).toBe("/my/project/src/utils.py");
  });
});

describe("codespellRunner.run", () => {
  test("runs codespell with quiet-level=2 in projectDir", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["codespell", "--quiet-level=2"], {
      stdout: FIXTURE_TEXT,
      stderr: "",
      exitCode: 1, // codespell exits non-zero when issues found
    });

    const issues = await codespellRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(runner.calls[0]).toEqual(["codespell", "--quiet-level=2"]);
    expect(issues).toHaveLength(2);
  });

  test("returns [] when codespell finds no issues", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["codespell", "--quiet-level=2"], {
      stdout: "",
      stderr: "",
      exitCode: 0,
    });

    const issues = await codespellRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(issues).toHaveLength(0);
  });
});

describe("codespellRunner.isAvailable", () => {
  test("returns true when codespell --version exits 0", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["codespell", "--version"], {
      stdout: "2.3.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await codespellRunner.isAvailable(runner);
    expect(result).toBe(true);
  });

  test("returns false when codespell --version exits non-zero", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["codespell", "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    const result = await codespellRunner.isAvailable(runner);
    expect(result).toBe(false);
  });
});
