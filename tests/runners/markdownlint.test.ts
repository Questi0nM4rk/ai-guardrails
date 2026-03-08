import { describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { markdownlintRunner, parseMarkdownlintOutput } from "@/runners/markdownlint";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

const FIXTURE_PATH = resolve(import.meta.dir, "../fixtures/markdownlint-output.txt");
const PROJECT_DIR = "/project";

const FIXTURE_TEXT = await Bun.file(FIXTURE_PATH).text();

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

const MARKDOWNLINT_CMD = [
    "markdownlint-cli2",
    "**/*.md",
    "!node_modules/**",
    "!dist/**",
    "!.venv/**",
    "!venv/**",
    "!build/**",
    "--config",
    ".markdownlint.jsonc",
];

describe("parseMarkdownlintOutput", () => {
    test("returns LintIssue[] from fixture", () => {
        const issues = parseMarkdownlintOutput(FIXTURE_TEXT, PROJECT_DIR);
        expect(issues).toHaveLength(2);

        const first = issues[0];
        expect(first).toBeDefined();
        if (!first) return;
        expect(first.rule).toBe("markdownlint/MD013/line-length");
        expect(first.linter).toBe("markdownlint");
        expect(first.file).toBe("/project/docs/README.md");
        expect(first.line).toBe(3);
        expect(first.col).toBe(1);
        expect(first.message).toBe("Line length [Expected: 80; Actual: 120]");
        expect(first.severity).toBe("warning");
        expect(first.fingerprint).toHaveLength(64);
    });

    test("extracts MD rule code correctly", () => {
        const issues = parseMarkdownlintOutput(FIXTURE_TEXT, PROJECT_DIR);
        const second = issues[1];
        expect(second).toBeDefined();
        if (!second) return;
        expect(second.rule).toBe("markdownlint/MD041/first-line-heading");
    });

    test("returns [] for empty output", () => {
        const issues = parseMarkdownlintOutput("", PROJECT_DIR);
        expect(issues).toHaveLength(0);
    });

    test("returns [] for output with no matching lines", () => {
        const issues = parseMarkdownlintOutput("Checking...\nAll good.", PROJECT_DIR);
        expect(issues).toHaveLength(0);
    });

    test("resolves relative paths to absolute", () => {
        const issues = parseMarkdownlintOutput(FIXTURE_TEXT, "/my/project");
        const first = issues[0];
        expect(first).toBeDefined();
        if (!first) return;
        expect(first.file).toBe("/my/project/docs/README.md");
    });
});

describe("markdownlintRunner.run", () => {
    test("parses stdout regardless of non-zero exit code", async () => {
        const runner = new FakeCommandRunner();
        runner.register(MARKDOWNLINT_CMD, {
            stdout: FIXTURE_TEXT,
            stderr: "",
            exitCode: 1, // markdownlint-cli2 exits non-zero on issues
        });

        const issues = await markdownlintRunner.run({
            projectDir: PROJECT_DIR,
            config: makeConfig(),
            commandRunner: runner,
            fileManager: new FakeFileManager(),
        });

        expect(runner.calls[0]).toEqual(MARKDOWNLINT_CMD);
        expect(issues).toHaveLength(2);
    });

    test("returns [] for empty output", async () => {
        const runner = new FakeCommandRunner();
        runner.register(MARKDOWNLINT_CMD, {
            stdout: "",
            stderr: "",
            exitCode: 0,
        });

        const issues = await markdownlintRunner.run({
            projectDir: PROJECT_DIR,
            config: makeConfig(),
            commandRunner: runner,
            fileManager: new FakeFileManager(),
        });

        expect(issues).toHaveLength(0);
    });
});

describe("markdownlintRunner.generateConfig", () => {
    test("returns .markdownlint.jsonc string", () => {
        const output = markdownlintRunner.generateConfig(makeConfig());
        expect(output).not.toBeNull();
        expect(typeof output).toBe("string");
        expect(output).toContain("MD013");
        expect(output).toContain("MD033");
        expect(output).toContain("MD041");
    });
});

describe("markdownlintRunner.isAvailable", () => {
    test("returns true when markdownlint-cli2 --version exits 0", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["markdownlint-cli2", "--version"], {
            stdout: "markdownlint-cli2 v0.17.2",
            stderr: "",
            exitCode: 0,
        });
        const result = await markdownlintRunner.isAvailable(runner);
        expect(result).toBe(true);
    });

    test("returns false when markdownlint-cli2 --version exits non-zero", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["markdownlint-cli2", "--version"], {
            stdout: "",
            stderr: "not found",
            exitCode: 127,
        });
        const result = await markdownlintRunner.isAvailable(runner);
        expect(result).toBe(false);
    });
});
