import { protectRead, protectWrite } from "@/check/builder-path";
import { COMMAND_RULES } from "@/check/rules/commands";
import { DEFAULT_PATH_RULES } from "@/check/rules/paths";
import type { HooksConfig, RuleSet } from "@/check/types";

export function buildRuleSet(config: HooksConfig): RuleSet {
  const extraPathRules = [
    ...(config.managedFiles ?? []).map((f) =>
      protectWrite(new RegExp(`${escapeRegExp(f)}$`), `Writing to managed file: ${f}`)
    ),
    ...(config.managedPaths ?? []).map((p) =>
      protectWrite(new RegExp(escapeRegExp(p)), `Writing to managed path: ${p}`)
    ),
    ...(config.protectedReadPaths ?? []).map((p) =>
      protectRead(new RegExp(escapeRegExp(p)), `Reading protected path: ${p}`)
    ),
  ];

  return {
    commandRules: COMMAND_RULES,
    pathRules: [...DEFAULT_PATH_RULES, ...extraPathRules],
  };
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export async function loadHookConfig(): Promise<HooksConfig> {
  return {};
}
