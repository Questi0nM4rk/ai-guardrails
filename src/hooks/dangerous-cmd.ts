import { checkCommand } from "@/hooks/dangerous-patterns";
import { allow, deny, readHookInput } from "@/hooks/runner";
import { extractBashCommand } from "@/hooks/types";

export function isDangerous(command: string): string | null {
  const reason = checkCommand(command);
  return reason !== null ? `Blocked: ${reason}` : null;
}

export async function runDangerousCmd(): Promise<never> {
  const input = await readHookInput();
  const command = extractBashCommand(input.tool_input);
  const reason = isDangerous(command);
  if (reason !== null) {
    deny(`[dangerous-cmd] ${reason}`);
  }
  allow();
}
