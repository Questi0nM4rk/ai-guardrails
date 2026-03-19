import { beforeEach, describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { parseTscOutput, tscRunner } from "@/runners/tsc";
import { clearResolveToolPathCache } from "@/utils/resolve-tool-path";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

beforeEach(() => clearResolveToolPathCache());

const FIXTURE_PATH = resolve(import.meta.dir, "../fixtures/tsc-output.txt");
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
    noConsoleLevel: "warn",
    isAllowed: () => false,
    ...overrides,
  };
}

describe("parseTscOutput", () => {
  test("returns correct LintIssue[] from fixture", () => {
    const issues = parseTscOutput(FIXTURE_TEXT, PROJECT_DIR);
    expect(issues).toHaveLength(3);

    const first = issues[0];
    expect(first).toBeDefined();
    if (!first) return;
    expect(first.rule).toBe("tsc/TS2322");
    expect(first.linter).toBe("tsc");
    expect(first.file).toBe("/project/src/foo.ts");
    expect(first.line).toBe(10);
    expect(first.col).toBe(5);
    expect(first.message).toBe("Type 'string' is not assignable to type 'number'.");
    expect(first.severity).toBe("error");
    expect(first.fingerprint).toHaveLength(64);
  });

  test("returns [] for clean output", () => {
    const issues = parseTscOutput("", PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("handles multi-line errors by skipping non-matching lines", () => {
    const text = [
      "src/foo.ts(5,3): error TS2322: Type 'string' is not assignable to type 'number'.",
      "  5 | const x: number = 'hello';", // continuation line — should be skipped
      "    |   ~~~~~~~~~~~~~~~~~~~",
      "src/bar.ts(10,1): error TS2304: Cannot find name 'foo'.",
    ].join("\n");
    const issues = parseTscOutput(text, PROJECT_DIR);
    expect(issues).toHaveLength(2);
  });

  test("maps error lines to error severity", () => {
    const issues = parseTscOutput(FIXTURE_TEXT, PROJECT_DIR);
    const errorIssue = issues[0];
    expect(errorIssue?.severity).toBe("error");
  });

  test("maps warning lines to warning severity", () => {
    const text =
      "src/foo.ts(5,3): warning TS6133: 'x' is declared but its value is never read.";
    const issues = parseTscOutput(text, PROJECT_DIR);
    expect(issues).toHaveLength(1);
    expect(issues[0]?.severity).toBe("warning");
  });

  test("prefixes rule with tsc/TS", () => {
    const issues = parseTscOutput(FIXTURE_TEXT, PROJECT_DIR);
    const second = issues[1];
    expect(second).toBeDefined();
    if (!second) return;
    expect(second.rule).toBe("tsc/TS2304");
  });

  test("resolves file path relative to projectDir", () => {
    const issues = parseTscOutput(FIXTURE_TEXT, "/my/project");
    const first = issues[0];
    expect(first).toBeDefined();
    if (!first) return;
    expect(first.file).toBe("/my/project/src/foo.ts");
  });
});

const LOCAL_TSC = `${PROJECT_DIR}/node_modules/.bin/tsc`;

describe("tscRunner.run", () => {
  test("prefers local node_modules/.bin/tsc over global", async () => {
    const runner = new FakeCommandRunner();
    // resolveTscPath probes local tsc first
    runner.register([LOCAL_TSC, "--version"], {
      stdout: "Version 5.8.0",
      stderr: "",
      exitCode: 0,
    });
    runner.register([LOCAL_TSC, "--noEmit", "--pretty", "false"], {
      stdout: FIXTURE_TEXT,
      stderr: "",
      exitCode: 1, // tsc exits non-zero on errors
    });

    const issues = await tscRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(issues).toHaveLength(3);
    // The run call uses the local tsc path
    expect(runner.calls).toContainEqual([LOCAL_TSC, "--noEmit", "--pretty", "false"]);
  });

  test("falls back to global tsc when local is not found", async () => {
    const runner = new FakeCommandRunner();
    // Local tsc not available (exitCode 127)
    runner.register([LOCAL_TSC, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    runner.register(["tsc", "--noEmit", "--pretty", "false"], {
      stdout: FIXTURE_TEXT,
      stderr: "",
      exitCode: 1,
    });

    const issues = await tscRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(issues).toHaveLength(3);
    expect(runner.calls).toContainEqual(["tsc", "--noEmit", "--pretty", "false"]);
  });

  test("parses stdout and stderr combined for error lines", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_TSC, "--version"], {
      stdout: "Version 5.8.0",
      stderr: "",
      exitCode: 0,
    });
    runner.register([LOCAL_TSC, "--noEmit", "--pretty", "false"], {
      stdout: "",
      stderr: FIXTURE_TEXT,
      exitCode: 1,
    });

    const issues = await tscRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(issues).toHaveLength(3);
  });

  test("returns [] when no errors", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_TSC, "--version"], {
      stdout: "Version 5.8.0",
      stderr: "",
      exitCode: 0,
    });
    runner.register([LOCAL_TSC, "--noEmit", "--pretty", "false"], {
      stdout: "",
      stderr: "",
      exitCode: 0,
    });

    const issues = await tscRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(issues).toHaveLength(0);
  });
});

// isAvailable uses cwd-relative path when no projectDir is supplied
const LOCAL_TSC_CWD = "node_modules/.bin/tsc";

describe("tscRunner.isAvailable with projectDir", () => {
  test("uses projectDir when provided to find local tsc", async () => {
    const runner = new FakeCommandRunner();
    const projectDirLocal = `${PROJECT_DIR}/node_modules/.bin/tsc`;
    runner.register([projectDirLocal, "--version"], {
      stdout: "Version 5.8.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await tscRunner.isAvailable(runner, PROJECT_DIR);
    expect(result).toBe(true);
    expect(runner.calls[0]).toContain(projectDirLocal);
  });

  test("falls back to global tsc when local not found given projectDir", async () => {
    const runner = new FakeCommandRunner();
    const projectDirLocal = `${PROJECT_DIR}/node_modules/.bin/tsc`;
    runner.register([projectDirLocal, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    runner.register(["tsc", "--version"], {
      stdout: "Version 5.8.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await tscRunner.isAvailable(runner, PROJECT_DIR);
    expect(result).toBe(true);
  });
});

describe("tscRunner.isAvailable", () => {
  test("returns true when local tsc exits 0", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_TSC_CWD, "--version"], {
      stdout: "Version 5.8.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await tscRunner.isAvailable(runner);
    expect(result).toBe(true);
  });

  test("returns true when global tsc exits 0 and local is absent", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_TSC_CWD, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    runner.register(["tsc", "--version"], {
      stdout: "Version 5.8.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await tscRunner.isAvailable(runner);
    expect(result).toBe(true);
  });

  test("returns false when both local and global tsc are absent", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_TSC_CWD, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    runner.register(["tsc", "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    const result = await tscRunner.isAvailable(runner);
    expect(result).toBe(false);
  });
});
