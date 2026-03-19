import { beforeEach, describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import {
  golangciLintRunner,
  parseGolangciOutput,
  resetVersionFlagCache,
} from "@/runners/golangci-lint";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

const FIXTURE_PATH = resolve(import.meta.dir, "../fixtures/golangci-output.json");
const PROJECT_DIR = "/project";

const FIXTURE_JSON = await Bun.file(FIXTURE_PATH).text();

function makeConfig(overrides?: Partial<ResolvedConfig>): ResolvedConfig {
  return {
    profile: "standard",
    ignore: [],
    allow: [],
    values: { line_length: 100, indent_width: 2 },
    ignoredRules: new Set(),
    ignorePaths: [],
    noConsoleLevel: "warn",
    isAllowed: () => false,
    ...overrides,
  };
}

describe("parseGolangciOutput", () => {
  test("returns correct LintIssue[] from fixture", () => {
    const issues = parseGolangciOutput(FIXTURE_JSON, PROJECT_DIR);
    expect(issues).toHaveLength(2);

    const first = issues[0];
    expect(first).toBeDefined();
    if (!first) return;
    expect(first.rule).toBe("golangci-lint/unused");
    expect(first.linter).toBe("golangci-lint");
    expect(first.file).toBe("/project/main.go");
    expect(first.line).toBe(10);
    expect(first.col).toBe(1);
    expect(first.message).toBe("func `foo` is unused");
    expect(first.severity).toBe("error");
  });

  test("returns [] when Issues is null", () => {
    const json = JSON.stringify({ Issues: null });
    const issues = parseGolangciOutput(json, PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("returns [] when Issues is empty array", () => {
    const json = JSON.stringify({ Issues: [] });
    const issues = parseGolangciOutput(json, PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("resolves relative file paths to absolute", () => {
    const issues = parseGolangciOutput(FIXTURE_JSON, PROJECT_DIR);
    const second = issues[1];
    expect(second).toBeDefined();
    if (!second) return;
    expect(second.file).toBe("/project/util/helper.go");
  });

  test("all issues have error severity", () => {
    const issues = parseGolangciOutput(FIXTURE_JSON, PROJECT_DIR);
    for (const issue of issues) {
      expect(issue.severity).toBe("error");
    }
  });
});

describe("golangciLintRunner.run", () => {
  beforeEach(() => {
    resetVersionFlagCache();
  });

  test("uses --output.json.path=stdout flag for version >= 1.64", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["golangci-lint", "--version"], {
      stdout: "golangci-lint has version 1.64.0",
      stderr: "",
      exitCode: 0,
    });
    runner.register(["golangci-lint", "run", "--output.json.path=stdout", "./..."], {
      stdout: FIXTURE_JSON,
      stderr: "",
      exitCode: 1,
    });

    const issues = await golangciLintRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(runner.calls[1]).toEqual([
      "golangci-lint",
      "run",
      "--output.json.path=stdout",
      "./...",
    ]);
    expect(issues).toHaveLength(2);
  });

  test("uses --out-format=json for version < 1.64", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["golangci-lint", "--version"], {
      stdout: "golangci-lint has version 1.63.4",
      stderr: "",
      exitCode: 0,
    });
    runner.register(["golangci-lint", "run", "--out-format=json", "./..."], {
      stdout: FIXTURE_JSON,
      stderr: "",
      exitCode: 1,
    });

    const issues = await golangciLintRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(runner.calls[1]).toEqual([
      "golangci-lint",
      "run",
      "--out-format=json",
      "./...",
    ]);
    expect(issues).toHaveLength(2);
  });
});

describe("golangciLintRunner.isAvailable", () => {
  test("returns true when golangci-lint --version exits 0", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["golangci-lint", "--version"], {
      stdout: "golangci-lint has version 1.64.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await golangciLintRunner.isAvailable(runner);
    expect(result).toBe(true);
  });

  test("returns false when golangci-lint --version exits non-zero", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["golangci-lint", "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    const result = await golangciLintRunner.isAvailable(runner);
    expect(result).toBe(false);
  });
});
