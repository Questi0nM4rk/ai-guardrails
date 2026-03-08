import { describe, expect, test } from "bun:test";
import { generateLefthookConfig, lefthookGenerator } from "@/generators/lefthook";
import type { LanguagePlugin } from "@/languages/types";
import type { ResolvedConfig } from "@/config/schema";

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

function makePlugin(id: string): LanguagePlugin {
  return {
    id,
    name: id,
    detect: async () => true,
    runners: () => [],
  };
}

describe("lefthookGenerator", () => {
  test("id is lefthook", () => {
    expect(lefthookGenerator.id).toBe("lefthook");
  });

  test("configFile is lefthook.yml", () => {
    expect(lefthookGenerator.configFile).toBe("lefthook.yml");
  });

  test("output contains pre-commit section", () => {
    const output = lefthookGenerator.generate(makeConfig());
    expect(output).toContain("pre-commit:");
  });

  test("output contains commit-msg section", () => {
    const output = lefthookGenerator.generate(makeConfig());
    expect(output).toContain("commit-msg:");
  });

  test("output contains gitleaks", () => {
    const output = lefthookGenerator.generate(makeConfig());
    expect(output).toContain("gitleaks");
  });

  test("output contains codespell", () => {
    const output = lefthookGenerator.generate(makeConfig());
    expect(output).toContain("codespell");
  });
});

describe("generateLefthookConfig", () => {
  test("includes python section when python plugin active", () => {
    const plugins = [makePlugin("python")];
    const output = generateLefthookConfig(makeConfig(), plugins);
    expect(output).toContain("ruff");
  });

  test("includes typescript section when typescript plugin active", () => {
    const plugins = [makePlugin("typescript")];
    const output = generateLefthookConfig(makeConfig(), plugins);
    expect(output).toContain("biome");
  });

  test("output matches snapshot for python + typescript", () => {
    const plugins = [makePlugin("python"), makePlugin("typescript")];
    const output = generateLefthookConfig(makeConfig(), plugins);
    expect(output).toMatchSnapshot();
  });

  test("output matches snapshot for empty plugins", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toMatchSnapshot();
  });
});
