import type { BashToolInput } from "@/hooks/types";
import { allow, deny, readHookInput } from "@/hooks/runner";

const BLOCKED_PATTERNS: RegExp[] = [
  /rm\s+-rf?\s+[^/\s]*\/?\s*$|rm\s+-rf\s+\//,
  /git\s+push\s+.*(?:--force(?!-with-lease)|-f\b)/,
  /git\s+reset\s+--hard/,
  /git\s+checkout\s+--/,
  /git\s+clean\s+-[a-z]*f/,
  /git\s+commit\s+.*--no-verify/,
];

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
  const bash = input.tool_input as unknown as BashToolInput;
  const reason = isDangerous(bash.command ?? "");
  if (reason !== null) {
    deny(reason);
  }
  allow();
}
