import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { claudeSettingsGenerator } from "@/generators/claude-settings";

function makeConfig() {
  return buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse({})
  );
}

interface ParsedSettings {
  permissions?: { deny?: unknown };
  hooks?: {
    PreToolUse?: Array<{
      matcher: string;
      hooks: Array<{ command: string; timeout: number }>;
    }>;
    PostToolUse?: Array<{
      matcher: string;
      hooks: Array<{ command: string; timeout: number }>;
    }>;
  };
}

function parse(output: string): ParsedSettings {
  return JSON.parse(output) as ParsedSettings;
}

describe("claudeSettingsGenerator", () => {
  test("has correct id", () => {
    expect(claudeSettingsGenerator.id).toBe("claude-settings");
  });

  test("has correct configFile", () => {
    expect(claudeSettingsGenerator.configFile).toBe(".claude/settings.json");
  });

  test("generate returns non-empty string", () => {
    const output = claudeSettingsGenerator.generate(makeConfig());
    expect(output.length).toBeGreaterThan(0);
  });

  test("generate output is valid JSON", () => {
    const output = claudeSettingsGenerator.generate(makeConfig());
    expect(() => JSON.parse(output)).not.toThrow();
  });

  test("generate output does not duplicate hook rules in permissions.deny (BUG-009)", () => {
    const parsed = parse(claudeSettingsGenerator.generate(makeConfig())) as Record<
      string,
      unknown
    >;
    expect(parsed.permissions).toBeUndefined();
  });

  test("generate output contains exactly one PreToolUse and one PostToolUse hook", () => {
    const parsed = parse(claudeSettingsGenerator.generate(makeConfig()));
    expect(parsed.hooks?.PreToolUse).toHaveLength(1);
    expect(parsed.hooks?.PostToolUse).toHaveLength(1);
  });

  test("PreToolUse covers Bash + Edit + Write + NotebookEdit + Read", () => {
    const parsed = parse(claudeSettingsGenerator.generate(makeConfig()));
    expect(parsed.hooks?.PreToolUse?.[0]?.matcher).toBe(
      "Bash|Edit|Write|NotebookEdit|Read"
    );
  });

  test("PostToolUse covers Edit|Write|NotebookEdit", () => {
    const parsed = parse(claudeSettingsGenerator.generate(makeConfig()));
    expect(parsed.hooks?.PostToolUse?.[0]?.matcher).toBe("Edit|Write|NotebookEdit");
  });

  test("hook command points at ai-guardrails-hk-cc-tools", () => {
    const parsed = parse(claudeSettingsGenerator.generate(makeConfig()));
    expect(parsed.hooks?.PreToolUse?.[0]?.hooks[0]?.command).toBe(
      "ai-guardrails-hk-cc-tools"
    );
    expect(parsed.hooks?.PostToolUse?.[0]?.hooks[0]?.command).toBe(
      "ai-guardrails-hk-cc-tools"
    );
  });

  test("hook timeout is 60s (under CC's default Bash tool budget)", () => {
    const parsed = parse(claudeSettingsGenerator.generate(makeConfig()));
    expect(parsed.hooks?.PreToolUse?.[0]?.hooks[0]?.timeout).toBe(60);
    expect(parsed.hooks?.PostToolUse?.[0]?.hooks[0]?.timeout).toBe(60);
  });

  test("hook command does not use shell guards (Iron Law 4 covers infra failure)", () => {
    const output = claudeSettingsGenerator.generate(makeConfig());
    expect(output).not.toContain("command -v");
    expect(output).not.toContain("[ ! -f");
    expect(output).not.toContain("./dist/");
  });

  test("generate output matches snapshot", () => {
    const output = claudeSettingsGenerator.generate(makeConfig());
    expect(output).toMatchSnapshot();
  });
});
