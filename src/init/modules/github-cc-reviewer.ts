import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

const CONFIG_PATH = ".coderabbit.yaml";

const CODERABBIT_YAML = `# ai-guardrails managed — CodeRabbit AI reviewer config
language: "en-US"
tone_instructions: ""
early_access: false
enable_free_tier: true
reviews:
  profile: "auto"           # auto | chill | assertive
  request_changes_workflow: false
  high_level_summary: true
  poem: false
  review_status: true
  collapse_walkthrough: false
  auto_review:
    enabled: true
    drafts: false
    base_branches: ["main"]
chat:
  auto_reply: true
`;

export const githubCcReviewerModule: InitModule = {
  id: "github-cc-reviewer",
  name: "CodeRabbit AI Reviewer",
  description:
    "Add .coderabbit.yaml to enable AI-powered PR reviews (free for open source)",
  category: "github",
  defaultEnabled: true,
  disableFlag: "--no-reviewer",

  async detect(ctx: InitContext): Promise<boolean> {
    const hasGit = await ctx.fileManager.exists(join(ctx.projectDir, ".git"));
    if (!hasGit) return false;
    if (ctx.github === undefined) return false;
    return ctx.github.authenticated;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    if (ctx.github === undefined) {
      return {
        status: "skipped",
        message: "No GitHub repo detected — skipping CodeRabbit configuration",
      };
    }

    if (!ctx.github.authenticated) {
      return {
        status: "skipped",
        message: "Not authenticated with GitHub — run `gh auth login` then re-run init",
      };
    }

    const fullPath = join(ctx.projectDir, CONFIG_PATH);

    const alreadyExists = await ctx.fileManager.exists(fullPath);
    if (alreadyExists) {
      return {
        status: "skipped",
        message: `${CONFIG_PATH} already exists — skipping to preserve your configuration`,
      };
    }

    await ctx.fileManager.writeText(fullPath, CODERABBIT_YAML);

    return {
      status: "ok",
      message: `Created ${CONFIG_PATH} — CodeRabbit will auto-install on first PR open`,
      filesCreated: [CONFIG_PATH],
    };
  },
};
