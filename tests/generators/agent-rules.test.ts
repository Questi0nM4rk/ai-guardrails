import { describe, expect, test } from "bun:test";
import {
  AGENT_SYMLINKS,
  agentRulesGenerator,
  buildAgentRules,
  detectAgentTools,
} from "@/generators/agent-rules";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";

describe("detectAgentTools", () => {
  test("detects claude from .claude directory", async () => {
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/.claude/settings.json`, "{}");
    const result = await detectAgentTools(PROJECT_DIR, fm);
    expect(result.claude).toBe(true);
  });

  test("detects cursor from .cursorrules", async () => {
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/.cursorrules`, "# rules");
    const result = await detectAgentTools(PROJECT_DIR, fm);
    expect(result.cursor).toBe(true);
  });

  test("detects cursor from .cursor/rules directory", async () => {
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/.cursor/rules/base.md`, "# rules");
    const result = await detectAgentTools(PROJECT_DIR, fm);
    expect(result.cursor).toBe(true);
  });

  test("detects windsurf from .windsurfrules", async () => {
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/.windsurfrules`, "# rules");
    const result = await detectAgentTools(PROJECT_DIR, fm);
    expect(result.windsurf).toBe(true);
  });

  test("detects copilot from .github/copilot-instructions.md", async () => {
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/.github/copilot-instructions.md`, "# instructions");
    const result = await detectAgentTools(PROJECT_DIR, fm);
    expect(result.copilot).toBe(true);
  });

  test("detects cline from .clinerules", async () => {
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/.clinerules`, "# rules");
    const result = await detectAgentTools(PROJECT_DIR, fm);
    expect(result.cline).toBe(true);
  });

  test("detects aider from .aider.conf.yml", async () => {
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/.aider.conf.yml`, "model: gpt-4");
    const result = await detectAgentTools(PROJECT_DIR, fm);
    expect(result.aider).toBe(true);
  });

  test("returns all false for empty project", async () => {
    const fm = new FakeFileManager();
    const result = await detectAgentTools(PROJECT_DIR, fm);
    expect(result.claude).toBe(false);
    expect(result.cursor).toBe(false);
    expect(result.windsurf).toBe(false);
    expect(result.copilot).toBe(false);
    expect(result.cline).toBe(false);
    expect(result.aider).toBe(false);
  });
});

describe("buildAgentRules", () => {
  test("claude rules contain Claude Code Specific section", () => {
    const rules = buildAgentRules("claude");
    expect(rules).toContain("Claude Code Specific");
  });

  test("cursor rules contain Cursor Specific section", () => {
    const rules = buildAgentRules("cursor");
    expect(rules).toContain("Cursor Specific");
  });

  test("all rules contain core principles section", () => {
    const tools = ["claude", "cursor", "windsurf", "copilot", "cline", "aider"] as const;
    for (const tool of tools) {
      const rules = buildAgentRules(tool);
      expect(rules).toContain("Core Principles");
    }
  });
});

describe("AGENT_SYMLINKS", () => {
  test("cursor maps to .cursorrules", () => {
    expect(AGENT_SYMLINKS.cursor).toBe(".cursorrules");
  });

  test("windsurf maps to .windsurfrules", () => {
    expect(AGENT_SYMLINKS.windsurf).toBe(".windsurfrules");
  });
});

describe("agentRulesGenerator", () => {
  test("id is agent-rules", () => {
    expect(agentRulesGenerator.id).toBe("agent-rules");
  });

  test("output contains base rules", () => {
    const config = {
      profile: "standard" as const,
      ignore: [],
      allow: [],
      values: { line_length: 88, indent_width: 4 },
      ignoredRules: new Set<string>(),
      isAllowed: () => false,
    };
    const output = agentRulesGenerator.generate(config);
    expect(output).toContain("Core Principles");
  });
});
