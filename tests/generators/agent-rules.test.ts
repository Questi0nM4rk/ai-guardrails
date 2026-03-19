import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { agentRulesGenerator, buildAgentRules } from "@/generators/agent-rules";

function makeConfig() {
  return buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse({})
  );
}

describe("agentRulesGenerator", () => {
  test("has correct id", () => {
    expect(agentRulesGenerator.id).toBe("agent-rules");
  });

  test("has correct configFile", () => {
    expect(agentRulesGenerator.configFile).toBe(".ai-guardrails/agent-rules/base.md");
  });

  test("generate returns non-empty string", () => {
    const output = agentRulesGenerator.generate(makeConfig());
    expect(output.length).toBeGreaterThan(0);
  });

  test("generate output contains core principles heading", () => {
    const output = agentRulesGenerator.generate(makeConfig());
    expect(output).toContain("## Core Principles");
  });

  test("generate output contains git workflow section", () => {
    const output = agentRulesGenerator.generate(makeConfig());
    expect(output).toContain("## Git Workflow");
  });

  test("generate output contains security section", () => {
    const output = agentRulesGenerator.generate(makeConfig());
    expect(output).toContain("## Security");
  });

  test("generate output matches snapshot", () => {
    const output = agentRulesGenerator.generate(makeConfig());
    expect(output).toMatchSnapshot();
  });
});

describe("buildAgentRules", () => {
  test("claude variant contains Claude Code specific section", () => {
    const output = buildAgentRules("claude");
    expect(output).toContain("## Claude Code Specific");
  });

  test("cursor variant contains Cursor specific section", () => {
    const output = buildAgentRules("cursor");
    expect(output).toContain("## Cursor Specific");
  });

  test("windsurf variant contains Windsurf specific section", () => {
    const output = buildAgentRules("windsurf");
    expect(output).toContain("## Windsurf Specific");
  });

  test("copilot variant contains GitHub Copilot specific section", () => {
    const output = buildAgentRules("copilot");
    expect(output).toContain("## GitHub Copilot Specific");
  });

  test("cline variant contains Cline specific section", () => {
    const output = buildAgentRules("cline");
    expect(output).toContain("## Cline Specific");
  });

  test("aider variant contains Aider specific section", () => {
    const output = buildAgentRules("aider");
    expect(output).toContain("## Aider Specific");
  });

  test("all variants contain base rules", () => {
    for (const tool of [
      "claude",
      "cursor",
      "windsurf",
      "copilot",
      "cline",
      "aider",
    ] as const) {
      const output = buildAgentRules(tool);
      expect(output).toContain("## Core Principles");
    }
  });

  test("buildAgentRules claude matches snapshot", () => {
    expect(buildAgentRules("claude")).toMatchSnapshot();
  });

  test("buildAgentRules cursor matches snapshot", () => {
    expect(buildAgentRules("cursor")).toMatchSnapshot();
  });
});
