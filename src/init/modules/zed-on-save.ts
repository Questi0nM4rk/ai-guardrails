import { homedir } from "node:os";
import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import type { JsonObject } from "@/utils/json-merge";
import {
  isJsonObject,
  mergeWithoutOverwrite,
  readJsonObject,
} from "@/utils/json-merge";

export const zedOnSaveModule: InitModule = {
  id: "zed-on-save",
  name: "Zed On-Save Formatting",
  description: "Configure Zed to format on save via .zed/settings.json",
  category: "editor",
  defaultEnabled: true,
  disableFlag: "--no-zed",
  dependsOn: ["biome-config", "ruff-config"],

  async detect(ctx: InitContext): Promise<boolean> {
    const hasZedConfig = await ctx.fileManager.exists(
      join(homedir(), ".config", "zed")
    );
    if (hasZedConfig) return true;

    const result = await ctx.commandRunner.run(["zed", "--version"], {
      cwd: ctx.projectDir,
    });
    return result.exitCode === 0;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const hasTs = ctx.languages.some((l) => l.id === "typescript");
    const hasPython = ctx.languages.some((l) => l.id === "python");

    if (!hasTs && !hasPython) {
      return { status: "skipped", message: "No supported languages detected" };
    }

    const zedDir = join(ctx.projectDir, ".zed");
    const settingsPath = join(zedDir, "settings.json");

    await ctx.fileManager.mkdir(zedDir, { parents: true });

    const languages: JsonObject = {};
    if (hasTs) {
      languages.TypeScript = {
        formatter: {
          external: {
            command: "biome",
            arguments: ["format", "--stdin-file-path", "{buffer_path}"],
          },
        },
      };
      languages.JavaScript = {
        formatter: {
          external: {
            command: "biome",
            arguments: ["format", "--stdin-file-path", "{buffer_path}"],
          },
        },
      };
    }

    if (hasPython) {
      languages.Python = {
        formatter: {
          external: {
            command: "ruff",
            arguments: ["format", "-"],
          },
        },
      };
    }

    const settingsExisted = await ctx.fileManager.exists(settingsPath);
    const rawExisting = await readJsonObject(settingsPath, ctx.fileManager);
    // undefined means the file exists but has malformed JSON — write fresh
    const existing = rawExisting ?? {};

    // Merge top-level keys without overwriting existing user values.
    const topLevelAdditions: JsonObject = {
      format_on_save: "on",
      formatter: "language_server",
    };
    const merged = mergeWithoutOverwrite(existing, topLevelAdditions);

    // Merge languages at 2 levels: preserve user's existing per-language configs,
    // but add any language keys we're introducing that aren't already present.
    const existingLanguages = isJsonObject(existing.languages)
      ? existing.languages
      : {};
    merged.languages = mergeWithoutOverwrite(existingLanguages, languages);
    await ctx.fileManager.writeText(settingsPath, JSON.stringify(merged, null, 2));

    return {
      status: "ok",
      message: ".zed/settings.json written",
      ...(settingsExisted
        ? { filesModified: [".zed/settings.json"] as const }
        : { filesCreated: [".zed/settings.json"] as const }),
    };
  },
};
