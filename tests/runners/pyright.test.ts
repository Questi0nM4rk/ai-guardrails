import { beforeEach, describe, expect, test } from "bun:test";
import type { ResolvedConfig } from "@/config/schema";
import { parsePyrightOutput, pyrightRunner } from "@/runners/pyright";
import { clearResolveToolPathCache } from "@/utils/resolve-tool-path";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

beforeEach(() => clearResolveToolPathCache());

const FIXTURE_PATH = new URL("../fixtures/pyright-output.json", import.meta.url)
  .pathname;
const fixtureText = await Bun.file(FIXTURE_PATH).text();

const PROJECT_DIR = "/home/user/project";

/** Minimal ResolvedConfig that allows everything (no filtering) */
function makeConfig(): ResolvedConfig {
  return {
    profile: "standard",
    ignore: [],
    allow: [],
    values: { line_length: 88, indent_width: 4 },
    ignoredRules: new Set(),
    ignorePaths: [],
    noConsoleLevel: "warn",
    isAllowed: () => false,
  };
}

describe("parsePyrightOutput", () => {
  test("returns correct LintIssue[] from fixture", () => {
    // Fixture has 3 diagnostics: error, warning, information
    // information is skipped, so we expect 2 results
    const issues = parsePyrightOutput(fixtureText, PROJECT_DIR);

    expect(issues).toHaveLength(2);

    const errorIssue = issues[0];
    expect(errorIssue).toBeDefined();
    if (!errorIssue) return;
    expect(errorIssue.rule).toBe("pyright/reportArgumentType");
    expect(errorIssue.linter).toBe("pyright");
    expect(errorIssue.file).toBe("/home/user/project/src/services/auth.py");
    expect(errorIssue.line).toBe(25); // 0-indexed 24 → 1-indexed 25
    expect(errorIssue.col).toBe(16); // 0-indexed 15 → 1-indexed 16
    expect(errorIssue.message).toBe('Type "str" is not assignable to type "int"');
    expect(errorIssue.severity).toBe("error");

    const warningIssue = issues[1];
    expect(warningIssue).toBeDefined();
    if (!warningIssue) return;
    expect(warningIssue.rule).toBe("pyright/reportUnknownVariableType");
    expect(warningIssue.severity).toBe("warning");
    expect(warningIssue.line).toBe(10); // 0-indexed 9 → 1-indexed 10
    expect(warningIssue.col).toBe(5); // 0-indexed 4 → 1-indexed 5
  });

  test("skips information-level diagnostics", () => {
    const input = JSON.stringify({
      generalDiagnostics: [
        {
          file: "/project/src/foo.py",
          severity: "information",
          message: "Import could be stubbed",
          range: {
            start: { line: 0, character: 0 },
            end: { line: 0, character: 10 },
          },
          rule: "reportMissingTypeStubs",
        },
      ],
      summary: { errorCount: 0, warningCount: 0, informationCount: 1 },
    });

    const issues = parsePyrightOutput(input, "/project");
    expect(issues).toHaveLength(0);
  });

  test("converts 0-indexed lines to 1-indexed", () => {
    const input = JSON.stringify({
      generalDiagnostics: [
        {
          file: "/project/src/foo.py",
          severity: "error",
          message: "Type error",
          range: {
            start: { line: 0, character: 0 },
            end: { line: 0, character: 5 },
          },
          rule: "reportArgumentType",
        },
      ],
      summary: { errorCount: 1, warningCount: 0, informationCount: 0 },
    });

    const issues = parsePyrightOutput(input, "/project");
    expect(issues).toHaveLength(1);
    expect(issues[0]?.line).toBe(1); // 0 + 1
    expect(issues[0]?.col).toBe(1); // 0 + 1
  });

  test("handles missing rule with unknown fallback", () => {
    const input = JSON.stringify({
      generalDiagnostics: [
        {
          file: "/project/src/foo.py",
          severity: "error",
          message: "Some error without a rule",
          range: {
            start: { line: 5, character: 2 },
            end: { line: 5, character: 10 },
          },
        },
      ],
      summary: { errorCount: 1, warningCount: 0, informationCount: 0 },
    });

    const issues = parsePyrightOutput(input, "/project");
    expect(issues).toHaveLength(1);
    expect(issues[0]?.rule).toBe("pyright/unknown");
  });

  test("returns [] for empty stdout", () => {
    const issues = parsePyrightOutput("", "/project");
    expect(issues).toHaveLength(0);
  });

  test("returns [] for invalid JSON", () => {
    const issues = parsePyrightOutput("not valid json {[}", "/project");
    expect(issues).toHaveLength(0);
  });

  test("returns [] when generalDiagnostics is missing", () => {
    const issues = parsePyrightOutput(
      JSON.stringify({ summary: { errorCount: 0 } }),
      "/project"
    );
    expect(issues).toHaveLength(0);
  });
});

// Local pyright path when isAvailable is called without projectDir (uses ".")
const LOCAL_PYRIGHT_CWD = "node_modules/.bin/pyright";

