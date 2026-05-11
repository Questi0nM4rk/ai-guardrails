// End-to-end smoke test for the compiled ai-guardrails-hk-cc-tools binary.
// Skipped when the binary is missing (CI runs `bun run build:hk-cc` first).

import { describe, expect, test } from "bun:test";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const BIN = resolve(import.meta.dir, "..", "..", "dist", "ai-guardrails-hk-cc-tools");
const SKIP = !existsSync(BIN);

interface Decision {
  hookSpecificOutput?: {
    permissionDecision?: "allow" | "ask" | "deny";
    permissionDecisionReason?: string;
  };
}

async function fire(input: Record<string, unknown>) {
  const proc = Bun.spawn([BIN], {
    stdin: new Response(JSON.stringify(input)),
    stdout: "pipe",
    stderr: "pipe",
    env: { ...process.env, HOOK_KIT_ASKPASS: "" },
  });
  const [stdout, exitCode] = await Promise.all([
    new Response(proc.stdout).text(),
    proc.exited,
  ]);
  const decision: Decision = stdout.trim() === "" ? {} : JSON.parse(stdout);
  return { decision, exitCode };
}

const baseEvent = {
  hook_event_name: "PreToolUse",
  session_id: "t",
  cwd: "/tmp",
  transcript_path: "/tmp/x",
};

describe.skipIf(SKIP)("ai-guardrails-hk-cc-tools cc-tools adapter", () => {
  test("escalates git push --force as ask", async () => {
    const { decision } = await fire({
      ...baseEvent,
      tool_name: "Bash",
      tool_input: { command: "git push --force origin main" },
    });
    expect(decision.hookSpecificOutput?.permissionDecision).toBe("ask");
    expect(decision.hookSpecificOutput?.permissionDecisionReason).toContain(
      "[ai-guardrails]"
    );
  });

  test("approves harmless ls (no decision payload)", async () => {
    const { decision, exitCode } = await fire({
      ...baseEvent,
      tool_name: "Bash",
      tool_input: { command: "ls -la" },
    });
    expect(exitCode).toBe(0);
    expect(decision.hookSpecificOutput).toBeUndefined();
  });

  test("escalates write to .env as ask", async () => {
    const { decision } = await fire({
      ...baseEvent,
      tool_name: "Write",
      tool_input: { file_path: "/tmp/.env" },
    });
    expect(decision.hookSpecificOutput?.permissionDecision).toBe("ask");
    expect(decision.hookSpecificOutput?.permissionDecisionReason).toContain(".env");
  });

  test("escalates read of ~/.ssh/", async () => {
    const { decision } = await fire({
      ...baseEvent,
      tool_name: "Read",
      tool_input: { file_path: "/home/me/.ssh/id_rsa" },
    });
    expect(decision.hookSpecificOutput?.permissionDecision).toBe("ask");
  });
});
