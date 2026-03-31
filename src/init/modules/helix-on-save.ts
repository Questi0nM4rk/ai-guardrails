import { homedir } from "node:os";
import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const helixOnSaveModule: InitModule = {
  id: "helix-on-save",
  name: "Helix LSP On-Save",
  description: "Configure Helix LSP for on-save linting via .helix/languages.toml",
  category: "editor",
  defaultEnabled: true,
  disableFlag: "--no-helix",
  dependsOn: ["biome-config", "ruff-config"],

  async detect(ctx: InitContext): Promise<boolean> {
    const hasHelixConfig = await ctx.fileManager.exists(
      join(homedir(), ".config", "helix")
    );
    if (hasHelixConfig) return true;

    const result = await ctx.commandRunner.run(["hx", "--version"], {
      cwd: ctx.projectDir,
    });
    return result.exitCode === 0;
  },

  async execute(_ctx: InitContext): Promise<InitModuleResult> {
    return { status: "ok", message: "TODO: implement" };
  },
};
