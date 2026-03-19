import { describe, expect, test } from "bun:test";
import type { FileManager } from "@/infra/file-manager";
import { setupAgentInstructionsStep } from "@/steps/setup-agent-instructions";
import { FakeFileManager } from "../fakes/fake-file-manager";

describe("setupAgentInstructionsStep", () => {
  test("skips and returns ok when no AI agent tool config detected", async () => {
    const fm = new FakeFileManager();
    // No AI tool config files seeded

    const result = await setupAgentInstructionsStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("skipped");
    expect(fm.written).toHaveLength(0);
  });

  test("writes agent rules file for cursor when .cursorrules exists", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.cursorrules", "# existing cursor rules");

    const result = await setupAgentInstructionsStep("/project", fm);

    expect(result.status).toBe("ok");
    // Cursor has a symlink target defined in AGENT_SYMLINKS
    const writtenPaths = fm.written.map(([p]) => p);
    expect(writtenPaths.some((p) => p.includes("cursorrules"))).toBe(true);
  });

  test("returns ok without writing when only claude tool is detected", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.claude/settings.json", "{}");

    const result = await setupAgentInstructionsStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(fm.written).toHaveLength(0);
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
    expect(fm.written.length).toBeGreaterThanOrEqual(2);
  });

  test("written file content includes base rules text", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.cursorrules", "");

    await setupAgentInstructionsStep("/project", fm);

    const cursorEntry = fm.written.find(([p]) => p.includes("cursorrules"));
    expect(cursorEntry).toBeDefined();
    if (!cursorEntry) return;
    const [, content] = cursorEntry;
    expect(content).toContain("AI Agent Rules");
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
