import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const githubProtectedPatternsModule: InitModule = {
  id: "github-protected-patterns",
  name: "GitHub Protected Branch Patterns",
  description:
    "Apply branch protection rules to release/* and other named patterns via Rulesets API",
  category: "github",
  defaultEnabled: true,
  disableFlag: "--no-protected-patterns",
  dependsOn: ["github-branch-protection"],

  async detect(ctx: InitContext): Promise<boolean> {
    const hasGit = await ctx.fileManager.exists(join(ctx.projectDir, ".git"));
    if (!hasGit) return false;
    if (ctx.github === undefined) return false;
    return ctx.github.authenticated;
  },

  async execute(_ctx: InitContext): Promise<InitModuleResult> {
    return { status: "ok", message: "TODO: implement" };
  },
};
