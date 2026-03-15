import { callRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

export const gitDestructiveGroup: RuleGroup = {
  id: "git-destructive",
  name: "Git destructive operations",
  commandRules: [
    callRule("git", {
      sub: "reset",
      flags: ["--hard"],
      reason: "git reset --hard",
    }),
    callRule("git", {
      sub: "checkout",
      hasDdash: true,
      reason: "git checkout -- (discard working tree changes)",
    }),
    callRule("git", {
      sub: "restore",
      hasDdash: true,
      reason: "git restore -- (discard working tree changes)",
    }),
    callRule("git", {
      sub: "clean",
      flags: ["--force"],
      reason: "git clean --force",
    }),
    callRule("git", {
      sub: "branch",
      flags: ["--delete", "--force"],
      reason: "git branch --delete --force (force delete)",
    }),
  ],
  denyGlobs: [
    "Bash(git reset --hard*)",
    "Bash(git checkout -- *)",
    "Bash(git restore -- *)",
    "Bash(git clean -f*)",
    "Bash(git clean --force*)",
    "Bash(git branch -D *)",
    "Bash(git branch --delete --force *)",
  ],
};
