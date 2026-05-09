// dangerous-cmd hook — walking-skeleton dogfood of @questi0nm4rk/hook-kit.
// AG's existing rule definitions are translated to hook-kit modules at
// runtime (see check/to-hook-kit.ts), then evaluated by hook-kit's engine.
// The `isDangerous(command)` signature is preserved so the BDD step files
// that call it directly keep working.

import { type HookEvent, evaluate as hkEvaluate } from "@questi0nm4rk/hook-kit";
import { toHookOutput } from "@/check/output";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { toCommandModule, toPathModules } from "@/check/to-hook-kit";
import type { CheckResult } from "@/check/types";
import { readHookInput } from "@/hooks/runner";
import { extractBashCommand } from "@/hooks/types";

/** Map a hook-kit Decision back to AG's CheckResult so callers (incl. BDD
 *  steps) keep their existing assertion shapes. */
function fromHookKit(decision: Awaited<ReturnType<typeof hkEvaluate>>): CheckResult {
  if (decision === null) return { decision: "allow" };
  if (decision.kind === "deny") return { decision: "deny", reason: decision.reason };
  if (decision.kind === "escalate") return { decision: "ask", reason: decision.reason };
  // context — not produced by command/pipe/redirect rules in this path
  return { decision: "allow" };
}

function bashEvent(command: string): HookEvent {
  return {
    eventName: "PreToolUse",
    sessionId: "ag-dangerous-cmd",
    cwd: process.cwd(),
    transcriptPath: "",
    toolName: "Bash",
    toolInput: { command },
    raw: {},
  };
}

export async function isDangerous(command: string): Promise<CheckResult | null> {
  const config = await loadHookConfig();
  const ruleset = buildRuleSet(config);
  const modules = [
    toCommandModule(ruleset.commandRules, "[dangerous-cmd]"),
    ...toPathModules(ruleset.pathRules, "[dangerous-cmd]"),
  ];
  const decision = await hkEvaluate(bashEvent(command), modules);
  const result = fromHookKit(decision);
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
