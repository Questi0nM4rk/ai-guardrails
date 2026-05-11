import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { HookEvent } from "@questi0nm4rk/hook-kit";
import { createModule, evaluate } from "@questi0nm4rk/hook-kit";
import { suppressCommentsRule } from "@/check/rules/suppress-comments";

const modules = [
  createModule(
    {
      id: "suppress-comments",
      name: "Suppress unjustified linter-disable comments",
      events: ["PostToolUse"],
      matchers: ["Edit", "Write", "NotebookEdit"],
    },
    [suppressCommentsRule()]
  ),
];

function tmpFile(contents: string, ext: string): string {
  const dir = mkdtempSync(join(tmpdir(), "ag-supp-"));
  const path = join(dir, `f${ext}`);
  writeFileSync(path, contents);
  return path;
}

function event(filePath: string, eventName: "PreToolUse" | "PostToolUse"): HookEvent {
  return {
    eventName,
    sessionId: "test",
    cwd: "/",
    transcriptPath: "",
    raw: {},
    toolName: "Edit",
    toolInput: { file_path: filePath },
  };
}

describe("suppressCommentsRule", () => {
  test("returns null on PreToolUse (only fires post)", async () => {
    const filePath = tmpFile("// @ts-ignore\n", ".ts"); // ai-guardrails-allow: ts-ignore "test fixture string, not a real suppression"
    expect(await evaluate(event(filePath, "PreToolUse"), modules)).toBeNull();
  });

  test("escalates on unjustified ts-ignore", async () => {
    const filePath = tmpFile(
      "const x = 1;\n// @ts-ignore\nconst y: string = 1 as any;\n", // ai-guardrails-allow: ts-ignore "test fixture string, not a real suppression"
      ".ts"
    );
    const decision = await evaluate(event(filePath, "PostToolUse"), modules);
    expect(decision).not.toBeNull();
    if (decision === null) return;
    expect(decision.kind).toBe("escalate");
    if (decision.kind !== "escalate") return;
    expect(decision.label).toBe("[suppress-comments]");
    expect(decision.reason).toContain("unjustified linter suppression");
  });

  test("returns null when allow-comment justifies the suppression", async () => {
    const filePath = tmpFile(
      `const x: any = 1; // @ts-ignore // ai-guardrails-allow: ts-ignore "third-party type"\n`,
      ".ts"
    );
    expect(await evaluate(event(filePath, "PostToolUse"), modules)).toBeNull();
  });

  test("returns null for unknown extensions", async () => {
    const filePath = tmpFile("// noqa\n", ".unknown");
    expect(await evaluate(event(filePath, "PostToolUse"), modules)).toBeNull();
  });

  test("returns null when file is missing", async () => {
    expect(
      await evaluate(event("/nonexistent/file.ts", "PostToolUse"), modules)
    ).toBeNull();
  });
});
