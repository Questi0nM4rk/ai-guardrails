import { callRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

export const gitForcePushGroup: RuleGroup = {
  id: "git-force-push",
  name: "Git force push",
  commandRules: [
    callRule("git", {
      sub: "push",
      flags: ["--force"],
      noFlags: ["--force-with-lease"],
      reason: "git push --force",
    }),
  ],
  denyGlobs: [
    "Bash(git push --force)",
    "Bash(git push --force *)",
    "Bash(git push -f *)",
  ],
};
