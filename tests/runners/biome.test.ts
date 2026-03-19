import { beforeEach, describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import {
  biomeRunner,
  getBiomeVersion,
  parseBiomeRdjsonOutput,
  resetBiomeVersionCache,
} from "@/runners/biome";
import { clearResolveToolPathCache } from "@/utils/resolve-tool-path";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

beforeEach(() => {
  clearResolveToolPathCache();
  resetBiomeVersionCache();
});

const FIXTURE_PATH = resolve(import.meta.dir, "../fixtures/biome-rdjson-output.json");
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

describe("parseBiomeRdjsonOutput", () => {
  test("returns correct LintIssue[] from fixture", () => {
    const issues = parseBiomeRdjsonOutput(FIXTURE_JSON, PROJECT_DIR);
    expect(issues).toHaveLength(3);

    const first = issues[0];
    expect(first).toBeDefined();
    if (!first) return;
    expect(first.rule).toBe("biome/lint/correctness/noUnusedVariables");
    expect(first.linter).toBe("biome");
    expect(first.file).toBe("/project/src/foo.ts");
    expect(first.line).toBe(10); // biome v2 emits 1-based line numbers directly
    expect(first.col).toBe(4); // biome v2 emits 1-based column numbers directly
    expect(first.message).toBe("This variable is unused.");
    // biome v2 rdjson omits severity field; defaults to warning
    expect(first.severity).toBe("warning");
  });

  test("returns [] for empty diagnostics array", () => {
    const issues = parseBiomeRdjsonOutput('{"diagnostics":[]}', PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("passes through 1-based line/column numbers from biome v2 rdjson", () => {
    const json = JSON.stringify({
      diagnostics: [
        {
          location: {
            path: "src/foo.ts",
            range: {
              start: { line: 1, column: 1 },
              end: { line: 1, column: 6 },
            },
          },
          code: { value: "lint/style/noVar" },
          message: "Use const or let instead of var.",
        },
      ],
    });
    const issues = parseBiomeRdjsonOutput(json, PROJECT_DIR);
    const issue = issues[0];
    expect(issue).toBeDefined();
    if (!issue) return;
    expect(issue.line).toBe(1);
    expect(issue.col).toBe(1);
  });

  test("resolves relative paths to absolute", () => {
    const json = JSON.stringify({
      diagnostics: [
        {
          location: {
            path: "src/nested/file.ts",
            range: {
              start: { line: 6, column: 3 },
              end: { line: 6, column: 11 },
            },
          },
          code: { value: "lint/correctness/noUnusedVariables" },
          message: "Unused.",
        },
      ],
    });
    const issues = parseBiomeRdjsonOutput(json, "/my/project");
    const issue = issues[0];
    expect(issue).toBeDefined();
    if (!issue) return;
    expect(issue.file).toBe("/my/project/src/nested/file.ts");
  });

  test("defaults severity to warning when absent (biome v2 omits severity field)", () => {
    const issues = parseBiomeRdjsonOutput(FIXTURE_JSON, PROJECT_DIR);
    // biome v2 rdjson does not include a severity field — all issues default to warning
    for (const issue of issues) {
      expect(issue.severity).toBe("warning");
    }
  });

  test("maps ERROR severity to error when present", () => {
    const json = JSON.stringify({
      diagnostics: [
        {
          location: {
            path: "src/foo.ts",
            range: {
              start: { line: 1, column: 1 },
              end: { line: 1, column: 5 },
            },
          },
          severity: "ERROR",
          code: { value: "lint/correctness/noUnusedVariables" },
          message: "Unused.",
        },
      ],
    });
    const issues = parseBiomeRdjsonOutput(json, PROJECT_DIR);
    const issue = issues[0];
    expect(issue).toBeDefined();
    if (!issue) return;
    expect(issue.severity).toBe("error");
  });

  test("returns [] for malformed JSON", () => {
    const issues = parseBiomeRdjsonOutput("not valid json", PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });
});

const LOCAL_BIOME_PROJECT = `${PROJECT_DIR}/node_modules/.bin/biome`;

describe("biomeRunner.run", () => {
  test("uses --reporter=rdjson flag (falls back to global when local absent)", async () => {
    const runner = new FakeCommandRunner();
    // Local biome not available — fall back to global
    runner.register([LOCAL_BIOME_PROJECT, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    runner.register(["biome", "--version"], {
      stdout: "biome 2.0.0",
      stderr: "",
      exitCode: 0,
    });
    runner.register(["biome", "ci", "--reporter=rdjson", PROJECT_DIR], {
      stdout: FIXTURE_JSON,
      stderr: "",
      exitCode: 1, // biome exits non-zero when issues found
    });

    const issues = await biomeRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(runner.calls).toContainEqual([
      "biome",
      "ci",
      "--reporter=rdjson",
      PROJECT_DIR,
    ]);
    expect(issues).toHaveLength(3);
  });

  test("parses stdout regardless of non-zero exit code", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_BIOME_PROJECT, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    runner.register(["biome", "--version"], {
      stdout: "biome 2.0.0",
      stderr: "",
      exitCode: 0,
    });
    runner.register(["biome", "ci", "--reporter=rdjson", PROJECT_DIR], {
      stdout: FIXTURE_JSON,
      stderr: "some stderr",
      exitCode: 2,
    });

    const issues = await biomeRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(issues).toHaveLength(3);
  });
});

const LOCAL_BIOME_CWD = "node_modules/.bin/biome";

describe("biomeRunner.isAvailable", () => {
  test("returns true when local biome exits 0", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_BIOME_CWD, "--version"], {
      stdout: "biome 2.0.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await biomeRunner.isAvailable(runner);
    expect(result).toBe(true);
  });

  test("returns true when global biome exits 0 (local absent)", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_BIOME_CWD, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    runner.register(["biome", "--version"], {
      stdout: "biome 2.0.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await biomeRunner.isAvailable(runner);
    expect(result).toBe(true);
  });

  test("returns false when both local and global are absent", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_BIOME_CWD, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    runner.register(["biome", "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    const result = await biomeRunner.isAvailable(runner);
    expect(result).toBe(false);
  });
});

describe("biomeRunner node_modules/.bin resolution", () => {
  const LOCAL_BIOME = `${PROJECT_DIR}/node_modules/.bin/biome`;

  test("isAvailable uses local node_modules/.bin/biome when present", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_BIOME, "--version"], {
      stdout: "biome 2.0.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await biomeRunner.isAvailable(runner, PROJECT_DIR);
    expect(result).toBe(true);
    expect(runner.calls[0]).toContain(LOCAL_BIOME);
  });

  test("isAvailable falls back to global biome when local absent", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_BIOME, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    runner.register(["biome", "--version"], {
      stdout: "biome 2.0.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await biomeRunner.isAvailable(runner, PROJECT_DIR);
    expect(result).toBe(true);
  });

  test("run uses local node_modules/.bin/biome when present", async () => {
    const runner = new FakeCommandRunner();
    // resolveBiomePath probes local first
    runner.register([LOCAL_BIOME, "--version"], {
      stdout: "biome 2.0.0",
      stderr: "",
      exitCode: 0,
    });
    runner.register([LOCAL_BIOME, "ci", "--reporter=rdjson", PROJECT_DIR], {
      stdout: FIXTURE_JSON,
      stderr: "",
      exitCode: 1,
    });

    const issues = await biomeRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(runner.calls).toContainEqual([
      LOCAL_BIOME,
      "ci",
      "--reporter=rdjson",
      PROJECT_DIR,
    ]);
    expect(issues).toHaveLength(3);
  });
});

describe("getBiomeVersion", () => {
  test("getBiomeVersion parses version from biome output", async () => {
    const runner = new FakeCommandRunner();
    runner.register([LOCAL_BIOME_PROJECT, "--version"], {
      stdout: "biome 2.4.8",
      stderr: "",
      exitCode: 0,
    });

    const version = await getBiomeVersion(runner, PROJECT_DIR);
    expect(version).toBe("2.4.8");
  });

  test("getBiomeVersion falls back to global biome when local not found", async () => {
    const runner = new FakeCommandRunner();
    // local biome absent
    runner.register([LOCAL_BIOME_PROJECT, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    // global biome present
    runner.register(["biome", "--version"], {
      stdout: "biome 2.5.0",
      stderr: "",
      exitCode: 0,
    });

    const version = await getBiomeVersion(runner, PROJECT_DIR);
    expect(version).toBe("2.5.0");
  });

  test("getBiomeVersion returns undefined on failure", async () => {
    const runner = new FakeCommandRunner();
    // local biome absent
    runner.register([LOCAL_BIOME_PROJECT, "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    // global biome absent
    runner.register(["biome", "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });

    const version = await getBiomeVersion(runner, PROJECT_DIR);
    expect(version).toBeUndefined();
  });
});
