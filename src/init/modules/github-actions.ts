import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import { setupCiStep } from "@/steps/setup-ci";

export const githubActionsModule: InitModule = {
  id: "github-actions",
  name: "GitHub Actions",
  description: "Write .github/workflows/ai-guardrails.yml CI workflow",
  category: "ci",
  defaultEnabled: true,
  disableFlag: "--no-ci",

  async detect(ctx: InitContext): Promise<boolean> {
    return ctx.fileManager.exists(join(ctx.projectDir, ".git"));
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const languageIds = new Set(ctx.languages.map((l) => l.id));
    const result = await setupCiStep(ctx.projectDir, ctx.fileManager, languageIds);

    if (result.status === "error") {
      return { status: "error", message: result.message };
    }

    return {
      status: "ok",
      message: result.message,
      filesCreated: [".github/workflows/ai-guardrails.yml"],
    };
  },
};
