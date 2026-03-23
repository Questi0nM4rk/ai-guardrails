import { join } from "node:path";
import { parse as parseToml, stringify as stringifyToml } from "smol-toml";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import { PROJECT_CONFIG_PATH } from "@/models/paths";
import { isPlainObject } from "@/utils/deep-merge";

function readNumber(flags: Record<string, unknown>, key: string): number | undefined {
  const val = flags[key];
  return typeof val === "number" ? val : undefined;
}

function readStringArray(
  flags: Record<string, unknown>,
  key: string
): string[] | undefined {
  const val = flags[key];
  if (!Array.isArray(val)) return undefined;
  const strings = val.filter((v): v is string => typeof v === "string");
  return strings.length > 0 ? strings : undefined;
}

export const configTuningModule: InitModule = {
  id: "config-tuning",
  name: "Config Tuning",
  description:
    "Update .ai-guardrails/config.toml with line_length, indent_width, ignore rules, ignore paths",
  category: "profile",
  defaultEnabled: true,
  dependsOn: ["profile-selection"],

  async detect(_ctx: InitContext): Promise<boolean> {
    return true;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const dest = join(ctx.projectDir, PROJECT_CONFIG_PATH);

    let existing: Record<string, unknown> = {};
    try {
      const text = await ctx.fileManager.readText(dest);
      const parsed: unknown = parseToml(text);
      existing = isPlainObject(parsed) ? parsed : {};
    } catch {
      // File may not exist yet — start fresh
    }

    const configSection = isPlainObject(existing.config) ? { ...existing.config } : {};

    const lineLength = readNumber(ctx.flags, "line_length");
    if (lineLength !== undefined) {
      configSection.line_length = lineLength;
    }

    const indentWidth = readNumber(ctx.flags, "indent_width");
    if (indentWidth !== undefined) {
      configSection.indent_width = indentWidth;
    }

    const updated: Record<string, unknown> = {
      ...existing,
      ...(Object.keys(configSection).length > 0 ? { config: configSection } : {}),
    };

    const ignoreRules = readStringArray(ctx.flags, "ignore_rules");
    if (ignoreRules !== undefined) {
      const existingIgnore = Array.isArray(existing.ignore) ? existing.ignore : [];
      const existingRuleSet = new Set(
        existingIgnore
          .filter(isPlainObject)
          .map((entry) => (typeof entry.rule === "string" ? entry.rule : null))
          .filter((r): r is string => r !== null)
      );
      const newEntries = ignoreRules
        .filter((rule) => !existingRuleSet.has(rule))
        .map((rule) => ({
          rule,
          reason: "user-configured at init",
        }));
      updated.ignore = [...existingIgnore, ...newEntries];
    }

    const ignorePaths = readStringArray(ctx.flags, "ignore_paths");
    if (ignorePaths !== undefined) {
      const existingPaths = Array.isArray(existing.ignore_paths)
        ? existing.ignore_paths.filter((v): v is string => typeof v === "string")
        : [];
      const existingPathSet = new Set(existingPaths);
      const newPaths = ignorePaths.filter((p) => !existingPathSet.has(p));
      updated.ignore_paths = [...existingPaths, ...newPaths];
    }

    try {
      await ctx.fileManager.writeText(dest, stringifyToml(updated));
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e);
      return { status: "error", message: `Failed to write config: ${message}` };
    }

    return {
      status: "ok",
      message: "Config tuning applied",
      filesModified: [PROJECT_CONFIG_PATH],
    };
  },
};
