import { describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { clangTidyRunner, parseClangTidyOutput } from "@/runners/clang-tidy";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

const FIXTURE_PATH = resolve(import.meta.dir, "../fixtures/clang-tidy-output.txt");
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

describe("parseClangTidyOutput", () => {
    test("returns LintIssue[] from fixture", () => {
        const issues = parseClangTidyOutput(FIXTURE_TEXT);
        // 2 warnings + 1 error = 3 issues; note lines are skipped
        expect(issues).toHaveLength(3);
    });

    test("skips note-level lines", () => {
        const text = [
            "/project/src/main.cpp:10:5: warning: use of old-style cast [modernize-use-auto]",
            "/project/include/util.h:22:3: note: expanded from macro 'ASSERT' [some-check]",
        ].join("\n");

        const issues = parseClangTidyOutput(text);
        expect(issues).toHaveLength(1);
        expect(issues[0]?.rule).toBe("clang-tidy/modernize-use-auto");
    });

    test("maps fields correctly", () => {
        const issues = parseClangTidyOutput(FIXTURE_TEXT);
        const first = issues[0];
        expect(first).toBeDefined();
        if (!first) return;
        expect(first.rule).toBe("clang-tidy/modernize-use-auto");
        expect(first.linter).toBe("clang-tidy");
        expect(first.file).toBe("/project/src/main.cpp");
        expect(first.line).toBe(10);
        expect(first.col).toBe(5);
        expect(first.message).toBe("use of old-style cast");
        expect(first.severity).toBe("warning");
        expect(first.fingerprint).toHaveLength(64);
    });

    test("maps error level to error severity", () => {
        const issues = parseClangTidyOutput(FIXTURE_TEXT);
        const errorIssue = issues.find(
            (i) => i.rule === "clang-tidy/cppcoreguidelines-avoid-assert"
        );
        expect(errorIssue).toBeDefined();
        if (!errorIssue) return;
        expect(errorIssue.severity).toBe("error");
    });

    test("returns [] for empty input", () => {
        const issues = parseClangTidyOutput("");
        expect(issues).toHaveLength(0);
    });
});

describe("clangTidyRunner.run", () => {
    test("returns [] when no C/C++ files found", async () => {
        const runner = new FakeCommandRunner();
        const fm = new FakeFileManager();
        // No files seeded — glob returns empty

        const issues = await clangTidyRunner.run({
            projectDir: PROJECT_DIR,
            config: makeConfig(),
            commandRunner: runner,
            fileManager: fm,
        });

        expect(issues).toHaveLength(0);
        expect(runner.calls).toHaveLength(0);
    });

    test("runs clang-tidy on found C/C++ files", async () => {
        const runner = new FakeCommandRunner();
        const fm = new FakeFileManager();
        fm.seed("src/main.cpp", "int main() {}");
        fm.seed("src/lib.cpp", "void foo() {}");

        runner.register(["clang-tidy", "--quiet", "src/main.cpp", "src/lib.cpp"], {
            stdout: "",
            stderr: FIXTURE_TEXT,
            exitCode: 1,
        });

        const issues = await clangTidyRunner.run({
            projectDir: PROJECT_DIR,
            config: makeConfig(),
            commandRunner: runner,
            fileManager: fm,
        });

        expect(runner.calls).toHaveLength(1);
        expect(issues).toHaveLength(3);
    });
});

describe("clangTidyRunner.run uses stderr for diagnostics", () => {
    test("parses diagnostics from stderr, not stdout", async () => {
        const runner = new FakeCommandRunner();
        const fm = new FakeFileManager();
        fm.seed("src/main.cpp", "int main() {}");

        // clang-tidy writes diagnostics to stderr; stdout is empty
        runner.register(["clang-tidy", "--quiet", "src/main.cpp"], {
            stdout: "",
            stderr: FIXTURE_TEXT,
            exitCode: 1,
        });

        const issues = await clangTidyRunner.run({
            projectDir: PROJECT_DIR,
            config: makeConfig(),
            commandRunner: runner,
            fileManager: fm,
        });

        expect(issues).toHaveLength(3);
    });

    test("returns [] when diagnostics are only in stdout (ignored)", async () => {
        const runner = new FakeCommandRunner();
        const fm = new FakeFileManager();
        fm.seed("src/main.cpp", "int main() {}");

        // clang-tidy writes to stderr; stdout output is not parsed
        runner.register(["clang-tidy", "--quiet", "src/main.cpp"], {
            stdout: FIXTURE_TEXT,
            stderr: "",
            exitCode: 1,
        });

        const issues = await clangTidyRunner.run({
            projectDir: PROJECT_DIR,
            config: makeConfig(),
            commandRunner: runner,
            fileManager: fm,
        });

        expect(issues).toHaveLength(0);
    });
});

describe("clangTidyRunner.isAvailable", () => {
    test("returns true when clang-tidy --version exits 0", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["clang-tidy", "--version"], {
            stdout: "LLVM version 17.0.0",
            stderr: "",
            exitCode: 0,
        });
        const result = await clangTidyRunner.isAvailable(runner);
        expect(result).toBe(true);
    });

    test("returns false when clang-tidy --version exits non-zero", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["clang-tidy", "--version"], {
            stdout: "",
            stderr: "command not found",
            exitCode: 127,
        });
        const result = await clangTidyRunner.isAvailable(runner);
        expect(result).toBe(false);
    });
});
