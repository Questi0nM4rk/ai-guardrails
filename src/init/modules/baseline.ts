import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import { snapshotStep } from "@/steps/snapshot-step";

export const baselineModule: InitModule = {
  id: "baseline",
  name: "Baseline",
  description: "Capture baseline snapshot of current lint issues",
  category: "baseline",
  defaultEnabled: true,
  disableFlag: "--no-baseline",
  dependsOn: [
    "profile-selection",
    "config-tuning",
    "ruff-config",
    "biome-config",
    "editorconfig",
    "markdownlint-config",
    "codespell-config",
    "lefthook",
    "claude-settings",
    "tool-install",
  ],

  async detect(_ctx: InitContext): Promise<boolean> {
    return true;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const result = await snapshotStep(
      ctx.projectDir,
      ctx.languages,
      ctx.config,
      ctx.commandRunner,
      ctx.fileManager
    );

    if (result.status === "error") {
      return { status: "error", message: result.message };
    }

    return {
      status: "ok",
      message: result.message,
    };
  },
};
