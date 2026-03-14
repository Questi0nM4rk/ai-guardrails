import { evaluate } from "@/check/engine";
import { toHookOutput } from "@/check/output";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { readHookInput } from "@/hooks/runner";

export async function runProtectConfigs(): Promise<never> {
  const input = await readHookInput();
  const toolName = input.tool_name;
  const config = await loadHookConfig();
  const ruleset = buildRuleSet(config);

  if (toolName === "Bash") {
    const command =
      typeof input.tool_input.command === "string" ? input.tool_input.command : "";
    const result = await evaluate({ type: "bash", command }, ruleset);
    toHookOutput(result, "protect-configs");
  }

  if (toolName === "Edit" || toolName === "Write" || toolName === "NotebookEdit") {
    const rawPath = input.tool_input.file_path ?? input.tool_input.path;
    const path = typeof rawPath === "string" ? rawPath : "";
    const result = await evaluate({ type: "write", path }, ruleset);
    toHookOutput(result, "protect-configs");
  }

  process.exit(0);
}
