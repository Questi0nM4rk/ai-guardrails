import { evaluate } from "@/check/engine";
import { toHookOutput } from "@/check/output";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { readHookInput } from "@/hooks/runner";
import { extractBashCommand } from "@/hooks/types";

export async function isDangerous(command: string): Promise<string | null> {
  const config = await loadHookConfig();
  const ruleset = buildRuleSet(config);
  const result = await evaluate({ type: "bash", command }, ruleset);
  if (result.decision === "allow") return null;
  return result.reason;
}

export async function runDangerousCmd(): Promise<never> {
  const input = await readHookInput();
  const command = extractBashCommand(input.tool_input);
  const config = await loadHookConfig();
  const ruleset = buildRuleSet(config);
  const result = await evaluate({ type: "bash", command }, ruleset);
  toHookOutput(result, "dangerous-cmd");
}
