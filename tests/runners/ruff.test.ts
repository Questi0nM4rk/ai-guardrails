import { describe, expect, test } from "bun:test";
import type { ResolvedConfig } from "@/config/schema";
import { parseRuffOutput, ruffRunner } from "@/runners/ruff";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

const FIXTURE_PATH = new URL("../fixtures/ruff-output.json", import.meta.url).pathname;
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

describe("parseRuffOutput", () => {
  test("returns correct raw issues from fixture", () => {
    const issues = parseRuffOutput(fixtureText, makeConfig(), PROJECT_DIR);

    expect(issues).toHaveLength(3);

    const e501 = issues[0];
    expect(e501).toBeDefined();
    if (!e501) return;
    expect(e501.rule).toBe("ruff/E501");
    expect(e501.linter).toBe("ruff");
    expect(e501.file).toBe("/home/user/project/src/utils.py");
    expect(e501.line).toBe(42);
    expect(e501.col).toBe(89);
    expect(e501.message).toBe("Line too long (120 > 88 characters)");
    expect(e501.severity).toBe("error");

    const f401 = issues[1];
    expect(f401).toBeDefined();
    if (!f401) return;
    expect(f401.rule).toBe("ruff/F401");
    expect(f401.severity).toBe("error");

    const w291 = issues[2];
    expect(w291).toBeDefined();
    if (!w291) return;
    expect(w291.rule).toBe("ruff/W291");
    expect(w291.severity).toBe("warning");
  });

  test("returns [] for empty stdout", () => {
    const issues = parseRuffOutput("", makeConfig(), PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("returns [] for invalid JSON", () => {
    const issues = parseRuffOutput("not valid json {[}", makeConfig(), PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("returns [] for null JSON", () => {
    const issues = parseRuffOutput("null", makeConfig(), PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("severity is error for E-prefixed codes", () => {
    const input = JSON.stringify([
      {
        code: "E501",
        filename: "/project/src/foo.py",
        location: { row: 1, column: 1 },
        end_location: { row: 1, column: 10 },
        message: "Line too long",
        fix: null,
        url: "",
      },
    ]);
    const issues = parseRuffOutput(input, makeConfig(), "/project");
    expect(issues[0]?.severity).toBe("error");
  });

  test("severity is error for F-prefixed codes", () => {
    const input = JSON.stringify([
      {
        code: "F401",
        filename: "/project/src/foo.py",
        location: { row: 1, column: 1 },
        end_location: { row: 1, column: 10 },
        message: "Unused import",
        fix: null,
        url: "",
      },
    ]);
    const issues = parseRuffOutput(input, makeConfig(), "/project");
    expect(issues[0]?.severity).toBe("error");
  });

  test("severity is warning for W-prefixed codes", () => {
    const input = JSON.stringify([
      {
        code: "W291",
        filename: "/project/src/foo.py",
        location: { row: 5, column: 10 },
        end_location: { row: 5, column: 15 },
        message: "Trailing whitespace",
        fix: null,
        url: "",
      },
    ]);
    const issues = parseRuffOutput(input, makeConfig(), "/project");
    expect(issues[0]?.severity).toBe("warning");
  });
});

describe("ruffRunner fingerprint stability", () => {
  test("same issue at different project roots produces the same fingerprint", async () => {
    // src/foo.py with E501 at line 1 — same source content, different project roots
    const sourceContent = "x = 1 + 1  # some long line\n";

    const makeInput = (absProjectDir: string) =>
      JSON.stringify([
        {
          code: "E501",
          filename: `${absProjectDir}/src/foo.py`,
          location: { row: 1, column: 89 },
          end_location: { row: 1, column: 120 },
          message: "Line too long",
          fix: null,
          url: "",
        },
      ]);

    const runFor = async (absProjectDir: string) => {
      const commandRunner = new FakeCommandRunner();
      commandRunner.register(["ruff", "check", "--output-format=json", absProjectDir], {
        stdout: makeInput(absProjectDir),
        stderr: "",
        exitCode: 1,
      });
      const fileManager = new FakeFileManager();
      fileManager.seed(`${absProjectDir}/src/foo.py`, sourceContent);
      return ruffRunner.run({
        projectDir: absProjectDir,
        config: makeConfig(),
        commandRunner,
        fileManager,
      });
    };

    const issuesAlice = await runFor("/alice/repo");
    const issuesBob = await runFor("/bob/repo");

    expect(issuesAlice).toHaveLength(1);
    expect(issuesBob).toHaveLength(1);
    // LintIssue.file differs (absolute) but fingerprint must be identical
    expect(issuesAlice[0]?.file).toBe("/alice/repo/src/foo.py");
    expect(issuesBob[0]?.file).toBe("/bob/repo/src/foo.py");
    expect(issuesAlice[0]?.fingerprint).toBe(issuesBob[0]?.fingerprint);
    expect(issuesAlice[0]?.fingerprint).toHaveLength(64);
  });

  test("same issue with different error message but same source line produces the same fingerprint", async () => {
    // Two runs of ruff at the same file — message changes (tool upgrade) but source stays same
    const sourceContent = "import os\nx = 1\n";
    const absFile = "/project/src/foo.py";
    const makeInput = (msg: string) =>
      JSON.stringify([
        {
          code: "F401",
          filename: absFile,
          location: { row: 1, column: 1 },
          end_location: { row: 1, column: 9 },
          message: msg,
          fix: null,
          url: "",
        },
      ]);

    const runWithMessage = async (msg: string) => {
      const commandRunner = new FakeCommandRunner();
      commandRunner.register(["ruff", "check", "--output-format=json", "/project"], {
        stdout: makeInput(msg),
        stderr: "",
        exitCode: 1,
      });
      const fileManager = new FakeFileManager();
      fileManager.seed(absFile, sourceContent);
      return ruffRunner.run({
        projectDir: "/project",
        config: makeConfig(),
        commandRunner,
        fileManager,
      });
    };

    const issuesV1 = await runWithMessage("`os` imported but unused");
    const issuesV2 = await runWithMessage(
      "`os` imported but never used (different wording)"
    );

    expect(issuesV1).toHaveLength(1);
    expect(issuesV2).toHaveLength(1);
    // Fingerprints must be identical despite different messages — source-based stability
    expect(issuesV1[0]?.fingerprint).toBe(issuesV2[0]?.fingerprint);
  });

  test("run produces fingerprint with length 64 for each issue", async () => {
    const commandRunner = new FakeCommandRunner();
    const projectDir = "/home/user/project";
    commandRunner.register(["ruff", "check", "--output-format=json", projectDir], {
      stdout: fixtureText,
      stderr: "",
      exitCode: 1,
    });
    // Seed source files used in fixture
    const fileManager = new FakeFileManager();
    fileManager.seed(`${projectDir}/src/utils.py`, "# placeholder\n".repeat(50));
    fileManager.seed(`${projectDir}/src/models.py`, "# placeholder\n".repeat(10));

    const issues = await ruffRunner.run({
      projectDir,
      config: makeConfig(),
      commandRunner,
      fileManager,
    });

    expect(issues).toHaveLength(3);
    for (const issue of issues) {
      expect(issue.fingerprint).toHaveLength(64);
    }
  });
});

describe("ruffRunner", () => {
  test("isAvailable returns true when ruff exits 0", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["ruff", "--version"], {
      stdout: "ruff 0.4.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await ruffRunner.isAvailable(runner);
    expect(result).toBe(true);
  });

  test("isAvailable returns false when ruff exits non-zero", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["ruff", "--version"], {
      stdout: "",
      stderr: "ruff: command not found",
      exitCode: 127,
    });
    const result = await ruffRunner.isAvailable(runner);
    expect(result).toBe(false);
  });

  test("run calls ruff with correct args", async () => {
    const commandRunner = new FakeCommandRunner();
    const projectDir = "/home/user/project";
    commandRunner.register(["ruff", "check", "--output-format=json", projectDir], {
      stdout: "[]",
      stderr: "",
      exitCode: 0,
    });

    const issues = await ruffRunner.run({
      projectDir,
      config: makeConfig(),
      commandRunner,
      fileManager: new FakeFileManager(),
    });

    expect(commandRunner.calls).toContainEqual([
      "ruff",
      "check",
      "--output-format=json",
      projectDir,
    ]);
    expect(issues).toHaveLength(0);
  });

  test("run returns [] when ruff produces empty output", async () => {
    const commandRunner = new FakeCommandRunner();
    const projectDir = "/home/user/project";
    commandRunner.register(["ruff", "check", "--output-format=json", projectDir], {
      stdout: "",
      stderr: "some error",
      exitCode: 1,
    });

    const issues = await ruffRunner.run({
      projectDir,
      config: makeConfig(),
      commandRunner,
      fileManager: new FakeFileManager(),
    });

    expect(issues).toHaveLength(0);
  });

  test("id and name are correct", () => {
    expect(ruffRunner.id).toBe("ruff");
    expect(ruffRunner.name).toBe("Ruff");
    expect(ruffRunner.configFile).toBe("ruff.toml");
  });
});
