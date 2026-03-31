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
    const existingSettings = await readJsonObject(settingsPath, ctx.fileManager);
    const mergedSettings = mergeWithoutOverwrite(existingSettings, settingsAdditions);
    await ctx.fileManager.writeText(
      settingsPath,
      JSON.stringify(mergedSettings, null, 2)
    );

    // Build extensions recommendations for detected languages only
    const recommendations: string[] = [];
    if (hasTs) recommendations.push("biomejs.biome");
    if (hasPython) recommendations.push("charliermarsh.ruff");

    const extensionsPath = join(vscodeDir, "extensions.json");
    const existingExtensions = await readJsonObject(extensionsPath, ctx.fileManager);
    const existingRecs = Array.isArray(existingExtensions.recommendations)
      ? existingExtensions.recommendations.filter(
          (r): r is string => typeof r === "string"
        )
      : [];
    const mergedRecs = [
      ...existingRecs,
      ...recommendations.filter((r) => !existingRecs.includes(r)),
    ];
    const mergedExtensions = mergeWithoutOverwrite(existingExtensions, {
      recommendations: mergedRecs,
    });
    await ctx.fileManager.writeText(
      extensionsPath,
      JSON.stringify(mergedExtensions, null, 2)
    );

    return {
      status: "ok",
      message: ".vscode/settings.json and .vscode/extensions.json written",
      filesCreated: [".vscode/settings.json", ".vscode/extensions.json"],
    };
  },
};
