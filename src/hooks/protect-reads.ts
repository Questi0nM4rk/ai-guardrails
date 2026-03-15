import { evaluate } from "@/check/engine";
import { toHookOutput } from "@/check/output";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { readHookInput } from "@/hooks/runner";

export async function runProtectReads(): Promise<never> {
  const input = await readHookInput();
  const toolName = input.tool_name;

  if (toolName === "Read") {
    const rawPath = input.tool_input.file_path;
    const path = typeof rawPath === "string" ? rawPath : "";
    const config = await loadHookConfig();
    const ruleset = buildRuleSet(config);
    const result = await evaluate({ type: "read", path }, ruleset);
    toHookOutput(result, "protect-reads");
  }

  process.exit(0);
}
