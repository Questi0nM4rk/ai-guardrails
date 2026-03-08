import { describe, expect, test } from "bun:test";
import { parseAllowComments } from "@/hooks/allow-comment";

describe("parseAllowComments", () => {
    test("parses Python/shell style # comment", () => {
        const lines = [
            'x = 1  # ai-guardrails-allow: ruff/E501 "URL cannot be shortened"',
        ];
        const allows = parseAllowComments(lines);
        expect(allows).toHaveLength(1);
        expect(allows[0]?.rule).toBe("ruff/E501");
        expect(allows[0]?.reason).toBe("URL cannot be shortened");
        expect(allows[0]?.line).toBe(1);
    });

    test("parses TypeScript/JS // comment", () => {
        const lines = [
            'const x = 1; // ai-guardrails-allow: biome/noExplicitAny "external API type"',
        ];
        const allows = parseAllowComments(lines);
        expect(allows).toHaveLength(1);
        expect(allows[0]?.rule).toBe("biome/noExplicitAny");
        expect(allows[0]?.reason).toBe("external API type");
        expect(allows[0]?.line).toBe(1);
    });

    test("parses Lua -- comment", () => {
        const lines = [
            'local x = val -- ai-guardrails-allow: luacheck/W311 "loop variable shadowing"',
        ];
        const allows = parseAllowComments(lines);
        expect(allows).toHaveLength(1);
        expect(allows[0]?.rule).toBe("luacheck/W311");
        expect(allows[0]?.reason).toBe("loop variable shadowing");
        expect(allows[0]?.line).toBe(1);
    });

    test("returns empty array for lines with no allow comments", () => {
        const lines = ["x = 1", "y = 2", "# just a regular comment"];
        const allows = parseAllowComments(lines);
        expect(allows).toHaveLength(0);
    });

    test("returns empty array for empty input", () => {
        expect(parseAllowComments([])).toHaveLength(0);
    });

    test("handles multiple allow comments in the same file", () => {
        const lines = [
            "x = 1",
            '  # ai-guardrails-allow: ruff/E501 "long URL"',
            "y = 2",
            '  // ai-guardrails-allow: biome/noAny "external"',
        ];
        const allows = parseAllowComments(lines);
        expect(allows).toHaveLength(2);
        expect(allows[0]?.rule).toBe("ruff/E501");
        expect(allows[0]?.line).toBe(2);
        expect(allows[1]?.rule).toBe("biome/noAny");
        expect(allows[1]?.line).toBe(4);
    });

    test("extracts rule and reason correctly", () => {
        const lines = [
            'code  # ai-guardrails-allow: shellcheck/SC2086 "word splitting intentional"',
        ];
        const allows = parseAllowComments(lines);
        expect(allows[0]?.rule).toBe("shellcheck/SC2086");
        expect(allows[0]?.reason).toBe("word splitting intentional");
    });

    test("returns correct 1-indexed line numbers", () => {
        const lines = [
            "line 1",
            "line 2",
            '# ai-guardrails-allow: ruff/E501 "test"',
            "line 4",
        ];
        const allows = parseAllowComments(lines);
        expect(allows[0]?.line).toBe(3);
    });

    test("skips allow comment without a quoted reason", () => {
        const lines = ["# ai-guardrails-allow: ruff/E501"];
        const allows = parseAllowComments(lines);
        expect(allows).toHaveLength(0);
    });

    test("handles allow comment as standalone comment line", () => {
        const lines = ['# ai-guardrails-allow: ruff/T201 "CLI tool"'];
        const allows = parseAllowComments(lines);
        expect(allows).toHaveLength(1);
        expect(allows[0]?.rule).toBe("ruff/T201");
    });

    test("trims whitespace around rule and reason", () => {
        const lines = ['x = 1  #  ai-guardrails-allow:  ruff/E501  "reason here"'];
        const allows = parseAllowComments(lines);
        expect(allows).toHaveLength(1);
        expect(allows[0]?.rule).toBe("ruff/E501");
        expect(allows[0]?.reason).toBe("reason here");
    });
});
