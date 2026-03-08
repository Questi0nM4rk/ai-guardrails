import { describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { parseShellcheckOutput, shellcheckRunner } from "@/runners/shellcheck";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

const FIXTURE_PATH = resolve(import.meta.dir, "../fixtures/shellcheck-output.json");
const PROJECT_DIR = "/project";

const FIXTURE_JSON = await Bun.file(FIXTURE_PATH).text();

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

describe("parseShellcheckOutput", () => {
    test("returns correct LintIssue[] from fixture", () => {
        const issues = parseShellcheckOutput(FIXTURE_JSON, PROJECT_DIR);
        expect(issues).toHaveLength(2);

        const first = issues[0];
        expect(first).toBeDefined();
        if (!first) return;
        expect(first.rule).toBe("shellcheck/SC2086");
        expect(first.linter).toBe("shellcheck");
        expect(first.file).toBe("/project/script.sh");
        expect(first.line).toBe(3);
        expect(first.col).toBe(1);
        expect(first.message).toBe(
            "Double quote to prevent globbing and word splitting."
        );
        expect(first.severity).toBe("error");
        expect(first.fingerprint).toHaveLength(64);
    });

    test("maps SC codes correctly (e.g. SC2086)", () => {
        const issues = parseShellcheckOutput(FIXTURE_JSON, PROJECT_DIR);
        const sc2086 = issues.find((i) => i.rule === "shellcheck/SC2086");
        expect(sc2086).toBeDefined();
        if (!sc2086) return;
        expect(sc2086.rule).toBe("shellcheck/SC2086");
    });

    test("maps warning level to warning severity", () => {
        const issues = parseShellcheckOutput(FIXTURE_JSON, PROJECT_DIR);
        const warning = issues.find((i) => i.rule === "shellcheck/SC2034");
        expect(warning).toBeDefined();
        if (!warning) return;
        expect(warning.severity).toBe("warning");
        expect(warning.line).toBe(7);
        expect(warning.col).toBe(5);
        expect(warning.message).toBe("var appears unused. Verify it or export it.");
    });

    test("maps error level to error severity", () => {
        const issues = parseShellcheckOutput(FIXTURE_JSON, PROJECT_DIR);
        const error = issues.find((i) => i.rule === "shellcheck/SC2086");
        expect(error).toBeDefined();
        if (!error) return;
        expect(error.severity).toBe("error");
    });

    test("returns [] for empty comments array", () => {
        const issues = parseShellcheckOutput('{"comments":[]}', PROJECT_DIR);
        expect(issues).toHaveLength(0);
    });

    test("returns [] for malformed JSON", () => {
        const issues = parseShellcheckOutput("not valid json", PROJECT_DIR);
        expect(issues).toHaveLength(0);
    });
});

describe("shellcheckRunner.run", () => {
    test("returns [] when no shell files found", async () => {
        const runner = new FakeCommandRunner();
        const fm = new FakeFileManager();
        // No shell files seeded

        const issues = await shellcheckRunner.run({
            projectDir: PROJECT_DIR,
            config: makeConfig(),
            commandRunner: runner,
            fileManager: fm,
        });

        expect(issues).toHaveLength(0);
        expect(runner.calls).toHaveLength(0);
    });

    test("calls shellcheck with all found shell files", async () => {
        const runner = new FakeCommandRunner();
        // Seed with subdirectory path: FakeFileManager **/* glob requires a "/" before the filename
        runner.register(
            ["shellcheck", "--format=json1", "scripts/script.sh", "scripts/other.bash"],
            {
                stdout: FIXTURE_JSON,
                stderr: "",
                exitCode: 1,
            }
        );

        const fm = new FakeFileManager();
        fm.seed("scripts/script.sh", "#!/bin/bash\necho $foo\n");
        fm.seed("scripts/other.bash", "#!/bin/bash\nvar=unused\n");

        const issues = await shellcheckRunner.run({
            projectDir: PROJECT_DIR,
            config: makeConfig(),
            commandRunner: runner,
            fileManager: fm,
        });

        expect(runner.calls).toHaveLength(1);
        const call = runner.calls[0];
        expect(call).toBeDefined();
        if (!call) return;
        expect(call[0]).toBe("shellcheck");
        expect(call[1]).toBe("--format=json1");
        expect(call).toContain("scripts/script.sh");
        expect(call).toContain("scripts/other.bash");
        expect(issues).toHaveLength(2);
    });
});

describe("shellcheckRunner.isAvailable", () => {
    test("returns true when shellcheck --version exits 0", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["shellcheck", "--version"], {
            stdout: "ShellCheck, version 0.9.0",
            stderr: "",
            exitCode: 0,
        });
        const result = await shellcheckRunner.isAvailable(runner);
        expect(result).toBe(true);
    });

    test("returns false when shellcheck --version exits non-zero", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["shellcheck", "--version"], {
            stdout: "",
            stderr: "not found",
            exitCode: 127,
        });
        const result = await shellcheckRunner.isAvailable(runner);
        expect(result).toBe(false);
    });
});