describe("pyrightRunner", () => {
  test("isAvailable returns true when local pyright exits 0", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_PYRIGHT_CWD, "--version"], {
      stdout: "pyright 1.1.385",
      stderr: "",
      exitCode: 0,
    });
    const result = await pyrightRunner.isAvailable(runner);
    expect(result).toBe(true);
  });

  test("isAvailable returns true when global pyright exits 0 (local absent)", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_PYRIGHT_CWD, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    runner.register(["pyright", "--version"], {
      stdout: "pyright 1.1.385",
      stderr: "",
      exitCode: 0,
    });
    const result = await pyrightRunner.isAvailable(runner);
    expect(result).toBe(true);
  });

  test("isAvailable returns false when both local and global are absent", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_PYRIGHT_CWD, "--version"], {
      stdout: "",
      stderr: "pyright: command not found",
      exitCode: 127,
    });
    runner.register(["pyright", "--version"], {
      stdout: "",
      stderr: "pyright: command not found",
      exitCode: 127,
    });
    const result = await pyrightRunner.isAvailable(runner);
    expect(result).toBe(false);
  });

  test("run calls pyright with --outputjson (falls back to global)", async () => {
    const commandRunner = new FakeCommandRunner();
    const projectDir = "/home/user/project";
    const localPyright = `${projectDir}/node_modules/.bin/pyright`;
    // Local not available
    commandRunner.register([localPyright, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    commandRunner.register(["pyright", "--version"], {
      stdout: "pyright 1.1.385",
      stderr: "",
      exitCode: 0,
    });
    commandRunner.register(["pyright", "--outputjson", projectDir], {
      stdout: JSON.stringify({
        generalDiagnostics: [],
        summary: { errorCount: 0, warningCount: 0, informationCount: 0 },
      }),
      stderr: "",
      exitCode: 0,
    });

    const issues = await pyrightRunner.run({
      projectDir,
      config: makeConfig(),
      commandRunner,
      fileManager: new FakeFileManager(),
    });

    expect(commandRunner.calls).toContainEqual(["pyright", "--outputjson", projectDir]);
    expect(issues).toHaveLength(0);
  });

  test("run returns issues even when exitCode is non-zero", async () => {
    const commandRunner = new FakeCommandRunner();
    const projectDir = "/home/user/project";
    const localPyright = `${projectDir}/node_modules/.bin/pyright`;
    commandRunner.register([localPyright, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    commandRunner.register(["pyright", "--version"], {
      stdout: "pyright 1.1.385",
      stderr: "",
      exitCode: 0,
    });
    commandRunner.register(["pyright", "--outputjson", projectDir], {
      stdout: JSON.stringify({
        generalDiagnostics: [
          {
            file: "/home/user/project/src/foo.py",
            severity: "error",
            message: "Type error",
            range: {
              start: { line: 3, character: 0 },
              end: { line: 3, character: 5 },
            },
            rule: "reportArgumentType",
          },
        ],
        summary: { errorCount: 1, warningCount: 0, informationCount: 0 },
      }),
      stderr: "",
      exitCode: 1,
    });

    const issues = await pyrightRunner.run({
      projectDir,
      config: makeConfig(),
      commandRunner,
      fileManager: new FakeFileManager(),
    });

    // pyright exits 1 on errors but stdout still has valid JSON
    expect(issues).toHaveLength(1);
  });

  test("id, name, and configFile are correct", () => {
    expect(pyrightRunner.id).toBe("pyright");
    expect(pyrightRunner.name).toBe("Pyright");
    expect(pyrightRunner.configFile).toBe("pyrightconfig.json");
  });
});

describe("pyrightRunner node_modules/.bin resolution", () => {
  const PROJECT_DIR = "/home/user/project";
  const LOCAL_PYRIGHT = `${PROJECT_DIR}/node_modules/.bin/pyright`;

  test("isAvailable uses local node_modules/.bin/pyright when present", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_PYRIGHT, "--version"], {
      stdout: "pyright 1.1.385",
      stderr: "",
      exitCode: 0,
    });
    const result = await pyrightRunner.isAvailable(runner, PROJECT_DIR);
    expect(result).toBe(true);
    expect(runner.calls[0]).toContain(LOCAL_PYRIGHT);
  });

  test("isAvailable falls back to global pyright when local absent", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_PYRIGHT, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    runner.register(["pyright", "--version"], {
      stdout: "pyright 1.1.385",
      stderr: "",
      exitCode: 0,
    });
    const result = await pyrightRunner.isAvailable(runner, PROJECT_DIR);
    expect(result).toBe(true);
  });

  test("run uses local node_modules/.bin/pyright when present", async () => {
    const runner = new FakeCommandRunner();
    // resolvePyrightPath probes local first
    runner.register([LOCAL_PYRIGHT, "--version"], {
      stdout: "pyright 1.1.385",
      stderr: "",
      exitCode: 0,
    });
    runner.register([LOCAL_PYRIGHT, "--outputjson", PROJECT_DIR], {
      stdout: JSON.stringify({
        generalDiagnostics: [],
        summary: { errorCount: 0, warningCount: 0, informationCount: 0 },
      }),
      stderr: "",
      exitCode: 0,
    });

    const issues = await pyrightRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(runner.calls).toContainEqual([LOCAL_PYRIGHT, "--outputjson", PROJECT_DIR]);
    expect(issues).toHaveLength(0);
  });
});
