import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parse as parseToml } from "smol-toml";
import { protectRead, protectWrite } from "@/check/builder-path";
import { COMMAND_RULES } from "@/check/rules/commands";
import { DEFAULT_PATH_RULES } from "@/check/rules/paths";
import type { HooksConfig, RuleSet } from "@/check/types";
import { ProjectConfigSchema } from "@/config/schema";

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
  try {
    const configPath = join(process.cwd(), ".ai-guardrails", "config.toml");
    const text = await readFile(configPath, "utf8");
    const raw = parseToml(text);
    const config = ProjectConfigSchema.parse(raw);
    const hooks = config.hooks;
    if (hooks === undefined) return {};
    return {
      ...(hooks.managed_files !== undefined && { managedFiles: hooks.managed_files }),
      ...(hooks.managed_paths !== undefined && { managedPaths: hooks.managed_paths }),
      ...(hooks.protected_read_paths !== undefined && {
        protectedReadPaths: hooks.protected_read_paths,
      }),
    };
  } catch {
    return {};
  }
}
