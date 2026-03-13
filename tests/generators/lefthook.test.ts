import { describe, expect, test } from "bun:test";
import type { ResolvedConfig } from "@/config/schema";
import { generateLefthookConfig, lefthookGenerator } from "@/generators/lefthook";
import type { LanguagePlugin } from "@/languages/types";

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

  test("generate() throws — use generateLefthookConfig instead", () => {
    expect(() => lefthookGenerator.generate(makeConfig())).toThrow(
      "lefthookGenerator.generate() must not be called directly"
    );
  });

  test("output contains pre-commit section", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain("pre-commit:");
  });

  test("output contains commit-msg section", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain("commit-msg:");
  });

  test("output contains gitleaks", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain("gitleaks");
  });

  test("output contains codespell", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain("codespell");
  });
});

describe("no-commits-to-main hook", () => {
  test("blocks commits to main branch", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain('"main"');
  });

  test("also blocks commits to master branch", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain('"master"');
  });

  test("check script uses OR condition for main and master", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    // Should contain: if [ "$branch" = "main" ] || [ "$branch" = "master" ]
    expect(output).toMatch(
      /"\$branch"\s*=\s*"main"\s*\]\s*\|\|\s*\[.*"\$branch"\s*=\s*"master"/
    );
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
