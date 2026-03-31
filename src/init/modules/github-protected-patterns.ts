import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import { parseWorkflowJobNames } from "@/utils/parse-workflow-jobs";

const DEFAULT_PATTERNS = ["release/*"];

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

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    if (ctx.github === undefined) {
      return {
        status: "skipped",
        message: "No GitHub repo detected — skipping protected patterns",
      };
    }

    if (!ctx.github.authenticated) {
      return {
        status: "skipped",
        message: "Not authenticated with GitHub — run `gh auth login` then re-run init",
      };
    }

    const { owner, repo } = ctx.github;
    const jobNames = await parseWorkflowJobNames(ctx.projectDir, ctx.fileManager);

    const apiArgs = buildRulesetArgs(owner, repo, DEFAULT_PATTERNS, jobNames);
    const result = await ctx.commandRunner.run(apiArgs, { cwd: ctx.projectDir });

    if (result.exitCode !== 0) {
      const stderr = result.stderr.toLowerCase();

      if (
        stderr.includes("not authenticated") ||
        stderr.includes("401") ||
        stderr.includes("requires authentication")
      ) {
        return {
          status: "skipped",
          message:
            "GitHub authentication required — run `gh auth login` then re-run init",
        };
      }

      return {
        status: "error",
        message: `Failed to create branch ruleset: ${result.stderr.trim()}`,
      };
    }

    return {
      status: "ok",
      message: `Created repository ruleset for patterns: ${DEFAULT_PATTERNS.join(", ")}`,
    };
  },
};

function buildRulesetArgs(
  owner: string,
  repo: string,
  patterns: readonly string[],
  jobNames: readonly string[]
): string[] {
  const args = [
    "gh",
    "api",
    `repos/${owner}/${repo}/rulesets`,
    "--method",
    "POST",
    "--field",
    "name=ai-guardrails protected branches",
    "--field",
    "target=branch",
    "--field",
    "enforcement=active",
  ];

  for (const pattern of patterns) {
    args.push("--field", `conditions[ref_name][include][]=${pattern}`);
  }

  args.push(
    "--field",
    "rules[0][type]=pull_request",
    "--field",
    "rules[0][parameters][required_approving_review_count]=1",
    "--field",
    "rules[0][parameters][dismiss_stale_reviews_on_push]=true",
    "--field",
    "rules[0][parameters][require_last_push_approval]=false",
    "--field",
    "rules[1][type]=required_status_checks",
    "--field",
    "rules[1][parameters][strict_required_status_checks_policy]=true"
  );

  for (let i = 0; i < jobNames.length; i++) {
    const name = jobNames[i];
    if (name !== undefined) {
      args.push(
        "--field",
        `rules[1][parameters][required_status_checks][${i}][context]=${name}`
      );
    }
  }

  args.push(
    "--field",
    "rules[2][type]=non_fast_forward",
    "--field",
    "rules[3][type]=deletion",
    "--field",
    "rules[4][type]=required_conversation_resolution"
  );

  return args;
}
