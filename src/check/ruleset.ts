import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parse as parseToml } from "smol-toml";
import { recurseRule } from "@/check/builder-cmd";
import { protectRead, protectWrite } from "@/check/builder-path";
import { ALL_RULE_GROUPS, collectCommandRules } from "@/check/rules/groups";
import { DEFAULT_MANAGED_FILES, DEFAULT_PATH_RULES } from "@/check/rules/paths";
import type { CommandRule, HooksConfig, RuleSet } from "@/check/types";
import { ProjectConfigSchema } from "@/config/schema";
import { PROJECT_CONFIG_PATH } from "@/models/paths";
import { isEnoent } from "@/utils/errors";

export function buildRuleSet(config: HooksConfig): RuleSet {
  const disabled = new Set(config.disabledGroups ?? []);
  const activeGroups = ALL_RULE_GROUPS.filter((g) => !disabled.has(g.id));

  const commandRules: CommandRule[] = [
    recurseRule(), // always active regardless of disabled groups
    ...collectCommandRules(activeGroups),
  ];

  const extraPathRules = [
    ...DEFAULT_MANAGED_FILES.map((f) =>
      protectWrite(
        new RegExp(`(?:^|/)${escapeRegExp(f)}$`), // nosemgrep: detect-non-literal-regexp // ai-guardrails-allow: semgrep/detect-non-literal-regexp "input fully escaped via escapeRegExp; no ReDoS risk"
        `Writing to managed file: ${f}`
      )
    ),
    ...(config.managedFiles ?? []).map((f) =>
      protectWrite(
        new RegExp(`(?:^|/)${escapeRegExp(f)}$`), // nosemgrep: detect-non-literal-regexp // ai-guardrails-allow: semgrep/detect-non-literal-regexp "input fully escaped via escapeRegExp; no ReDoS risk"
        `Writing to managed file: ${f}`
      )
    ),
    ...(config.managedPaths ?? []).map((p) =>
      protectWrite(
        new RegExp(escapeRegExp(p)), // nosemgrep: detect-non-literal-regexp // ai-guardrails-allow: semgrep/detect-non-literal-regexp "input fully escaped via escapeRegExp; no ReDoS risk"
        `Writing to managed path: ${p}`
      )
    ),
    ...(config.protectedReadPaths ?? []).map((p) =>
      protectRead(
        new RegExp(escapeRegExp(p)), // nosemgrep: detect-non-literal-regexp // ai-guardrails-allow: semgrep/detect-non-literal-regexp "input fully escaped via escapeRegExp; no ReDoS risk"
        `Reading protected path: ${p}`
      )
    ),
  ];

  return {
    commandRules,
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
      ...(hooks.disabled_groups !== undefined && {
        disabledGroups: hooks.disabled_groups,
      }),
    };
  } catch (e: unknown) {
    // ENOENT is expected — no config file means use defaults.
    // Other errors (bad TOML, Zod mismatch, permissions) deserve a warning so
    // users know their custom config isn't active. This function is only called
    // from hook processes (not pipeline domain code), so stderr is acceptable.
    const isNotFound = isEnoent(e);
    if (!isNotFound) {
      process.stderr.write(`[ai-guardrails] config load error: ${String(e)}\n`);
    }
    return {};
  }
}
