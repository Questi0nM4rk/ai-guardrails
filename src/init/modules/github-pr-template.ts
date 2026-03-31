import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

const TEMPLATE_PATH = ".github/pull_request_template.md";

const PR_TEMPLATE = `## Summary

<!-- 1-3 bullet points describing what changed and why -->

## Test plan

<!-- Checklist of steps to verify the change works -->
- [ ]

## Notes

<!-- Anything reviewers should know: breaking changes, migration steps, known issues -->
`;

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

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const fullPath = join(ctx.projectDir, TEMPLATE_PATH);

    const alreadyExists = await ctx.fileManager.exists(fullPath);
    if (alreadyExists) {
      return {
        status: "skipped",
        message: `${TEMPLATE_PATH} already exists — skipping to preserve your template`,
      };
    }

    await ctx.fileManager.mkdir(join(ctx.projectDir, ".github"), { parents: true });
    await ctx.fileManager.writeText(fullPath, PR_TEMPLATE);

    return {
      status: "ok",
      message: `Created ${TEMPLATE_PATH}`,
      filesCreated: [TEMPLATE_PATH],
    };
  },
};
