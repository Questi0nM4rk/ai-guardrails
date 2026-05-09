// Hook entrypoint — delegates to hook-kit's claudeCodeAdapter.

import { evaluate as hkEvaluate, run } from "@questi0nm4rk/hook-kit";
import { claudeCodeAdapter } from "@questi0nm4rk/hook-kit/adapters/claude-code";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { buildAllModules, fromHookKit, synthesizeHookEvent } from "@/check/to-hook-kit";
import type { CheckResult } from "@/check/types";

const LABEL = "[ai-guardrails]";

async function loadModules() {
  return buildAllModules(buildRuleSet(await loadHookConfig()), LABEL);
}

/** Bash-only convenience used by BDD step files. */
export async function isDangerous(command: string): Promise<CheckResult | null> {
  const event = synthesizeHookEvent({ type: "bash", command }, "ag-isDangerous");
  const result = fromHookKit(await hkEvaluate(event, await loadModules()));
  return result.decision === "allow" ? null : result;
}

export async function runHookEvent(): Promise<never> {
  await run(await loadModules(), claudeCodeAdapter);
  process.exit(0);
}
