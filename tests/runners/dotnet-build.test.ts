import { describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { dotnetBuildRunner, parseDotnetBuildOutput } from "@/runners/dotnet-build";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

const FIXTURE_PATH = resolve(import.meta.dir, "../fixtures/dotnet-build-output.txt");
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

describe("parseDotnetBuildOutput", () => {
  test("returns correct LintIssue[] from fixture", () => {
    const issues = parseDotnetBuildOutput(FIXTURE_TEXT, PROJECT_DIR, makeConfig());
    // fixture has 2 warnings + 1 error = 3 issues
    expect(issues).toHaveLength(3);

    const first = issues[0];
    expect(first).toBeDefined();
    if (!first) return;
    expect(first.rule).toBe("dotnet-build/CS0168");
    expect(first.linter).toBe("dotnet-build");
    expect(first.file).toBe("/project/src/MyClass.cs");
    expect(first.line).toBe(12);
    expect(first.col).toBe(5);
    expect(first.message).toBe("Variable 'e' is declared but never used");
    expect(first.severity).toBe("warning");
  });

  test("captures both warnings and errors", () => {
    const issues = parseDotnetBuildOutput(FIXTURE_TEXT, PROJECT_DIR, makeConfig());
    const severities = issues.map((i) => i.severity);
    expect(severities).toContain("warning");
    expect(severities).toContain("error");
  });

  test("returns [] for empty output", () => {
    const issues = parseDotnetBuildOutput("", PROJECT_DIR, makeConfig());
    expect(issues).toHaveLength(0);
  });

  test("skips malformed lines", () => {
    const output = [
      "Build started...",
      "Some random build output",
      "Error: something weird",
      "src/Foo.cs(1,1): error CS0001: Real error [proj.csproj]",
    ].join("\n");
    const issues = parseDotnetBuildOutput(output, PROJECT_DIR, makeConfig());
    expect(issues).toHaveLength(1);
    expect(issues[0]?.rule).toBe("dotnet-build/CS0001");
  });

  test("resolves relative file path against projectDir", () => {
    const output =
      "src/Foo.cs(5,3): error CS0103: The name 'x' does not exist [proj.csproj]";
    const issues = parseDotnetBuildOutput(output, "/my/project", makeConfig());
    expect(issues[0]?.file).toBe("/my/project/src/Foo.cs");
  });

  test("preserves absolute file path unchanged", () => {
    const output =
      "/absolute/path/Foo.cs(5,3): error CS0103: The name 'x' does not exist [proj.csproj]";
    const issues = parseDotnetBuildOutput(output, PROJECT_DIR, makeConfig());
    expect(issues[0]?.file).toBe("/absolute/path/Foo.cs");
  });

  test("profile minimal filters out warnings", () => {
    const issues = parseDotnetBuildOutput(
      FIXTURE_TEXT,
      PROJECT_DIR,
      makeConfig({ profile: "minimal" })
    );
    expect(issues.every((i) => i.severity === "error")).toBe(true);
    expect(issues).toHaveLength(1);
  });

  test("profile standard includes warnings", () => {
    const issues = parseDotnetBuildOutput(
      FIXTURE_TEXT,
      PROJECT_DIR,
      makeConfig({ profile: "standard" })
    );
    const warnings = issues.filter((i) => i.severity === "warning");
    expect(warnings.length).toBeGreaterThan(0);
  });

  test("profile strict includes warnings", () => {
    const issues = parseDotnetBuildOutput(
      FIXTURE_TEXT,
      PROJECT_DIR,
      makeConfig({ profile: "strict" })
    );
    const warnings = issues.filter((i) => i.severity === "warning");
    expect(warnings.length).toBeGreaterThan(0);
  });

  test("prefixes rule with dotnet-build/", () => {
    const output =
      "src/Foo.cs(1,1): error CS0103: The name 'x' does not exist [proj.csproj]";
    const issues = parseDotnetBuildOutput(output, PROJECT_DIR, makeConfig());
    expect(issues[0]?.rule).toBe("dotnet-build/CS0103");
  });
});

describe("dotnetBuildRunner.isAvailable", () => {
  test("returns true when dotnet exits 0", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["dotnet", "--version"], {
      stdout: "9.0.200",
      stderr: "",
      exitCode: 0,
    });
    const result = await dotnetBuildRunner.isAvailable(runner, PROJECT_DIR);
    expect(result).toBe(true);
  });

  test("returns false when dotnet exits non-zero", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["dotnet", "--version"], {
      stdout: "",
      stderr: "command not found",
      exitCode: 127,
    });
    const result = await dotnetBuildRunner.isAvailable(runner, PROJECT_DIR);
    expect(result).toBe(false);
  });

  test("returns false when commandRunner throws", async () => {
    const runner = new FakeCommandRunner();
    // No registration — FakeCommandRunner returns exitCode 0 by default for unknown keys,
    // so we override run to throw to simulate a missing binary.
    const throwingRunner = {
      calls: runner.calls,
      async run(_args: string[]): Promise<never> {
        throw new Error("ENOENT: dotnet not found");
      },
    };
    const result = await dotnetBuildRunner.isAvailable(throwingRunner, PROJECT_DIR);
    expect(result).toBe(false);
  });
});

describe("dotnetBuildRunner.run", () => {
  test("returns LintIssue[] from stdout+stderr combined", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["dotnet", "build", "--no-restore", "-v:q"], {
      stdout: FIXTURE_TEXT,
      stderr: "",
      exitCode: 1,
    });

    const issues = await dotnetBuildRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(issues).toHaveLength(3);
    expect(issues.every((i) => typeof i.fingerprint === "string")).toBe(true);
  });

  test("returns [] when build output has no diagnostics", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["dotnet", "build", "--no-restore", "-v:q"], {
      stdout: "Build succeeded.\n    0 Warning(s)\n    0 Error(s)\n",
      stderr: "",
      exitCode: 0,
    });

    const issues = await dotnetBuildRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig(),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(issues).toHaveLength(0);
  });

  test("filters warnings in minimal profile", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["dotnet", "build", "--no-restore", "-v:q"], {
      stdout: FIXTURE_TEXT,
      stderr: "",
      exitCode: 1,
    });

    const issues = await dotnetBuildRunner.run({
      projectDir: PROJECT_DIR,
      config: makeConfig({ profile: "minimal" }),
      commandRunner: runner,
      fileManager: new FakeFileManager(),
    });

    expect(issues.every((i) => i.severity === "error")).toBe(true);
  });

  test("runner id, name, configFile are correct", () => {
    expect(dotnetBuildRunner.id).toBe("dotnet-build");
    expect(dotnetBuildRunner.name).toBe("dotnet build");
    expect(dotnetBuildRunner.configFile).toBeNull();
  });
});
