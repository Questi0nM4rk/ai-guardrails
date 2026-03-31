import { homedir } from "node:os";
import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const nvimOnSaveModule: InitModule = {
  id: "nvim-on-save",
  name: "Neovim On-Save Linting",
  description:
    "Generate .nvim/conform.lua project-local config snippet for conform.nvim",

  category: "editor",
  defaultEnabled: false,
  disableFlag: "--no-nvim",
  dependsOn: ["biome-config", "ruff-config"],

  async detect(ctx: InitContext): Promise<boolean> {
    const hasNvimConfig = await ctx.fileManager.exists(
      join(homedir(), ".config", "nvim")
    );
    if (hasNvimConfig) return true;

    const result = await ctx.commandRunner.run(["nvim", "--version"], {
      cwd: ctx.projectDir,
    });
    return result.exitCode === 0;
  },

  async execute(_ctx: InitContext): Promise<InitModuleResult> {
    return { status: "ok", message: "TODO: implement" };
  },
};
