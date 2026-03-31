import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import type { JsonObject } from "@/utils/json-merge";
import { mergeWithoutOverwrite, readJsonObject } from "@/utils/json-merge";

export const vscodeOnSaveModule: InitModule = {
  id: "vscode-on-save",
  name: "VS Code On-Save Linting",
  description: "Configure VS Code to lint and format on save via .vscode/settings.json",
  category: "editor",
  defaultEnabled: true,
  disableFlag: "--no-vscode",
  dependsOn: ["biome-config", "ruff-config"],

  async detect(ctx: InitContext): Promise<boolean> {
    const hasVscodeDir = await ctx.fileManager.exists(join(ctx.projectDir, ".vscode"));
    if (hasVscodeDir) return true;

    const result = await ctx.commandRunner.run(["code", "--version"], {
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

    const vscodeDir = join(ctx.projectDir, ".vscode");
    await ctx.fileManager.mkdir(vscodeDir, { parents: true });

    // Build settings additions for detected languages only
    const settingsAdditions: JsonObject = {
      "editor.formatOnSave": true,
    };

    if (hasTs) {
      settingsAdditions["editor.codeActionsOnSave"] = {
        "source.fixAll.biome": "explicit",
        "source.organizeImports.biome": "explicit",
      };
      settingsAdditions["[typescript]"] = {
        "editor.defaultFormatter": "biomejs.biome",
      };
      settingsAdditions["[javascript]"] = {
        "editor.defaultFormatter": "biomejs.biome",
      };
      settingsAdditions["[json]"] = { "editor.defaultFormatter": "biomejs.biome" };
    }

    if (hasPython) {
      settingsAdditions["[python]"] = {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
      };
      settingsAdditions["python.linting.enabled"] = true;
      settingsAdditions["ruff.enable"] = true;
      settingsAdditions["ruff.fixAll"] = true;
      settingsAdditions["ruff.organizeImports"] = true;
    }

    // Deep merge: only add keys not already present in user's file
    const settingsPath = join(vscodeDir, "settings.json");
    const settingsExisted = await ctx.fileManager.exists(settingsPath);
    const existingSettings = await readJsonObject(settingsPath, ctx.fileManager);
    // undefined means the file exists but has malformed JSON — write fresh
    const baseSettings = existingSettings ?? {};
    const mergedSettings = mergeWithoutOverwrite(baseSettings, settingsAdditions);
    await ctx.fileManager.writeText(
      settingsPath,
      JSON.stringify(mergedSettings, null, 2)
    );

    // Build extensions recommendations for detected languages only
    const recommendations: string[] = [];
    if (hasTs) recommendations.push("biomejs.biome");
    if (hasPython) recommendations.push("charliermarsh.ruff");

    const extensionsPath = join(vscodeDir, "extensions.json");
    const extensionsExisted = await ctx.fileManager.exists(extensionsPath);
    const existingExtensions = await readJsonObject(extensionsPath, ctx.fileManager);
    // undefined means the file exists but has malformed JSON — write fresh
    const baseExtensions = existingExtensions ?? {};
    const existingRecs = Array.isArray(baseExtensions.recommendations)
      ? baseExtensions.recommendations.filter((r): r is string => typeof r === "string")
      : [];
    const mergedRecs = [
      ...existingRecs,
      ...recommendations.filter((r) => !existingRecs.includes(r)),
    ];
    const mergedExtensions = { ...baseExtensions, recommendations: mergedRecs };
    await ctx.fileManager.writeText(
      extensionsPath,
      JSON.stringify(mergedExtensions, null, 2)
    );

    const filesCreated: string[] = [];
    const filesModified: string[] = [];
    if (settingsExisted) {
      filesModified.push(".vscode/settings.json");
    } else {
      filesCreated.push(".vscode/settings.json");
    }
    if (extensionsExisted) {
      filesModified.push(".vscode/extensions.json");
    } else {
      filesCreated.push(".vscode/extensions.json");
    }

    return {
      status: "ok",
      message: ".vscode/settings.json and .vscode/extensions.json written",
      ...(filesCreated.length > 0 && { filesCreated }),
      ...(filesModified.length > 0 && { filesModified }),
    };
  },
};
