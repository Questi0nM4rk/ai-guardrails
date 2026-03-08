import { describe, expect, test } from "bun:test";
import type { ResolvedConfig } from "@/config/schema";
import { parsePyrightOutput, pyrightRunner } from "@/runners/pyright";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

const FIXTURE_PATH = new URL("../fixtures/pyright-output.json", import.meta.url)
    .pathname;
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

describe("parsePyrightOutput", () => {
    test("returns correct LintIssue[] from fixture", () => {
        // Fixture has 3 diagnostics: error, warning, information
        // information is skipped, so we expect 2 results
        const issues = parsePyrightOutput(fixtureText);

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
        expect(errorIssue.fingerprint).toHaveLength(64);

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

        const issues = parsePyrightOutput(input);
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

        const issues = parsePyrightOutput(input);
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

        const issues = parsePyrightOutput(input);
        expect(issues).toHaveLength(1);
        expect(issues[0]?.rule).toBe("pyright/unknown");
    });

    test("returns [] for empty stdout", () => {
        const issues = parsePyrightOutput("");
        expect(issues).toHaveLength(0);
    });

    test("returns [] for invalid JSON", () => {
        const issues = parsePyrightOutput("not valid json {[}");
        expect(issues).toHaveLength(0);
    });

    test("returns [] when generalDiagnostics is missing", () => {
        const issues = parsePyrightOutput(
            JSON.stringify({ summary: { errorCount: 0 } })
        );
        expect(issues).toHaveLength(0);
    });
});

describe("pyrightRunner", () => {
    test("isAvailable returns true when pyright exits 0", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["pyright", "--version"], {
            stdout: "pyright 1.1.385",
            stderr: "",
            exitCode: 0,
        });
        const result = await pyrightRunner.isAvailable(runner);
        expect(result).toBe(true);
    });

    test("isAvailable returns false when pyright exits non-zero", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["pyright", "--version"], {
            stdout: "",
            stderr: "pyright: command not found",
            exitCode: 127,
        });
        const result = await pyrightRunner.isAvailable(runner);
        expect(result).toBe(false);
    });

    test("run calls pyright with --outputjson", async () => {
        const commandRunner = new FakeCommandRunner();
        const projectDir = "/home/user/project";
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

        expect(commandRunner.calls).toContainEqual([
            "pyright",
            "--outputjson",
            projectDir,
        ]);
        expect(issues).toHaveLength(0);
    });

    test("run returns issues even when exitCode is non-zero", async () => {
        const commandRunner = new FakeCommandRunner();
        const projectDir = "/home/user/project";
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
