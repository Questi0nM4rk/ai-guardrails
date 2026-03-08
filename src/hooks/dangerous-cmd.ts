import { DANGEROUS_REGEX_PATTERNS } from "@/hooks/dangerous-patterns";
import { allow, deny, readHookInput } from "@/hooks/runner";
import { extractBashCommand } from "@/hooks/types";

const BLOCKED_PATTERNS: RegExp[] = DANGEROUS_REGEX_PATTERNS;

export function isDangerous(command: string): string | null {
    for (const pattern of BLOCKED_PATTERNS) {
        if (pattern.test(command)) {
            return `Blocked: command matches dangerous pattern: ${pattern.source}`;
        }
    }
    return null;
}

export async function runDangerousCmd(): Promise<never> {
    const input = await readHookInput();
    const command = extractBashCommand(input.tool_input);
    const reason = isDangerous(command);
    if (reason !== null) {
        deny(reason);
    }
    allow();
}
