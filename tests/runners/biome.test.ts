import { describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { biomeRunner, parseBiomeRdjsonOutput } from "@/runners/biome";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

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
        expect(first.line).toBe(10); // 0-indexed 9 → 1-indexed 10
        expect(first.col).toBe(4); // 0-indexed 3 → 1-indexed 4
        expect(first.message).toBe("This variable is unused.");
        expect(first.severity).toBe("error");
        expect(first.fingerprint).toHaveLength(64);
    });

    test("returns [] for empty diagnostics array", () => {
        const issues = parseBiomeRdjsonOutput('{"diagnostics":[]}', PROJECT_DIR);
        expect(issues).toHaveLength(0);
    });

    test("converts 0-indexed lines to 1-indexed", () => {
        const json = JSON.stringify({
            diagnostics: [
                {
                    location: {
                        path: { text: "src/foo.ts" },
                        range: {
                            start: { line: 0, character: 0 },
                            end: { line: 0, character: 5 },
                        },
                    },
                    severity: "ERROR",
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
                        path: { text: "src/nested/file.ts" },
                        range: {
                            start: { line: 5, character: 2 },
                            end: { line: 5, character: 10 },
                        },
                    },
                    severity: "ERROR",
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

    test("maps WARNING severity to warning", () => {
        const issues = parseBiomeRdjsonOutput(FIXTURE_JSON, PROJECT_DIR);
        const warning = issues.find(
            (i) => i.rule === "biome/lint/suspicious/noExplicitAny"
        );
        expect(warning).toBeDefined();
        if (!warning) return;
        expect(warning.severity).toBe("warning");
    });

    test("maps ERROR severity to error", () => {
        const issues = parseBiomeRdjsonOutput(FIXTURE_JSON, PROJECT_DIR);
        const error = issues.find(
            (i) => i.rule === "biome/lint/correctness/noUnusedVariables"
        );
        expect(error).toBeDefined();
        if (!error) return;
        expect(error.severity).toBe("error");
    });

    test("returns [] for malformed JSON", () => {
        const issues = parseBiomeRdjsonOutput("not valid json", PROJECT_DIR);
        expect(issues).toHaveLength(0);
    });
});

describe("biomeRunner.run", () => {
    test("uses --reporter=rdjson flag", async () => {
        const runner = new FakeCommandRunner();
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

        expect(runner.calls[0]).toEqual([
            "biome",
            "ci",
            "--reporter=rdjson",
            PROJECT_DIR,
        ]);
        expect(issues).toHaveLength(3);
    });

    test("parses stdout regardless of non-zero exit code", async () => {
        const runner = new FakeCommandRunner();
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

describe("biomeRunner.isAvailable", () => {
    test("returns true when biome --version exits 0", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["biome", "--version"], {
            stdout: "biome 2.0.0",
            stderr: "",
            exitCode: 0,
        });
        const result = await biomeRunner.isAvailable(runner);
        expect(result).toBe(true);
    });

    test("returns false when biome --version exits non-zero", async () => {
        const runner = new FakeCommandRunner();
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

        expect(runner.calls[0]).toContain(LOCAL_BIOME);
        expect(issues).toHaveLength(3);
    });
});
