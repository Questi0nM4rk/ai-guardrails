import { callRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

export const GIT_DESTRUCTIVE_GROUP: RuleGroup = {
  id: "git-destructive",
  label: "git destructive — reset, checkout, restore, clean",
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
      flags: ["-f"],
      reason: "git clean with force flag",
    }),
  ],
  denyGlobs: [
    "Bash(git reset --hard*)",
    "Bash(git checkout -- *)",
    "Bash(git restore -- *)",
    "Bash(git clean -f*)",
    "Bash(git clean --force*)",
  ],
} as const;
