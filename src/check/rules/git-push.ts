import { callRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

export const GIT_PUSH_GROUP: RuleGroup = {
  id: "git-push",
  label: "git push — force push without lease",
  commandRules: [
    callRule("git", {
      sub: "push",
      flags: ["--force"],
      noFlags: ["--force-with-lease"],
      reason: "git push --force without --force-with-lease",
    }),
  ],
  denyGlobs: [
    "Bash(git push --force)",
    "Bash(git push --force *)",
    "Bash(git push -f *)",
  ],
} as const;
