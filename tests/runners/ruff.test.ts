import { describe, expect, test } from "bun:test";
import type { ResolvedConfig } from "@/config/schema";
import { parseRuffOutput, ruffRunner } from "@/runners/ruff";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

const FIXTURE_PATH = new URL("../fixtures/ruff-output.json", import.meta.url).pathname;
const fixtureText = await Bun.file(FIXTURE_PATH).text();

/** Minimal ResolvedConfig that allows everything (no filtering) */
function makeConfig(): ResolvedConfig {
  return {
    profile: "standard",
    ignore: [],
    allow: [],
    values: { line_length: 88, indent_width: 4 },
    ignoredRules: new Set(),
    isAllowed: () => false,
  };
}

describe("parseRuffOutput", () => {
  test("returns correct LintIssue[] from fixture", () => {
    const issues = parseRuffOutput(fixtureText, makeConfig());

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
    expect(e501.fingerprint).toHaveLength(64);

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
    const issues = parseRuffOutput("", makeConfig());
    expect(issues).toHaveLength(0);
  });

  test("returns [] for invalid JSON", () => {
    const issues = parseRuffOutput("not valid json {[}", makeConfig());
    expect(issues).toHaveLength(0);
  });

  test("returns [] for null JSON", () => {
    const issues = parseRuffOutput("null", makeConfig());
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
    const issues = parseRuffOutput(input, makeConfig());
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
    const issues = parseRuffOutput(input, makeConfig());
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
    const issues = parseRuffOutput(input, makeConfig());
    expect(issues[0]?.severity).toBe("warning");
  });
});

describe("ruffRunner", () => {
  test("isAvailable returns true when ruff exits 0", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["ruff", "--version"], { stdout: "ruff 0.4.0", stderr: "", exitCode: 0 });
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

  test("generateConfig returns non-null string", () => {
    const config = ruffRunner.generateConfig(makeConfig());
    expect(config).not.toBeNull();
    expect(typeof config).toBe("string");
    if (config !== null) {
      expect(config.length).toBeGreaterThan(0);
    }
  });

  test("id and name are correct", () => {
    expect(ruffRunner.id).toBe("ruff");
    expect(ruffRunner.name).toBe("Ruff");
    expect(ruffRunner.configFile).toBe("ruff.toml");
  });
});
