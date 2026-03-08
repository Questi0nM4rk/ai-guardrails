import type { HookInput } from "@/hooks/types";

export async function readHookInput(): Promise<HookInput> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk as Buffer);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8")) as HookInput;
}

export function allow(): never {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "allow" },
    }),
  );
  process.exit(0);
}

export function deny(reason: string): never {
  process.stderr.write(`${reason}\n`);
  process.exit(2);
}
