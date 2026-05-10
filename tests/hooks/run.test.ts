// Subprocess-based smoke tests for the `hook run` entrypoint. Spawns the CLI
// via `bun run src/cli.ts` so we exercise the full claudeCodeAdapter wire path
// (stdin parse → hook-kit evaluate → adapter writeOutput) without depending on
// the compiled `dist/` binary.

import { describe, expect, test } from "bun:test";
import { resolve } from "node:path";

const CLI = resolve(import.meta.dir, "..", "..", "src", "cli.ts");

interface Output {
  stdout: string;
  stderr: string;
  exitCode: number;
}

interface ParsedDecision {
  hookSpecificOutput?: {
    hookEventName?: string;
    permissionDecision?: string;
    permissionDecisionReason?: string;
  };
}

async function runHook(
  input: Record<string, unknown>,
  envOverrides: Record<string, string> = {}
): Promise<Output> {
  const proc = Bun.spawn(["bun", "run", CLI, "hook", "run"], {
    stdin: new Response(JSON.stringify(input)),
    stdout: "pipe",
    stderr: "pipe",
    // Default: unset askpass so we exercise the harness-ask fallback. Tests
    // that want the broker-failure path override with HOOK_KIT_ASKPASS.
    env: { ...process.env, HOOK_KIT_ASKPASS: "", ...envOverrides },
  });
  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ]);
  return { stdout, stderr, exitCode };
}

function parseDecision(stdout: string): ParsedDecision {
  return JSON.parse(stdout) as ParsedDecision;
}

const baseEvent = {
  session_id: "t",
  transcript_path: "",
  cwd: "/tmp",
  hook_event_name: "PreToolUse",
};

describe("hook run — subprocess smoke", () => {
  test("safe bash command exits 0 silently", async () => {
    const out = await runHook({
      ...baseEvent,
      tool_name: "Bash",
      tool_input: { command: "ls -la" },
    });
    expect(out.exitCode).toBe(0);
    expect(out.stdout).toBe("");
  });

  test("dangerous bash command falls through to harness-ask", async () => {
    const out = await runHook({
      ...baseEvent,
      tool_name: "Bash",
      tool_input: { command: "git push --force" },
    });
    expect(out.exitCode).toBe(0);
    const decision = parseDecision(out.stdout).hookSpecificOutput;
    expect(decision?.permissionDecision).toBe("ask");
    expect(decision?.permissionDecisionReason).toContain("[ai-guardrails]");
    expect(decision?.permissionDecisionReason).toContain("git push --force");
  });

  test("write to .env triggers a path-rule decision", async () => {
    const out = await runHook({
      ...baseEvent,
      tool_name: "Write",
      tool_input: { file_path: "/tmp/.env" },
    });
    expect(out.exitCode).toBe(0);
    expect(parseDecision(out.stdout).hookSpecificOutput?.permissionDecision).toBe(
      "ask"
    );
  });

  test("read of /home/.../.ssh/ triggers a path-rule decision", async () => {
    const out = await runHook({
      ...baseEvent,
      tool_name: "Read",
      tool_input: { file_path: "/home/me/.ssh/id_rsa" },
    });
    expect(out.exitCode).toBe(0);
    expect(parseDecision(out.stdout).hookSpecificOutput?.permissionDecision).toBe(
      "ask"
    );
  });

  test("misconfigured askpass denies (Iron Law 3 fail-closed)", async () => {
    const out = await runHook(
      {
        ...baseEvent,
        tool_name: "Bash",
        tool_input: { command: "git push --force" },
      },
      { HOOK_KIT_ASKPASS: "/bin/false" }
    );
    expect(out.exitCode).toBe(0);
    // Iron Law 3 exception: broker infra expected but broken → deny, not ask.
    expect(parseDecision(out.stdout).hookSpecificOutput?.permissionDecision).toBe(
      "block"
    );
  });
});
