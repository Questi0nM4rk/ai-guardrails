import { describe, expect, test } from "bun:test";
import type { FileManager } from "@/infra/file-manager";
import { installHooksStep } from "@/steps/install-hooks";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

const CLAUDE_DIR = "/fake-home/.claude";
const SETTINGS_PATH = `${CLAUDE_DIR}/settings.json`;

function makeFailingFileManager(): FileManager {
  const inner = new FakeFileManager();
  return {
    readText: (p) => inner.readText(p),
    writeText: async () => {
      throw new Error("disk full");
    },
    appendText: (p, c) => inner.appendText(p, c),
    exists: (p) => inner.exists(p),
    mkdir: (p, o) => inner.mkdir(p, o),
    glob: (p, c, i) => inner.glob(p, c, i),
    isSymlink: (p) => inner.isSymlink(p),
    delete: (p) => inner.delete(p),
  };
}

describe("installHooksStep", () => {
  test("creates settings file if absent", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    const result = await installHooksStep(fm, cons, CLAUDE_DIR);

    expect(result.status).toBe("ok");
    expect(fm.written).toHaveLength(1);
    const [path] = fm.written[0] ?? ["", ""];
    expect(path).toBe(SETTINGS_PATH);
  });

  test("written file contains all three hook matchers", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    await installHooksStep(fm, cons, CLAUDE_DIR);

    const [, content] = fm.written[0] ?? ["", ""];
    const settings = JSON.parse(content) as Record<string, unknown>;
    const ptus = (settings.hooks as Record<string, unknown>).PreToolUse as Array<{
      matcher: string;
    }>;
    const matchers = ptus.map((e) => e.matcher);
    expect(matchers).toContain("Bash");
    expect(matchers).toContain("Edit|Write|NotebookEdit");
    expect(matchers).toContain("Read");
  });

  test("merges into existing settings without overwriting", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();
    const existing = {
      permissions: { deny: ["/secret/**"] },
      hooks: {
        PreToolUse: [
          { matcher: "WebFetch", hooks: [{ type: "command", command: "my-hook" }] },
        ],
      },
    };
    fm.seed(SETTINGS_PATH, JSON.stringify(existing));

    const result = await installHooksStep(fm, cons, CLAUDE_DIR);

    expect(result.status).toBe("ok");
    const [, content] = fm.written[0] ?? ["", ""];
    const settings = JSON.parse(content) as Record<string, unknown>;

    // Existing deny permissions preserved
    const permissions = settings.permissions as { deny: string[] };
    expect(permissions.deny).toEqual(["/secret/**"]);

    // Existing matcher preserved
    const ptus = (settings.hooks as Record<string, unknown>).PreToolUse as Array<{
      matcher: string;
    }>;
    expect(ptus.some((e) => e.matcher === "WebFetch")).toBe(true);
    expect(ptus.some((e) => e.matcher === "Bash")).toBe(true);
  });

  test("idempotent on re-run — does not duplicate hooks", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    // First run
    await installHooksStep(fm, cons, CLAUDE_DIR);
    const [, firstContent] = fm.written[0] ?? ["", ""];

    // Second run uses the output from first run
    const fm2 = new FakeFileManager();
    fm2.seed(SETTINGS_PATH, firstContent);
    const cons2 = new FakeConsole();

    await installHooksStep(fm2, cons2, CLAUDE_DIR);
    const [, secondContent] = fm2.written[0] ?? ["", ""];

    const first = JSON.parse(firstContent) as Record<string, unknown>;
    const second = JSON.parse(secondContent) as Record<string, unknown>;
    const firstPtus = (first.hooks as Record<string, unknown>).PreToolUse as unknown[];
    const secondPtus = (second.hooks as Record<string, unknown>)
      .PreToolUse as unknown[];

    expect(secondPtus).toHaveLength(firstPtus.length);
    expect(secondContent).toBe(firstContent);
  });

  test("logs info message on success", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    await installHooksStep(fm, cons, CLAUDE_DIR);

    expect(cons.infos).toHaveLength(1);
    expect(cons.infos[0]).toContain("~/.claude/settings.json");
  });

  test("returns error when fileManager throws", async () => {
    const fm = makeFailingFileManager();
    const cons = new FakeConsole();

    const result = await installHooksStep(fm, cons, CLAUDE_DIR);

    expect(result.status).toBe("error");
    if (result.status === "error") {
      expect(result.message).toContain("disk full");
    }
  });

  test("handles invalid JSON in existing file gracefully by starting fresh", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();
    fm.seed(SETTINGS_PATH, "{ invalid json }");

    const result = await installHooksStep(fm, cons, CLAUDE_DIR);

    // Invalid JSON is caught — merges from scratch with empty settings
    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === SETTINGS_PATH);
    expect(written).toBeDefined();
    const output = JSON.parse(written?.[1] ?? "{}");
    expect(output.hooks?.PreToolUse).toHaveLength(3);
  });
});
