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
    // Zod.parse() already returns the validated type; no cast needed.
    return hookInputSchema.parse(JSON.parse(Buffer.concat(chunks).toString("utf8")));
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

export function deny(reason: string): never {
    process.stderr.write(`${reason}\n`);
    process.exit(2);
}
