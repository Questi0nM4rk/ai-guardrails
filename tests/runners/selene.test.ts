import { describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { parseSeleneOutput, seleneRunner } from "@/runners/selene";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

const FIXTURE_PATH = resolve(import.meta.dir, "../fixtures/selene-output.json");
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
    isAllowed: () => false,
    ...overrides,
  };
}

describe("parseSeleneOutput", () => {
  test("returns LintIssue[] from fixture", () => {
    const issues = parseSeleneOutput(FIXTURE_JSON, PROJECT_DIR);
    expect(issues).toHaveLength(2);

    const first = issues[0];
    expect(first).toBeDefined();
    if (!first) return;
    expect(first.rule).toBe("selene/unused_variable");
    expect(first.linter).toBe("selene");
    expect(first.file).toBe("/project/src/game.lua");
    expect(first.line).toBe(10);
    expect(first.col).toBe(5);
    expect(first.message).toBe("unused variable `score`");
    expect(first.fingerprint).toHaveLength(64);
  });

  test("maps Warning severity to warning", () => {
    const issues = parseSeleneOutput(FIXTURE_JSON, PROJECT_DIR);
    const warning = issues.find((i) => i.rule === "selene/unused_variable");
    expect(warning).toBeDefined();
    if (!warning) return;
    expect(warning.severity).toBe("warning");
  });

  test("maps Error severity to error", () => {
    const issues = parseSeleneOutput(FIXTURE_JSON, PROJECT_DIR);
    const error = issues.find(
      (i) => i.rule === "selene/incorrect_standard_library_use"
    );
    expect(error).toBeDefined();
    if (!error) return;
    expect(error.severity).toBe("error");
  });

  test("returns [] for empty array", () => {
    const issues = parseSeleneOutput("[]", PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("returns [] for malformed JSON", () => {
    const issues = parseSeleneOutput("not valid json", PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });
});

describe("seleneRunner.run", () => {
  test("returns [] when no Lua files found", async () => {
    const runner = new FakeCommandRunner();
    const fm = new FakeFileManager();
    // No Lua files seeded in FakeFileManager — glob returns []

    const issues = await seleneRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: fm,
    });

    expect(issues).toHaveLength(0);
    // selene should not have been called
    expect(runner.calls).toHaveLength(0);
  });

  test("calls selene with Json2 display style when Lua files present", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["selene", "--display-style=Json2", PROJECT_DIR], {
      stdout: FIXTURE_JSON,
      stderr: "",
      exitCode: 1, // selene exits non-zero when issues found
    });
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/src/game.lua`, "-- code");

    const issues = await seleneRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: fm,
    });

    expect(runner.calls[0]).toEqual(["selene", "--display-style=Json2", PROJECT_DIR]);
    expect(issues).toHaveLength(2);
  });
});

describe("seleneRunner.isAvailable", () => {
  test("returns true when selene --version exits 0", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["selene", "--version"], {
      stdout: "selene 0.27.1",
      stderr: "",
      exitCode: 0,
    });
    const result = await seleneRunner.isAvailable(runner);
    expect(result).toBe(true);
  });

  test("returns false when selene --version exits non-zero", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["selene", "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    const result = await seleneRunner.isAvailable(runner);
    expect(result).toBe(false);
  });
});
