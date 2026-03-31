import { homedir } from "node:os";
import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

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

  async execute(_ctx: InitContext): Promise<InitModuleResult> {
    return { status: "ok", message: "TODO: implement" };
  },
};
