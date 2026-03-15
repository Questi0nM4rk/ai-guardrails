import { describe, expect, test } from "bun:test";
import type { ResolvedConfig } from "@/config/schema";
import { claudeSettingsGenerator } from "@/generators/claude-settings";

const mockConfig: ResolvedConfig = {
  profile: "standard",
  ignore: [],
  allow: [],
  values: { line_length: 88, indent_width: 2 },
  ignoredRules: new Set(),
  isAllowed: () => false,
};

describe("claudeSettingsGenerator", () => {
  test("id is claude-settings", () => {
    expect(claudeSettingsGenerator.id).toBe("claude-settings");
  });

  test("configFile is .claude/settings.json", () => {
    expect(claudeSettingsGenerator.configFile).toBe(".claude/settings.json");
  });

  test("generates valid JSON", () => {
    const output = claudeSettingsGenerator.generate(mockConfig);
    expect(() => JSON.parse(output)).not.toThrow();
  });

  test("output matches snapshot", () => {
    const output = claudeSettingsGenerator.generate(mockConfig);
    expect(output).toMatchSnapshot();
  });

  test("includes dangerous-cmd hook for Bash", () => {
    const output = claudeSettingsGenerator.generate(mockConfig);
    expect(output).toContain("dangerous-cmd");
    expect(output).toContain('"Bash"');
  });

  test("includes protect-configs hook for Edit|Write|NotebookEdit", () => {
    const output = claudeSettingsGenerator.generate(mockConfig);
    expect(output).toContain("protect-configs");
    expect(output).toContain("Edit|Write|NotebookEdit");
  });

  test("includes protect-reads hook for Read", () => {
    const output = claudeSettingsGenerator.generate(mockConfig);
    expect(output).toContain("protect-reads");
    expect(output).toContain('"Read"');
  });

  test("includes DANGEROUS_DENY_GLOBS in permissions.deny", () => {
    const output = claudeSettingsGenerator.generate(mockConfig);
    const parsed = JSON.parse(output) as { permissions?: { deny?: unknown[] } };
    expect(Array.isArray(parsed.permissions?.deny)).toBe(true);
    expect((parsed.permissions?.deny ?? []).length).toBeGreaterThan(0);
  });
});
