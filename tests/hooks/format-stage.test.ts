import { describe, expect, test } from "bun:test";
import { Glob } from "bun";
import { FORMATTERS, getStagedFiles } from "@/hooks/format-stage";

describe("FORMATTERS", () => {
    test("has an entry for Python files", () => {
        const hasPy = FORMATTERS.some((f) => new Glob(f.glob).match("foo.py"));
        expect(hasPy).toBe(true);
    });

    test("has an entry for TypeScript files", () => {
        const hasTs = FORMATTERS.some((f) => new Glob(f.glob).match("foo.ts"));
        expect(hasTs).toBe(true);
    });

    test("has an entry for Rust files", () => {
        const hasRs = FORMATTERS.some((f) => new Glob(f.glob).match("foo.rs"));
        expect(hasRs).toBe(true);
    });

    test("has an entry for Go files", () => {
        const hasGo = FORMATTERS.some((f) => new Glob(f.glob).match("foo.go"));
        expect(hasGo).toBe(true);
    });

    test("has an entry for Lua files", () => {
        const hasLua = FORMATTERS.some((f) => new Glob(f.glob).match("foo.lua"));
        expect(hasLua).toBe(true);
    });

    test("has an entry for C files", () => {
        const hasC = FORMATTERS.some((f) => new Glob(f.glob).match("foo.c"));
        expect(hasC).toBe(true);
    });

    test("has an entry for C++ files", () => {
        const hasCpp = FORMATTERS.some((f) => new Glob(f.glob).match("foo.cpp"));
        expect(hasCpp).toBe(true);
    });

    test("each formatter has a non-empty glob", () => {
        for (const formatter of FORMATTERS) {
            expect(formatter.glob.length).toBeGreaterThan(0);
        }
    });

    test("each formatter cmd returns an array with at least one element", () => {
        for (const formatter of FORMATTERS) {
            const result = formatter.cmd(["test.ts"]);
            expect(result.length).toBeGreaterThan(0);
        }
    });
});

describe("getStagedFiles", () => {
    test("returns an array (does not throw when git is unavailable)", () => {
        // getStagedFiles calls execSync("git diff --cached --name-only")
        // In a test environment without a git index, it returns [] gracefully.
        const result = getStagedFiles();
        expect(Array.isArray(result)).toBe(true);
    });

    test("filters out empty strings from git output", () => {
        // If git returns empty output, result should be empty array not [""]
        const result = getStagedFiles();
        for (const file of result) {
            expect(file.length).toBeGreaterThan(0);
        }
    });
});

describe("tryRun error handling", () => {
    test("FORMATTERS cmd entries return non-empty arrays", () => {
        // Verify each formatter produces a non-empty command array that tryRun can use
        for (const formatter of FORMATTERS) {
            const cmd = formatter.cmd(["test-file.py"]);
            expect(cmd.length).toBeGreaterThan(0);
            expect(cmd[0]).toBeTruthy(); // first element (the binary name) must be defined
        }
    });
});
