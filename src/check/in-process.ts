import { evaluate as hkEvaluate } from "@questi0nm4rk/hook-kit";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { buildAllModules, fromHookKit, synthesizeHookEvent } from "@/check/to-hook-kit";
import type { CheckResult } from "@/check/types";

const LABEL = "[ai-guardrails]";

async function loadModules() {
  return buildAllModules(buildRuleSet(await loadHookConfig()), LABEL);
}

/** In-process Bash command evaluation for BDD steps and tests. */
export async function isDangerous(command: string): Promise<CheckResult | null> {
  const event = synthesizeHookEvent({ type: "bash", command }, "ag-isDangerous");
  const result = fromHookKit(await hkEvaluate(event, await loadModules()));
  return result.decision === "allow" ? null : result;
}
