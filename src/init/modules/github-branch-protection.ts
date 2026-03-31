import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const githubBranchProtectionModule: InitModule = {
  id: "github-branch-protection",
  name: "GitHub Branch Protection",
  description: "Enforce PRs, CI checks, and code review before merging to main",
  category: "github",
  defaultEnabled: true,
  disableFlag: "--no-branch-protection",
  dependsOn: ["github-actions"],

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
