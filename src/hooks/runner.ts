import { z } from "zod";
import type { HookInput } from "@/hooks/types";

const hookInputSchema = z.object({
  session_id: z.string(),
  transcript_path: z.string(),
  cwd: z.string(),
  hook_event_name: z.string(),
  tool_name: z.string(),
  tool_input: z.record(z.unknown()),
});

export async function readHookInput(): Promise<HookInput> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk)));
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    process.stderr.write("ai-guardrails hook: invalid JSON on stdin\n");
    process.exit(2);
  }
  try {
    // Zod.parse() already returns the validated type; no cast needed.
    return hookInputSchema.parse(parsed);
  } catch {
    process.stderr.write("ai-guardrails hook: unexpected hook input shape\n");
    process.exit(2);
  }
}

export function allow(): never {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "allow",
      },
    })
  );
  process.exit(0);
}

export function ask(reason: string): never {
  process.stdout.write(JSON.stringify({ permissionDecision: "ask", reason }));
  process.exit(0);
}

export function deny(reason: string): never {
  process.stderr.write(`${reason}\n`);
  process.exit(2);
}
