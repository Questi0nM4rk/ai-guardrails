import { readFile } from "node:fs/promises";
import { join } from "node:path";
import type { HookModule, Rule } from "@questi0nm4rk/hook-kit";
import { createModule, path, redirect } from "@questi0nm4rk/hook-kit";
import { parse as parseToml } from "smol-toml";
import { ALL_RULE_GROUPS, collectModules } from "@/check/rules/groups";
import {
  DEFAULT_MANAGED_FILES,
  defaultReadModule,
  defaultRedirectModule,
  defaultWriteModule,
} from "@/check/rules/paths";
import { ProjectConfigSchema } from "@/config/schema";
import { PROJECT_CONFIG_PATH } from "@/models/paths";
import { isEnoent } from "@/utils/errors";

const LABEL = "[ai-guardrails]";

export interface HooksConfig {
  managedFiles?: string[];
  managedPaths?: string[];
  protectedReadPaths?: string[];
  disabledGroups?: string[];
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function exactFileRegExp(file: string): RegExp {
  // nosemgrep: detect-non-literal-regexp // ai-guardrails-allow: semgrep/detect-non-literal-regexp "input fully escaped"
  return new RegExp(`(?:^|/)${escapeRegExp(file)}$`);
}

function literalRegExp(s: string): RegExp {
  // nosemgrep: detect-non-literal-regexp // ai-guardrails-allow: semgrep/detect-non-literal-regexp "input fully escaped"
  return new RegExp(escapeRegExp(s));
}

function dynamicWriteRules(config: HooksConfig): Rule[] {
  const writes: Rule[] = [];
  for (const file of DEFAULT_MANAGED_FILES) {
    writes.push(
      path(exactFileRegExp(file))
        .onWrite()
        .escalate(`Writing to managed file: ${file}`, LABEL)
    );
  }
  for (const file of config.managedFiles ?? []) {
    writes.push(
      path(exactFileRegExp(file))
        .onWrite()
        .escalate(`Writing to managed file: ${file}`, LABEL)
    );
  }
  for (const p of config.managedPaths ?? []) {
    writes.push(
      path(literalRegExp(p)).onWrite().escalate(`Writing to managed path: ${p}`, LABEL)
    );
  }
  return writes;
}

function dynamicRedirectRules(config: HooksConfig): Rule[] {
  const reds: Rule[] = [];
  for (const file of DEFAULT_MANAGED_FILES) {
    reds.push(
      redirect(exactFileRegExp(file)).escalate(
        `Redirect into managed file: ${file}`,
        LABEL
      )
    );
  }
  for (const file of config.managedFiles ?? []) {
    reds.push(
      redirect(exactFileRegExp(file)).escalate(
        `Redirect into managed file: ${file}`,
        LABEL
      )
    );
  }
  for (const p of config.managedPaths ?? []) {
    reds.push(
      redirect(literalRegExp(p)).escalate(`Redirect into managed path: ${p}`, LABEL)
    );
  }
  return reds;
}

function dynamicReadRules(config: HooksConfig): Rule[] {
  return (config.protectedReadPaths ?? []).map((p) =>
    path(literalRegExp(p)).onRead().escalate(`Reading protected path: ${p}`, LABEL)
  );
}

/** Build the full HookModule[] from project config — used by src/hooks.ts and
 *  the in-process helper. Filters disabled groups, composes default + dynamic
 *  path/redirect rules, returns one flat module list ready for hook-kit. */
export function buildAllModules(config: HooksConfig = {}): HookModule[] {
  const disabled = new Set(config.disabledGroups ?? []);
  const groupModules = collectModules(
    ALL_RULE_GROUPS.filter((g) => !disabled.has(g.id))
  );

  const writeRules = dynamicWriteRules(config);
  const redirectRules = dynamicRedirectRules(config);
  const readRules = dynamicReadRules(config);

  const dynamicModules: HookModule[] = [];
  if (writeRules.length > 0) {
    dynamicModules.push(
      createModule(
        {
          id: "ai-guardrails-paths-write-extra",
          name: "ai-guardrails dynamic write protection",
          events: ["PreToolUse"],
          matchers: ["Edit", "Write", "NotebookEdit"],
        },
        writeRules
      )
    );
  }
  if (redirectRules.length > 0) {
    dynamicModules.push(
      createModule(
        {
          id: "ai-guardrails-redirects-extra",
          name: "ai-guardrails dynamic redirect protection",
          events: ["PreToolUse"],
          matchers: ["Bash"],
        },
        redirectRules
      )
    );
  }
  if (readRules.length > 0) {
    dynamicModules.push(
      createModule(
        {
          id: "ai-guardrails-paths-read-extra",
          name: "ai-guardrails dynamic read protection",
          events: ["PreToolUse"],
          matchers: ["Read"],
        },
        readRules
      )
    );
  }

  return [
    ...groupModules,
    defaultWriteModule,
    defaultReadModule,
    defaultRedirectModule,
    ...dynamicModules,
  ];
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
    if (!isEnoent(e)) {
      process.stderr.write(`[ai-guardrails] config load error: ${String(e)}\n`);
    }
    return {};
  }
}
