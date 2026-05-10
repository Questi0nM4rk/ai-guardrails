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

async function runHook(input: Record<string, unknown>): Promise<Output> {
  const proc = Bun.spawn(["bun", "run", CLI, "hook", "run"], {
    stdin: new Response(JSON.stringify(input)),
    stdout: "pipe",
    stderr: "pipe",
    // Don't let the subprocess pick up HOOK_KIT_ASKPASS from the test env;
    // unset askpass = harness-ask fallback, which is what we assert against.
    env: { ...process.env, HOOK_KIT_ASKPASS: "" },
  });
  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ]);
  return { stdout, stderr, exitCode };
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
    const parsed = JSON.parse(out.stdout) as {
      hookSpecificOutput?: {
        hookEventName?: string;
        permissionDecision?: string;
        permissionDecisionReason?: string;
      };
    };
    expect(parsed.hookSpecificOutput?.permissionDecision).toBe("ask");
    expect(parsed.hookSpecificOutput?.permissionDecisionReason).toContain(
      "[ai-guardrails]"
    );
    expect(parsed.hookSpecificOutput?.permissionDecisionReason).toContain(
      "git push --force"
    );
  });

  test("write to .env triggers a path-rule decision", async () => {
    const out = await runHook({
      ...baseEvent,
      tool_name: "Write",
      tool_input: { file_path: "/tmp/.env" },
    });
    expect(out.exitCode).toBe(0);
    const parsed = JSON.parse(out.stdout) as {
      hookSpecificOutput?: { permissionDecision?: string };
    };
    expect(parsed.hookSpecificOutput?.permissionDecision).toBe("ask");
  });

  test("read of /home/.../.ssh/ triggers a path-rule decision", async () => {
    const out = await runHook({
      ...baseEvent,
      tool_name: "Read",
      tool_input: { file_path: "/home/me/.ssh/id_rsa" },
    });
    expect(out.exitCode).toBe(0);
    const parsed = JSON.parse(out.stdout) as {
      hookSpecificOutput?: { permissionDecision?: string };
    };
    expect(parsed.hookSpecificOutput?.permissionDecision).toBe("ask");
  });

  test("misconfigured askpass denies (Iron Law 3 fail-closed)", async () => {
    const proc = Bun.spawn(["bun", "run", CLI, "hook", "run"], {
      stdin: new Response(
        JSON.stringify({
          ...baseEvent,
          tool_name: "Bash",
          tool_input: { command: "git push --force" },
        })
      ),
      stdout: "pipe",
      stderr: "pipe",
      env: { ...process.env, HOOK_KIT_ASKPASS: "/bin/false" },
    });
    const [stdout, exitCode] = await Promise.all([
      new Response(proc.stdout).text(),
      proc.exited,
    ]);
    expect(exitCode).toBe(0);
    const parsed = JSON.parse(stdout) as {
      hookSpecificOutput?: { permissionDecision?: string };
    };
    // Iron Law 3 exception: broker infra expected but broken → deny, not ask.
    expect(parsed.hookSpecificOutput?.permissionDecision).toBe("block");
  });
});
