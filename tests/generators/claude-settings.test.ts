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

  test("generate output contains permissions.deny array", () => {
    const output = claudeSettingsGenerator.generate(makeConfig());
    const parsed = JSON.parse(output) as { permissions?: { deny?: unknown } };
    expect(Array.isArray(parsed.permissions?.deny)).toBe(true);
  });

  test("generate output contains PreToolUse hooks", () => {
    const output = claudeSettingsGenerator.generate(makeConfig());
    const parsed = JSON.parse(output) as {
      hooks?: { PreToolUse?: unknown[] };
    };
    expect(Array.isArray(parsed.hooks?.PreToolUse)).toBe(true);
    const hooks = parsed.hooks?.PreToolUse ?? [];
    expect(hooks.length).toBeGreaterThan(0);
  });

  test("generate output has Bash PreToolUse hook", () => {
    const output = claudeSettingsGenerator.generate(makeConfig());
    const parsed = JSON.parse(output) as {
      hooks?: { PreToolUse?: Array<{ matcher: string }> };
    };
    const hooks = parsed.hooks?.PreToolUse ?? [];
    const bashHook = hooks.find((h) => h.matcher === "Bash");
    expect(bashHook).toBeDefined();
  });

  test("generate output has Edit|Write|NotebookEdit PreToolUse hook", () => {
    const output = claudeSettingsGenerator.generate(makeConfig());
    const parsed = JSON.parse(output) as {
      hooks?: { PreToolUse?: Array<{ matcher: string }> };
    };
    const hooks = parsed.hooks?.PreToolUse ?? [];
    const editHook = hooks.find((h) => h.matcher === "Edit|Write|NotebookEdit");
    expect(editHook).toBeDefined();
  });

  test("hook commands use command -v guard not file-existence guard", () => {
    const output = claudeSettingsGenerator.generate(makeConfig());
    expect(output).toContain("command -v ai-guardrails");
    expect(output).not.toContain("[ ! -f");
  });

  test("hook commands do not reference ./dist/", () => {
    const output = claudeSettingsGenerator.generate(makeConfig());
    expect(output).not.toContain("./dist/");
  });

  test("generate output matches snapshot", () => {
    const output = claudeSettingsGenerator.generate(makeConfig());
    expect(output).toMatchSnapshot();
  });
});
