import { describe, expect, test } from "bun:test";
import type { ResolvedConfig } from "@/config/schema";
import { ruffGenerator } from "@/generators/ruff";
import { HASH_PREFIX, makeHashHeader } from "@/utils/hash";

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
    const newlineIdx = output.indexOf("\n");
    const headerLine = output.slice(0, newlineIdx);
    const body = output.slice(newlineIdx + 1);
    expect(headerLine).toStartWith(HASH_PREFIX);
    expect(headerLine).toBe(makeHashHeader(body));
  });

  test("output contains line-length from config", () => {
    const output = ruffGenerator.generate(
      makeConfig({ values: { line_length: 120, indent_width: 4 } })
    );
    expect(output).toContain("line-length = 120");
  });

  test("output contains indent-width from config", () => {
    const output = ruffGenerator.generate(
      makeConfig({ values: { line_length: 88, indent_width: 2 } })
    );
    expect(output).toContain("indent-width = 2");
  });

  test("output contains select all", () => {
    const output = ruffGenerator.generate(makeConfig());
    expect(output).toContain('select = ["ALL"]');
  });
});
