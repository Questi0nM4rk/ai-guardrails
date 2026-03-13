import { describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { parseShfmtOutput, shfmtRunner } from "@/runners/shfmt";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

const FIXTURE_PATH = resolve(import.meta.dir, "../fixtures/shfmt-output.txt");
const PROJECT_DIR = "/project";

const FIXTURE_TXT = await Bun.file(FIXTURE_PATH).text();

function makeConfig(overrides?: Partial<ResolvedConfig>): ResolvedConfig {
  return {
    profile: "standard",
    ignore: [],
    allow: [],
    values: { line_length: 100, indent_width: 2 },
    ignoredRules: new Set(),
    isAllowed: () => false,
    ...overrides,
  };
}

describe("parseShfmtOutput", () => {
  test("returns one LintIssue per listed file", () => {
    const issues = parseShfmtOutput(FIXTURE_TXT, PROJECT_DIR);
    expect(issues).toHaveLength(2);

    const first = issues[0];
    expect(first).toBeDefined();
    if (!first) return;
    expect(first.rule).toBe("shfmt/format");
    expect(first.linter).toBe("shfmt");
    expect(first.file).toBe("/project/script.sh");
    expect(first.line).toBe(1);
    expect(first.col).toBe(1);
    expect(first.message).toBe("File needs formatting — run: shfmt -w script.sh");
    expect(first.severity).toBe("error");
    expect(first.fingerprint).toHaveLength(64);
  });

  test("returns [] for empty output", () => {
    const issues = parseShfmtOutput("", PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("returns [] for whitespace-only output", () => {
    const issues = parseShfmtOutput("   \n  \n", PROJECT_DIR);
    expect(issues).toHaveLength(0);
  });

  test("maps second file in fixture correctly", () => {
    const issues = parseShfmtOutput(FIXTURE_TXT, PROJECT_DIR);
    const second = issues[1];
    expect(second).toBeDefined();
    if (!second) return;
    expect(second.file).toBe("/project/other.sh");
    expect(second.message).toBe("File needs formatting — run: shfmt -w other.sh");
  });
});

describe("shfmtRunner.run", () => {
  test("returns [] when no shell files found", async () => {
    const runner = new FakeCommandRunner();
    const fm = new FakeFileManager();
    // No shell files seeded

    const issues = await shfmtRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: fm,
    });

    expect(issues).toHaveLength(0);
    expect(runner.calls).toHaveLength(0);
  });

  test("calls shfmt -l with found shell files", async () => {
    const runner = new FakeCommandRunner();
    // Seed with subdirectory path: FakeFileManager **/* glob requires a "/" before the filename
    runner.register(["shfmt", "-l", "scripts/script.sh"], {
      stdout: "scripts/script.sh\n",
      stderr: "",
      exitCode: 1,
    });

    const fm = new FakeFileManager();
    fm.seed("scripts/script.sh", "#!/bin/bash\necho 'unformatted'");

    const issues = await shfmtRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: fm,
    });

    expect(runner.calls).toHaveLength(1);
    const call = runner.calls[0];
    expect(call).toBeDefined();
    if (!call) return;
    expect(call[0]).toBe("shfmt");
    expect(call[1]).toBe("-l");
    expect(call).toContain("scripts/script.sh");
    expect(issues).toHaveLength(1);
  });

  test("returns [] when all files are already formatted (empty stdout)", async () => {
    const runner = new FakeCommandRunner();
    // Seed with subdirectory path: FakeFileManager **/* glob requires a "/" before the filename
    runner.register(["shfmt", "-l", "scripts/script.sh"], {
      stdout: "",
      stderr: "",
      exitCode: 0,
    });

    const fm = new FakeFileManager();
    fm.seed("scripts/script.sh", "#!/bin/bash\necho 'formatted'\n");

    const issues = await shfmtRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: fm,
    });

    expect(issues).toHaveLength(0);
  });
});

describe("shfmtRunner.isAvailable", () => {
  test("returns true when shfmt --version exits 0", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["shfmt", "--version"], {
      stdout: "v3.7.0",
      stderr: "",
      exitCode: 0,
    });
    const result = await shfmtRunner.isAvailable(runner);
    expect(result).toBe(true);
  });

  test("returns false when shfmt --version exits non-zero", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["shfmt", "--version"], {
      stdout: "",
      stderr: "not found",
      exitCode: 127,
    });
    const result = await shfmtRunner.isAvailable(runner);
    expect(result).toBe(false);
  });
});
