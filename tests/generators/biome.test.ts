import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { biomeGenerator } from "@/generators/biome";

function makeConfig(profile?: "strict" | "standard" | "minimal") {
  return buildResolvedConfig(
    MachineConfigSchema.parse({ profile: profile ?? "standard" }),
    ProjectConfigSchema.parse({})
  );
}

function parseJsonBody(output: string): unknown {
  const jsonBody = output
    .split("\n")
    .filter((line) => !line.startsWith("//"))
    .join("\n")
    .trim();
  return JSON.parse(jsonBody);
}

describe("biomeGenerator", () => {
  test("has correct id", () => {
    expect(biomeGenerator.id).toBe("biome");
  });

  test("has correct configFile", () => {
    expect(biomeGenerator.configFile).toBe("biome.jsonc");
  });

  test("is scoped to typescript language", () => {
    expect(biomeGenerator.languages).toEqual(["typescript"]);
  });

  test("strict profile has recommended true with explicit rule overrides", () => {
    const output = biomeGenerator.generate(makeConfig("strict"));
    const parsed = parseJsonBody(output) as {
      linter: {
        rules: { recommended: boolean; style?: unknown; suspicious?: unknown };
      };
    };
    expect(parsed.linter.rules.recommended).toBe(true);
    expect(parsed.linter.rules.style).toBeDefined();
    expect(parsed.linter.rules.suspicious).toBeDefined();
  });

  test("standard profile has recommended true with no category overrides", () => {
    const output = biomeGenerator.generate(makeConfig("standard"));
    const parsed = parseJsonBody(output) as {
      linter: {
        rules: {
          recommended: boolean;
          style?: unknown;
          suspicious?: unknown;
          correctness?: unknown;
        };
      };
    };
    expect(parsed.linter.rules.recommended).toBe(true);
    expect(parsed.linter.rules.style).toBeUndefined();
    expect(parsed.linter.rules.suspicious).toBeUndefined();
    expect(parsed.linter.rules.correctness).toBeUndefined();
  });

  test("minimal profile has recommended false with only critical rules", () => {
    const output = biomeGenerator.generate(makeConfig("minimal"));
    const parsed = parseJsonBody(output) as {
      linter: {
        rules: {
          recommended: boolean;
          correctness?: Record<string, string>;
          suspicious?: Record<string, string>;
          style?: unknown;
        };
      };
    };
    expect(parsed.linter.rules.recommended).toBe(false);
    expect(parsed.linter.rules.correctness).toBeDefined();
    expect(parsed.linter.rules.suspicious?.noExplicitAny).toBe("error");
    expect(parsed.linter.rules.style).toBeUndefined();
  });

  test("profiles produce different linter.rules sections", () => {
    const strict = biomeGenerator.generate(makeConfig("strict"));
    const standard = biomeGenerator.generate(makeConfig("standard"));
    const minimal = biomeGenerator.generate(makeConfig("minimal"));
    expect(strict).not.toBe(standard);
    expect(standard).not.toBe(minimal);
    expect(strict).not.toBe(minimal);
  });

  test("generate output contains valid JSON body for all profiles", () => {
    for (const profile of ["strict", "standard", "minimal"] as const) {
      const output = biomeGenerator.generate(makeConfig(profile));
      expect(() => parseJsonBody(output)).not.toThrow();
    }
  });

  test("strict output matches snapshot", () => {
    expect(biomeGenerator.generate(makeConfig("strict"))).toMatchSnapshot();
  });

  test("standard output matches snapshot", () => {
    expect(biomeGenerator.generate(makeConfig("standard"))).toMatchSnapshot();
  });

  test("minimal output matches snapshot", () => {
    expect(biomeGenerator.generate(makeConfig("minimal"))).toMatchSnapshot();
  });
});
