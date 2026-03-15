import { evaluate } from "@/check/engine";
import { toHookOutput } from "@/check/output";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import type { CheckResult } from "@/check/types";
import { readHookInput } from "@/hooks/runner";
import { extractBashCommand } from "@/hooks/types";

export async function isDangerous(command: string): Promise<CheckResult | null> {
  const config = await loadHookConfig();
  const ruleset = buildRuleSet(config);
  const result = await evaluate({ type: "bash", command }, ruleset);
  if (result.decision === "allow") return null;
  return result;
}

export async function runDangerousCmd(): Promise<never> {
  const input = await readHookInput();
  const command = extractBashCommand(input.tool_input);
  const result = await isDangerous(command);
  if (result !== null) {
    toHookOutput(result, "dangerous-cmd");
  }
  process.exit(0);
}
