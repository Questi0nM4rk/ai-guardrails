import { describe, expect, test } from "bun:test";
import type { ResolvedConfig } from "@/config/schema";
import { staticcheckGenerator } from "@/generators/staticcheck";

function makeConfig(overrides: Partial<ResolvedConfig> = {}): ResolvedConfig {
  return {
    profile: "standard",
    ignore: [],
    allow: [],
    values: { line_length: 88, indent_width: 2 },
    ignoredRules: new Set(),
    ignorePaths: [],
    noConsoleLevel: "warn",
    isAllowed: () => false,
    ...overrides,
  };
}

describe("staticcheckGenerator", () => {
  test("generates staticcheck.conf with all checks enabled", () => {
    const output = staticcheckGenerator.generate(makeConfig());
    expect(output).toContain("[checks]");
    expect(output).toContain('enabled = ["all"]');
  });

  test("includes hash header", () => {
    const output = staticcheckGenerator.generate(makeConfig());
    expect(output).toMatch(/^# ai-guardrails:sha256=/);
  });

  test("has configFile set to staticcheck.conf", () => {
    expect(staticcheckGenerator.configFile).toBe("staticcheck.conf");
  });

  test("has languages set to go", () => {
    expect(staticcheckGenerator.languages).toEqual(["go"]);
  });

  test("output matches snapshot", () => {
    const output = staticcheckGenerator.generate(makeConfig());
    expect(output).toMatchSnapshot();
  });
});
