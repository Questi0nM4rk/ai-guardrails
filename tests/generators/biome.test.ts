import { describe, expect, test } from "bun:test";
import type { ResolvedConfig } from "@/config/schema";
import { biomeGenerator } from "@/generators/biome";

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

describe("biomeGenerator", () => {
    test("id is biome", () => {
        expect(biomeGenerator.id).toBe("biome");
    });

    test("configFile is biome.json", () => {
        expect(biomeGenerator.configFile).toBe("biome.json");
    });

    test("output matches snapshot", () => {
        const output = biomeGenerator.generate(makeConfig());
        expect(output).toMatchSnapshot();
    });

    test("output is valid JSON", () => {
        const output = biomeGenerator.generate(makeConfig());
        expect(() => JSON.parse(output)).not.toThrow();
    });

    test("output contains lineWidth from config", () => {
        const output = biomeGenerator.generate(
            makeConfig({ values: { line_length: 120, indent_width: 2 } })
        );
        const parsed = JSON.parse(output) as { formatter: { lineWidth: number } };
        expect(parsed.formatter.lineWidth).toBe(120);
    });

    test("output has schema reference", () => {
        const output = biomeGenerator.generate(makeConfig());
        expect(output).toContain("biomejs.dev/schemas");
    });

    test("noExplicitAny is error", () => {
        const output = biomeGenerator.generate(makeConfig());
        const parsed = JSON.parse(output) as {
            linter: { rules: { suspicious: { noExplicitAny: string } } };
        };
        expect(parsed.linter.rules.suspicious.noExplicitAny).toBe("error");
    });
});
