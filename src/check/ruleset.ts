import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parse as parseToml } from "smol-toml";
import { recurseRule } from "@/check/builder-cmd";
import { protectRead, protectWrite } from "@/check/builder-path";
import { ALL_RULE_GROUPS, collectCommandRules } from "@/check/rules/groups";
import { DEFAULT_MANAGED_FILES, DEFAULT_PATH_RULES } from "@/check/rules/paths";
import type { HooksConfig, RuleSet } from "@/check/types";
import { ProjectConfigSchema } from "@/config/schema";
import { PROJECT_CONFIG_PATH } from "@/models/paths";

export function buildRuleSet(config: HooksConfig): RuleSet {
  const extraPathRules = [
    ...DEFAULT_MANAGED_FILES.map((f) =>
      protectWrite(
        new RegExp(`(?:^|/)${escapeRegExp(f)}$`), // nosemgrep: detect-non-literal-regexp — fully escaped via escapeRegExp; no ReDoS risk
        `Writing to managed file: ${f}`
      )
    ),
    ...(config.managedFiles ?? []).map((f) =>
      protectWrite(
        new RegExp(`(?:^|/)${escapeRegExp(f)}$`), // nosemgrep: detect-non-literal-regexp — fully escaped via escapeRegExp; no ReDoS risk
        `Writing to managed file: ${f}`
      )
    ),
    ...(config.managedPaths ?? []).map((p) =>
      // nosemgrep: detect-non-literal-regexp — input is fully escaped via escapeRegExp; no ReDoS risk
      protectWrite(new RegExp(escapeRegExp(p)), `Writing to managed path: ${p}`)
    ),
    ...(config.protectedReadPaths ?? []).map((p) =>
      // nosemgrep: detect-non-literal-regexp — input is fully escaped via escapeRegExp; no ReDoS risk
      protectRead(new RegExp(escapeRegExp(p)), `Reading protected path: ${p}`)
    ),
  ];

  return {
    commandRules: [recurseRule(), ...collectCommandRules(ALL_RULE_GROUPS)],
    pathRules: [...DEFAULT_PATH_RULES, ...extraPathRules],
  };
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export async function loadHookConfig(): Promise<HooksConfig> {
  try {
    const configPath = join(process.cwd(), PROJECT_CONFIG_PATH);
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
  } catch (e: unknown) {
    const isNotFound =
      e instanceof Error && "code" in e && (e as { code: unknown }).code === "ENOENT";
    if (!isNotFound) {
      process.stderr.write(`[ai-guardrails] config load error: ${String(e)}\n`);
    }
    return {};
  }
}
