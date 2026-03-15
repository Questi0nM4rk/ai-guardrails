import { evaluate } from "@/check/engine";
import { toHookOutput } from "@/check/output";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { readHookInput } from "@/hooks/runner";

export async function runProtectConfigs(): Promise<never> {
  const input = await readHookInput();
  const toolName = input.tool_name;
  // Bash events are handled by the dangerous-cmd hook, which includes redirect-to-protected-path
  // checks via checkRedirectsAgainstPathRules. protect-configs handles file write tools only.

  if (toolName === "Edit" || toolName === "Write" || toolName === "NotebookEdit") {
    const config = await loadHookConfig();
    const ruleset = buildRuleSet(config);
    const rawPath =
      input.tool_input.file_path ??
      input.tool_input.notebook_path ??
      input.tool_input.path;
    const path = typeof rawPath === "string" ? rawPath : "";
    const result = await evaluate({ type: "write", path }, ruleset);
    toHookOutput(result, "protect-configs");
  }

  process.exit(0);
}
