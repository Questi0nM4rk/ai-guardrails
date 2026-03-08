import { describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { clippyRunner, parseClippyNdjson } from "@/runners/clippy";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

function makeConfig(): ResolvedConfig {
    return {
        profile: "standard",
        ignore: [],
        allow: [],
        values: { line_length: 100, indent_width: 4 },
        ignoredRules: new Set(),
        isAllowed: () => false,
    };
}

const FIXTURE_PATH = resolve(import.meta.dir, "../fixtures/clippy-output.ndjson");
const PROJECT_DIR = "/project";

const FIXTURE_NDJSON = await Bun.file(FIXTURE_PATH).text();

describe("parseClippyNdjson", () => {
    test("returns LintIssue[] from fixture", () => {
        const issues = parseClippyNdjson(FIXTURE_NDJSON, PROJECT_DIR);
        // Only 2 valid compiler-message objects with non-null code
        expect(issues).toHaveLength(2);
    });

    test("filters non-compiler-message objects", () => {
        const ndjson = [
            JSON.stringify({ reason: "compiler-artifact", target: { name: "mylib" } }),
            JSON.stringify({
                reason: "compiler-message",
                message: {
                    code: { code: "clippy::needless_return" },
                    level: "warning",
                    message: "unneeded `return` statement",
                    spans: [
                        {
                            file_name: "src/main.rs",
                            line_start: 5,
                            column_start: 5,
                            is_primary: true,
                        },
                    ],
                },
            }),
            JSON.stringify({ reason: "build-finished", success: true }),
        ].join("\n");

        const issues = parseClippyNdjson(ndjson, PROJECT_DIR);
        expect(issues).toHaveLength(1);
    });

    test("filters messages with null code", () => {
        const ndjson = JSON.stringify({
            reason: "compiler-message",
            message: {
                code: null,
                level: "note",
                message: "some build note",
                spans: [
                    {
                        file_name: "src/lib.rs",
                        line_start: 1,
                        column_start: 1,
                        is_primary: true,
                    },
                ],
            },
        });

        const issues = parseClippyNdjson(ndjson, PROJECT_DIR);
        expect(issues).toHaveLength(0);
    });

    test("uses primary span for file/line/col", () => {
        const ndjson = JSON.stringify({
            reason: "compiler-message",
            message: {
                code: { code: "clippy::needless_return" },
                level: "warning",
                message: "unneeded `return` statement",
                spans: [
                    {
                        file_name: "src/main.rs",
                        line_start: 3,
                        column_start: 1,
                        is_primary: false,
                    },
                    {
                        file_name: "src/main.rs",
                        line_start: 5,
                        column_start: 5,
                        is_primary: true,
                    },
                ],
            },
        });

        const issues = parseClippyNdjson(ndjson, PROJECT_DIR);
        expect(issues).toHaveLength(1);
        const issue = issues[0];
        expect(issue).toBeDefined();
        if (!issue) return;
        expect(issue.line).toBe(5);
        expect(issue.col).toBe(5);
        expect(issue.file).toBe("/project/src/main.rs");
    });

    test("maps fields correctly", () => {
        const issues = parseClippyNdjson(FIXTURE_NDJSON, PROJECT_DIR);
        const first = issues[0];
        expect(first).toBeDefined();
        if (!first) return;
        expect(first.rule).toBe("clippy/clippy::needless_return");
        expect(first.linter).toBe("clippy");
        expect(first.file).toBe("/project/src/main.rs");
        expect(first.line).toBe(5);
        expect(first.col).toBe(5);
        expect(first.message).toBe("unneeded `return` statement");
        expect(first.severity).toBe("warning");
        expect(first.fingerprint).toHaveLength(64);
    });

    test("maps error level to error severity", () => {
        const issues = parseClippyNdjson(FIXTURE_NDJSON, PROJECT_DIR);
        const errorIssue = issues.find((i) => i.rule === "clippy/clippy::unwrap_used");
        expect(errorIssue).toBeDefined();
        if (!errorIssue) return;
        expect(errorIssue.severity).toBe("error");
    });
});

describe("clippyRunner.run", () => {
    test("runs cargo clippy with correct args and returns issues", async () => {
        const runner = new FakeCommandRunner();
        runner.register(
            ["cargo", "clippy", "--message-format=json", "--", "-D", "warnings"],
            {
                stdout: FIXTURE_NDJSON,
                stderr: "",
                exitCode: 1, // cargo exits non-zero when clippy finds errors
            }
        );

        const issues = await clippyRunner.run({
            projectDir: PROJECT_DIR,
            config: makeConfig(),
            commandRunner: runner,
            fileManager: new FakeFileManager(),
        });

        expect(runner.calls).toContainEqual([
            "cargo",
            "clippy",
            "--message-format=json",
            "--",
            "-D",
            "warnings",
        ]);
        expect(issues).toHaveLength(2);
    });

    test("returns [] when no issues", async () => {
        const runner = new FakeCommandRunner();
        runner.register(
            ["cargo", "clippy", "--message-format=json", "--", "-D", "warnings"],
            {
                stdout: "",
                stderr: "",
                exitCode: 0,
            }
        );

        const issues = await clippyRunner.run({
            projectDir: PROJECT_DIR,
            config: makeConfig(),
            commandRunner: runner,
            fileManager: new FakeFileManager(),
        });

        expect(issues).toHaveLength(0);
    });
});

describe("clippyRunner.isAvailable", () => {
    test("returns true when cargo clippy --version exits 0", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["cargo", "clippy", "--version"], {
            stdout: "clippy 0.1.85",
            stderr: "",
            exitCode: 0,
        });
        const result = await clippyRunner.isAvailable(runner);
        expect(result).toBe(true);
    });

    test("returns false when cargo clippy --version exits non-zero", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["cargo", "clippy", "--version"], {
            stdout: "",
            stderr: "error: no such subcommand",
            exitCode: 101,
        });
        const result = await clippyRunner.isAvailable(runner);
        expect(result).toBe(false);
    });
});
