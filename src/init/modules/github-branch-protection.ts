import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import { parseWorkflowJobNames } from "@/utils/parse-workflow-jobs";

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

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    if (ctx.github === undefined) {
      return {
        status: "skipped",
        message: "No GitHub repo detected — skipping branch protection",
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

    const apiArgs = buildProtectionArgs(owner, repo, jobNames);
    const result = await ctx.commandRunner.run(apiArgs, { cwd: ctx.projectDir });

    if (result.exitCode !== 0) {
      const stderr = result.stderr.toLowerCase();

      if (stderr.includes("branch not found") || stderr.includes("404")) {
        return {
          status: "skipped",
          message:
            "Branch protection will be applied on first push to main (branch does not exist yet)",
        };
      }

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

      if (stderr.includes("free plan") || stderr.includes("billing")) {
        return {
          status: "skipped",
          message:
            "Branch protection on private repos requires a paid GitHub plan — skipping",
        };
      }

      return {
        status: "error",
        message: `Failed to set branch protection: ${result.stderr.trim()}`,
      };
    }

    const checksNote =
      jobNames.length > 0 ? `, required status checks: ${jobNames.join(", ")}` : "";

    return {
      status: "ok",
      message: `Branch protection set on main — required PRs, 1 approving review, dismiss stale reviews, no force-push${checksNote}`,
    };
  },
};

function buildProtectionArgs(
  owner: string,
  repo: string,
  jobNames: readonly string[]
): string[] {
  const args = [
    "gh",
    "api",
    `repos/${owner}/${repo}/branches/main/protection`,
    "--method",
    "PUT",
    "--field",
    "required_status_checks[strict]=true",
  ];

  for (const name of jobNames) {
    args.push("--field", `required_status_checks[contexts][]=${name}`);
  }

  args.push(
    "--field",
    "enforce_admins=false",
    "--field",
    "required_pull_request_reviews[required_approving_review_count]=1",
    "--field",
    "required_pull_request_reviews[dismiss_stale_reviews]=true",
    "--field",
    "restrictions=null",
    "--field",
    "allow_force_pushes=false",
    "--field",
    "allow_deletions=false",
    "--field",
    "required_conversation_resolution=true"
  );

  return args;
}
