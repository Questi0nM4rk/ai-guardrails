import { describe, expect, test } from "bun:test";
import { ruffGenerator } from "@/generators/ruff";
import { verifyHash } from "@/utils/hash";
import type { ResolvedConfig } from "@/config/schema";

function makeConfig(overrides?: Partial<ResolvedConfig>): ResolvedConfig {
  return {
    profile: "standard",
    ignore: [],
    allow: [],
    values: { line_length: 88, indent_width: 4 },
    ignoredRules: new Set(),
    isAllowed: () => false,
    ...overrides,
  };
}

describe("ruffGenerator", () => {
  test("id is ruff", () => {
    expect(ruffGenerator.id).toBe("ruff");
  });

  test("configFile is ruff.toml", () => {
    expect(ruffGenerator.configFile).toBe("ruff.toml");
  });

  test("output matches snapshot", () => {
    const output = ruffGenerator.generate(makeConfig());
    expect(output).toMatchSnapshot();
  });

  test("output has valid hash header", () => {
    const output = ruffGenerator.generate(makeConfig());
    expect(verifyHash(output)).toBe(true);
  });

  test("output contains line-length from config", () => {
    const output = ruffGenerator.generate(
      makeConfig({ values: { line_length: 120, indent_width: 4 } }),
    );
    expect(output).toContain("line-length = 120");
  });

  test("output contains indent-width from config", () => {
    const output = ruffGenerator.generate(
      makeConfig({ values: { line_length: 88, indent_width: 2 } }),
    );
    expect(output).toContain("indent-width = 2");
  });

  test("output contains select all", () => {
    const output = ruffGenerator.generate(makeConfig());
    expect(output).toContain('select = ["ALL"]');
  });
});
