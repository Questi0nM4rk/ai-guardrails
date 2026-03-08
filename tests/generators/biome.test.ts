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

    test("configFile is biome.jsonc", () => {
        expect(biomeGenerator.configFile).toBe("biome.jsonc");
    });

    test("output matches snapshot", () => {
        const output = biomeGenerator.generate(makeConfig());
        expect(output).toMatchSnapshot();
    });

    test("output starts with JSONC hash header", () => {
        const output = biomeGenerator.generate(makeConfig());
        expect(output).toMatch(/^\/\/ ai-guardrails:sha256=[0-9a-f]{64}\n/);
    });

    test("output contains lineWidth from config", () => {
        const output = biomeGenerator.generate(
            makeConfig({ values: { line_length: 120, indent_width: 2 } })
        );
        expect(output).toContain('"lineWidth": 120');
    });

    test("output has schema reference", () => {
        const output = biomeGenerator.generate(makeConfig());
        expect(output).toContain("biomejs.dev/schemas");
    });

    test("noExplicitAny is error", () => {
        const output = biomeGenerator.generate(makeConfig());
        expect(output).toContain('"noExplicitAny": "error"');
    });
});
