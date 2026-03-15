import { callRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

export const GIT_WORKFLOW_GROUP: RuleGroup = {
  id: "git-workflow",
  label: "git workflow — commit hooks bypass, branch force delete",
  commandRules: [
    callRule("git", {
      sub: "commit",
      flags: ["--no-verify"],
      reason: "git commit --no-verify (bypasses hooks)",
    }),
    callRule("git", {
      sub: "branch",
      flags: ["--delete", "--force"],
      reason: "git branch force delete",
    }),
  ],
  denyGlobs: [
    "Bash(git commit --no-verify*)",
    "Bash(git commit -n *)",
    "Bash(git branch -D *)",
  ],
} as const;
