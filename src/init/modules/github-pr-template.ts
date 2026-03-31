import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const githubPrTemplateModule: InitModule = {
  id: "github-pr-template",
  name: "GitHub PR Template",
  description: "Create .github/pull_request_template.md for consistent PR descriptions",
  category: "github",
  defaultEnabled: true,
  disableFlag: "--no-pr-template",

  async detect(ctx: InitContext): Promise<boolean> {
    const hasGit = await ctx.fileManager.exists(join(ctx.projectDir, ".git"));
    if (!hasGit) return false;
    return ctx.github !== undefined;
  },

  async execute(_ctx: InitContext): Promise<InitModuleResult> {
    return { status: "ok", message: "TODO: implement" };
  },
};
