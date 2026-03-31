import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

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

  async execute(_ctx: InitContext): Promise<InitModuleResult> {
    return { status: "ok", message: "TODO: implement" };
  },
};
