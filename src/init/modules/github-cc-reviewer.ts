import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const githubCcReviewerModule: InitModule = {
  id: "github-cc-reviewer",
  name: "CodeRabbit AI Reviewer",
  description:
    "Add .coderabbit.yaml to enable AI-powered PR reviews (free for open source)",
  category: "github",
  defaultEnabled: true,
  disableFlag: "--no-reviewer",
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
