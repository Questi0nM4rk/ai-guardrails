import { describe, expect, test } from "bun:test";
import { type ClaudeSettings, mergeHooks } from "@/utils/merge-claude-settings";

const SAMPLE_HOOKS = [
  {
    matcher: "Bash",
    hooks: [{ type: "command", command: "ai-guardrails hook dangerous-cmd" }],
  },
  {
    matcher: "Edit|Write|NotebookEdit",
    hooks: [{ type: "command", command: "ai-guardrails hook protect-configs" }],
  },
] as const;

describe("mergeHooks", () => {
  test("merges hooks into empty settings", () => {
    const result = mergeHooks({}, SAMPLE_HOOKS);

    expect(result.hooks?.PreToolUse).toHaveLength(2);
    expect(result.hooks?.PreToolUse?.[0]?.matcher).toBe("Bash");
    expect(result.hooks?.PreToolUse?.[1]?.matcher).toBe("Edit|Write|NotebookEdit");
  });

  test("preserves existing hooks and adds new ones", () => {
    const existing: ClaudeSettings = {
      hooks: {
        PreToolUse: [
          {
            matcher: "WebFetch",
            hooks: [{ type: "command", command: "my-hook" }],
          },
        ],
      },
    };

    const result = mergeHooks(existing, SAMPLE_HOOKS);

    const ptus = result.hooks?.PreToolUse ?? [];
    expect(ptus).toHaveLength(3);
    expect(ptus.some((e) => e.matcher === "WebFetch")).toBe(true);
    expect(ptus.some((e) => e.matcher === "Bash")).toBe(true);
    expect(ptus.some((e) => e.matcher === "Edit|Write|NotebookEdit")).toBe(true);
  });

  test("deduplicates by command string", () => {
    const existing: ClaudeSettings = {
      hooks: {
        PreToolUse: [
          {
            matcher: "Bash",
            hooks: [{ type: "command", command: "ai-guardrails hook dangerous-cmd" }],
          },
        ],
      },
    };

    const result = mergeHooks(existing, SAMPLE_HOOKS);

    const bashEntry = result.hooks?.PreToolUse?.find((e) => e.matcher === "Bash");
    expect(bashEntry?.hooks).toHaveLength(1);
  });

  test("preserves unknown settings fields", () => {
    const existing: ClaudeSettings = {
      permissions: { deny: ["/etc/**"] },
      customField: "preserved",
      nested: { a: 1, b: 2 },
    };

    const result = mergeHooks(existing, SAMPLE_HOOKS);

    expect(result.permissions?.deny).toEqual(["/etc/**"]);
    expect(result.customField).toBe("preserved");
    expect(result.nested).toEqual({ a: 1, b: 2 });
  });

  test("merges new hooks into existing matcher without duplicating", () => {
    const existing: ClaudeSettings = {
      hooks: {
        PreToolUse: [
          {
            matcher: "Bash",
            hooks: [{ type: "command", command: "existing-cmd" }],
          },
        ],
      },
    };

    const incoming = [
      {
        matcher: "Bash",
        hooks: [
          { type: "command", command: "existing-cmd" },
          { type: "command", command: "new-cmd" },
        ],
      },
    ] as const;

    const result = mergeHooks(existing, incoming);

    const bashEntry = result.hooks?.PreToolUse?.find((e) => e.matcher === "Bash");
    expect(bashEntry?.hooks).toHaveLength(2);
    const commands = bashEntry?.hooks.map((h) => h.command) ?? [];
    expect(commands).toContain("existing-cmd");
    expect(commands).toContain("new-cmd");
  });

  test("returns empty PreToolUse array when both existing and incoming are empty", () => {
    const result = mergeHooks({}, []);

    expect(result.hooks?.PreToolUse).toEqual([]);
  });

  test("preserves existing hooks field keys beyond PreToolUse", () => {
    const existing: ClaudeSettings = {
      hooks: {
        PreToolUse: [],
        PostToolUse: [
          { matcher: "*", hooks: [{ type: "command", command: "post-hook" }] },
        ],
      },
    };

    const result = mergeHooks(existing, SAMPLE_HOOKS);

    expect((result.hooks as Record<string, unknown>).PostToolUse).toEqual([
      { matcher: "*", hooks: [{ type: "command", command: "post-hook" }] },
    ]);
  });
});
