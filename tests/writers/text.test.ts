import { describe, expect, test } from "bun:test";
import type { LintIssue } from "@/models/lint-issue";
import { formatIssue, formatIssues } from "@/writers/text";

function makeIssue(overrides: Partial<LintIssue> = {}): LintIssue {
    return {
        rule: "E501",
        linter: "ruff",
        file: "/project/foo.py",
        line: 10,
        col: 1,
        message: "Line too long",
        severity: "error",
        fingerprint: "abc123",
        ...overrides,
    };
}

describe("formatIssues", () => {
    test("returns empty string for no issues", () => {
        expect(formatIssues([])).toBe("");
    });

    test("includes file, line, col in output", () => {
        const issue = makeIssue({ file: "/project/foo.py", line: 42, col: 5 });
        const output = formatIssues([issue]);
        expect(output).toContain("/project/foo.py:42:5");
    });

    test("includes rule in output", () => {
        const issue = makeIssue({ linter: "ruff", rule: "ruff/E501" });
        const output = formatIssues([issue]);
        expect(output).toContain("ruff/E501");
    });

    test("includes message in output", () => {
        const issue = makeIssue({ message: "Line too long (120 > 88)" });
        const output = formatIssues([issue]);
        expect(output).toContain("Line too long (120 > 88)");
    });

    test("includes severity in output", () => {
        const issue = makeIssue({ severity: "warning" });
        const output = formatIssues([issue]);
        expect(output).toContain("WARNING");
    });

    test("shows issue count summary", () => {
        const issues = [makeIssue(), makeIssue({ rule: "F401" })];
        const output = formatIssues(issues);
        expect(output).toContain("2 issue(s)");
    });

    test("formats multiple issues as separate lines", () => {
        const issues = [
            makeIssue({ file: "/a.py", line: 1 }),
            makeIssue({ file: "/b.py", line: 2 }),
        ];
        const output = formatIssues(issues);
        expect(output).toContain("/a.py");
        expect(output).toContain("/b.py");
    });
});

describe("formatIssue", () => {
    test("formats a single issue", () => {
        const issue = makeIssue({
            file: "/foo.py",
            line: 5,
            col: 3,
            rule: "ruff/E501",
            linter: "ruff",
        });
        const output = formatIssue(issue);
        expect(output).toContain("/foo.py:5:3");
        expect(output).toContain("ruff/E501");
    });
});
