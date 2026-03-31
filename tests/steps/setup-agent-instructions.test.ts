import { describe, expect, test } from "bun:test";
import type { FileManager } from "@/infra/file-manager";
import { setupAgentInstructionsStep } from "@/steps/setup-agent-instructions";
import { FakeFileManager } from "../fakes/fake-file-manager";

describe("setupAgentInstructionsStep", () => {
  test("always generates AGENTS.md even when no AI tool config detected", async () => {
    const fm = new FakeFileManager();

    const result = await setupAgentInstructionsStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("AGENTS.md");
    const writtenPaths = fm.written.map(([p]) => p);
    expect(writtenPaths.some((p) => p.endsWith("AGENTS.md"))).toBe(true);
  });

  test("AGENTS.md content contains base rules", async () => {
    const fm = new FakeFileManager();

    await setupAgentInstructionsStep("/project", fm);

    const agentsEntry = fm.written.find(([p]) => p.endsWith("AGENTS.md"));
    expect(agentsEntry).toBeDefined();
    if (!agentsEntry) return;
    const [, content] = agentsEntry;
    expect(content).toContain("AI Agent Rules");
    expect(content).toContain("## Core Principles");
  });

  test("AGENTS.md does not contain tool-specific sections", async () => {
    const fm = new FakeFileManager();

    await setupAgentInstructionsStep("/project", fm);

    const agentsEntry = fm.written.find(([p]) => p.endsWith("AGENTS.md"));
    expect(agentsEntry).toBeDefined();
    if (!agentsEntry) return;
    const [, content] = agentsEntry;
    expect(content).not.toContain("## Claude Code Specific");
    expect(content).not.toContain("## Cursor Specific");
  });

  test("writes agent rules file for cursor when .cursorrules exists", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.cursorrules", "# existing cursor rules");

    const result = await setupAgentInstructionsStep("/project", fm);

    expect(result.status).toBe("ok");
    const writtenPaths = fm.written.map(([p]) => p);
    expect(writtenPaths.some((p) => p.includes("cursorrules"))).toBe(true);
  });

  test("returns ok and writes AGENTS.md when only claude tool is detected", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.claude/settings.json", "{}");

    const result = await setupAgentInstructionsStep("/project", fm);

    expect(result.status).toBe("ok");
    const writtenPaths = fm.written.map(([p]) => p);
    expect(writtenPaths.some((p) => p.endsWith("AGENTS.md"))).toBe(true);
  });

  test("writes agent rules for windsurf when .windsurfrules exists", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.windsurfrules", "# windsurf rules");

    const result = await setupAgentInstructionsStep("/project", fm);

    expect(result.status).toBe("ok");
    const writtenPaths = fm.written.map(([p]) => p);
    expect(writtenPaths.some((p) => p.includes("windsurfrules"))).toBe(true);
  });

  test("writes multiple agent rule files when multiple tools detected", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.cursorrules", "");
    fm.seed("/project/.windsurfrules", "");

    const result = await setupAgentInstructionsStep("/project", fm);

    expect(result.status).toBe("ok");
    // cursor rules + windsurf rules + AGENTS.md + CLAUDE.md = at least 3
    expect(fm.written.length).toBeGreaterThanOrEqual(3);
  });

  test("written cursor file content includes base rules text", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.cursorrules", "");

    await setupAgentInstructionsStep("/project", fm);

    const cursorEntry = fm.written.find(([p]) => p.includes("cursorrules"));
    expect(cursorEntry).toBeDefined();
    if (!cursorEntry) return;
    const [, content] = cursorEntry;
    expect(content).toContain("AI Agent Rules");
  });

  test("creates CLAUDE.md with guardrails section when it does not exist", async () => {
    const fm = new FakeFileManager();

    await setupAgentInstructionsStep("/project", fm);

    const claudeEntry = fm.written.find(([p]) => p.endsWith("CLAUDE.md"));
    expect(claudeEntry).toBeDefined();
    if (!claudeEntry) return;
    const [, content] = claudeEntry;
    expect(content).toContain("## AI Guardrails");
  });

  test("appends guardrails section to existing CLAUDE.md", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/CLAUDE.md", "# My Project\n\nExisting content.\n");

    await setupAgentInstructionsStep("/project", fm);

    const appendedEntry = fm.appended.find(([p]) => p.endsWith("CLAUDE.md"));
    expect(appendedEntry).toBeDefined();
    if (!appendedEntry) return;
    const [, appended] = appendedEntry;
    expect(appended).toContain("## AI Guardrails");
  });

  test("does not duplicate guardrails section when already present in CLAUDE.md", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      "/project/CLAUDE.md",
      "# My Project\n\n## AI Guardrails - Code Standards\n\nAlready here.\n"
    );

    await setupAgentInstructionsStep("/project", fm);

    // appendText must NOT have been called for CLAUDE.md
    const appendedEntry = fm.appended.find(([p]) => p.endsWith("CLAUDE.md"));
    expect(appendedEntry).toBeUndefined();
  });

  test("returns error on writeText failure", async () => {
    const inner = new FakeFileManager();
    inner.seed("/project/.cursorrules", "");

    const throwingFm: FileManager = {
      readText: (p) => inner.readText(p),
      writeText: async () => {
        throw new Error("write failed");
      },
      appendText: (p, c) => inner.appendText(p, c),
      exists: (p) => inner.exists(p),
      mkdir: (_p, _o) => Promise.resolve(),
      glob: (p, c, i) => inner.glob(p, c, i),
      isSymlink: (p) => inner.isSymlink(p),
      delete: (p) => inner.delete(p),
    };

    const result = await setupAgentInstructionsStep("/project", throwingFm);

    expect(result.status).toBe("error");
    expect(result.message).toContain("Agent instructions setup failed");
  });
});
